"""Aggregate stored product verdicts without fitting thresholds or executing models."""
import collections
import csv
import hashlib
import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def binary_metrics(rows, prediction):
    counts = collections.Counter((row['truth'] == 'defect', prediction(row)) for row in rows)
    tp, fn, fp, tn = (counts[key] for key in ((True, True), (True, False), (False, True), (False, False)))
    def rate(num, den):
        return {'num': num, 'den': den, 'rate': num / den if den else None}
    return dict(tp=tp, fn=fn, fp=fp, tn=tn, recall=rate(tp, tp+fn), fpr=rate(fp, fp+tn),
                f1=rate(2*tp, 2*tp+fp+fn), precision=rate(tp, tp+fp))


def summarize(rows):
    binary = binary_metrics(rows, lambda row: row['binary_verdict'] == 'defect')
    groups = []
    for _, items in itertools.groupby(sorted(rows, key=lambda row: row['fusion_score']), key=lambda row: row['fusion_score']):
        labels = [row['truth'] == 'defect' for row in items]
        groups.append((sum(labels), len(labels)-sum(labels)))
    ng, ok = binary['tp']+binary['fn'], binary['fp']+binary['tn']
    negatives = wins = 0
    for positive, negative in groups:
        wins += positive*(negatives+negative/2)
        negatives += negative
    tp = seen = 0
    ap = 0.
    for positive, negative in reversed(groups):
        tp += positive
        seen += positive+negative
        if ng:
            ap += positive/ng*tp/seen
    binary.update(auroc=wins/(ng*ok) if ng and ok else None, average_precision=ap if ng and ok else None)
    decided = [row for row in rows if row['verdict'] != 'hold']
    hold = len(rows)-len(decided)
    return {'products': len(rows), 'binary_threshold': binary,
            'final_with_hold': {'decided_products': len(decided), 'hold_products': hold,
                                'hold_rate': hold/len(rows) if rows else None,
                                'coverage': len(decided)/len(rows) if rows else None,
                                'decided_only_metrics': binary_metrics(decided, lambda row: row['verdict'] == 'defect')},
            'single_model_hvq': binary_metrics(rows, lambda row: row['hvq_positive']),
            'single_model_rtdetr': binary_metrics(rows, lambda row: row['rtdetr_positive'])}


def derive(source_report, manifest):
    source_report, manifest = Path(source_report), Path(manifest)
    report = json.loads(source_report.read_text())
    if report.get('status') != 'FINAL_COMPLETE':
        raise ValueError('Source final report is not complete')
    predictions = source_report.parent/'all_predictions.csv'
    expected, cameras = {}, collections.defaultdict(set)
    with manifest.open() as stream:
        for row in csv.DictReader(stream):
            identity = (row['category'], row['split'], row['truth'])
            product = row['product_id']
            if product in expected and expected[product] != identity:
                raise ValueError('Manifest product metadata conflict')
            if row['camera'] in cameras[product]:
                raise ValueError('Manifest duplicate camera')
            expected[product] = identity
            cameras[product].add(row['camera'])
    if any(views != {'C1', 'C2', 'C3', 'C4', 'C5'} for views in cameras.values()):
        raise ValueError('Manifest incomplete five-view product')
    with predictions.open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != report['cohort_products'] or len(expected) != len(rows):
        raise ValueError('Cohort count mismatch')
    seen = set()
    for row in rows:
        product = row['product_id']
        if product in seen or expected.get(product) != (row['category'], row['split'], row['truth']):
            raise ValueError('Duplicate, unknown or mismatched product')
        seen.add(product)
        if row['truth'] not in ('normal', 'defect') or row['binary_verdict'] not in ('normal', 'defect') or row['verdict'] not in ('normal', 'defect', 'hold'):
            raise ValueError('Invalid truth or stored verdict')
        for key in ('hvq_positive', 'rtdetr_positive'):
            if row[key] not in ('True', 'False'):
                raise ValueError('Invalid component boolean')
            row[key] = row[key] == 'True'
        row['fusion_score'] = float(row['fusion_score'])
        if not math.isfinite(row['fusion_score']):
            raise ValueError('Nonfinite stored score')
    splits = dict(collections.Counter(row['split'] for row in rows))
    if splits != report['split_counts']:
        raise ValueError('Split identity mismatch')
    test = summarize([row for row in rows if row['split'] == 'test'])
    for key in ('tp', 'fn', 'fp', 'tn', 'recall', 'f1', 'auroc'):
        actual, original = test['binary_threshold'][key], report['test']['binary_threshold'][key]
        actual = actual.get('rate') if isinstance(actual, dict) else actual
        original = original.get('rate') if isinstance(original, dict) else original
        if (actual is None) != (original is None) or (actual is not None and not math.isclose(actual, original, rel_tol=1e-10, abs_tol=1e-12)):
            raise ValueError(f'Source test reproduction failed: {key}')
    by_category = {category: summarize([row for row in rows if row['category'] == category]) for category in sorted({row['category'] for row in rows})}
    macro = {}
    for key in ('f1', 'recall', 'auroc'):
        values = [entry['binary_threshold'][key] for entry in by_category.values()]
        values = [value.get('rate') if isinstance(value, dict) else value for value in values]
        values = [value for value in values if value is not None]
        macro[key] = sum(values)/len(values) if values else None
    return {'scope': 'all_inferred_products_reference', 'timestamp': datetime.now(timezone.utc).isoformat(),
            'model_version': report['model_version'], 'source_report': str(source_report.resolve()),
            'source_report_sha256': sha256(source_report), 'predictions_sha256': sha256(predictions),
            'manifest_sha256': sha256(manifest), 'split_counts': splits,
            'overall': summarize(rows), 'category_macro': macro, 'by_category': by_category,
            'test_reference': report['test'], 'csv_consistency_verified': True,
            'independent_sql_verified': False, 'training_overlap': report.get('training_overlap'),
            'contains_calibration_products': True, 'deployment_eligible': False}
