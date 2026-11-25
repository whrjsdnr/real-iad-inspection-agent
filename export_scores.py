"""완료된 원시 점수만 CSV로 내보낸다. 미완료/실패는 누락 수를 별도로 보고한다."""
import sqlite3,csv,argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--score-db',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
c=sqlite3.connect('file:'+str(a.score_db.resolve())+'?mode=ro',uri=True)
r=c.execute('''SELECT p.product_id,p.category,v.camera,p.truth,p.split,v.hvq,v.rtdetr,v.image_path,v.width,v.height,v.source_fingerprint FROM products p JOIN views v USING(product_id) WHERE p.status='COMPLETED' ORDER BY p.product_id,v.camera''')
tmp=a.output.with_suffix('.tmp');count=0
with tmp.open('w',newline='') as f:
 w=csv.writer(f);w.writerow([x[0] for x in r.description])
 for row in r:w.writerow(row);count+=1
if a.output.exists():raise ValueError('기존 CSV를 덮어쓰지 않습니다')
tmp.replace(a.output);print(json.dumps({'images':count,'products':count//5,'verdicts':'UNCONFIGURED_RAW_SCORES_ONLY'}))
