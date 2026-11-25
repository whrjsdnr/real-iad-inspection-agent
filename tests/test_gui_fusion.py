"""GUI 추론 퓨전 계약(app.gui_fusion) 단위 테스트."""
import pytest

from app.gui_fusion import apply_fusion_contract, check_view_scores, verdict_rationale


def _contract(th=0.5, margin=0.01):
    return {
        "rtdetr_conf_threshold": 0.55,
        "hvq_threshold": 60.0,
        "weights": {"rtdetr": 0.7, "hvq": 0.3},
        "category_params": {
            "status": "CONFIGURED",
            "threshold": th,
            "margin": margin,
            "lookups": {
                # x=[0, 0.6, 1.0] / p=[0.1, 0.5, 0.9]
                "rtdetr": {"x": [0.0, 0.6, 1.0], "p": [0.1, 0.5, 0.9], "n": 3},
                # x=[0, 50, 100] / p=[0.2, 0.6, 0.8]
                "hvq": {"x": [0.0, 50.0, 100.0], "p": [0.2, 0.6, 0.8], "n": 3},
            },
        },
    }


def _views(rt, hvq):
    return ({f"C{i}": rt for i in range(1, 6)},
            {f"C{i}": hvq for i in range(1, 6)})


def test_configured_defect():
    vrt, vhvq = _views(0.99, 100.0)
    out = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract())
    assert out["status"] == "CONFIGURED"
    assert out["rtdetr_positive"] and out["hvq_positive"]
    # rt 0.99 → 0.5 + (0.39/0.4)*0.4 = 0.89 ; hvq 100 → 0.8
    assert out["rt_percentile"] == pytest.approx(0.89, abs=1e-6)
    assert out["hvq_percentile"] == pytest.approx(0.8, abs=1e-6)
    assert out["fusion_score"] == pytest.approx(0.7 * 0.89 + 0.3 * 0.8, abs=1e-6)
    assert out["verdict"] == "defect"
    assert out["binary_verdict"] == "defect"


def test_gate_zeroes_below_threshold():
    vrt, vhvq = _views(0.10, 100.0)  # rt 0.10 < 0.55 → 0
    out = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract())
    assert not out["rtdetr_positive"]
    assert out["rt"] == 0.0
    assert out["rt_percentile"] == pytest.approx(0.1, abs=1e-6)  # lookup 최솟값
    assert out["verdict"] == "normal"


def test_gate_zeroes_hvq_below_threshold():
    vrt, vhvq = _views(0.99, 30.0)  # hvq 30 < 60 → 0
    out = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract())
    assert out["rtdetr_positive"] and not out["hvq_positive"]
    assert out["hvq"] == 0.0
    assert out["hvq_percentile"] == pytest.approx(0.2, abs=1e-6)


def test_hold_band():
    # score가 TH와 margin 안에 들어오도록 hvq를 조정
    # rt 0.99 → 0.89 기여 0.623, 목표 score 0.5 → hvq_pct=(0.5-0.623)/0.3 → 음수라
    # th를 score에 맞춰 잡는 편이 간단
    vrt, vhvq = _views(0.99, 100.0)
    out = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract())
    score = out["fusion_score"]
    out2 = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                 view_hvq_max16=vhvq,
                                 contract=_contract(th=score, margin=0.01))
    assert out2["verdict"] == "hold"
    out3 = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                 view_hvq_max16=vhvq,
                                 contract=_contract(th=score + 0.5, margin=0.01))
    assert out3["verdict"] == "normal"
    assert out3["binary_verdict"] == "normal"


def test_product_agg_is_max_over_views():
    vrt = {"C1": 0.1, "C2": 0.7, "C3": 0.2, "C4": 0.3, "C5": 0.4}
    vhvq = {"C1": 10, "C2": 20, "C3": 90, "C4": 30, "C5": 40}
    out = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract())
    assert out["rtdetr_raw"] == 0.7
    assert out["hvq_max16"] == 90


