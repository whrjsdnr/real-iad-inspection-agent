"""지표 4개의 분자/분모, 분모 0 처리, pending/confirmed 분리 검증."""
from datetime import datetime, timedelta

import pytest

from app.models import Attempt, Finding, Review, View
from app.seed_mock import MODEL_VERSION
from app.tools import compute_inspection_metrics

ISO = "%Y-%m-%dT%H:%M:%S"
T0 = datetime(2026, 11, 1, 9, 0, 0)


def _attempt(session, pid, item, status, i):
    session.add(
        Attempt(
            attempt_id=f"ATT-{pid}",
            product_id=pid,
            item=item,
            started_at=(T0 + timedelta(hours=i)).strftime(ISO),
            status=status,
            model_version=MODEL_VERSION,
            mapping_version="roi-lut-v1",
        )
    )


def _views(session, pid, item):
    for cam in ("C1", "C2", "C3", "C4", "C5"):
        session.add(
            View(
                view_id=f"V-{pid}-{cam}",
                attempt_id=f"ATT-{pid}",
                product_id=pid,
                item=item,
                camera_id=cam,
                image_uri=f"mock://images/{item}/{pid}/{cam}.png",
                error_map_uri=f"mock://errmaps/{item}/{pid}/{cam}.png",
                status="ok",
                model_version=MODEL_VERSION,
                mapping_version="roi-lut-v1",
            )
        )


def _review(session, pid, item, part_id, cam, truth, state, i):
    session.add(
        Review(
            review_id=f"REV-{pid}-{part_id}",
            product_id=pid,
            item=item,
            part_id=part_id,
            camera_id=cam,
            truth_label=truth,
            review_state=state,
            reviewer="qa-1",
            reason=None,
            reviewed_at=(T0 + timedelta(hours=i, minutes=40)).strftime(ISO),
        )
    )


def _finding(session, pid, item, part_id, cam, model_version, i):
    session.add(
        Finding(
            finding_id=f"F-{pid}-{part_id}-{i}",
            view_id=f"V-{pid}-{cam}",
            product_id=pid,
            item=item,
            camera_id=cam,
            source="anomaly",
            bbox_x1=210,
            bbox_y1=50,
            bbox_x2=250,
            bbox_y2=90,
            score=0.9,
            part_id=part_id,
            model_version=model_version,
            mapping_version="roi-lut-v1",
        )
    )


@pytest.fixture()
def handbuilt(session):
    """toothbrush / bristle@C1 인구:
    P1 confirmed defect + finding(anomaly-v1)  -> 적중
    P2 confirmed normal + finding(anomaly-v1)  -> 오경보
    P3 pending    defect  (finding 없음)
    P4 confirmed defect  (finding 없음)        -> miss
    P5 confirmed defect + finding(defect-v1)   -> anomaly-v1 기준 miss
    시도 10건: 실패 3건 (missing/blurred/inference_error)
    """
    item = "toothbrush"
    for i, cam in enumerate(("C1", "C2", "C3", "C4", "C5"), start=1):
        _attempt(session, f"P{i}", item, "completed", i)
        _views(session, f"P{i}", item)

    _attempt(session, "P6", item, "capture_missing", 6)
    _attempt(session, "P7", item, "capture_blurred", 7)
    _attempt(session, "P8", item, "inference_error", 8)
    _attempt(session, "P9", item, "completed", 9)
    _attempt(session, "P10", item, "completed", 10)

    _review(session, "P1", item, "bristle", "C1", "defect", "confirmed", 1)
    _finding(session, "P1", item, "bristle", "C1", MODEL_VERSION, 1)
    _review(session, "P2", item, "bristle", "C1", "normal", "confirmed", 2)
    _finding(session, "P2", item, "bristle", "C1", MODEL_VERSION, 2)
    _review(session, "P3", item, "bristle", "C1", "defect", "pending", 3)
    _review(session, "P4", item, "bristle", "C1", "defect", "confirmed", 4)
    _review(session, "P5", item, "bristle", "C1", "defect", "confirmed", 5)
    _finding(session, "P5", item, "bristle", "C1", "mock-defect-v1", 5)
    session.commit()
    return session


