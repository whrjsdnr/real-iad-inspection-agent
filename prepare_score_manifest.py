"""기존 제품키·분할을 보존해 신규 추론 코호트만 선정한다. 새 Val/Test를 만들지 않는다."""
from pathlib import Path
from collections import defaultdict, Counter
import argparse,csv,json,hashlib,random

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--data-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--images',type=int,default=120000);p.add_argument('--seed',type=int,default=20261123);a=p.parse_args()
 if a.images%5: p.error('C1~C5 단위이므로 images는5의 배수여야 합니다')
 a.output.mkdir(parents=True,exist_ok=False);groups=defaultdict(list)
 with a.source.open() as f:
  for r in csv.DictReader(f):groups[r['product_id']].append(r)
 valid=defaultdict(list);errors=[]
 for pid,rows in groups.items():
  reason=None
  if len(rows)!=5 or {r['view'] for r in rows} != {f'C{i}' for i in range(1,6)}:reason='VIEW_MISSING_OR_DUPLICATE'
  elif any(len({r[k] for r in rows})!=1 for k in ['category','status','split']):reason='METADATA_OR_SPLIT_CONFLICT'
  elif any(not (a.data_root/r['image_path']).is_file() for r in rows):reason='SOURCE_FILE_MISSING'
  if reason:errors.append({'product_id':pid,'reason':reason});continue
  valid[rows[0]['category']].append(pid)
 target=a.images//5
 if sum(map(len,valid.values()))<target:raise ValueError('유효 제품 수 부족')
 rng=random.Random(a.seed)
 for category in sorted(valid):valid[category].sort();rng.shuffle(valid[category])
 # 품목별 round-robin으로 선정한다. 라벨/결함 위치는 추출에 사용하지 않는다.
 chosen=[];offset=0
 while len(chosen)<target:
  for category in sorted(valid):
   if offset<len(valid[category]):chosen.append(valid[category][offset])
   if len(chosen)==target:break
  offset+=1
 fields=['product_id','category','camera','truth','split','image_path','mask_path','width','height']
 with (a.output/'manifest.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for pid in chosen:
   for r in sorted(groups[pid],key=lambda x:x['view']):
    w.writerow(dict(product_id=pid,category=r['category'],camera=r['view'],truth='defect' if r['status']=='NG' else 'normal',split=r['split'],image_path=r['image_path'],mask_path=r.get('mask_path',''),width=r['width'],height=r['height']))
 result={'kind':'NEW_INFERENCE_COHORT_NOT_ORIGINAL_FUSION_EXPERIMENT','images':a.images,'products':len(chosen),'source_products':len(groups),'categories':dict(Counter(groups[p][0]['category'] for p in chosen)),'split_product_counts':dict(Counter(groups[p][0]['split'] for p in chosen)),'status_products':dict(Counter(groups[p][0]['status'] for p in chosen)),'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((a.output/'manifest.csv').read_bytes()).hexdigest(),'seed':a.seed,'selection':'category_round_robin_seeded_shuffle_NO_GT_SELECTION','split_policy':'preserve_original_column_not_recreated','training_overlap':'UNKNOWN_ORIGINAL_30000_ID_LIST_MISSING','calibration_eligible':False,'errors':errors}
 (a.output/'selection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
