"""Read-only host check: overview, final report API and registered agent tool agree."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def check(base):
    parsed = urlparse(base)
    if parsed.hostname not in ("localhost", "127.0.0.1") or parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("Use the local read-only development API or local central API")
    result = {"state": "BLOCKED", "checks": [], "errors": [], "note": "No inference, report generation, DB writes or server restarts."}

    def read(path, body=None):
        request = Request(base.rstrip("/") + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=8) as response:
            return json.load(response)

    try:
        overview = read("/status/overview")
        final = read("/performance/final")
        tools = read("/tools")
        if "get_final_performance" not in tools.get("tools", []):
            raise ValueError("get_final_performance is not registered on this server")
        agent = read("/tools/get_final_performance", {})
        summaries = [overview["final_performance"], final["summary"], agent]
        result["states"] = [summary["state"] for summary in summaries]
        result["loaded"] = overview["loaded"]
        result["score_backfill"] = overview["score_backfill"]
        for key in ("state", "available", "is_fixture", "model_version", "report_path", "metrics"):
            if not all(summary.get(key) == summaries[0].get(key) for summary in summaries):
                result["errors"].append(f"Overview/API/agent mismatch: {key}; rerun if report was published during this check")
            else:
                result["checks"].append(key)
        if final["state"] != final["summary"]["state"]:
            result["errors"].append("Final API envelope/summary state mismatch")
        if any(summary.get("is_fixture") for summary in summaries):
            result["errors"].append("Fixture performance is not real-data synchronization evidence")
        if summaries[0].get("available"):
            pipeline = overview.get("pipeline", {})
            report_mv = summaries[0].get("model_version")
            # 활성 DB run이 이 보고서의 활성화 형태인지 확인한다.
            # (계약 v2 활성화: run metadata.report_model_version == 보고서 model_version,
            #  구 report-only 상태에서는 source_model_version과 직접 비교하는 폐백)
            active_match = False
            try:
                runs = read("/fusion/runs").get("runs", [])
                active = next((r for r in runs if r.get("is_active")), None)
                if active and report_mv:
                    active_match = (active.get("fusion_run_id") == report_mv
                                    or active.get("report_model_version") == report_mv)
            except Exception:  # noqa: BLE001 - /fusion/runs 없는 구 서버 폐백
                active_match = False
            if not active_match:
                metrics = summaries[0].get('metrics') or {}
                expected_run = metrics.get('source_model_version') if metrics.get('database_run_activated') is False else report_mv
                active_match = pipeline.get("model_run") == expected_run
            if not active_match or pipeline.get("model_run_status") != "COMPLETE":
                result["errors"].append("Report does not match a completed active DB model run")
            else:
                result["checks"].append("active_model_run")
        result["metrics"] = summaries[0].get("metrics")
        result["model_version"] = summaries[0].get("model_version")
        result["state"] = "FAILED" if result["errors"] else "VERIFIED" if summaries[0].get("available") else "CONSISTENT_REPORT_NOT_AVAILABLE"
    except Exception as error:
        result["errors"].append(f"{type(error).__name__}: {error}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, default=Path("reports/gui_validation/sync-final/live-api-check.json"))
    args = parser.parse_args()
    result = check(args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"] == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