def test_unconfigured_returns_raw_only():
    c = _contract()
    c["category_params"] = None
    vrt, vhvq = _views(0.99, 100.0)
    out = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=c)
    assert out["status"] == "UNCONFIGURED"
    assert out["verdict"] is None
    assert out["rtdetr_raw"] == 0.99


def test_missing_views_rejected():
    with pytest.raises(ValueError):
        check_view_scores({"C1": 0.1}, {"C1": 1.0})


def test_rationale_mentions_components():
    vrt, vhvq = _views(0.99, 100.0)
    out = apply_fusion_contract(item="toothbrush", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract())
    lines = verdict_rationale(out)
    text = "\n".join(lines)
    assert "RT-DETR" in text and "HVQ" in text and "TH" in text
    un = verdict_rationale({"status": "UNCONFIGURED"})
    assert "미확정" in un[0]


# ---------------------------------------------------------------- 계약 v2

V2_VERSION = "weighted-minmax-heatmap-mean-rt40-v1"


def _contract_v2(th=0.5, margin=0.01):
    return {
        "rtdetr_conf_threshold": 0.4,
        "hvq_threshold": 81.0,
        "weights": {"rtdetr": 0.7, "hvq": 0.3},
        "contract_version": V2_VERSION,
        "category_params": {
            "status": "CONFIGURED",
            "threshold": th,
            "margin": margin,
            "normalizers": {
                "rt_input": {"min": 0.2, "max": 1.0},
                "hv_input": {"min": 20.0, "max": 100.0},
            },
        },
    }


def test_v2_minmax_weighted_sum_and_verdict():
    vrt, vhvq = _views(0.9, 90.0)
    out = apply_fusion_contract(item="usb", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract_v2())
    assert out["contract_version"] == V2_VERSION
    assert out["status"] == "CONFIGURED"
    # rt (0.9-0.2)/0.8=0.875, hvq (90-20)/80=0.875 → 0.875
    assert out["rt_percentile"] == pytest.approx(0.875, abs=1e-6)
    assert out["hvq_percentile"] == pytest.approx(0.875, abs=1e-6)
    assert out["fusion_score"] == pytest.approx(0.875, abs=1e-6)
    assert out["verdict"] == "defect"


def test_v2_rt_prefilter_zeroes_below_04():
    vrt, vhvq = _views(0.39, 90.0)  # 0.4 미만 → rt_input 0
    out = apply_fusion_contract(item="usb", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract_v2())
    assert not out["rtdetr_positive"]
    assert out["rt"] == 0.0
    # (0-0.2)/0.8 = -0.25 (외삽 허용)
    assert out["rt_percentile"] == pytest.approx(-0.25, abs=1e-6)


def test_v2_hvq_not_gated_by_threshold():
    # hvq 30 < 81 이어도 연속 점수 그대로 min-max에 넣는다 (게이트 없음)
    vrt, vhvq = _views(0.9, 30.0)
    out = apply_fusion_contract(item="usb", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract_v2())
    assert not out["hvq_positive"]  # 부가 단일모델 참고값만 False
    assert out["hvq"] == 30.0
    assert out["hvq_percentile"] == pytest.approx((30 - 20) / 80, abs=1e-6)


def test_v2_extrapolation_beyond_range_allowed():
    vrt, vhvq = _views(1.0, 200.0)  # validation 범위 밖 외삽
    out = apply_fusion_contract(item="usb", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract_v2())
    assert out["rt_percentile"] == pytest.approx(1.0, abs=1e-6)
    assert out["hvq_percentile"] == pytest.approx((200 - 20) / 80, abs=1e-6)
    assert out["fusion_score"] > 1.0  # 클립 없음


def test_v2_hold_band_and_rationale():
    vrt, vhvq = _views(0.9, 90.0)
    out = apply_fusion_contract(item="usb", view_rt_raw=vrt,
                                view_hvq_max16=vhvq, contract=_contract_v2(th=0.875, margin=0.01))
    assert out["verdict"] == "hold"
    text = "\n".join(verdict_rationale(out))
    assert "heatmap_mean" in text and "min-max" in text and "외삽" in text
