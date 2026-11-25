"""고정 ONNX로 신규 코호트 원시 점수 추출. TH 미확정 시 자동 판정하지 않는다.

제품 트랜잭션, fingerprint, flock으로 재시작/중복 실행을 제어한다.
기존 inference.py·inference_hvq.py는 수정하거나 모델을 재변환하지 않는다.
"""
from pathlib import Path
from collections import defaultdict
import argparse,json,hashlib,sqlite3,time,os,sys,fcntl,signal,traceback,resource

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def load_manifest(path):
 import csv
 groups=defaultdict(list)
 with Path(path).open() as f:
  for r in csv.DictReader(f):groups[r['product_id']].append(r)
 for pid,rows in groups.items():
  if len(rows)!=5 or {r['camera'] for r in rows}!={f'C{i}' for i in range(1,6)}:raise ValueError(f'{pid}: 시점 누락/중복')
  if any(len({r[k] for r in rows})!=1 for k in ['category','split','truth']):raise ValueError(f'{pid}: 메타데이터/분할 누수')
 return groups

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--data-root',type=Path,required=True);p.add_argument('--mv-root',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--limit-products',type=int);p.add_argument('--resume',action='store_true');p.add_argument('--retry-failed',action='store_true');p.add_argument('--save-maps-products',type=int,default=0);a=p.parse_args()
 cfg=json.loads(a.config.read_text());groups=load_manifest(a.manifest)
 if cfg['runner'].get('score_inference_batch')!=5:raise ValueError('사용자 확정 모델 batch=5 설정이 필요합니다')
 order=list(groups)
 if a.limit_products:order=order[:a.limit_products]
 a.output.mkdir(parents=True,exist_ok=True)
 lock=(a.output/'process.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 sys.path.insert(0,str(a.mv_root));import inference as RT;import hvq_common as H
 import torch,numpy as np,onnxruntime as ort
 from PIL import Image
 torch.set_num_threads(1)
 rtpath=a.mv_root/cfg['rtdetr']['onnx'];hvpath=a.mv_root/cfg['hvq']['onnx_fp16']
 binding={'manifest_sha256':sha(a.manifest),'config_sha256':sha(a.config),'rtdetr_onnx_sha256':sha(rtpath),'hvq_onnx_sha256':sha(hvpath),'data_root':str(a.data_root.resolve()),'save_maps_products':a.save_maps_products,'mode':'RAW_SCORES_ONLY_UNCALIBRATED'}
 identity=a.output/'binding.json'
 if identity.exists():
  if not a.resume:raise ValueError('기존 실행은 --resume이 필요합니다')
  if json.loads(identity.read_text())!=binding:raise ValueError('재개 설정/입력/모델 해시 불일치')
 else:identity.write_text(json.dumps(binding,indent=2))
 con=sqlite3.connect(a.output/'scores.sqlite',timeout=30);con.execute('PRAGMA journal_mode=WAL')
 con.executescript('''CREATE TABLE IF NOT EXISTS products(product_id TEXT PRIMARY KEY,category TEXT,split TEXT,truth TEXT,status TEXT,error TEXT,hvq_max REAL,rtdetr_max REAL,seconds REAL,completed_at TEXT);
 CREATE TABLE IF NOT EXISTS views(product_id TEXT,camera TEXT,image_path TEXT,hvq REAL,rtdetr REAL,width INTEGER,height INTEGER,boxes_json TEXT,map_path TEXT,source_fingerprint TEXT,PRIMARY KEY(product_id,camera));''')
 def options(n):
  o=ort.SessionOptions();o.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL;o.intra_op_num_threads=n;o.inter_op_num_threads=1;return o
 rt=ort.InferenceSession(str(rtpath),sess_options=options(cfg['runner']['rtdetr_threads']),providers=['CPUExecutionProvider'])
 hv=H.HVQONNXFP16IOEngine(hvpath,30,session_options=options(cfg['runner']['hvq_threads']))
 bm=H.load_branch_mapping(a.mv_root/'hvq_best.pt');maps=a.output/'maps';maps.mkdir(exist_ok=True)
 status='RUNNING';started=time.monotonic();durations=[];processed=failed=0
 def progress(final=None):
  counts=dict(con.execute('SELECT status,count(*) FROM products GROUP BY status').fetchall());done=counts.get('COMPLETED',0);rate=processed/(time.monotonic()-started) if processed else 0
  state={'status':final or status,'pid':os.getpid(),'products_expected':len(order),'completed':done,'failed':counts.get('FAILED',0),'processed_this_process':processed,'seconds_this_process':time.monotonic()-started,'products_per_second':rate,'eta_seconds':max(0,len(order)-sum(counts.values()))/rate if rate else None,'p95_seconds':float(np.percentile(durations,95)) if durations else None,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'automatic_verdicts':False,'training_overlap':'UNKNOWN','errors_are_not_zero_scores':True,'model_batch_size':5,'views_per_product':5}
  tmp=a.output/'state.tmp';tmp.write_text(json.dumps(state,indent=2));tmp.replace(a.output/'state.json');print(json.dumps(state),flush=True)
 def interrupt(*_):raise KeyboardInterrupt()
 signal.signal(signal.SIGTERM,interrupt);progress()
 try:
  for position,pid in enumerate(order):
   old=con.execute('SELECT status FROM products WHERE product_id=?',(pid,)).fetchone()
   if old and (old[0]=='COMPLETED' or not a.retry_failed):continue
   rows=sorted(groups[pid],key=lambda r:r['camera']);timer=time.monotonic();views=[];images=[]
   try:
    category=rows[0]['category']
    if category not in bm:raise ValueError('HVQ 분기 없음')
    # 한 제품5장만 메모리에 유지한다. 모델 입력에 GT는 전달하지 않는다.
    for r in rows:
     path=(a.data_root/r['image_path']).resolve()
     if not path.is_relative_to(a.data_root.resolve()):raise ValueError('경로 탈출')
     with Image.open(path) as im:
      im.load();images.append(im.convert('RGB'))
     if images[-1].size!=(int(r['width']),int(r['height'])):raise ValueError('이미지 해상도 불일치')
    with torch.inference_mode():
     # 사용자 확정: 모델 입력도 제품 단위 batch5. 서로 다른 제품의 시점을 섞지 않는다.
     if len(images)!=5:raise ValueError('모델 입력 배치는 C1~C5 정확히5장이어야 합니다')
     outputs=rt.run(None,{rt.get_inputs()[0].name:RT.preprocess(images,cfg['rtdetr']['imgsz']).numpy()})
     if not all(np.isfinite(x).all() for x in outputs):raise ValueError('RT 출력 NaN/Inf')
     detections=RT.postprocess(torch.from_numpy(outputs[0]),torch.from_numpy(outputs[1]),torch.tensor([im.size for im in images]),conf=cfg['rtdetr']['score_floor'],iou=cfg['rtdetr']['iou'])
     pred=hv.infer(H.preprocess(images,cfg['hvq']['imgsz']),torch.tensor([bm[category]]*5,dtype=torch.long))
     scores=H.scores_from_pred(pred).float().tolist()
    if not np.isfinite(scores).all() or not torch.isfinite(pred).all():raise ValueError('HVQ 출력 NaN/Inf')
    for r,im,det,hs,heat in zip(rows,images,detections,scores,pred):
     mp=''
     if position<a.save_maps_products:
      target=maps/(hashlib.sha256((pid+r['camera']).encode()).hexdigest()[:20]+'.npy');tmp=target.with_suffix('.tmp')
      with tmp.open('wb') as f:np.save(f,heat.float().numpy())
      tmp.replace(target);mp=str(target)
     boxes=[{'bbox':b,'class_id':int(l),'confidence':float(s)} for b,l,s in zip(det['boxes'].tolist(),det['labels'].tolist(),det['scores'].tolist())]
     rs=max((b['confidence'] for b in boxes),default=0.)
     stat=(a.data_root/r['image_path']).stat();views.append((pid,r['camera'],r['image_path'],float(hs),rs,im.width,im.height,json.dumps(boxes),mp,f'stat:{stat.st_size}:{stat.st_mtime_ns}'))
    seconds=time.monotonic()-timer
    with con:
     con.execute('DELETE FROM views WHERE product_id=?',(pid,));con.executemany('INSERT INTO views VALUES (?,?,?,?,?,?,?,?,?,?)',views)
     con.execute('INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?,?)',(pid,category,rows[0]['split'],rows[0]['truth'],'COMPLETED',None,max(v[3] for v in views),max(v[4] for v in views),seconds,time.strftime('%Y-%m-%dT%H:%M:%S%z')))
    durations.append(seconds);processed+=1
   except Exception as exc:
    failed+=1
    with con:con.execute('INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?,?)',(pid,rows[0]['category'],rows[0]['split'],rows[0]['truth'],'FAILED',traceback.format_exc(),None,None,time.monotonic()-timer,time.strftime('%Y-%m-%dT%H:%M:%S%z')))
    print(json.dumps({'product':pid,'error':repr(exc)}),flush=True)
   finally:
    for im in images:im.close()
   if (processed+failed)%cfg['runner']['progress_every']==0:progress()
  status='COMPLETED_RAW_SCORES'
 except KeyboardInterrupt:status='INTERRUPTED'
 finally:progress(status);con.close()
 return 0 if status=='COMPLETED_RAW_SCORES' and not failed else 2
if __name__=='__main__':raise SystemExit(main())