def _metrics(session, **overrides):
    params = dict(
        item="toothbrush",
        part_id="bristle",
        camera_id="C1",
        date_from="2026-11-01T00:00:00",
        date_to="2026-12-31T23:59:59",
        model_version=MODEL_VERSION,
        review_state="confirmed",
        session=session,
    )
    params.update(overrides)
    return compute_inspection_metrics(**params)


def test_metric_numerators_denominators(handbuilt):
    m = _metrics(handbuilt)["metrics"]
    # confirmed_defect_rate: 불량 확인 3(P1,P4,P5) / 검수 확정 4(P1,P2,P4,P5)
    assert m["confirmed_defect_rate"]["num"] == 3
    assert m["confirmed_defect_rate"]["den"] == 4
    assert m["confirmed_defect_rate"]["rate"] == pytest.approx(3 / 4)
    # part_miss_rate: miss 2(P4, P5) / 불량 확인 3 - P5는 다른 모델 버전 finding이라 miss 처리
    assert m["part_miss_rate"]["num"] == 2
    assert m["part_miss_rate"]["den"] == 3
    assert m["part_miss_rate"]["rate"] == pytest.approx(2 / 3)
    # part_false_alarm_rate: 오경보 1(P2) / 정상 확인 1
    assert m["part_false_alarm_rate"]["num"] == 1
    assert m["part_false_alarm_rate"]["den"] == 1
    assert m["part_false_alarm_rate"]["rate"] == pytest.approx(1.0)
    # capture_process_failure_rate: 실패 3 / 시도 10
    assert m["capture_process_failure_rate"]["num"] == 3
    assert m["capture_process_failure_rate"]["den"] == 10
    assert m["capture_process_failure_rate"]["rate"] == pytest.approx(0.3)


def test_model_version_filter_changes_predictions(handbuilt):
    m = _metrics(handbuilt, model_version="mock-defect-v1")["metrics"]
    # P5의 finding만 이 버전에 잡힌다 -> miss 0, 나머지 불량 2건은 miss
    assert m["part_miss_rate"]["num"] == 2
    assert m["part_miss_rate"]["den"] == 3


def test_denominator_zero_returns_null(handbuilt):
    m = _metrics(handbuilt, part_id="handle")["metrics"]
    for name in ("confirmed_defect_rate", "part_miss_rate", "part_false_alarm_rate"):
        assert m[name]["den"] == 0
        assert m[name]["rate"] is None
        assert m[name]["reason"] == "denominator_zero"
    # 시도는 item 수준으로 남아 있어 capture 지표는 계산된다
    assert m["capture_process_failure_rate"]["rate"] == pytest.approx(0.3)

    m2 = _metrics(handbuilt, item="nonexistent")["metrics"]
    for name, v in m2.items():
        assert v["rate"] is None
        assert v["reason"] == "denominator_zero"


def test_pending_confirmed_not_mixed(handbuilt):
    confirmed = _metrics(handbuilt)["metrics"]
    pending = _metrics(handbuilt, review_state="pending")["metrics"]
    # confirmed만 따로: P1,P2,P4,P5 (P3 pending 제외)
    assert confirmed["confirmed_defect_rate"]["den"] == 4
    # pending만 따로: P3 뿐
    assert pending["confirmed_defect_rate"]["num"] == 1
    assert pending["confirmed_defect_rate"]["den"] == 1
    assert pending["part_miss_rate"]["num"] == 1  # finding 없음 -> miss
    assert pending["part_miss_rate"]["den"] == 1
    assert pending["part_false_alarm_rate"]["den"] == 0
    assert pending["part_false_alarm_rate"]["reason"] == "denominator_zero"


def test_response_contains_versions(handbuilt):
    res = _metrics(handbuilt)
    assert res["definition_version"] == "metrics-v1"
    assert res["model_version"] == MODEL_VERSION
    assert "mapping_version" in res
    assert res["filters"]["review_state"] == "confirmed"
