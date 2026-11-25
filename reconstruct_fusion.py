"""명시적으로 검증된 분할의 저장 점수로만 신규 퓨전을 보정한다. 원 실험 재현을 주장하지 않는다."""
from pathlib import Path
import argparse,json,csv,hashlib
from datetime import datetime,timezone
from fusion_calibration import product_scores,fit,predict,confusion

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scores',type=Path,required=True);p.add_argument('--split-audit',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 audit=json.loads(a.split_audit.read_text());digest=hashlib.sha256(a.scores.read_bytes()).hexdigest()
 if audit.get('score_csv_sha256')!=digest or audit.get('training_overlap')!='VERIFIED_DISJOINT' or audit.get('split_status')!='VERIFIED':
  p.error('분할·학습 비중복·점수 해시가 확인된 audit가 필요합니다. 현재 원시 추론 코호트는 보정용으로 사용할 수 없습니다')
 cfg=json.loads(a.config.read_text());rows=[]
 with a.scores.open() as f:
  for r in csv.DictReader(f):
   if r['split'] not in ['validation','test']:continue
   r['hvq']=float(r['hvq']);r['rtdetr']=float(r['rtdetr']);rows.append(r)
 products=product_scores(rows);val=[p for p in products if p['split']=='validation'];test=[p for p in products if p['split']=='test']
 if not val:raise ValueError('Val 없음')
 fitted=fit(val,weights=cfg['weights'],drop_tolerance=cfg['calibration']['f1_drop_tolerance'],minimum_products=cfg['calibration']['minimum_validation_products'],minimum_per_class=cfg['calibration']['minimum_per_class'])
 predictions=[dict(p,**predict(p,fitted,evaluation=True)) for p in test];valid=[p for p in predictions if p['status']=='CONFIGURED']
 metric=confusion([p['truth']=='defect' for p in valid],[p['binary_verdict']=='defect' for p in valid]);metric['hold']={'num':sum(p['verdict']=='hold' for p in valid),'den':len(valid)}
 result=cfg|{'reproduction_status':'RECONSTRUCTED','calibrated_parameters':fitted,'category_thresholds':{k:v['threshold'] for k,v in fitted['categories'].items() if v['status']=='CONFIGURED'},'category_margins':{k:v['margin'] for k,v in fitted['categories'].items() if v['status']=='CONFIGURED'},'experiment_date':datetime.now(timezone.utc).isoformat(),'validation_manifest_reference':audit.get('validation_manifest_reference'),'normalization_lookup_reference':'fusion_config.json#calibrated_parameters.categories','provenance':cfg['provenance']|{'newly_derived':{'score_sha256':digest,'split_audit':str(a.split_audit)},'status':'new_reconstruction_not_original_reproduction'}}
 a.output.mkdir(parents=True,exist_ok=False)
 for name,value in [('fusion_config.json',result),('test_metrics.json',metric),('test_predictions.json',predictions)]:
  (a.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))
 print(json.dumps({'status':'RECONSTRUCTED','validation_products':len(val),'test_products':len(test),'unconfigured_test_products':len(test)-len(valid)},ensure_ascii=False))
if __name__=='__main__':main()
