"""운영 DB에 퓨전 계약 v2(weighted-minmax-heatmap-mean-rt40-v1)를 활성화한다.

작업 절차 (사용자 승인됨 — 운영 반영):
1. 저장 점수(재추론 없음)로 24,000제품 전체를 계약 v2 규칙으로 재판정한다.
   scripts/report_minmax_fusion.py의 evaluate() 로직을 그대로 재사용한다.
2. 재판정 결과를 새 model_run(fusion_analysis.model_runs)과
   fusion_analysis.product_predictions에 기록한다.
   기존 max16 run은 is_active=False로 보존하며, 어떤 행도 삭제하지 않는다.
3. 기록 직후 보고서 predictions과 전수 대조(제품 단위 일치, 오차 0)를 수행하고,
   통과 시에만 is_active를 새 run으로 전환한다.
4. public.metrics_snapshots에 기준선 v2를 등록한다
   (Test 3,593 / 전체 24,000 참고 분리, 분자·분모 포함, 전체 집계에는
   "학습 포함 가능성" 경고를 명시).
5. reviews 등 기존 테이블은 변경하지 않으며, 활성화 전후 행 수가
   동일함을 검증한다.

재시작 가능: 이미 기록된 제품은 스킵하고 누락분만 이어서 삽입한다.
진행 로그: reports/contract_v2_activation/activation.log
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.report_minmax_fusion import evaluate  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import get_engine  # noqa: E402

CONTRACT_VERSION = "weighted-minmax-heatmap-mean-rt40-v1"
SCORE_SOURCE = Path("/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1/max16_scores/hvq_max16.sqlite")
REPORT_DIR = ROOT / "reports/final_performance_minmax"
REPORT = REPORT_DIR / "performance.json"
REPORT_CSV = REPORT_DIR / "all_predictions.csv"
LOG_DIR = ROOT / "reports/contract_v2_activation"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "activation.log", encoding="utf-8"),
              logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("activate-v2")

CHUNK = 2000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_report_predictions() -> dict[str, dict]:
    with REPORT_CSV.open() as stream:
        return {row["product_id"]: row for row in csv.DictReader(stream)}


def recompute() -> tuple[list[dict], dict, str]:
    """저장 점수로 계약 v2를 재계산하고 보고서와의 일치를 검증한다."""
    profile = json.loads((ROOT / "config/fusion_evaluation.json").read_text())
    config = json.loads((ROOT / "config/fusion.json").read_text())
    connection = sqlite3.connect("file:" + str(SCORE_SOURCE) + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in connection.execute(
            """SELECT p.product_id,p.category,p.split,p.truth,
               max(v.rtdetr_raw) AS rtdetr_raw,max(v.hvq_mean) AS hvq_mean
               FROM products p JOIN views v USING(product_id)
               WHERE p.status='COMPLETED' GROUP BY p.product_id""")]
    finally:
        connection.close()
    if len(rows) != 24000 or len({r["product_id"] for r in rows}) != 24000:
        raise SystemExit(f"저장 점수 코호트가 24,000제품이 아닙니다: {len(rows)}")
    parameters = evaluate(rows, profile, config)
    identity = hashlib.sha256(json.dumps(
        {"profile": profile, "parameters": parameters}, sort_keys=True).encode()).hexdigest()
    run_hash = identity[:24]
    # 보고서 predictions과 전수 대조 (제품 단위, 오차 0)
    report_rows = load_report_predictions()
    if set(report_rows) != {r["product_id"] for r in rows}:
        raise SystemExit("보고서 CSV와 저장 점수의 제품 집합이 다릅니다")
    # 두 모델 양성 일치 판정(config/fusion.json fusion 규칙 — 구 run과 동일 의미)
    rules = config["fusion"]
    for row in rows:
        if row["rtdetr_positive"] and row["hvq_positive"]:
            row["agreement_verdict"] = rules["both_positive"]
        elif not row["rtdetr_positive"] and not row["hvq_positive"]:
            row["agreement_verdict"] = rules["both_negative"]
        else:
            row["agreement_verdict"] = rules["disagree"]
    mismatches = []
    for row in rows:
        ref = report_rows[row["product_id"]]
        checks = [
            ("fusion_score", row["fusion_score"], float(ref["fusion_score"])),
            ("threshold", row["threshold"], float(ref["threshold"])),
            ("margin", row["margin"], float(ref["margin"])),
            ("binary_verdict", row["binary_verdict"], ref["binary_verdict"]),
            ("verdict", row["verdict"], ref["verdict"]),
            ("rtdetr_positive", row["rtdetr_positive"], ref["rtdetr_positive"] == "True"),
            ("hvq_positive", row["hvq_positive"], ref["hvq_positive"] == "True"),
        ]
        for name, got, want in checks:
            if isinstance(got, float):
                ok = math.isclose(got, want, rel_tol=0, abs_tol=1e-9)
            else:
                ok = got == want
            if not ok:
                mismatches.append((row["product_id"], name, got, want))
        if mismatches:
            break
    if mismatches:
        raise SystemExit(f"보고서와 불일치: {mismatches[:5]}")
    log.info("전수 대조 통과: 24,000제품 오차 0 (fusion_score/TH/margin/판정/양성フラグ)")
    return rows, parameters, run_hash


def main() -> None:
    started = datetime.now(timezone.utc)
    log.info("=== 계약 v2 운영 활성화 시작 ===")
    rows, parameters, run_hash = recompute()
    fusion_run_id = f"{CONTRACT_VERSION}:{run_hash}"
    log.info("신규 fusion_run_id=%s", fusion_run_id)

    engine = get_engine("admin")
    old_run = engine.connect().execute(text(
        "SELECT fusion_run_id FROM fusion_analysis.model_runs WHERE is_active")).scalar()
    log.info("기존 활성 run(보존 대상)=%s", old_run)

    with engine.begin() as conn:
        reviews_before = conn.execute(text("SELECT count(*) FROM public.reviews")).scalar()
        prev_before = conn.execute(text(
            "SELECT count(*) FROM fusion_analysis.product_predictions")).scalar()

    # --- 1) model_run 등록 (있으면 갱신, 없으면 삽입) ---
    now = started.isoformat()
    profile_doc = {
        "contract_version": CONTRACT_VERSION,
        "weights": {"rtdetr": 0.7, "hvq": 0.3},
        "hvq_score_variant": "heatmap_mean",
        "rtdetr_conf_threshold": 0.4,
        "normalization": "validation_category_minmax",
        "clip_outside_validation_range": False,
        "hvq_prefilter": "none_continuous_mean_score",
        "product_aggregation": "max_C1_C5",
        "threshold": "validation_F1_highest_optimal_interval_midpoint",
        "margin": "validation_F1_drop_tolerance_0.005",
        "decision": "hold_if_abs_score_minus_threshold_le_margin_else_binary",
        "hvq_thresholds": {},
    }
    parameters_doc = {"categories": {
        cat: {"status": "CONFIGURED",
              "threshold": p["threshold"], "margin": p["margin"],
              "normalizers": {k: p["normalizers"][k] for k in ("rt_input", "hv_input")},
              "validation_products": p["validation_products"],
              "validation_best_f1": p["validation_best_f1"],
              "plateau_lower": p["plateau_lower"], "plateau_upper": p["plateau_upper"]}
        for cat, p in parameters.items()}}
    metadata_doc = {
        "contract_version": CONTRACT_VERSION,
        "report_model_version": json.loads(REPORT.read_text())["model_version"],
        "evaluation_report": str(REPORT),
        "evaluation_report_sha256": sha256(REPORT),
        "evaluation_products": 24000, "test_products": 3593,
        "source_model_version": old_run,
        "preserved_previous_run": old_run,
        "training_overlap": "UNKNOWN_ORIGINAL_30000_ID_LIST_MISSING",
        "hvq_raw_column_semantics": "product max of continuous heatmap_mean (legacy column name hvq_max16_raw)",
        "percentile_columns": "rt_percentile/hvq_percentile hold min-max normalized scores for this run (legacy column names; not percentiles)",
        "activation": "operational_db_updates_applied",
        "database_run_activated": False,
        "activated_at": None,
    }
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO fusion_analysis.model_runs "
            "(fusion_run_id, score_set_id, status, is_active, deployment_eligible, "
            " profile, parameters, metadata, created_at, updated_at) "
            "VALUES (:rid, :ssid, 'ACTIVATING', false, true, :profile, :params, :meta, :now, :now) "
            "ON CONFLICT (fusion_run_id) DO UPDATE SET "
            " status=EXCLUDED.status, profile=EXCLUDED.profile, "
            " parameters=EXCLUDED.parameters, metadata=EXCLUDED.metadata, updated_at=EXCLUDED.updated_at"),
            {"rid": fusion_run_id, "ssid": "max16:5daa5dae7e609c3f50b6c894",
             "profile": json.dumps(profile_doc), "params": json.dumps(parameters_doc),
             "meta": json.dumps(metadata_doc), "now": now})

    # --- 2) product_predictions 재개 가능 삽입 (완료 제품 스킵) ---
    with engine.connect() as conn:
        attempt_map = dict(conn.execute(text(
            "SELECT product_id, attempt_id FROM public.inspection_attempts "
            "WHERE status='completed'")).all())
        done = {r[0] for r in conn.execute(text(
            "SELECT product_id FROM fusion_analysis.product_predictions "
            "WHERE fusion_run_id=:rid"), {"rid": fusion_run_id}).all()}
    missing = [r for r in rows if r["product_id"] not in done]
    log.info("예측 기록: 전체 %d / 이미 기록 %d / 신규 삽입 %d", len(rows), len(done), len(missing))
    for i in range(0, len(missing), CHUNK):
        chunk = missing[i:i + CHUNK]
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO fusion_analysis.product_predictions "
                "(fusion_run_id, product_id, category, split, truth, source_attempt_id, "
                " rtdetr_raw, hvq_max16_raw, rtdetr_filtered, hvq_filtered, "
                " rt_percentile, hvq_percentile, rtdetr_positive, hvq_positive, "
                " agreement_verdict, fusion_score, threshold, margin, binary_verdict, verdict) "
                "VALUES (:fusion_run_id,:product_id,:category,:split,:truth,:source_attempt_id,"
                " :rtdetr_raw,:hvq_max16_raw,:rtdetr_filtered,:hvq_filtered,"
                " :rt_percentile,:hvq_percentile,:rtdetr_positive,:hvq_positive,"
                " :agreement_verdict,:fusion_score,:threshold,:margin,:binary_verdict,:verdict)"),
                [{
                    "fusion_run_id": fusion_run_id,
                    "product_id": r["product_id"], "category": r["category"],
                    "split": r["split"], "truth": r["truth"],
                    "source_attempt_id": attempt_map.get(r["product_id"]),
                    "rtdetr_raw": r["rtdetr_raw"], "hvq_max16_raw": r["hvq_mean"],
                    "rtdetr_filtered": r["rt_input"], "hvq_filtered": r["hv_input"],
                    # NOT NULL 컬럼 — v2 run에는 min-max 정규화 값을 기록(아래 메타데이터 명시)
                    "rt_percentile": r["rt_normalized"], "hvq_percentile": r["hvq_normalized"],
                    "rtdetr_positive": r["rtdetr_positive"], "hvq_positive": r["hvq_positive"],
                    "agreement_verdict": r["agreement_verdict"],
                    "fusion_score": r["fusion_score"], "threshold": r["threshold"],
                    "margin": r["margin"], "binary_verdict": r["binary_verdict"],
                    "verdict": r["verdict"],
                } for r in chunk])
        log.info("예측 삽입 진행: %d/%d", min(i + CHUNK, len(missing)), len(missing))

    # --- 3) DB 기록 최종 검증 (전수 + 혼동행렬) ---
    with engine.connect() as conn:
        count = conn.execute(text(
            "SELECT count(*) FROM fusion_analysis.product_predictions "
            "WHERE fusion_run_id=:rid"), {"rid": fusion_run_id}).scalar()
        if count != 24000:
            raise SystemExit(f"예측 기록 수 불일치: {count}/24000 — 다음 실행에서 이어서 기록합니다")
        db_rows = conn.execute(text(
            "SELECT product_id, fusion_score, threshold, margin, binary_verdict, verdict "
            "FROM fusion_analysis.product_predictions WHERE fusion_run_id=:rid"),
            {"rid": fusion_run_id}).all()
    mismatches = []
    by_product = {r["product_id"]: r for r in rows}
    for product_id, fusion_score, threshold, margin, binary_verdict, verdict in db_rows:
        src = by_product[product_id]
        if not (math.isclose(fusion_score, src["fusion_score"], abs_tol=1e-12)
                and math.isclose(threshold, src["threshold"], abs_tol=1e-12)
                and math.isclose(margin, src["margin"], abs_tol=1e-12)
                and binary_verdict == src["binary_verdict"] and verdict == src["verdict"]):
            mismatches.append(product_id)
            if len(mismatches) > 5:
                break
    if mismatches:
        raise SystemExit(f"DB 기록과 재계산 값 불일치: {mismatches}")
    log.info("DB 예측 전수 검증 통과: 24,000제품 오차 0")

    # --- 4) 기준선 v2 스냅샷 등록 (보고서 값, 분자/분모 포함) ---
    report = json.loads(REPORT.read_text())
    computed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    snapshot_rows = []
    for scope_key, split_ref, warning in (
            ("test", "test", None),
            ("overall", "all_including_validation",
             "validation 포함 참고 집계 — 원본 train(16,797제품)과의 중복 UNKNOWN, "
             "학습 포함 가능성 있음; 기준선으로 Test 분리 값을 사용할 것")):
        summary = report[scope_key]
        bt = summary["binary_threshold"]
        hold = summary["final_with_hold"]
        base = {"item": None, "part_id": None, "mapping_version": None, "camera_id": None,
                "date_from": None, "date_to": None,
                "model_version": CONTRACT_VERSION,
                "definition_version": "metrics-v2",
                "computed_at": computed_at,
                "source_scope": "evaluation_reference",
                "baseline_kind": "contract_baseline_v2",
                "review_status": "gt_or_confirmed",
                "split_reference": split_ref}
        metrics = [
            ("product_recall", bt["recall"]["num"], bt["recall"]["den"], bt["recall"]["rate"], None),
            ("product_fpr", bt["fpr"]["num"], bt["fpr"]["den"], bt["fpr"]["rate"], None),
            ("product_precision", bt["precision"]["num"], bt["precision"]["den"], bt["precision"]["rate"], None),
            ("product_f1", bt["f1"]["num"], bt["f1"]["den"], bt["f1"]["rate"], None),
            ("product_fn", bt["fn"], bt["recall"]["den"], bt["fn"] / bt["recall"]["den"], None),
            ("product_fp", bt["fp"], bt["fpr"]["den"], bt["fp"] / bt["fpr"]["den"], None),
            ("product_auroc", 0, 0, bt["auroc"], "rate_without_count_denominator"),
            ("product_average_precision", 0, 0, bt["average_precision"], "rate_without_count_denominator"),
            ("hold_rate", hold["hold_products"], summary["products"], hold["hold_rate"], None),
            ("decision_coverage", hold["decided_products"], summary["products"], hold["coverage"], None),
        ]
        for metric, num, den, value, reason in metrics:
            row = dict(base)
            combined = "; ".join(p for p in (reason, warning) if p)
            row.update({"metric": metric, "numerator": num, "denominator": den,
                        "value": value, "reason": combined or None})
            snapshot_rows.append(row)
    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM public.metrics_snapshots WHERE model_version=:mv "
            "AND baseline_kind='contract_baseline_v2'"), {"mv": CONTRACT_VERSION})
        conn.execute(text(
            "INSERT INTO public.metrics_snapshots "
            "(metric, definition_version, numerator, denominator, value, reason, item, "
            " part_id, camera_id, date_from, date_to, model_version, mapping_version, "
            " computed_at, source_scope, baseline_kind, split_reference, review_status) "
            "VALUES (:metric,:definition_version,:numerator,:denominator,:value,:reason,:item,"
            " :part_id,:camera_id,:date_from,:date_to,:model_version,:mapping_version,"
            " :computed_at,:source_scope,:baseline_kind,:split_reference,:review_status)"),
            snapshot_rows)
    log.info("기준선 v2 스냅샷 등록: %d행 (Test+전체, 분자/분모 포함)", len(snapshot_rows))

    # --- 5) 활성 run 전환 (보고서 일치 확인 후에만) + 무결성 검증 ---
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE fusion_analysis.model_runs SET is_active=false, updated_at=:now "
            "WHERE fusion_run_id<>:rid AND is_active"), {"rid": fusion_run_id, "now": now})
        meta = conn.execute(text(
            "SELECT metadata FROM fusion_analysis.model_runs WHERE fusion_run_id=:rid"),
            {"rid": fusion_run_id}).scalar() or {}
        meta["database_run_activated"] = True
        meta["activated_at"] = now
        conn.execute(text(
            "UPDATE fusion_analysis.model_runs SET is_active=true, status='COMPLETE', "
            "metadata=:meta, updated_at=:now WHERE fusion_run_id=:rid"),
            {"rid": fusion_run_id, "meta": json.dumps(meta), "now": now})
        reviews_after = conn.execute(text("SELECT count(*) FROM public.reviews")).scalar()
        prev_after = conn.execute(text(
            "SELECT count(*) FROM fusion_analysis.product_predictions")).scalar()
    if reviews_after != reviews_before:
        raise SystemExit(f"reviews 행 수 변경 감지: {reviews_before} -> {reviews_after}")
    with engine.connect() as conn:
        old_count = conn.execute(text(
            "SELECT count(*) FROM fusion_analysis.product_predictions "
            "WHERE fusion_run_id=:rid"), {"rid": old_run}).scalar()
    if old_count != 24000 or prev_after != 48000:
        raise SystemExit(
            f"구/신 run 예측 보존 검증 실패: old={old_count} (기대 24000), total={prev_after} (기대 48000)")
    log.info("is_active 전환 완료: %s -> %s (구 run 예측 24,000행 보존, reviews 무결성 유지)", old_run, fusion_run_id)

    summary = {"fusion_run_id": fusion_run_id, "previous_run": old_run,
               "activated_at": now, "predictions": 24000,
               "report_verified": True, "discrepancy": 0,
               "snapshots": len(snapshot_rows),
               "test_f1": report["test"]["binary_threshold"]["f1"]["rate"],
               "test_recall": report["test"]["binary_threshold"]["recall"]["rate"]}
    (LOG_DIR / "activation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))
    log.info("=== 활성화 완료: %s ===", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
