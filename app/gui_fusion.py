"""GUI 추론의 퓨전 계약 적용 — 순수 파이썬 (백엔드·러너·테스트 공용).

계약 버전에 따라 두 체계를 지원한다.

구 계약 (max16/백분위 — fusion-max16-rt55-w70-30):
  - 제품 집계: C1~C5 max (rtdetr_raw, hvq_max16)
  - 게이트(postfilter): 성분 임계 미달 점수는 0으로
    rtdetr_positive = rtdetr_raw >= rtdetr_conf_threshold (0.55)
    hvq_positive    = hvq_max16   >= 품목별 hvq 임계값
  - 정규화: validation 카테고리 경험적 중간순위 백분위 lookup (선형 보간, 범위 밖 0/1)
  - 퓨전 점수: 0.7 * rt_percentile + 0.3 * hvq_percentile
  - 판정: |score - TH| <= margin → hold, 아니면 score >= TH → defect / normal

계약 v2 (weighted-minmax-heatmap-mean-rt40-v1, 운영 활성):
  - 제품 집계: C1~C5 max (rtdetr_raw, hvq heatmap_mean)
  - RT 게이트: rtdetr_raw < 0.4 이면 rt_input=0, HVQ는 게이트 없이 연속 mean 사용
  - 정규화: validation 품목별 min-max (외삽 허용, 클립 없음)
  - 퓨전 점수: 0.7 * rt_minmax + 0.3 * hvq_minmax
  - 판정: 구 계약과 동일 (TH=Val F1 최적 구간 중점, margin=F1 하락 0.005 이내)
"""
from __future__ import annotations

from fusion_calibration import percentile

EXPECTED_VIEWS = ("C1", "C2", "C3", "C4", "C5")


def check_view_scores(view_rt_raw: dict[str, float], view_hvq_max16: dict[str, float]) -> None:
    if set(view_rt_raw) != set(EXPECTED_VIEWS) or set(view_hvq_max16) != set(EXPECTED_VIEWS):
        raise ValueError(f"C1~C5 5개 시점 점수가 필요합니다: {sorted(view_rt_raw)}")


V2_CONTRACT_VERSION = "weighted-minmax-heatmap-mean-rt40-v1"


def _minmax(value: float, stats: dict) -> float:
    lo, hi = float(stats["min"]), float(stats["max"])
    if not hi > lo:
        raise ValueError("상수 validation min-max 범위는 거부됩니다")
    return (value - lo) / (hi - lo)


