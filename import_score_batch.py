"""완료 score 제품을 공통 DB에 멱등 기록한다. TH 미확정 판정은 NULL을 유지한다."""
from pathlib import Path
import argparse,sqlite3,json,hashlib,os
from datetime import datetime,timezone
from app.db import get_engine
from app.models import Attempt,View,Finding
from sqlalchemy.orm import Session

def ingest(score_db,data_root,limit_products=None):
 if not (os.getenv('DATABASE_URL_BATCH') or os.getenv('DATABASE_URL')):
  raise ValueError('대상 DATABASE_URL_BATCH 또는 DATABASE_URL을 명시하세요. 기존 로컬 DB에 암묵적으로 적재하지 않습니다')
 c=sqlite3.connect('file:'+str(Path(score_db).resolve())+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 binding=json.loads(Path(score_db).with_name('binding.json').read_text());tag='uncalibrated-scores:'+hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()[:16];added=skipped=0
 engine=get_engine('batch')
 for p in c.execute("SELECT * FROM products WHERE status='COMPLETED' ORDER BY completed_at,product_id"):
  if limit_products is not None and added+skipped>=limit_products:break
  aid=hashlib.sha256((tag+p['product_id']).encode()).hexdigest()
  with Session(engine) as s:
   if s.get(Attempt,aid):skipped+=1;continue
   now=datetime.now(timezone.utc).isoformat();s.add(Attempt(attempt_id=aid,product_id=p['product_id'],item=p['category'],started_at=p['completed_at'],processed_at=now,status='completed',model_version=tag,mapping_version='parts-roi-v1',verdict=None,review_status='pending',truth_label=p['truth']))
   for v in c.execute('SELECT * FROM views WHERE product_id=?',(p['product_id'],)):
    map_path=v['map_path'] or ''
    if map_path:
     resolved=Path(map_path)
     if not resolved.is_absolute():resolved=Path(score_db).resolve().parent/resolved
     resolved=resolved.resolve()
     if not resolved.is_relative_to(Path(score_db).resolve().parent) or not resolved.is_file():raise ValueError('raw map 경로/출처 검증 실패')
     map_path=str(resolved)
    vid=aid+':'+v['camera'];s.add(View(view_id=vid,attempt_id=aid,product_id=p['product_id'],item=p['category'],camera_id=v['camera'],image_uri=str((Path(data_root)/v['image_path']).resolve()),error_map_uri=map_path,width=v['width'],height=v['height'],status='ok',model_version=tag,mapping_version='parts-roi-v1'))
    s.add(Finding(finding_id=vid+':hvq',view_id=vid,product_id=p['product_id'],item=p['category'],camera_id=v['camera'],source='anomaly',kind='hvq_score',bbox_x1=0,bbox_y1=0,bbox_x2=v['width'],bbox_y2=v['height'],score=v['hvq'],part_id='unknown',model_version=tag,mapping_version='parts-roi-v1',map_uri=map_path or None,meta_json=json.dumps({'calibration':'UNCONFIGURED','raw_map_shape':'1x224x224','rtdetr_score':v['rtdetr'],'split':p['split'],'training_overlap':'UNKNOWN'})))
    for i,b in enumerate(json.loads(v['boxes_json'])):
     box=b['bbox'];s.add(Finding(finding_id=vid+f':rt:{i}',view_id=vid,product_id=p['product_id'],item=p['category'],camera_id=v['camera'],source='defect',kind='rtdetr_box',bbox_x1=int(box[0]),bbox_y1=int(box[1]),bbox_x2=int(box[2]),bbox_y2=int(box[3]),score=b['confidence'],part_id='unknown',model_version=tag,mapping_version='parts-roi-v1',meta_json=json.dumps({'class_id':b['class_id'],'calibration':'UNCONFIGURED'})))
   s.commit();added+=1
 return {'added':added,'skipped':skipped,'model_version':tag,'automatic_verdicts':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--score-db',type=Path,required=True);p.add_argument('--data-root',type=Path,required=True);p.add_argument('--limit-products',type=int);a=p.parse_args();print(json.dumps(ingest(a.score_db,a.data_root,a.limit_products)))
