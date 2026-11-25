"""metrics/fusion 단위 테스트 — 합성 20개 제품으로 기대값 검증.

  cd ~/agent && .venv/bin/pytest tests/test_metrics_fusion.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

import fusion  # noqa: E402
from migrate import migrate  # noqa: E402
import metrics  # noqa: E402
from fusion import ROIMapper  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(str(db_path))
    con.executescript("""
    CREATE TABLE inspection_attempts (
        attempt_id TEXT PRIMARY KEY, product_id TEXT, item TEXT, started_at TEXT,
        status TEXT, model_version TEXT, mapping_version TEXT,
        verdict TEXT, review_status TEXT, truth_label TEXT, processed_at TEXT);
    CREATE TABLE reviews (
        review_id TEXT PRIMARY KEY, product_id TEXT, item TEXT, part_id TEXT,
        camera_id TEXT, truth_label TEXT, review_state TEXT, reviewer TEXT,
        reason TEXT, reviewed_at TEXT, fp_fn TEXT, corrected_label TEXT);
    CREATE TABLE findings (
        finding_id TEXT PRIMARY KEY, view_id TEXT, product_id TEXT, item TEXT,
        camera_id TEXT, source TEXT, kind TEXT,
        bbox_x1 INT, bbox_y1 INT, bbox_x2 INT, bbox_y2 INT,
        score REAL, part_id TEXT, model_version TEXT, mapping_version TEXT,
        map_uri TEXT, meta_json TEXT);
    CREATE TABLE metrics_snapshots (
        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT, metric TEXT,
        definition_version TEXT, numerator INT, denominator INT, value REAL,
        reason TEXT, item TEXT, part_id TEXT, camera_id TEXT,
        date_from TEXT, date_to TEXT, model_version TEXT, mapping_version TEXT,
        computed_at TEXT);
    """)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(db_path))
    migrate(db_path)  # 신규 컬럼/테이블 가가 적용 (이미 존재핟면 무시)
    yield con, db_path
    con.close()


def _seed_20_products(con) -> None:
    """TP=8, FN=2, FP=2, TN=8, hold=3 (확정 집계에서 보류 제외 검증용)."""
    rows = []
    for i in range(10):  # truth defect
        verdict = "defect" if i < 8 else "normal"
        rows.append((f"a{i}", f"p{i}", "toothbrush", "t", "completed", "m1", "roi1",
                     verdict, "none", "defect", "2026-11-20T00:00:00"))
    for i in range(10, 20):  # truth normal
        verdict = "defect" if i < 12 else "normal"
        rows.append((f"a{i}", f"p{i}", "toothbrush", "t", "completed", "m1", "roi1",
                     verdict, "none", "normal", "2026-11-20T00:00:00"))
    for i in range(20, 23):  # hold
        rows.append((f"a{i}", f"p{i}", "toothbrush", "t", "completed", "m1", "roi1",
                     "hold", "none", "defect", "2026-11-20T00:00:00"))
    con.executemany(
        "INSERT INTO inspection_attempts VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()


def test_product_recall_fpr_f1_expected(db):
    con, _ = db
    _seed_20_products(con)
    m = metrics.product_metrics(item="toothbrush")
    assert m["tp"] == 8 and m["fn"] == 2 and m["fp"] == 2 and m["tn"] == 8
    assert m["hold"] == 3  # 보류는 확정 집계 제외, 별도 카운트
    assert m["product_recall"]["num"] == 8 and m["product_recall"]["den"] == 10
    assert m["product_recall"]["rate"] == pytest.approx(0.8)
    assert m["product_fpr"]["rate"] == pytest.approx(0.2)
    assert m["product_f1"]["num"] == 16 and m["product_f1"]["den"] == 20
    assert m["product_f1"]["rate"] == pytest.approx(0.8)


def test_denominator_zero_is_null(db):
    con, _ = db
    m = metrics.product_metrics(item="없는품목")
    assert m["product_recall"]["den"] == 0
    assert m["product_recall"]["rate"] is None


def test_suspect_counts_separate_from_confirmed(db):
    con, _ = db
    _seed_20_products(con)
    con.execute(
        "INSERT INTO reviews (review_id,product_id,item,part_id,camera_id,truth_label,review_state,reviewer,reason,reviewed_at,fp_fn,corrected_label) VALUES ('r1','p0','toothbrush','bristle','C1','defect',"
        "'pending','kim',NULL,'2026-11-21T00:00:00',NULL,NULL)")
    con.execute(
        "INSERT INTO reviews (review_id,product_id,item,part_id,camera_id,truth_label,review_state,reviewer,reason,reviewed_at,fp_fn,corrected_label) VALUES ('r2','p1','toothbrush','neck','C2','normal',"
        "'confirmed','kim',NULL,'2026-11-21T00:00:00','FP',NULL)")
    con.commit()
    s = metrics.suspect_counts()
    assert s["suspect_hold_count"] == 3
    assert s["suspect_pending_reviews"] == 1
    assert s["review_confirmed_count"] == 1


def test_snapshot_roundtrip(db):
    con, db_path = db
    _seed_20_products(con)
    metrics.compute_all(item="toothbrush", save=True)
    row = con.execute(
        "SELECT numerator, denominator, value FROM metrics_snapshots "
        "WHERE metric='product_recall'").fetchone()
    assert row == (8, 10, pytest.approx(0.8))


def test_fusion_rules_from_config():
    rules = {"both_positive": "defect", "both_negative": "normal",
             "disagree": "hold", "hvq_positive_only": "hold",
             "rtdetr_positive_only": "hold"}
    assert fusion.decide(True, True, rules) == "defect"
    assert fusion.decide(False, False, rules) == "normal"
    assert fusion.decide(True, False, rules) == "hold"
    assert fusion.decide(False, True, rules) == "hold"


def test_parse_view_filename_real_patterns():
    a = fusion.parse_view_filename("audiojack__0080_NG_HS_C1_20231023092901.jpg")
    assert a["item"] == "audiojack" and a["product_id"] == "audiojack_defect_0080"
    assert a["truth_label"] == "defect" and a["defect"] == "HS" and a["camera"] == "C1"
    b = fusion.parse_view_filename("toothbrush_0080_OK_C3_20231021132520.jpg")
    assert b["truth_label"] == "normal" and b["camera"] == "C3" and b["product_id"] == "toothbrush_normal_0080"
    c = fusion.parse_view_filename("plastic_nut_0120_NG_AK_C5_20231005.jpg")
    assert c["item"] == "plastic_nut" and c["camera"] == "C5"
    assert fusion.parse_view_filename("random_file.jpg") is None


def test_roi_mapper_unknown_fallback(tmp_path):
    cfg = tmp_path / "roi.json"
    cfg.write_text('{"version":"parts-roi-v1","items":{}}')
    mapper = ROIMapper(cfg)
    assert mapper.part_id("toothbrush", "C1", (0, 0, 10, 10)) == "unknown"


def test_aupro_no_gt_returns_reason(db):
    con, _ = db
    r = metrics.aupro()
    assert r["value"] is None and r["reason"] == "no_gt_mask"
