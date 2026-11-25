"""인트로 상태 위젯/최종 성능 도구 테스트 (파일 기반 부분)."""
import json
from pathlib import Path

import pytest

from app import status
from app.tools import TOOL_FUNCS


def _write_report(d: Path) -> Path:
    report = {
        "status": "FINAL_COMPLETE",
        "model_version": "fusion-max16-test",
        "timestamp": "2026-11-24T13:00:00+09:00",
        "cohort_products": 24000,
        "test": {
            "products": 1200,
            "binary_threshold": {
                "fp": 10, "fn": 20,
                "recall": {"num": 580, "den": 600, "rate": 0.966667},
                "f1": {"num": 1160, "den": 1200, "rate": 0.966667},
                "auroc": 0.981, "average_precision": 0.95,
            },
            "final_with_hold": {
                "hold_products": 30, "hold_rate": 0.025, "coverage": 0.975,
                "decided_only_metrics": {"fp": 8, "fn": 15,
                                         "f1": {"rate": 0.94}},
            },
            "single_model_hvq": {"f1": {"rate": 0.90}},
            "single_model_rtdetr": {"f1": {"rate": 0.91}},
        },
        "category_macro": {"f1": 0.92, "auroc": 0.97},
        "independent_sql_verified": True,
        "agent_tool_verified": True,
    }
    perf = d / "perf" / "performance.json"
    perf.parent.mkdir(parents=True)
    perf.write_text(json.dumps(report))
    (d / "latest.json").write_text(json.dumps(
        {"report": str(perf), "directory": str(perf.parent)}))
    return perf


def test_waiting_when_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path / "none"))
    monkeypatch.delenv("FINAL_PERFORMANCE_FIXTURE", raising=False)
    payload = status.final_performance_payload()
    assert payload["available"] is False
    summary = status.final_performance_summary(payload)
    assert summary["metrics"] is None
    assert summary["baseline_v1"]["f1"] == pytest.approx(0.9314)


def test_complete_from_latest_json(tmp_path, monkeypatch):
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path))
    monkeypatch.delenv("FINAL_PERFORMANCE_FIXTURE", raising=False)
    _write_report(tmp_path)
    payload = status.final_performance_payload()
    assert payload["available"] and not payload["is_fixture"]
    assert payload["state"] == "complete"
    summary = status.final_performance_summary(payload)
    m = summary["metrics"]
    assert m["fp"] == 10 and m["fn"] == 20
    assert m["recall"] == pytest.approx(0.966667)
    assert m["f1_micro"] == pytest.approx(0.966667)
    assert m["auroc"] == pytest.approx(0.981)
    assert m["hold_products"] == 30 and m["hold_rate"] == pytest.approx(0.025)
    assert m["final_fp"] == 8 and m["final_fn"] == 15
    assert m["f1_category_macro"] == pytest.approx(0.92)
    assert m["verified"] is True
    # 기준선 v1과 나란히
    assert summary["baseline_v1"]["recall"] == pytest.approx(0.938)


def test_fixture_fallback_and_real_precedence(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture_report.json"
    fixture_report = {
        "status": "FINAL_COMPLETE",
        "test": {
            "binary_threshold": {"fp": 1, "fn": 2,
                                 "recall": {"rate": 0.9},
                                 "f1": {"rate": 0.91},
                                 "auroc": 0.93},
            "final_with_hold": {"hold_products": 3, "hold_rate": 0.3},
        },
        "independent_sql_verified": True,
        "agent_tool_verified": True,
    }
    fixture.write_text(json.dumps(fixture_report))
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path / "none"))
    monkeypatch.setenv("FINAL_PERFORMANCE_FIXTURE", str(fixture))
    payload = status.final_performance_payload()
    assert payload["available"] and payload["is_fixture"]
    # 실 latest.json이 생기면 자동 전환
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    _write_report(real_dir)
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(real_dir))
    payload2 = status.final_performance_payload()
    assert payload2["available"] and not payload2["is_fixture"]
    assert status.final_performance_summary(payload2)["metrics"]["fp"] == 10


def test_state_waiting_vs_complete(tmp_path, monkeypatch):
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path / "none"))
    monkeypatch.delenv("FINAL_PERFORMANCE_FIXTURE", raising=False)
    monkeypatch.setattr(status, "_score_backfill", lambda: {"status": None})
    monkeypatch.setattr(status, "_pipeline_state", lambda: {"model_run_status": None})
    assert status.final_performance_state() == "waiting"
    monkeypatch.setattr(status, "_score_backfill",
                        lambda: {"status": "BACKFILLING"})
    assert status.final_performance_state() == "computing"
    _write_report(tmp_path)
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path))
    assert status.final_performance_state() == "complete"


