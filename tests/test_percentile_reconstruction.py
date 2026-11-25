"""합성 검증이며 원 실험 성능 재현을 뜻하지 않는다."""
import numpy as np
import pytest
from fusion_calibration import percentile_lookup,percentile,product_scores,fit,predict,threshold_and_margin

def test_ties_midrank_interpolation_and_outside():
 l=percentile_lookup([1,1,3,5]);assert l['p']==[.25,.625,.875]
 assert percentile([0,1,2,3,5,6],l)==pytest.approx([0,.25,.4375,.625,.875,1])
 assert percentile([1,2,3],percentile_lookup([2,2]))==pytest.approx([0,.5,1])

@pytest.mark.parametrize('values',[[float('nan')],[float('inf')],[]])
def test_bad_score_rejected(values):
 with pytest.raises(ValueError):percentile_lookup(values)

def sample(pid,split='validation'):
 return [dict(product_id=pid,category='c',camera=f'C{i}',truth='normal',split=split,hvq=i,rtdetr=i/10) for i in range(1,6)]

def test_max_before_normalization_and_group_integrity():
 p=product_scores(sample('x'))[0];assert p['hvq']==5 and p['rtdetr']==.5
 for rows in [sample('x')[:-1],sample('x')+[sample('x')[0]],sample('x')[:-1]+sample('x','test')[-1:]]:
  with pytest.raises(ValueError):product_scores(rows)

def test_calibration_only_validation_and_insufficient_classes():
 rows=[dict(product_id=str(i),category='c',truth='normal' if i<2 else 'defect',split='validation',hvq=i,rtdetr=i) for i in range(4)]
 f=fit(rows,weights={'hvq':.3,'rtdetr':.7},drop_tolerance=.005,minimum_products=4,minimum_per_class=2)
 assert f['categories']['c']['f1']==1
 assert predict(rows[-1],f)['binary_verdict']=='defect'
 with pytest.raises(ValueError):predict(rows[-1],f,evaluation=True)
 rows[-1]['split']='test'
 with pytest.raises(ValueError):fit(rows,weights={'hvq':.3,'rtdetr':.7},drop_tolerance=.005,minimum_products=4,minimum_per_class=2)
 f=fit(rows[:2],weights={'hvq':.3,'rtdetr':.7},drop_tolerance=.005,minimum_products=4,minimum_per_class=2)
 assert f['categories']['c']['status']=='UNCONFIGURED'
 assert predict(rows[-1],f)['verdict'] is None

def test_margin_plateau_and_exact_boundary():
 d=threshold_and_margin([.1,.2,.8,.9],[False,False,True,True],drop_tolerance=.005)
 assert d['f1']==1 and d['threshold']==pytest.approx(.5)
 assert d['plateau_lower']==.2 and d['plateau_upper']==.8
 assert d['margin']<=.3
 with pytest.raises(ValueError):threshold_and_margin([.1,.2],[False,False],drop_tolerance=.005)
