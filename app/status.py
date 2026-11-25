"""인트로 상태 위젯·대시보드 요약 카드용 읽기 전용 상태 집계.

모든 DB 접근은 read 엔진으로만 한다 (백그라운드 동기화 프로세스와의 충돌 방지).
final_performance는 ~/MV/.../final_performance/latest.json 존재 여부로 판정하고,
검증용으로 FINAL_PERFORMANCE_FIXTURE 환경변수에 JSON 경로를 주면 실 파일이 없을 때
대신 응답에 포함한다 (실 파일이 생기면 자동으로 실 데이터로 전환).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import text

from .db import get_engine
from .cohort_performance import sha256

AGENT_ROOT = Path(__file__).resolve().parents[1]

TARGET_PRODUCTS = 24000
TARGET_VIEWS = 120000

DEFAULT_FINAL_DIR = Path(
    "/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1/final_performance"
)

# 기준선 v1 (teammate 보고, Test 600+600) — config/teammate_fusion_reference.json과 동일
BASELINE_V1 = {
    "label": "기준선 v1 (Test NG600+OK600)",
    "recall": 0.938,
    "f1": 0.9314,
    "miss": 37,
    "false_alarm": 46,
    "source": "config/teammate_fusion_reference.json",
}


def _fusion_config() -> dict:
    return json.loads((AGENT_ROOT / "config" / "fusion.json").read_text())


def model_versions() -> dict:
    cfg = _fusion_config()
    mv = cfg.get("model_versions", {})
    return {
        "hvq": mv.get("hvq", "HVQ-Trans79ep-ONNX-FP16IO"),
        "rtdetr": mv.get("rtdetr", "RT-DETRv2-15ep-EMA-111classes-ONNX-FP32"),
        "hvq_epochs": 79,
        "rtdetr_epochs": "15 (EMA)",
        "weights": cfg.get("weights", {"hvq": 0.3, "rtdetr": 0.7}),
        "config_version": cfg.get("version"),
    }


def _final_dir() -> Path:
    explicit = os.getenv('FINAL_PERFORMANCE_DIR')
    if explicit:
        return Path(explicit)
    selected = AGENT_ROOT/'reports/final_performance_minmax'
    pointer = _load_report(selected/'latest.json')
    report = _load_report(Path(pointer['report'])) if pointer else None
    if (report and report.get('status') == 'FINAL_COMPLETE'
            and report.get('root_config_sha256') == sha256(AGENT_ROOT/'config/fusion.json')
            and report.get('evaluation_config_sha256') == sha256(AGENT_ROOT/'config/fusion_evaluation.json')):
        return selected
    return DEFAULT_FINAL_DIR


def _load_report(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def final_performance_payload() -> dict:
    """최종 성능 리포트 로드. 실 latest.json 우선, 없으면 fixture 환경변수 폐백."""
    d = _final_dir()
    latest_path = d / "latest.json"
    if latest_path.exists():
        latest = _load_report(latest_path)
        if latest:
            report_path = Path(latest.get("report", ""))
            report = _load_report(report_path)
            if report:
                # Separate derived report, bound to this exact immutable source.
                derived_path = Path(os.getenv('COHORT_PERFORMANCE_REPORT', str(AGENT_ROOT / 'reports/cohort_performance/latest.json')))
                derived = _load_report(derived_path)
                if (isinstance(derived, dict)
                        and derived.get('source_report_sha256') == sha256(report_path)
                        and derived.get('source_report') == str(report_path.resolve())
                        and derived.get('model_version') == report.get('model_version')
                        and derived.get('csv_consistency_verified') is True
                        and derived.get('overall', {}).get('products') == report.get('cohort_products')):
                    report['cohort_reference'] = derived
                return {"available": True, "is_fixture": False,
                        "state": "complete", "report_path": str(report_path),
                        "latest": latest, "report": report}
    fixture = os.getenv("FINAL_PERFORMANCE_FIXTURE", "")
    if fixture:
        report = _load_report(Path(fixture))
        if report:
            return {"available": True, "is_fixture": True,
                    "state": "complete", "report_path": fixture,
                    "latest": None, "report": report}
    return {"available": False, "is_fixture": False, "state": "waiting",
            "report_path": None, "latest": None, "report": None}


def final_performance_summary(payload: dict | None = None) -> dict:
    """대시보드 요약 카드/인트로 위젯용 요약. 지표는 실데이터 기준."""
    p = payload if payload is not None else final_performance_payload()
    out = {"available": p["available"], "is_fixture": p["is_fixture"],
           "state": p["state"], "report_path": p["report_path"],
           "model_version": None, "baseline_v1": BASELINE_V1, "metrics": None}
    report = p.get("report")
    if not report:
        return out
    test = report.get("test", {})
    cohort = report.get('cohort_reference')
    if not cohort and report.get('evaluation_scope') == 'all_inferred_products_reference' and report.get('overall'):
        cohort = {'overall': report['overall'], 'category_macro': report.get('overall_category_macro', {}),
                  'csv_consistency_verified': report.get('csv_consistency_verified', False), 'timestamp': report.get('timestamp')}
    evaluation = cohort['overall'] if cohort else test
    binary = evaluation.get("binary_threshold", {})
    hold = evaluation.get("final_with_hold", {})
    decided = hold.get("decided_only_metrics", {})
    macro = cohort['category_macro'] if cohort else report.get("category_macro", {})

    def _r(d, k):
        v = d.get(k)
        return v.get("rate") if isinstance(v, dict) else v

    out["model_version"] = report.get("model_version")
    out["metrics"] = {
        "cohort_products": report.get("cohort_products"),
        "test_products": test.get("products"),
        "source_model_version": report.get('source_model_version'),
        "database_run_activated": report.get('database_run_activated', True),
        "fusion_policy": report.get('profile'),
        "evaluation_products": evaluation.get('products'),
        "evaluation_scope": 'all_inferred_products_reference' if cohort else 'test',
        "contains_calibration_products": bool(cohort),
        "training_overlap": report.get('training_overlap'),
        "csv_consistency_verified": bool(cohort and cohort.get('csv_consistency_verified')),
        "test_reference": test.get('binary_threshold'),
        "test_f1_micro": _r(test.get('binary_threshold', {}), 'f1'),
        "test_recall": _r(test.get('binary_threshold', {}), 'recall'),
        "fp": binary.get("fp"),
        "fn": binary.get("fn"),
        "recall": _r(binary, "recall"),
        "f1_micro": _r(binary, "f1"),
        "auroc": binary.get("auroc"),
        "ap": binary.get("average_precision"),
        "f1_category_macro": macro.get("f1"),
        "auroc_category_macro": macro.get("auroc"),
        "hold_products": hold.get("hold_products"),
        "hold_rate": hold.get("hold_rate"),
        "coverage": hold.get("coverage"),
        "final_fp": decided.get("fp"),
        "final_fn": decided.get("fn"),
        "decided_f1": _r(decided, "f1"),
        "single_model_hvq_f1": _r(evaluation.get("single_model_hvq", {}), "f1"),
        "single_model_rtdetr_f1": _r(evaluation.get("single_model_rtdetr", {}), "f1"),
        "verified": bool(not cohort and report.get("independent_sql_verified")
                         and report.get("agent_tool_verified")),
        "timestamp": cohort.get('timestamp') if cohort else report.get("timestamp"),
    }
    return out


def _safe_count(engine, sql: str, params: dict | None = None) -> int | None:
    try:
        with engine.connect() as c:
            return int(c.execute(text(sql), params or {}).scalar())
    except Exception:  # noqa: BLE001 — 위젯은 부분 실패에도 살아남아야 함
        return None


def _loaded_counts() -> dict:
    engine = get_engine("read")
    products = _safe_count(engine, "SELECT count(*) FROM inspection_attempts")
    views = _safe_count(engine, "SELECT count(*) FROM inspection_views")
    return {
        "products": products,
        "views": views,
        "scope": "all_inspection_records",
        "product_count_unit": "inspection_attempt",
        "target_products": TARGET_PRODUCTS,
        "target_views": TARGET_VIEWS,
        "product_progress": (products / TARGET_PRODUCTS) if products else None,
        "view_progress": (views / TARGET_VIEWS) if views else None,
    }


def _score_backfill() -> dict:
    engine = get_engine("read")
    row = None
    try:
        with engine.connect() as c:
            row = c.execute(text(
                "SELECT status, expected_products, completed_products, completed_views, "
                "score_variant FROM fusion_analysis.score_sets "
                "ORDER BY updated_at DESC LIMIT 1"
            )).mappings().first()
    except Exception:  # noqa: BLE001
        row = None
    out = {"status": None, "expected_products": TARGET_PRODUCTS,
           "completed_products": None, "completed_views": None,
           "score_variant": None, "progress": None}
    if row:
        out.update({k: row.get(k) for k in
                    ("status", "expected_products", "completed_products",
                     "completed_views", "score_variant")})
        exp = row.get("expected_products") or TARGET_PRODUCTS
        done = row.get("completed_products")
        out["progress"] = (done / exp) if done is not None and exp else None
    return out


def _pipeline_state() -> dict:
    engine = get_engine("read")
    try:
        with engine.connect() as c:
            run = c.execute(text(
                "SELECT fusion_run_id, status, is_active FROM fusion_analysis.model_runs "
                "ORDER BY is_active DESC LIMIT 1"
            )).mappings().first()
    except Exception:  # noqa: BLE001
        run = None
    if not run:
        return {"model_run": None, "model_run_status": None}
    return {"model_run": run.get("fusion_run_id"),
            "model_run_status": run.get("status")}


def final_performance_state(*, payload=None, backfill=None, pipeline=None) -> str:
    """보고서 완료와 점수 처리 완료를 구분한다. 완료를 계산 중으로 표시하지 않는다."""
    p = payload if payload is not None else final_performance_payload()
    if p["available"]:
        return "complete"
    backfill = backfill if backfill is not None else _score_backfill()
    pipeline = pipeline if pipeline is not None else _pipeline_state()
    if pipeline.get("model_run_status") == "COMPLETE":
        return "report_pending"
    if (backfill.get("status") in ("BACKFILLING", "COMPLETE")
            or pipeline.get("model_run_status") in
            ("CALIBRATED_TEST_PENDING", "COMPLETE")):
        return "computing"
    return "waiting"


def overview() -> dict:
    fp = final_performance_payload()
    backfill = _score_backfill()
    pipeline = _pipeline_state()
    summary = final_performance_summary(fp)
    summary["state"] = final_performance_state(payload=fp, backfill=backfill, pipeline=pipeline)
    return {
        "loaded": _loaded_counts(),
        "score_backfill": backfill,
        "pipeline": pipeline,
        "final_performance": summary,
        "models": model_versions(),
    }
