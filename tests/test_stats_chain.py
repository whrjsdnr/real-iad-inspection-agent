"""query_error_stats의 stat_key로 get_case_evidence가 같은 사례 집합을 여는지 검증."""
import json

import pytest

from app.tools import get_case_evidence, query_error_stats

DATE_FROM = "2026-11-01T00:00:00"
DATE_TO = "2026-12-31T23:59:59"


def test_stat_key_chain_part_miss(seeded_session):
    res = query_error_stats(
        item="toothbrush",
        metric="part_miss_rate",
        group_by=["part_id", "camera_id"],
        date_from=DATE_FROM,
        date_to=DATE_TO,
        session=seeded_session,
    )
    assert res["definition_version"] == "metrics-v1"
    assert res["model_version"] is None or "mapping_version" in res

    rows = [r for r in res["rows"] if r["den"] > 0]
    assert rows, "seed 데이터에 분모>0 행이 있어야 한다"
    for r in res["rows"]:
        assert set(r) >= {"group", "num", "den", "rate", "stat_key"}
        assert 0 <= r["num"] <= r["den"]

    row = rows[0]
    # stat_key는 필터를 모두 포함한 stable string
    decoded = json.loads(row["stat_key"])
    assert decoded["metric"] == "part_miss_rate"
    assert decoded["item"] == "toothbrush"
    assert decoded["part_id"] == row["group"]["part_id"]
    assert decoded["camera_id"] == row["group"]["camera_id"]

    ev = get_case_evidence(stat_key=row["stat_key"], session=seeded_session)
    assert ev["definition_version"] == "metrics-v1"
    # 같은 사례 집합: 검수 기반 지표는 분모 집합(불량 확인 제품)
    assert ev["count"] == row["den"]
    assert len(ev["cases"]) == row["den"]
    for c in ev["cases"]:
        assert c["truth_label"] == "defect"
        assert c["prediction"] in ("defect", "normal")

    # 최소 1건의 C1~C5 evidence와 모델/매핑 버전
    c0 = ev["cases"][0]
    assert set(c0["evidence"]["all_views"].keys()) == {"C1", "C2", "C3", "C4", "C5"}
    assert c0["model_version"]
    assert c0["mapping_version"] == "roi-lut-v1"
    assert c0["review"]["state"] == "confirmed"
    # miss 사례는 box_ids가 비어 있어야 한다
    missed = [c for c in ev["cases"] if c["prediction"] == "normal"]
    assert len(missed) == row["num"]


def test_stat_key_chain_capture(seeded_session):
    res = query_error_stats(
        item="toothbrush",
        metric="capture_process_failure_rate",
        group_by=["model_version"],
        date_from=DATE_FROM,
        date_to=DATE_TO,
        session=seeded_session,
    )
    assert len(res["rows"]) == 1
    row = res["rows"][0]
    assert row["group"] == {"model_version": "mock-anomaly-v1"}

    ev = get_case_evidence(stat_key=row["stat_key"], session=seeded_session)
    # 캡처 지표는 오류 시도 집합(분자)을 연다
    assert ev["count"] == row["num"]
    for c in ev["cases"]:
        assert c["attempt_status"] in ("capture_missing", "capture_blurred", "inference_error")
        assert c["truth_label"] is None
        assert set(c["evidence"]["all_views"].keys()) == {"C1", "C2", "C3", "C4", "C5"}


def test_stat_key_stable(seeded_session):
    kw = dict(item="toy", metric="part_false_alarm_rate", group_by=["part_id"],
              date_from=DATE_FROM, date_to=DATE_TO, session=seeded_session)
    r1 = query_error_stats(**kw)["rows"]
    r2 = query_error_stats(**kw)["rows"]
    assert [r["stat_key"] for r in r1] == [r["stat_key"] for r in r2]


def test_group_by_camera_and_order(seeded_session):
    res = query_error_stats(
        item="toothbrush", metric="confirmed_defect_rate", group_by=["camera_id"],
        date_from=DATE_FROM, date_to=DATE_TO, order="desc", limit=3,
        session=seeded_session,
    )
    assert len(res["rows"]) <= 3
    rates = [r["rate"] for r in res["rows"] if r["rate"] is not None]
    assert rates == sorted(rates, reverse=True)


def test_invalid_metric_rejected(seeded_session):
    with pytest.raises(Exception):
        query_error_stats(item="toy", metric="bad_metric", group_by=["part_id"],
                          session=seeded_session)
