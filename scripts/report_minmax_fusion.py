"""Evaluate the user-selected RT0.4/heatmap_mean/minmax/70:30 contract from saved scores."""
import collections
import csv
import hashlib
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.cohort_performance import summarize, sha256
from fusion_calibration import threshold_and_margin

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1')


def fit_single_model_reference(rows, profile):
    """Reference-only HVQ standalone threshold fitted on validation products only.

    threshold_and_margin operates on [0,1] scores, so fit on validation min-max normalized
    heatmap_mean (same minmax semantics as the fusion normalization). The root
    hvq.threshold_default belongs to the legacy max16 score scale and must never be
    applied to continuous heatmap_mean.
    """
    val_hv = [row['hvq_mean'] for row in rows if row['split'] == 'validation']
    hv_lo, hv_hi = min(val_hv), max(val_hv)
    if not math.isfinite(hv_lo+hv_hi) or hv_lo == hv_hi:
        raise ValueError('Degenerate validation hvq minmax range')
    val_norm = [(x-hv_lo)/(hv_hi-hv_lo) for x in val_hv]
    fit = threshold_and_margin(val_norm,
                               [row['truth'] == 'defect' for row in rows if row['split'] == 'validation'],
                               drop_tolerance=profile['margin_f1_drop_tolerance'])
    info = {
        'score_variant': 'product_max_view_heatmap_mean',
        'normalization': f'validation minmax [{hv_lo:.6f}, {hv_hi:.6f}]',
        'threshold_source': 'validation_split_max_f1_interval_midpoint',
        'threshold_normalized': fit['threshold'],
        'threshold_raw_heatmap_mean': hv_lo + fit['threshold']*(hv_hi-hv_lo),
        'margin_normalized': fit['margin'],
        'validation_best_f1': fit['f1'],
        'note': ('HVQ 단독 참고 판정. 운영 퓨전 규칙과 무관. '
                 'fusion.json의 hvq.threshold_default는 max16 점수 척도 전용이며 heatmap_mean에 적용 금지.'),
    }
    return hv_lo, hv_hi, fit['threshold'], info


