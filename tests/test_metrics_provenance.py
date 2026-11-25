import pytest
import numpy as np
import metrics
from pixel_metrics import compute_aupro
from test_metrics_fusion import db,_seed_20_products

def test_twenty_product_counts_and_latest_attempt_deduplication(db):
 con,_=db;_seed_20_products(con)
 con.execute("INSERT INTO inspection_attempts VALUES ('new','p0','toothbrush','t','completed','m1','r','normal',NULL,'defect','2026-11-22')");con.commit()
 r=metrics.product_metrics(item='toothbrush');assert (r['tp'],r['fn'],r['fp'],r['tn'])==(7,3,2,8)
 assert r['product_precision']['rate']==pytest.approx(7/9)
 assert r['decision_coverage']=={'num':20,'den':23,'rate':20/23}

def test_mock_exclusion_missing_gt_and_hold(db):
 con,_=db;_seed_20_products(con)
 con.execute("UPDATE inspection_attempts SET model_version='mock-anomaly-v1' WHERE attempt_id='a0'")
 con.execute("UPDATE inspection_attempts SET truth_label=NULL WHERE attempt_id='a1'");con.commit()
 r=metrics.product_metrics();assert r['tp']==6 and r['suspect_products']==1 and r['hold']==3

def test_snapshots_reference_scope_preserved(db):
 con,_=db
 metrics.save_snapshot(metric='ref',num=37,den=600,value=37/600,baseline_kind='reference_baseline',source_scope='teammate_reported',review_status='UNVERIFIED')
 r=con.execute("SELECT baseline_kind,source_scope,review_status FROM metrics_snapshots").fetchone()
 assert r==('reference_baseline','teammate_reported','UNVERIFIED')
 assert metrics.product_metrics()['product_f1']['rate'] is None

def test_aupro_exact_perfect_and_degenerate():
 m=np.zeros((10,10),bool);m[3:5,3:5]=True
 assert compute_aupro([(m,m.astype(float))])['value']==pytest.approx(1)
 assert compute_aupro([(np.zeros_like(m),np.zeros_like(m,float))])['value'] is None
 with pytest.raises(ValueError):compute_aupro([(m,np.full(m.shape,np.nan))])


def test_uncalibrated_scores_do_not_produce_fp_fn_statistics():
 from app.tools import query_error_stats
 r=query_error_stats(item='toothbrush',metric='part_miss_rate',group_by=['part_id'],model_version='uncalibrated-scores:test')
 assert r['rows']==[] and r['reason']=='fusion_thresholds_unconfigured'
