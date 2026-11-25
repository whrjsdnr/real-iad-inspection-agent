"""Read-only audit of stored predictions against their saved max16 fusion contract."""
import collections
import csv
import json
import math
import sqlite3
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1')


def main():
    pipeline = BASE/'background_pipeline'
    contract = json.loads((pipeline/'contract.json').read_text())
    fitted = json.loads((pipeline/'parameters.json').read_text())
    config = json.loads((ROOT/'config/fusion.json').read_text())
    latest = json.loads((BASE/'final_performance/latest.json').read_text())
    report = json.loads(Path(latest['report']).read_text())
    assert contract == report['profile'], 'Report/profile contract mismatch'
    with (Path(latest['directory'])/'all_predictions.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    validation_ids = {row['product_id'] for row in rows if row['split'] == 'validation'}
    assert validation_ids == set(fitted['validation_product_ids'])
    assert not validation_ids & {row['product_id'] for row in rows if row['split'] == 'test'}
    database = sqlite3.connect('file:'+str(BASE/'max16_scores/hvq_max16.sqlite')+'?mode=ro', uri=True)
    try:
        maxima = {row[0]: row[1:] for row in database.execute('SELECT product_id,max(rtdetr_raw),max(hvq_max16),count(*),count(DISTINCT camera) FROM views GROUP BY product_id')}
    finally:
        database.close()
    groups = collections.defaultdict(list)
    def equal(a, b):
        assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-12), f'Value mismatch: {a} != {b}'
    for row in rows:
        rt, hv, count, cameras = maxima[row['product_id']]
        assert count == cameras == 5
        equal(row['rtdetr_raw'], rt)
        equal(row['hvq_max16_raw'], hv)
        category = row['category']
        rp, hp = rt >= contract['rtdetr_conf_threshold'], hv >= contract['hvq_thresholds'][category]
        assert (row['rtdetr_positive'] == 'True') == rp
        assert (row['hvq_positive'] == 'True') == hp
        equal(row['rtdetr_filtered'], rt if rp else 0.)
        equal(row['hvq_filtered'], hv if hp else 0.)
        parameters = fitted['categories'][category]
        for model, column in (('rtdetr', 'rt'), ('hvq', 'hvq')):
            lookup = parameters['lookups'][model]
            score = np.interp(float(row[f'{model}_filtered']), lookup['x'], lookup['p'], left=0., right=1.)
            equal(row[f'{column}_percentile'], score)
        score = sum(contract['weights'][model]*float(row[f'{column}_percentile']) for model, column in (('rtdetr', 'rt'), ('hvq', 'hvq')))
        equal(row['fusion_score'], score)
        equal(row['threshold'], parameters['threshold'])
        equal(row['margin'], parameters['margin'])
        verdict = 'defect' if score >= parameters['threshold'] else 'normal'
        assert row['binary_verdict'] == verdict
        assert row['verdict'] == ('hold' if abs(score-parameters['threshold']) <= parameters['margin'] else verdict)
        if row['split'] == 'validation':
            groups[category].append(row)
    tolerance = config['calibration']['f1_drop_tolerance']
    assert contract['margin'] == f'validation_F1_drop_tolerance_{tolerance}'
    for category, validation in groups.items():
        parameters = fitted['categories'][category]
        for model in ('rtdetr', 'hvq'):
            unique, counts = np.unique([float(row[f'{model}_filtered']) for row in validation], return_counts=True)
            ranks = np.cumsum(counts)-(counts-1)/2
            assert np.allclose(unique, parameters['lookups'][model]['x'], rtol=0, atol=1e-12)
            assert np.allclose((ranks-.5)/len(validation), parameters['lookups'][model]['p'], rtol=0, atol=1e-12)
        scores = np.array([float(row['fusion_score']) for row in validation])
        truth = np.array([row['truth'] == 'defect' for row in validation])
        ends = np.unique(np.r_[scores, 1.])
        curve = []
        lower = 0.
        for upper in ends:
            predicted = scores >= upper
            tp = int((truth & predicted).sum()); fp = int((~truth & predicted).sum()); fn = int((truth & ~predicted).sum())
            curve.append((lower, float(upper), 2*tp/(2*tp+fp+fn)))
            lower = float(upper)
        best = max(cell[2] for cell in curve)
        chosen = max(index for index, cell in enumerate(curve) if cell[2] == best)
        threshold = (curve[chosen][0]+curve[chosen][1])/2
        if threshold == curve[chosen][0] and chosen:
            threshold = curve[chosen][1]
        equal(parameters['threshold'], threshold)
        left = right = chosen
        while left and curve[left-1][2] >= best-tolerance:
            left -= 1
        while right+1 < len(curve) and curve[right+1][2] >= best-tolerance:
            right += 1
        margin = min(threshold-curve[left][0], curve[right][1]-threshold)
        if margin and left and margin == threshold-curve[left][0]:
            margin = float(np.nextafter(margin, 0.))
        equal(parameters['margin'], margin)
    result = {'status': 'PASSED_CURRENT_MAX16_CONTRACT', 'products_checked': len(rows),
              'view_scores_checked': sum(row[2] for row in maxima.values()), 'validation_products_checked': len(validation_ids),
              'categories_checked': len(groups), 'contract': contract,
              'original_minmax_contract_matches': False,
              'root_config_differences': {'rtdetr_conf_threshold': [config['rtdetr']['conf_threshold'], contract['rtdetr_conf_threshold']],
                                          'hvq_score_variant': [config['hvq']['score_variant'], contract['hvq_score_variant']]},
              'notes': ['No inference or stored verdict/parameter writes.', 'All-product reference includes calibration products; training overlap remains unknown.']}
    output = ROOT/'reports/gui_validation/fusion-contract-audit.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key != 'contract'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
