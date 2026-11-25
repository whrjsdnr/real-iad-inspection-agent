import csv
import json

import pytest

from app.cohort_performance import derive, summarize
from app import status


def fixture_files(tmp_path):
    rows = []
    for index in range(20):
        positive = index < 8 or 10 <= index < 13
        rows.append({'product_id': f'p{index}', 'category': 'brush',
                     'split': 'test' if index < 4 else 'validation' if index < 7 else 'train',
                     'truth': 'defect' if index < 10 else 'normal',
                     'binary_verdict': 'defect' if positive else 'normal',
                     'verdict': 'hold' if index in (7, 12) else 'defect' if positive else 'normal',
                     'fusion_score': 0.9 if positive else 0.1,
                     'hvq_positive': positive, 'rtdetr_positive': positive})
    predictions = tmp_path/'all_predictions.csv'
    with predictions.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = tmp_path/'manifest.csv'
    with manifest.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['product_id', 'category', 'split', 'truth', 'camera'])
        writer.writeheader()
        for row in rows:
            for camera in ('C1', 'C2', 'C3', 'C4', 'C5'):
                writer.writerow({**{key: row[key] for key in writer.fieldnames if key != 'camera'}, 'camera': camera})
    source = tmp_path/'performance.json'
    source.write_text(json.dumps({'status': 'FINAL_COMPLETE', 'model_version': 'test-model',
                                 'cohort_products': 20, 'split_counts': {'test': 4, 'validation': 3, 'train': 13},
                                 'test': {'products': 4, 'binary_threshold': {'tp': 4, 'fn': 0, 'fp': 0, 'tn': 0, 'recall': 1., 'f1': 1., 'auroc': None}}}))
    return source, manifest


def test_twenty_products_all_splits_keep_hold_separate(tmp_path):
    source, manifest = fixture_files(tmp_path)
    result = derive(source, manifest)
    overall = result['overall']
    binary = overall['binary_threshold']
    assert overall['products'] == 20
    assert (binary['tp'], binary['fn'], binary['fp'], binary['tn']) == (8, 2, 3, 7)
    assert binary['f1']['rate'] == pytest.approx(16/21)
    assert binary['recall'] == {'num': 8, 'den': 10, 'rate': .8}
    hold = overall['final_with_hold']
    assert hold['hold_products'] == 2 and hold['coverage'] == .9
    assert hold['decided_only_metrics']['f1']['rate'] == pytest.approx(14/18)
    assert result['test_reference']['products'] == 4
    assert result['contains_calibration_products'] and not result['independent_sql_verified']


def test_tied_scores_and_empty_denominators():
    rows = [{'truth': truth, 'binary_verdict': 'normal', 'verdict': 'hold', 'fusion_score': .5, 'hvq_positive': False, 'rtdetr_positive': False} for truth in ('defect', 'normal')]
    result = summarize(rows)
    assert result['binary_threshold']['auroc'] == .5
    assert result['binary_threshold']['average_precision'] == .5
    assert result['final_with_hold']['decided_only_metrics']['f1']['rate'] is None


def test_duplicate_predictions_are_rejected(tmp_path):
    source, manifest = fixture_files(tmp_path)
    predictions = tmp_path/'all_predictions.csv'
    predictions.write_text(predictions.read_text().replace('p19,', 'p18,'))
    with pytest.raises(ValueError, match='Duplicate'):
        derive(source, manifest)


def test_duplicate_manifest_camera_is_rejected(tmp_path):
    source, manifest = fixture_files(tmp_path)
    manifest.write_text(manifest.read_text().replace('C5', 'C4'))
    with pytest.raises(ValueError, match='duplicate camera'):
        derive(source, manifest)


def test_source_test_must_be_reproduced(tmp_path):
    source, manifest = fixture_files(tmp_path)
    report = json.loads(source.read_text())
    report['test']['binary_threshold']['fn'] = 1
    source.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='test reproduction'):
        derive(source, manifest)


def test_api_uses_bound_cohort_but_falls_back_after_source_changes(tmp_path, monkeypatch):
    source, manifest = fixture_files(tmp_path)
    derived = tmp_path/'cohort.json'
    derived.write_text(json.dumps(derive(source, manifest)))
    (tmp_path/'latest.json').write_text(json.dumps({'report': str(source)}))
    monkeypatch.setenv('FINAL_PERFORMANCE_DIR', str(tmp_path))
    monkeypatch.setenv('COHORT_PERFORMANCE_REPORT', str(derived))
    summary = status.final_performance_summary(status.final_performance_payload())
    assert summary['metrics']['evaluation_products'] == 20
    assert summary['metrics']['test_products'] == 4
    assert summary['metrics']['csv_consistency_verified']
    assert summary['metrics']['verified'] is False
    source.write_text(source.read_text()+'\n')
    summary = status.final_performance_summary(status.final_performance_payload())
    assert summary['metrics']['evaluation_scope'] == 'test'
    assert summary['metrics']['evaluation_products'] == 4
