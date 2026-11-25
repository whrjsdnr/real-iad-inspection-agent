"""지표 계산 — 분자/분모 함께 저장·표시. DB 접근은 dbconn(엔진) 공용 추상화.

지표:
  - 제품 단위 Recall / FPR / F1 (GT truth_label 대비 verdict, 확정 판정만 — 보류는 의심 건수로 별도 집계)
  - 확정 불량률 / 부위 미탐률 / 부위 오탬률 / 촬영·처리 실패율 (검수 확정 사례만, tools.compute_inspection_metrics 재사용)
  - 픽셀 AUPRO (GT 마스크 있는 사례만)
  - 처리 비용: 제품당 p95 / 피크 메모리 (기존 벤치마크 재사용, 출처 명시)

확정 FP/FN 집계는 검수 완료(review_state=confirmed) 사례로만 계산하고,
검수 전 데이터는 "의심 건수"로만 표시한다.

실행: ~/agent/.venv/bin/python metrics.py [--item toothbrush] [--save]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import dbconn  # 공용 엔진 추상화 (SQLite 폐백 / PostgreSQL)

AGENT_ROOT = Path(__file__).resolve().parent

PRODUCT_METRICS = ("product_recall", "product_fpr", "product_precision", "product_f1", "hold_rate", "decision_coverage", "capture_process_failure_rate")
SUSPECT_METRICS = ("suspect_hold_count", "suspect_pending_reviews", "review_confirmed_count")
COST_METRICS = ("cost_p95_ms_per_product", "peak_rss_mb")

COST_BASELINE = {
    "source": "benchmark:joint_config3(threads2+overlap)",
    "p95_ms_per_view": 395.0,
    "views_per_product": 5,
    "peak_rss_mb": 1368,
    "note": "제품당 p95 = 뷰 p95 x 5 (순차 합산 근사)",
}


def _window(params: dict, clause_col: str, date_from: str | None, date_to: str | None) -> str:
    sql = ""
    if date_from:
        sql += f" AND {clause_col} >= :date_from"
        params["date_from"] = date_from
    if date_to:
        sql += f" AND {clause_col} <= :date_to"
        params["date_to"] = date_to
    return sql


def product_metrics(*, item=None, date_from=None, date_to=None, model_version=None):
    """GT가 있는 최신 제품 시도만 집계한다. mock/fixture는 운영 지표에서 제외한다.

    부분 부위의 정상 검수만으로 전체 제품 정상을 확정하지 않는다. 제품 GT가
    없으면 part_id=product, camera_id=ALL인 명시적 제품 검수만 대체 GT로 쓴다.
    """
    params={}; filters="1=1"
    for column,value in [("item",item),("model_version",model_version)]:
        if value is not None: filters += f" AND a.{column}=:{column}"; params[column]=value
    filters += _window(params,"a.processed_at",date_from,date_to)
    rows=dbconn.query(f"""SELECT a.* FROM inspection_attempts a WHERE {filters}
        AND a.model_version NOT LIKE 'mock%'
        AND NOT EXISTS (SELECT 1 FROM inspection_views v WHERE v.attempt_id=a.attempt_id
                        AND v.image_uri LIKE 'mock://%')""",params)
    latest={}
    for row in rows:
        key=(row['product_id'],row['model_version'])
        stamp=(row.get('processed_at') or row.get('started_at') or '',row['attempt_id'])
        if key not in latest or stamp > latest[key][0]: latest[key]=(stamp,row)
    selected=[v[1] for v in latest.values()]
    completed=[r for r in selected if r['status']=='completed']
    hold=sum(r.get('verdict')=='hold' for r in completed)
    counts=dict(tp=0,fn=0,fp=0,tn=0); labeled=decided=suspect=0
    mixed=model_version is None and len({r['model_version'] for r in completed})>1
    for row in completed:
        gt=row.get('truth_label')
        if gt not in ('normal','defect'):
            reviews=dbconn.query("""SELECT truth_label FROM reviews WHERE product_id=:pid
              AND part_id='product' AND camera_id='ALL' AND review_state='confirmed'
              ORDER BY reviewed_at DESC, review_id DESC""",{'pid':row['product_id']})
            gt=reviews[0]['truth_label'] if reviews else None
        if gt not in ('normal','defect'): suspect+=1; continue
        labeled+=1
        if row.get('verdict') not in ('normal','defect'):continue
        decided+=1
        if mixed:continue
        name=('tp' if row['verdict']=='defect' else 'fn') if gt=='defect' else ('fp' if row['verdict']=='defect' else 'tn')
        counts[name]+=1
    def ratio(n,d):return {'num':n,'den':d,'rate':n/d if d else None}
    tp,fn,fp,tn=[counts[k] for k in ['tp','fn','fp','tn']]
    failed=sum(r['status']!='completed' for r in rows)
    return {**counts,'hold':hold,'suspect_products':suspect,'labeled_products':labeled,
            'reason':'mixed_model_baselines_require_filter' if mixed else None,
            'product_recall':ratio(tp,tp+fn),'product_fpr':ratio(fp,fp+tn),
            'product_precision':ratio(tp,tp+fp),'product_f1':ratio(2*tp,2*tp+fp+fn),
            'hold_rate':ratio(hold,len(completed)), 'decision_coverage':ratio(decided,labeled),
            'capture_process_failure_rate':ratio(failed,len(rows)),
            'source_scope':'operational_gt_or_product_review_excluding_mock'}


def review_metrics(item: str, **kwargs) -> dict:
    from app.tools import compute_inspection_metrics

    return compute_inspection_metrics(item=item, **kwargs)


def suspect_counts(*, item: str | None = None) -> dict:
    where, params = "", {}
    if item:
        where, params = " WHERE item=:item", {"item": item}
    hold_sql = (f"SELECT COUNT(*) AS c FROM inspection_attempts{where} AND verdict='hold'"
                if where else "SELECT COUNT(*) AS c FROM inspection_attempts WHERE verdict='hold'")
    hold = dbconn.query(hold_sql, params)[0]["c"]
    pending = dbconn.query(
        "SELECT COUNT(*) AS c FROM reviews WHERE review_state='pending'")[0]["c"]
    confirmed = dbconn.query(
        "SELECT COUNT(*) AS c FROM reviews WHERE review_state='confirmed'")[0]["c"]
    return {"suspect_hold_count": hold, "suspect_pending_reviews": pending,
            "review_confirmed_count": confirmed}


def aupro(*, item=None, steps=50):
    """원본 좌표 raw score map과 카메라별 GT 연결이 검증되기 전엔 N/A.

    기존 코드는 같은 제품의 다른 시점 마스크를 선택하거나 컬러PNG의 밝기를
    score로 사용했다. 명시적인 raw-map/GT 쌍은 pixel_metrics.compute_aupro에 전달한다.
    """
    return {"metric":"aupro","value":None,"used_products":0,
            "reason":"no_gt_mask","detail":"explicit_verified_camera_mask_and_raw_map_required"}


_GT_INDEX: dict[str, Path] | None = None


def _find_gt_mask(product_id: str) -> Path | None:
    """product_id → GT 마스크 경로(원본 해상도, evidence 저장 시 224로 리사이즈된 png)."""
    global _GT_INDEX
    if _GT_INDEX is None:
        dataset = AGENT_ROOT.parent / "dataset"
        _GT_INDEX = {p.stem: p for p in dataset.rglob("*.png")} if dataset.is_dir() else {}
    return _GT_INDEX.get(product_id)


def save_snapshot(*, metric, num, den, value, reason=None, item=None,
                  part_id=None, camera_id=None, date_from=None, date_to=None,
                  model_version=None, mapping_version=None, source_scope="operational",
                  baseline_kind="measured_baseline", split_reference=None, review_status="gt_or_confirmed") -> None:
    dbconn.execute(
        """INSERT INTO metrics_snapshots
           (metric, definition_version, numerator, denominator, value, reason,
            item, part_id, camera_id, date_from, date_to, model_version,
            mapping_version, computed_at, source_scope, baseline_kind, split_reference, review_status)
           VALUES (:metric, :dv, :num, :den, :value, :reason, :item, :part_id,
                   :camera_id, :date_from, :date_to, :model_version,
                   :mapping_version, :computed_at, :source_scope, :baseline_kind, :split_reference, :review_status)""",
        {"metric": metric, "dv": "metrics-v2", "num": num, "den": den,
         "value": value, "reason": reason, "item": item, "part_id": part_id,
         "camera_id": camera_id, "date_from": date_from, "date_to": date_to,
         "model_version": model_version, "mapping_version": mapping_version,
         "computed_at": datetime.now().isoformat(timespec="seconds"),
         "source_scope": source_scope, "baseline_kind": baseline_kind,
         "split_reference": split_reference, "review_status": review_status})


def compute_all(*, item: str | None = None, date_from=None, date_to=None,
                model_version=None, save: bool = False,
                include_aupro: bool = False) -> dict:
    out = {"filters": {"item": item, "date_from": date_from, "date_to": date_to,
                       "model_version": model_version},
           "product": product_metrics(item=item, date_from=date_from,
                                      date_to=date_to, model_version=model_version),
           "suspect": suspect_counts(item=item),
           "cost_baseline": {"status":"NOT_MEASURED", "reason":"view_p95_times_five_is_not_product_p95"}}
    if include_aupro:
        out["aupro"] = aupro(item=item)
    if save:
        pm = out["product"]
        base = dict(item=item, date_from=date_from, date_to=date_to,
                    model_version=model_version, mapping_version="parts-roi-v1")
        for m in PRODUCT_METRICS:
            r = pm[m]
            save_snapshot(metric=m, num=r["num"], den=r["den"], value=r["rate"],
                          reason=None if r["den"] else "denominator_zero", **base)

    return out


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="지표 계산 (분자/분모 함께)")
    p.add_argument("--item", default=None)
    p.add_argument("--date-from", default=None)
    p.add_argument("--date-to", default=None)
    p.add_argument("--model-version", default=None)
    p.add_argument("--aupro", action="store_true")
    p.add_argument("--save", action="store_true")
    p.add_argument("--json-out", default=None)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    result = compute_all(item=args.item, date_from=args.date_from,
                         date_to=args.date_to, model_version=args.model_version,
                         save=args.save, include_aupro=args.aupro)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