def apply_fusion_contract(
    *,
    item: str,
    view_rt_raw: dict[str, float],
    view_hvq_max16: dict[str, float],
    contract: dict,
) -> dict:
    """뷰 단위 원시 점수로 제품 퓨전 판정을 계산한다.

    contract = {
      "rtdetr_conf_threshold": float, "hvq_threshold": float,
      "weights": {"rtdetr": 0.7, "hvq": 0.3},
      "contract_version": "weighted-minmax-heatmap-mean-rt40-v1" | None,
      "category_params": {
        "threshold":..., "margin":...,
        "lookups": {...}                       # 구 계약(백분위)
        | "normalizers": {"rt_input": {...}, "hv_input": {...}}  # v2(min-max)
      } | None
    }
    """
    check_view_scores(view_rt_raw, view_hvq_max16)
    rt_raw = max(float(view_rt_raw[v]) for v in EXPECTED_VIEWS)
    hvq_raw = max(float(view_hvq_max16[v]) for v in EXPECTED_VIEWS)

    is_v2 = contract.get("contract_version") == V2_CONTRACT_VERSION
    rt_thr = float(contract["rtdetr_conf_threshold"])
    hvq_thr = float(contract["hvq_threshold"])
    rt_positive = rt_raw >= rt_thr
    hvq_positive = hvq_raw >= hvq_thr
    if is_v2:
        rt = rt_raw if rt_positive else 0.0
        hvq = hvq_raw  # 계약 v2: HVQ 게이트 없음 (연속 heatmap_mean)
    else:
        rt = rt_raw if rt_positive else 0.0
        hvq = hvq_raw if hvq_positive else 0.0

    out = {
        "item": item,
        "rtdetr_raw": rt_raw,
        "hvq_max16": hvq_raw,
        "rtdetr_conf_threshold": rt_thr,
        "hvq_threshold": hvq_thr,
        "rtdetr_positive": rt_positive,
        "hvq_positive": hvq_positive,
        "rt": rt,
        "hvq": hvq,
        "weights": dict(contract["weights"]),
        "contract_version": contract.get("contract_version"),
    }
    params = contract.get("category_params")
    if not params or params.get("status") != "CONFIGURED":
        out.update({"status": "UNCONFIGURED", "fusion_score": None,
                    "threshold": None, "margin": None,
                    "rt_percentile": None, "hvq_percentile": None,
                    "binary_verdict": None, "verdict": None})
        return out

    weights = contract["weights"]
    if is_v2:
        rt_pct = _minmax(rt, params["normalizers"]["rt_input"])
        hvq_pct = _minmax(hvq, params["normalizers"]["hv_input"])
    else:
        rt_pct = float(percentile([rt], params["lookups"]["rtdetr"])[0])
        hvq_pct = float(percentile([hvq], params["lookups"]["hvq"])[0])
    score = weights["rtdetr"] * rt_pct + weights["hvq"] * hvq_pct
    th = float(params["threshold"])
    margin = float(params["margin"])
    binary = "defect" if score >= th else "normal"
    verdict = "hold" if abs(score - th) <= margin else binary
    out.update({
        "status": "CONFIGURED",
        "fusion_score": round(score, 6),
        "threshold": th,
        "margin": margin,
        "rt_percentile": round(rt_pct, 6),
        "hvq_percentile": round(hvq_pct, 6),
        "binary_verdict": binary,
        "verdict": verdict,
    })
    return out


def verdict_rationale(product: dict) -> list[str]:
    """판정 근거 문장 — 결과 화면 '근거' 표시용."""
    if product.get("status") != "CONFIGURED":
        return ["품목별 퓨전 파라미터 미확정 — 원시 점수만 표시합니다."]
    is_v2 = product.get("contract_version") == V2_CONTRACT_VERSION
    if is_v2:
        lines = [
            f"C1~C5 최대 점수: RT-DETR {product['rtdetr_raw']:.4f} "
            f"(사전 임계 {product['rtdetr_conf_threshold']}), "
            f"HVQ heatmap_mean {product['hvq_max16']:.4f} (게이트 없음, 연속 점수)",
            f"RT 입력: {product['rt']:.4f} → min-max {product['rt_percentile']:.4f}, "
            f"HVQ 입력: {product['hvq']:.4f} → min-max {product['hvq_percentile']:.4f} "
            f"(가중합 0.7/0.3, validation 품목별 범위 — 외삽 허용)",
            f"퓨전 점수 {product['fusion_score']:.4f} vs 품목별 TH {product['threshold']} "
            f"± margin {product['margin']} → "
            f"{'보류 구간' if product['verdict'] == 'hold' else '판정 ' + product['binary_verdict']}",
        ]
        return lines
    lines = [
        f"C1~C5 최대 점수: RT-DETR {product['rtdetr_raw']:.4f} "
        f"(임계 {product['rtdetr_conf_threshold']}), "
        f"HVQ max_avgpool16 {product['hvq_max16']:.4f} "
        f"(임계 {product['hvq_threshold']})",
        f"게이트 후 점수: RT {product['rt']:.4f} → 백분위 {product['rt_percentile']:.4f}, "
        f"HVQ {product['hvq']:.4f} → 백분위 {product['hvq_percentile']:.4f} "
        f"(가중합 0.7/0.3)",
        f"퓨전 점수 {product['fusion_score']:.4f} vs 품목별 TH {product['threshold']} "
        f"± margin {product['margin']} → "
        f"{'보류 구간' if product['verdict'] == 'hold' else '판정 ' + product['binary_verdict']}",
    ]
    return lines
