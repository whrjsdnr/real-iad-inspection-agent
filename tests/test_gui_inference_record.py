"""GUI 추론 DB 기록 및 조회 헬 테스트 (SQLite + monkeypatch)."""
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app import gui_inference
from app.models import Attempt, Finding, View


class _NoClose:
    def __init__(self, s):
        self.s = s

    def __enter__(self):
        return self.s

    def __exit__(self, *a):
        return False


def _fake_result():
    return {
        "ok": True,
        "item": "toothbrush",
        "product_id": "gui_toothbrush_x",
        "views": {
            "C1": {"camera_id": "C1", "width": 640, "height": 480,
                   "image_path": "/tmp/fake/C1.jpg",
                   "rtdetr_raw": 0.9, "hvq_mean": 40.0, "hvq_max16": 88.0,
                   "detections": [
                       {"bbox": [10.0, 20.0, 110.0, 220.0], "class_id": 3,
                        "class_name": "scratch", "score": 0.91},
                       {"bbox": [300.0, 310.0, 350.0, 360.0], "class_id": 7,
                        "class_name": "dent", "score": 0.62},
                   ],
                   "heatmap_png": "/tmp/fake/C1_hvqmap.png",
                   "map_npy": "/tmp/fake/C1_map.npy"},
            "C2": {"camera_id": "C2", "width": 640, "height": 480,
                   "image_path": "/tmp/fake/C2.jpg",
                   "rtdetr_raw": 0.0, "hvq_mean": 30.0, "hvq_max16": 55.0,
                   "detections": [],
                   "heatmap_png": "/tmp/fake/C2_hvqmap.png",
                   "map_npy": "/tmp/fake/C2_map.npy"},
        },
        "product": {"verdict": "defect", "fusion_score": 0.8},
    }


def test_record_result_marks_gui_source(seeded_session, monkeypatch):
    monkeypatch.setattr(gui_inference, "get_session",
                        lambda role="admin": _NoClose(seeded_session))
    info = gui_inference.record_result(
        _fake_result(), attempt_id="gui-test01",
        product_id="gui_toothbrush_x", item="toothbrush")
    assert info["recorded"] and info["model_version"] == gui_inference.GUI_MODEL_TAG

    attempt = seeded_session.get(Attempt, "gui-test01")
    assert attempt is not None
    assert attempt.model_version == "gui-fusion-v1"
    assert attempt.verdict == "defect"
    assert attempt.status == "completed"

    views = seeded_session.query(View).filter_by(attempt_id="gui-test01").all()
    assert {v.camera_id for v in views} == {"C1", "C2"}
    assert all(v.model_version == "gui-fusion-v1" for v in views)

    findings = (seeded_session.query(Finding)
                .filter_by(product_id="gui_toothbrush_x").all())
    assert len(findings) == 2
    assert all(f.source == "gui" and f.kind == "rtdetr_box" for f in findings)
    # ROI LUT 적용 (toothbrush C1 ROI에 따라 bristle/neck 중 하나 또는 unknown)
    assert {f.part_id for f in findings} <= {"bristle", "neck", "handle", "unknown"}
    # 메타에 클래스 근거
    import json as _json
    meta = _json.loads(findings[0].meta_json)
    assert "class_name" in meta


@pytest.fixture()
def ro_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    with engine.begin() as c:
        c.execute(text("CREATE TABLE inspection_attempts ("
                       "attempt_id TEXT PRIMARY KEY, product_id TEXT, item TEXT, "
                       "status TEXT)"))
        c.execute(text("CREATE TABLE inspection_views ("
                       "view_id TEXT PRIMARY KEY, attempt_id TEXT, product_id TEXT, "
                       "item TEXT, camera_id TEXT, image_uri TEXT, status TEXT)"))
        c.execute(text("INSERT INTO inspection_attempts VALUES "
                       "('a1','p_full','cap','completed'),"
                       "('a2','p_partial','cap','completed'),"
                       "('a3','p_fail','cap','capture_missing')"))
        c.execute(text("INSERT INTO inspection_views VALUES "
                       "('a1:C1','a1','p_full','cap','C1','/x/C1.jpg','ok'),"
                       "('a1:C2','a1','p_full','cap','C2','/x/C2.jpg','ok'),"
                       "('a1:C3','a1','p_full','cap','C3','/x/C3.jpg','ok'),"
                       "('a1:C4','a1','p_full','cap','C4','/x/C4.jpg','ok'),"
                       "('a1:C5','a1','p_full','cap','C5','/x/C5.jpg','ok'),"
                       "('a2:C1','a2','p_partial','cap','C1','/y/C1.jpg','ok')"))
    yield engine
    engine.dispose()


def test_list_items(ro_engine, monkeypatch):
    monkeypatch.setattr(gui_inference, "get_engine", lambda role="read": ro_engine)
    assert gui_inference.list_items() == ["cap"]


def test_sample_products_only_complete_with_5_views(ro_engine, monkeypatch):
    monkeypatch.setattr(gui_inference, "get_engine", lambda role="read": ro_engine)
    assert gui_inference.sample_products("cap") == ["p_full"]


def test_product_view_paths_requires_five(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    for cam in ("C1", "C2", "C3", "C4", "C5"):
        (tmp_path / f"{cam}.jpg").write_bytes(b"x")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE inspection_attempts ("
                       "attempt_id TEXT PRIMARY KEY, product_id TEXT, item TEXT, "
                       "status TEXT)"))
        c.execute(text("CREATE TABLE inspection_views ("
                       "view_id TEXT PRIMARY KEY, attempt_id TEXT, product_id TEXT, "
                       "item TEXT, camera_id TEXT, image_uri TEXT, status TEXT)"))
        c.execute(text("INSERT INTO inspection_attempts VALUES ('a','p','cap','completed')"))
        for cam in ("C1", "C2", "C3", "C4", "C5"):
            c.execute(text("INSERT INTO inspection_views VALUES "
                           f"('a:{cam}','a','p','cap','{cam}','{tmp_path}/{cam}.jpg','ok')"))
    monkeypatch.setattr(gui_inference, "get_engine", lambda role="read": engine)
    views = gui_inference.product_view_paths("p")
    assert sorted(views) == ["C1", "C2", "C3", "C4", "C5"]
    assert all(isinstance(p, Path) and p.is_file() for p in views.values())
    with pytest.raises(ValueError):
        gui_inference.product_view_paths("nope")
    engine.dispose()