def evaluate(rows, profile, base_config):
    if profile['weights'] != base_config['weights']:
        raise ValueError('Root/contract weights mismatch')
    if (profile['rtdetr_conf_threshold'] != base_config['rtdetr']['conf_threshold']
            or profile['hvq_score_variant'] != base_config['hvq']['score_variant']):
        raise ValueError('Root score definition mismatch')
    if len({row['product_id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate product')
    for row in rows:
        row['rt_input'] = row['rtdetr_raw'] if row['rtdetr_raw'] >= profile['rtdetr_conf_threshold'] else 0.
        row['hv_input'] = row['hvq_mean']
    hv_lo, hv_hi, reference_threshold, _ = fit_single_model_reference(rows, profile)
    parameters = {}
    for row in rows:
        row['hvq_positive'] = (row['hvq_mean']-hv_lo)/(hv_hi-hv_lo) >= reference_threshold
    for category in sorted({row['category'] for row in rows}):
        validation = [row for row in rows if row['category'] == category and row['split'] == 'validation']
        if not validation or {row['truth'] for row in validation} != {'normal', 'defect'}:
            raise ValueError('Missing two-class validation support')
        normalizers = {}
        for key in ('rt_input', 'hv_input'):
            lo, hi = min(row[key] for row in validation), max(row[key] for row in validation)
            if not math.isfinite(lo+hi) or lo == hi:
                raise ValueError('Degenerate validation minmax range')
            normalizers[key] = {'min': lo, 'max': hi}
        selected = [row for row in rows if row['category'] == category]
        for row in selected:
            for key, target in (('rt_input', 'rt_normalized'), ('hv_input', 'hvq_normalized')):
                stats = normalizers[key]
                row[target] = (row[key]-stats['min'])/(stats['max']-stats['min'])
            row['fusion_score'] = profile['weights']['rtdetr']*row['rt_normalized']+profile['weights']['hvq']*row['hvq_normalized']
        fit = threshold_and_margin([row['fusion_score'] for row in validation], [row['truth'] == 'defect' for row in validation],
                                   drop_tolerance=profile['margin_f1_drop_tolerance'])
        parameters[category] = {'normalizers': normalizers, 'validation_products': len(validation),
                                'threshold': fit['threshold'], 'margin': fit['margin'],
                                'validation_best_f1': fit['f1'], 'plateau_lower': fit['plateau_lower'],
                                'plateau_upper': fit['plateau_upper']}
        for row in selected:
            row['threshold'], row['margin'] = fit['threshold'], fit['margin']
            row['binary_verdict'] = 'defect' if row['fusion_score'] >= fit['threshold'] else 'normal'
            row['verdict'] = 'hold' if abs(row['fusion_score']-fit['threshold']) <= fit['margin'] else row['binary_verdict']
            row['rtdetr_positive'] = row['rtdetr_raw'] >= profile['rtdetr_conf_threshold']
            # hvq_positive is set globally before the loop (validation-fitted reference).
    return parameters


def main():
    profile = json.loads((ROOT/'config/fusion_evaluation.json').read_text())
    config = json.loads((ROOT/'config/fusion.json').read_text())
    source = BASE/'max16_scores/hvq_max16.sqlite'
    connection = sqlite3.connect('file:'+str(source)+'?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in connection.execute('''SELECT p.product_id,p.category,p.split,p.truth,
          max(v.rtdetr_raw) AS rtdetr_raw,max(v.hvq_mean) AS hvq_mean,
          p.hvq_mean_max AS product_hvq_mean,count(*) AS views,count(DISTINCT v.camera) AS cameras,
          group_concat(v.camera) AS camera_ids
          FROM products p JOIN views v USING(product_id) WHERE p.status='COMPLETED' GROUP BY p.product_id''')]
    finally:
        connection.close()
    latest = json.loads((BASE/'final_performance/latest.json').read_text())
    source_report = json.loads(Path(latest['report']).read_text())
    with (Path(latest['directory'])/'all_predictions.csv').open() as stream:
        identity = {row['product_id']: (row['category'], row['split'], row['truth']) for row in csv.DictReader(stream)}
    if len(rows) != source_report['cohort_products'] or {row['product_id'] for row in rows} != set(identity):
        raise ValueError('Full source cohort identity mismatch')
    for row in rows:
        if (row['views'] != 5 or row['cameras'] != 5 or set(row['camera_ids'].split(',')) != {'C1','C2','C3','C4','C5'}
                or (row['category'],row['split'],row['truth']) != identity[row['product_id']]):
            raise ValueError('Five-view or GT/split mismatch')
        if not math.isclose(row['hvq_mean'], row['product_hvq_mean'], rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError('Saved heatmap_mean max inconsistency')
    fitted = evaluate(rows, profile, config)
    _,_,_, reference_info = fit_single_model_reference(rows, profile)
    test = [row for row in rows if row['split'] == 'test']
    validation_ids = [row['product_id'] for row in rows if row['split'] == 'validation']
    assert not set(validation_ids) & {row['product_id'] for row in test}
    identity_hash = hashlib.sha256(json.dumps({'profile': profile, 'parameters': fitted}, sort_keys=True).encode()).hexdigest()
    report = {'status': 'FINAL_COMPLETE', 'timestamp': datetime.now(timezone.utc).isoformat(),
              'model_version': 'fusion-minmax-mean-rt40-w70-30:'+identity_hash[:24],
              'source_model_version': source_report['model_version'], 'database_run_activated': False,
              'evaluation_scope': 'all_inferred_products_reference', 'cohort_products': len(rows),
              'cohort_views': sum(row['views'] for row in rows), 'split_counts': dict(collections.Counter(row['split'] for row in rows)),
              'profile': profile, 'parameters': fitted, 'validation_product_ids': validation_ids,
              'test_used_for_fitting': False, 'overall': summarize(rows), 'test': summarize(test),
              'by_category_overall': {category: summarize([row for row in rows if row['category'] == category]) for category in fitted},
              'training_overlap': source_report['training_overlap'], 'csv_consistency_verified': True,
              'independent_sql_verified': False, 'agent_tool_verified': False, 'deployment_eligible': False,
              'source_report': latest['report'], 'source_report_sha256': sha256(latest['report']),
              'root_config_sha256': sha256(ROOT/'config/fusion.json'),
              'evaluation_config_sha256': sha256(ROOT/'config/fusion_evaluation.json'),
              'source_models': config['model_versions'],
              'single_model_reference': reference_info,
              'notes': ['Continuous heatmap_mean is not gated by max16 thresholds.',
                        'RT product score is zero if no saved box reaches 0.4.',
                        'Minmax stats, TH and margin are fitted only on validation products.',
                        'No clipping beyond validation range; these scores are not probabilities.',
                        'All-product reference includes validation; the inference cohort was not used to train either vision model (owner-confirmed).',
                        'HVQ standalone single-model block is a validation-fitted reference only and never gates the fused score.',
                        'No operating configuration, DB verdict or model inference was changed.']}
    macro = {}
    for key in ('f1', 'auroc'):
        values = [category['binary_threshold'][key] for category in report['by_category_overall'].values()]
        values = [value['rate'] if isinstance(value, dict) else value for value in values]
        values = [value for value in values if value is not None]
        macro[key] = sum(values)/len(values) if values else None
    report['overall_category_macro'] = macro
    out = ROOT/'reports/final_performance_minmax'
    out.mkdir(parents=True, exist_ok=True)
    target = out/'performance.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    with (out/'all_predictions.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    pointer = out/'latest.tmp'
    pointer.write_text(json.dumps({'report': str(target), 'directory': str(out), 'model_version': report['model_version']}, indent=2))
    pointer.replace(out/'latest.json')
    print(json.dumps({'report': str(target), 'model_version': report['model_version'], 'overall': report['overall'], 'test': report['test']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
