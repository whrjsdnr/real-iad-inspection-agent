"""퓨전 판정 규칙 — 설정 파일 기반 (코드 하드코딩 금지).

  - RT-DETR conf≥임계 박스 존재 → 불량 근거
  - HVQ 이상 점수≥임계값 → 이상 근거 (임계값: hvq_best.pt validation.threshold, 카테고리별)
  - 둘 다 양성 → 불량 / 둘 다 음성 → 정상 / 어느 하나만 양성 → 보류 (설정 가능)
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config" / "fusion.json"

FNAME_RE = re.compile(
    r"^(?P<cat>[a-z0-9_]+?)_+(?P<seq>\d+)_(?P<label>OK|NG)(?:_(?P<defect>[A-Z0-9]+))?_?(?P<cam>C[1-5])_"
)


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    return json.loads(Path(path).read_text())


def parse_view_filename(name: str) -> dict | None:
    m = FNAME_RE.match(name)
    if not m:
        return None
    d = m.groupdict()
    label = "defect" if d["label"] == "NG" else "normal"
    return {
        "item": d["cat"],
        "seq": d["seq"],
        # Real-IAD에서 동일 일련번호가 OK/NG 양쪽에 존재하므로 그룹을 ID에 포함
        # (예: audiojack_defect_0080 / audiojack_normal_0080은 서로 다른 제품)
        "product_id": f"{d['cat']}_{label}_{d['seq']}",
        "truth_label": label,
        "defect": d.get("defect"),
        "camera": d["cam"],
    }


def load_hvq_thresholds(checkpoint) -> dict[str, float]:
    """hvq_best.pt의 validation.threshold(카테고리별, 학습 검증 근거)를 임계값으로 사용."""
    import torch  # noqa: PLC0415

    ck = torch.load(str(checkpoint), map_location="cpu", weights_only=False)
    val = ck.get("validation") or {}
    out = {}
    for cat, v in val.items():
        if isinstance(v, dict) and "threshold" in v:
            out[cat] = float(v["threshold"])
    return out


def hvq_threshold(item: str, thresholds: dict[str, float], default: float) -> float:
    return thresholds.get(item, default)


def decide(rt_positive: bool, hvq_positive: bool, rules: dict) -> str:
    """퓨전 판정: rules = config['fusion']."""
    if rt_positive and hvq_positive:
        return rules["both_positive"]
    if not rt_positive and not hvq_positive:
        return rules["both_negative"]
    if rt_positive:
        return rules["rtdetr_positive_only"]
    return rules["hvq_positive_only"]


def fuse_product(rt_boxes: list, hvq_score: float, hvq_thr: float,
                 rtdetr_conf: float, rules: dict) -> dict:
    """제품 단위 퓨전. rt_boxes: [{'score':..}, ...] (conf 필터 전처리 안 된 원본)."""
    rt_positive = any(b.get("score", 0.0) >= rtdetr_conf for b in rt_boxes)
    hvq_positive = hvq_score >= hvq_thr
    return {
        "verdict": decide(rt_positive, hvq_positive, rules),
        "rt_positive": rt_positive,
        "hvq_positive": hvq_positive,
        "hvq_threshold": hvq_thr,
    }


def score_max16(pred) -> list[float]:
    """pred (B,1,H,W) → avgpool(16,stride1) 후 최대 (EvalImageMax 계열) 점수 리스트."""
    import torch  # noqa: PLC0415
    import torch.nn.functional as F  # noqa: PLC0415

    pooled = F.avg_pool2d(pred.float(), 16, stride=1).flatten(1).max(dim=1).values
    return [float(v) for v in pooled]


def merge_thresholds(checkpoint_thr: dict, calibrated_path: Path | None) -> tuple[dict, str]:
    """임계값 병합: 교정 파일(OK 분포 p99) > checkpoint validation > 기본값.
    반환: (item→threshold, 출처 설명)."""
    merged = dict(checkpoint_thr)
    source = "checkpoint_validation"
    if calibrated_path and Path(calibrated_path).exists():
        cal = json.loads(Path(calibrated_path).read_text())
        for item, v in cal.get("items", {}).items():
            merged[item] = float(v["threshold"])
        source = f"ok_distribution_p99({cal.get('score_variant', '?')}, n≈{cal.get('per_item')}/품목)"
    return merged, source


class ROIMapper:
    """parts_roi.json 기반 부위 매핑. 정의 없으면 'unknown'."""

    def __init__(self, cfg_path: Path):
        cfg = json.loads(Path(cfg_path).read_text())
        self.version = cfg["version"]
        self.items = cfg.get("items", {})

    def part_id(self, item: str, camera: str, bbox) -> str:
        rois = self.items.get(item, {}).get(camera)
        if not rois:
            return "unknown"
        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        best, best_area = None, None
        for part, (rx1, ry1, rx2, ry2) in rois:
            if rx1 <= cx <= rx2 and ry1 <= cy <= ry2:
                area = (rx2 - rx1) * (ry2 - ry1)
                if best_area is None or area < best_area:
                    best, best_area = part, area
        return best if best else "unknown"


# ---------------------------------------------------------------------------
# 도출된 퓨전 설정 기반 판정 (fusion_derived.json만 읽음 — 스펙)
# ---------------------------------------------------------------------------
DEFAULT_DERIVED = DEFAULT_CONFIG


def load_derived(path: Path | None = None) -> dict | None:
    """도출 설정을 읽는다. 없으면 None(레거시 규칙 폐백)."""
    p = Path(path) if path else DEFAULT_DERIVED
    if not p.exists():
        return None
    cfg = json.loads(p.read_text())
    return cfg if cfg.get("derived") and cfg.get("score_norm") else None


def _norm(v: float, s: dict) -> float:
    return (v - s["min"]) / (s["max"] - s["min"]) if s["max"] > s["min"] else 0.0


def fuse_product_derived(rt_view_confs: list[float], hvq_view_scores: list[float],
                         derived: dict) -> dict:
    """뷰 단위 점수들로 제품 판정.
    - 뷰 결합: w_rt*norm(rt_conf) + w_hvq*norm(hvq_score)
    - 제품 집계: derived.score_definition.product_agg (mean|max)
    - TH±margin: >= TH+margin → defect, <= TH-margin → normal, 사이 → hold
    """
    if not rt_view_confs or len(rt_view_confs) != len(hvq_view_scores):
        raise ValueError("Aligned nonempty view scores required")
    sd = derived["score_definition"]
    w = derived["weights"]
    stats = derived["score_norm"]
    comb = [w["rtdetr"] * _norm(float(r), stats["rt"])
            + w["hvq"] * _norm(float(h), stats["hvq"])
            for r, h in zip(rt_view_confs, hvq_view_scores)]
    score = math.fsum(comb) / len(comb) if sd["product_agg"] == "mean" else max(comb)
    d = derived["derived"]
    th, margin = d["th"], d["margin"]
    if abs(score - th) <= margin or math.isclose(abs(score - th), margin, rel_tol=0, abs_tol=math.ulp(max(abs(score), abs(th)))):
        verdict = "hold"
    else:
        verdict = "defect" if score > th else "normal"
    return {"verdict": verdict, "fusion_score": round(score, 5),
            "th": th, "margin": margin, "agg": sd["product_agg"],
            "view_combined": [round(c, 5) for c in comb]}


def fuse_product_calibrated(rt_view_confs, hvq_view_scores, *, item, config=None):
    """새 확정 계약의 운영 진입점. 파라미터 없는 품목은 자동 판정하지 않는다."""
    from fusion_calibration import finite, predict
    cfg = config or load_config()
    fitted = cfg.get("calibrated_parameters")
    if not fitted:
        raise ValueError("퓨전 파라미터 미확정: 검증된 Val 분할로 보정해야 합니다")
    expected = len(cfg["capture"]["expected_views"])
    if len(rt_view_confs) != expected or len(hvq_view_scores) != expected:
        raise ValueError("제품은 C1~C5 점수 5개씩 필요합니다")
    result = predict({"category": item, "product_id": "RUNTIME",
                      "hvq": float(finite(hvq_view_scores).max()),
                      "rtdetr": float(finite(rt_view_confs).max())}, fitted)
    if result["status"] != "CONFIGURED":
        raise ValueError(f"{item}: 품목별 TH/정규화 미확정")
    return result
