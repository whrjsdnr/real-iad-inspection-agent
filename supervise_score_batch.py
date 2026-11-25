"""100제품 파일럿을 검증한 뒤 같은 batch5 설정으로 나머지를 재개한다. 자동 판정 없음."""
from pathlib import Path
import argparse,json,time,sqlite3,subprocess,sys,fcntl,os,numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--mv-root',type=Path,required=True);p.add_argument('--data-root',type=Path,required=True);a=p.parse_args()
 r=a.run_dir.resolve();log=(r/'supervisor.log').open('a',buffering=1)
 lock=(r/'supervisor.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 def state(phase,**extra):
  v={'phase':phase,'pid':os.getpid(),'batch_size':5,'automatic_verdicts':False,**extra};tmp=r/'pipeline.tmp';tmp.write_text(json.dumps(v,indent=2));tmp.replace(r/'pipeline_state.json');print(json.dumps(v),file=log,flush=True)
 state('WAITING_FOR_PILOT_100')
 while True:
  s=json.loads((r/'state.json').read_text());c=sqlite3.connect('file:'+str(r/'scores.sqlite')+'?mode=ro',uri=True)
  counts=dict(c.execute('SELECT status,count(*) FROM products GROUP BY status'));done=counts.get('COMPLETED',0)
  if counts.get('FAILED',0):state('BLOCKED_PILOT_FAILURE',counts=counts);return 2
  if s['status']=='INTERRUPTED':state('INTERRUPTED_PILOT');return 2
  if done>=100 and s['status']=='COMPLETED_RAW_SCORES':
   probe=(r/'process.lock').open('a')
   try:fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:probe.close();c.close();time.sleep(1);continue
   fcntl.flock(probe,fcntl.LOCK_UN);probe.close();break
  c.close();time.sleep(10)
 sizes=c.execute('SELECT count(*) FROM views').fetchone()[0];bad=c.execute('SELECT count(*) FROM (SELECT product_id,count(*) AS n FROM views GROUP BY product_id HAVING count(*)!=5)').fetchone()[0]
 times=[x[0] for x in c.execute('SELECT seconds FROM products')];nulls=c.execute('SELECT count(*) FROM views WHERE hvq IS NULL OR rtdetr IS NULL').fetchone()[0];c.close()
 if sizes!=500 or bad or nulls:state('BLOCKED_PILOT_INTEGRITY',views=sizes,bad_groups=bad,nulls=nulls);return 2
 pilot={'products':100,'images':500,'failed':0,'five_view_complete':100,'batch_size':5,'mean_seconds':float(np.mean(times)),'p95_seconds':float(np.percentile(times,95)),'peak_rss_mib':s['peak_rss_mib'],'estimated_remaining_hours':float(np.mean(times)*23900/3600),'verdict_distribution':'NOT_AVAILABLE_UNCONFIGURED_THRESHOLDS','accuracy_comparison':'NOT_EVALUATED_NO_CALIBRATED_VERDICTS','training_overlap':'UNKNOWN'}
 (r/'pilot_validation.json').write_text(json.dumps(pilot,indent=2));(r/'PILOT_REPORT.md').write_text('# Batch5 원시 점수 파일럿\n\n신규 추론 코호트이며 원 실험 재현이 아니다.\n\n```json\n'+json.dumps(pilot,ensure_ascii=False,indent=2)+'\n```\n\n팀원 참고 미검37/600·오검46/600은 이 파일럿의 측정값이 아니다. TH가 없어 정상/불량/보류와 정확도는 미평가다.\n')
 state('FULL_RAW_INFERENCE_RUNNING',pilot=pilot)
 cmd=[sys.executable,str(Path(__file__).with_name('score_batch.py')),'--manifest',str(a.manifest.resolve()),'--data-root',str(a.data_root.resolve()),'--mv-root',str(a.mv_root.resolve()),'--config',str(a.config.resolve()),'--output',str(r),'--save-maps-products','100','--resume']
 with (r/'full_batch.log').open('a',buffering=1) as f:child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT);(r/'full_batch.pid').write_text(str(child.pid));rc=child.wait()
 state('COMPLETED_RAW_INFERENCE' if rc==0 else 'FAILED_OR_INTERRUPTED',returncode=rc)
 return rc
if __name__=='__main__':raise SystemExit(main())
