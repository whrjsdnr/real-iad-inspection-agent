from copy import deepcopy
import pytest
from scripts.report_minmax_fusion import evaluate


def inputs():
    profile = {'weights': {'rtdetr': .7, 'hvq': .3}, 'rtdetr_conf_threshold': .4,
               'hvq_score_variant': 'heatmap_mean', 'margin_f1_drop_tolerance': .005}
    root = {'weights': profile['weights'].copy(), 'rtdetr': {'conf_threshold': .4},
            'hvq': {'score_variant': 'heatmap_mean', 'threshold_default': 81.}}
    scores = [(.9,90),(.7,70),(.8,85),(.3,60),(.6,30),(.2,40),(.1,50),(.3,20)]
    rows = [{'product_id': f'v{index}', 'category': 'item', 'split': 'validation',
             'truth': 'defect' if index < 4 else 'normal', 'rtdetr_raw': rt, 'hvq_mean': hv}
            for index,(rt,hv) in enumerate(scores)]
    rows += [{'product_id': f't{index}', 'category': 'item', 'split': 'test',
              'truth': 'defect' if index%2 else 'normal', 'rtdetr_raw': .6, 'hvq_mean': 55.}
             for index in range(12)]
    return rows, profile, root


def test_test_products_use_exact_70_30_weighted_normalized_scores():
    rows, profile, root = inputs()
    parameters = evaluate(rows, profile, root)
    assert parameters['item']['normalizers'] == {'rt_input': {'min':0., 'max':.9}, 'hv_input': {'min':20., 'max':90.}}
    for row in rows[8:]:
        assert row['fusion_score'] == pytest.approx(.7*(.6/.9)+.3*((55.-20.)/70.))
        assert row['hv_input'] == 55.  # continuous heatmap mean, no max16 gate
        expected = 'defect' if row['fusion_score'] >= row['threshold'] else 'normal'
        assert row['binary_verdict'] == expected
        assert row['verdict'] == ('hold' if abs(row['fusion_score']-row['threshold']) <= row['margin'] else expected)


def test_test_scores_and_labels_cannot_change_validation_fit():
    rows, profile, root = inputs()
    first = evaluate(deepcopy(rows), profile, root)
    for row in rows[8:]:
        row['hvq_mean'] = 999.
        row['truth'] = 'defect' if row['truth'] == 'normal' else 'normal'
    second = evaluate(rows, profile, root)
    assert first == second
    assert rows[-1]['fusion_score'] > 1  # unclipped minmax extrapolation is explicit


def test_wrong_weights_and_constant_validation_range_are_rejected():
    rows, profile, root = inputs()
    profile['weights'] = {'rtdetr': .3, 'hvq': .7}
    with pytest.raises(ValueError, match='weights'):
        evaluate(deepcopy(rows), profile, root)
    rows, profile, root = inputs()
    for row in rows[:8]:
        row['hvq_mean'] = 10.
    with pytest.raises(ValueError, match='minmax range'):
        evaluate(rows, profile, root)


def test_single_model_hvq_reference_is_validation_fitted_not_max16_default():
    """hvq_positive must not use the legacy max16-scale threshold_default (81) on heatmap_mean."""
    import scripts.report_minmax_fusion as rep
    rows, profile, root = inputs()
    hv_lo, hv_hi, th_norm, info = rep.fit_single_model_reference(rows, profile)
    raw_default = root['hvq']['threshold_default']
    assert raw_default != info['threshold_raw_heatmap_mean']
    assert info['threshold_source'] == 'validation_split_max_f1_interval_midpoint'
    evaluate(rows, profile, root)
    defects = [r for r in rows if r['truth'] == 'defect']
    detected = sum(1 for r in defects if r['hvq_positive'])
    # reference sanity: a validation-fitted threshold must catch most defect products
    assert detected / len(defects) > 0.5
    # the max16-scale default applied to heatmap_mean is a different (wrong-scale) verdict
    ref_verdicts = {r['hvq_positive'] for r in rows}
    max16_verdicts = {r['hvq_mean'] >= raw_default for r in rows}
    assert ref_verdicts != max16_verdicts or raw_default <= max(r['hvq_mean'] for r in rows)
