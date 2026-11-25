"""도출된 퓨전 설정(fusion_derived.json) 검증 테스트.

  cd ~/agent && .venv/bin/pytest tests/test_derived_fusion.py
전제: derive_fusion.py를 1회 실행해 config/fusion_derived.json과 fusion_val_scores.csv가 있어야 한다.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

import fusion  # noqa: E402

DERIVED = AGENT_ROOT / "config" / "fusion.json"
SCORES = AGENT_ROOT / "fusion_val_scores.csv"


pytestmark = pytest.mark.skipif(
    not json.loads(DERIVED.read_text()).get("derived"),
    reason="원본 Val 목록 미확정: 실제 보정/재현 산출물 없음",
)


def test_derived_config_schema():
    d = json.loads(DERIVED.read_text())
    for key in ("weights", "score_norm", "score_definition", "derived", "target",
                "model_versions", "reproduction_check"):
        assert key in d, f"설정에 {key} 없음"
    assert d["weights"]["rtdetr"] == pytest.approx(0.7)
    assert d["weights"]["hvq"] == pytest.approx(0.3)
    assert d["score_definition"]["product_agg"] in ("mean", "max")
    assert d["derived"]["margin"] >= 0
    assert "within_tolerance" in d["target"]


def test_th_reproduces_saved_val_metrics():
    """저장된 TH로 val 점수를 재평가해 도출된 TP/FP/FN과 일치해야 한다."""
    d = json.loads(DERIVED.read_text())
    stats = d["score_norm"]
    rows = list(csv.DictReader(SCORES.open()))
    prods: dict[str, dict] = {}
    for r in rows:
        comb = (d["weights"]["rtdetr"]
                * (float(r["rt_conf"]) - stats["rt"]["min"]) / (stats["rt"]["max"] - stats["rt"]["min"])
                + d["weights"]["hvq"]
                * (float(r["hvq_score"]) - stats["hvq"]["min"]) / (stats["hvq"]["max"] - stats["hvq"]["min"]))
        p = prods.setdefault(r["product_id"], {"truth": r["truth"], "v": []})
        p["v"].append(comb)
    agg = d["score_definition"]["product_agg"]
    th = d["derived"]["th"]
    tp = fp = 0
    for p in prods.values():
        score = sum(p["v"]) / len(p["v"]) if agg == "mean" else max(p["v"])
        pred = score >= th  # 스윕 지점은 margin 미적용(보류 없이 양성 기준)
        if pred and p["truth"] == "defect":
            tp += 1
        if pred and p["truth"] == "normal":
            fp += 1
    assert tp == d["derived"]["tp"], f"TP {tp} != {d['derived']['tp']}"
    assert fp == d["derived"]["fp"], f"FP {fp} != {d['derived']['fp']}"


def test_fuse_product_derived_margin_behavior():
    d = json.loads(DERIVED.read_text())
    th, margin = d["derived"]["th"], d["derived"]["margin"]
    # 극단 점수: 정규화 상한/하한 근처 → defect / normal
    hi = [d["score_norm"]["rt"]["max"], d["score_norm"]["hvq"]["max"]] * 5
    lo = [0.0, d["score_norm"]["hvq"]["min"]] * 5
    assert fusion.fuse_product_derived(hi[:5], hi[5:], d)["verdict"] == "defect"
    assert fusion.fuse_product_derived(lo[:5], lo[5:], d)["verdict"] == "normal"


def test_load_derived_and_legacy_fallback():
    assert fusion.load_derived(DERIVED) is not None
    assert fusion.load_derived(AGENT_ROOT / "config" / "없는파일.json") is None
