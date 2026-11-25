import io
import json

from scripts import check_final_sync


def responses(monkeypatch, *, state="complete", mismatch=False):
    summary = {"state": state, "available": state == "complete", "is_fixture": False,
               "model_version": "test-run", "report_path": "test-report", "metrics": {"fp": 1}}

    def request(req, timeout):
        path = req.full_url.removeprefix("http://localhost:8080")
        if path == "/status/overview":
            data = {"final_performance": summary, "loaded": {}, "score_backfill": {},
                    "pipeline": {"model_run": "test-run", "model_run_status": "COMPLETE"}}
        elif path == "/performance/final":
            data = {"state": state, "summary": summary}
        elif path == "/tools":
            data = {"tools": ["get_final_performance"]}
        elif path == "/tools/get_final_performance":
            assert req.get_method() == "POST" and req.data == b"{}"
            data = {**summary, "model_version": "stale-run"} if mismatch else summary
        else:
            raise AssertionError("Unexpected API call")
        return io.BytesIO(json.dumps(data).encode())

    monkeypatch.setattr(check_final_sync, "urlopen", request)


def test_live_sync_checker_rejects_stale_agent_result(monkeypatch):
    responses(monkeypatch, mismatch=True)
    assert check_final_sync.check("http://localhost:8080")["state"] == "FAILED"


def test_live_sync_checker_does_not_call_pending_report_verified(monkeypatch):
    responses(monkeypatch, state="report_pending")
    assert check_final_sync.check("http://localhost:8080")["state"] == "CONSISTENT_REPORT_NOT_AVAILABLE"


def test_live_sync_checker_compares_three_read_paths(monkeypatch):
    responses(monkeypatch)
    result = check_final_sync.check("http://localhost:8080")
    assert result["state"] == "VERIFIED" and "model_version" in result["checks"]