def test_get_final_performance_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path))
    monkeypatch.delenv("FINAL_PERFORMANCE_FIXTURE", raising=False)
    _write_report(tmp_path)
    r = TOOL_FUNCS["get_final_performance"]()
    assert r["available"] and r["state"] == "complete"
    assert r["metrics"]["f1_micro"] == pytest.approx(0.966667)
    assert r["baseline_v1"]["f1"] == pytest.approx(0.9314)
    assert r["definition_version"] == "metrics-v1"


def test_report_pending_consistent_across_overview_api_and_agent(tmp_path, monkeypatch):
    from app.api import performance_final
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path))
    monkeypatch.delenv("FINAL_PERFORMANCE_FIXTURE", raising=False)
    monkeypatch.setattr(status, "_score_backfill", lambda: {"status": "COMPLETE"})
    monkeypatch.setattr(status, "_pipeline_state", lambda: {"model_run_status": "COMPLETE"})
    monkeypatch.setattr(status, "_loaded_counts", lambda: {})
    assert status.overview()["final_performance"]["state"] == "report_pending"
    response = performance_final()
    assert response["state"] == response["summary"]["state"] == "report_pending"
    assert response["available"] is False and response["summary"]["metrics"] is None
    assert TOOL_FUNCS["get_final_performance"]()["state"] == "report_pending"
    # A later externally produced report becomes visible without a process restart.
    _write_report(tmp_path)
    assert status.overview()["final_performance"]["state"] == "complete"
    assert performance_final()["summary"]["metrics"]["fp"] == 10
    assert TOOL_FUNCS["get_final_performance"]()["state"] == "complete"


def test_completed_backfill_does_not_imply_completed_fusion_validation():
    assert status.final_performance_state(
        payload={"available": False}, backfill={"status": "COMPLETE"},
        pipeline={"model_run_status": "CALIBRATED_TEST_PENDING"}) == "computing"


def test_final_performance_tool_http_is_registered_without_starting_services(tmp_path, monkeypatch):
    import asyncio
    from app.api import app
    from app.readonly_api import app as readonly_app
    monkeypatch.setenv("FINAL_PERFORMANCE_DIR", str(tmp_path))
    monkeypatch.delenv("FINAL_PERFORMANCE_FIXTURE", raising=False)
    _write_report(tmp_path)

    async def check():
        async def post(application, body):
            messages = []
            received = False

            async def receive():
                nonlocal received
                if received:
                    return {"type": "http.disconnect"}
                received = True
                return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

            async def send(message):
                messages.append(message)

            path = "/tools/get_final_performance"
            scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                     "method": "POST", "scheme": "http", "path": path, "raw_path": path.encode(),
                     "query_string": b"", "headers": [(b"content-type", b"application/json")],
                     "server": ("test", 80), "client": ("127.0.0.1", 1), "root_path": ""}
            await application(scope, receive, send)
            code = next(message["status"] for message in messages if message["type"] == "http.response.start")
            data = json.loads(b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body"))
            return code, data

        for application in (app, readonly_app):
            # HTTP-only ASGI scope: no lifespan/migrations/workers/DB writes.
            code, data = await post(application, {})
            assert code == 200 and data["metrics"]["fp"] == 10
            code, _ = await post(application, {"item": []})
            assert code == 400
    asyncio.run(check())


def test_overview_does_not_reread_mutating_report_or_pipeline(monkeypatch):
    from unittest.mock import Mock
    payload = {"available": False, "is_fixture": False, "state": "waiting",
               "report_path": None, "report": None}
    load = Mock(return_value=payload)
    backfill = Mock(return_value={"status": "COMPLETE"})
    pipeline = Mock(return_value={"model_run_status": "COMPLETE"})
    monkeypatch.setattr(status, "final_performance_payload", load)
    monkeypatch.setattr(status, "_score_backfill", backfill)
    monkeypatch.setattr(status, "_pipeline_state", pipeline)
    monkeypatch.setattr(status, "_loaded_counts", lambda: {})
    assert status.overview()["final_performance"]["state"] == "report_pending"
    for reader in (load, backfill, pipeline):
        reader.assert_called_once()
