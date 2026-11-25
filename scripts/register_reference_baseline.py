"""전달받은 참고 성능을 출처 구분하여 저장한다. 운영 실측 집계에는 섞지 않는다."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import metrics,dbconn

def register():
    model='reference:teammate-hvq79-rtdetr15-UNVERIFIED'
    rows=dbconn.query('SELECT COUNT(*) AS n FROM metrics_snapshots WHERE model_version=:m AND baseline_kind=:k',{'m':model,'k':'reference_baseline'})
    if rows[0]['n']:return {'status':'EXISTS','rows':rows[0]['n']}
    values=[('product_recall',563,600),('ng_miss_rate',37,600),('product_fpr',46,600),('product_precision',563,609),('product_f1_micro_from_reported_counts',1126,1209)]
    # 분자는 전달된 혼동행렬에서 계산한 값이며 측정 성공으로 표기하지 않는다.
    for name,n,d in values:
        metrics.save_snapshot(metric=name,num=n,den=d,value=n/d,model_version=model,
          source_scope='teammate_reported_test_1200_not_reproduced',baseline_kind='reference_baseline',
          split_reference='TEAMMATE_REPORTED_NG600_OK600_ORIGINAL_LIST_MISSING',review_status='UNVERIFIED',
          reason='팀원 전달 Test 기준선 — 현재 환경 재현 미검증')
    metrics.save_snapshot(metric='product_f1_macro_30',num=None,den=30,value=.9314,model_version=model,
      source_scope='teammate_reported_category_macro',baseline_kind='reference_baseline',
      split_reference='TEAMMATE_REPORTED_NG600_OK600_ORIGINAL_LIST_MISSING',review_status='UNVERIFIED',
      reason='팀원 전달 품목 F1 단순평균; 분자 합계는 미제공. 전체 혼동행렬 F1과 별도')
    return {'status':'REGISTERED_REFERENCE_ONLY','rows':len(values)+1}
if __name__=='__main__':print(json.dumps(register(),ensure_ascii=False))
