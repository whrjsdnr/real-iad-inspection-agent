"""Actual masks versus reused numerical arrays; not browser/3D screenshots."""
import cv2,gzip,json,re,sqlite3,sys
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'reports/gui_validation/spatial-urgent'
index=json.loads((ROOT/'reports/ground_truth_heatmaps/index.json').read_text());cfg=json.loads((ROOT/'config/spatial_heatmap.json').read_text())
contract=json.loads((ROOT/'config/fusion_evaluation.json').read_text());style=(ROOT/'inspection-gui/src/styles/tokens.css').read_text()
def color(token):
 value=re.search(re.escape(token)+r'\s*:\s*#([0-9a-fA-F]{6})',style).group(1)
 return np.asarray([int(value[i:i+2],16) for i in (4,2,0)])
connection=sqlite3.connect(Path(cfg['source_score_cache']).resolve().as_uri()+'?mode=ro',uri=True);rows=[];checks=[]
for item,pid in [('toothbrush','toothbrush/NG/CH/S0001'),('zipper','zipper/NG/BX/S0002')]:
 entry=next(e for e in index['entries'] if e['product_id']==pid and e['view']=='C1')
 with gzip.open(ROOT/'reports/ground_truth_heatmaps'/(entry['id']+'.json.gz'),'rt') as stream:data=json.load(stream)
 image=cv2.imread(data['image_path']);mask=cv2.imread(data['mask_path'],cv2.IMREAD_GRAYSCALE)>0
 yy,xx=np.nonzero(mask);actual=np.zeros((64,64));actual[yy*64//mask.shape[0],xx*64//mask.shape[1]]=1
 assert np.array_equal(actual,np.array(data['positive_count']).reshape(64,64))
 boxes=json.loads(connection.execute('SELECT boxes_json FROM views WHERE product_id=? AND camera=?',(pid,'C1')).fetchone()[0])
 boxes=[box for box in boxes if box.get('confidence',box.get('score',0))>=contract['rtdetr_conf_threshold']]
 panels=[]
 for method,title in [('native','ACTUAL PIXEL MASK'),('grid','PRESERVED 64 CELL PRESENCE'),('compare','SAME IMAGE: MASK + RT BOXES')]:
  frame=image.copy();positive=mask if method=='native' else cv2.resize(actual.astype(np.uint8),(image.shape[1],image.shape[0]),interpolation=cv2.INTER_NEAREST)>0
  frame[positive]=(.4*frame[positive]+.6*color('--heat-fail')).astype(np.uint8)
  if method=='compare':
   for box in boxes:
    x0,y0,x1,y1=map(round,box['bbox']);cv2.rectangle(frame,(x0,y0),(x1,y1),color('--signal').tolist(),3)
  panel=np.zeros((550,512,3),np.uint8);panel[38:]=cv2.resize(frame,(512,512));cv2.putText(panel,title,(8,24),cv2.FONT_HERSHEY_SIMPLEX,.45,color('--text').tolist(),1);panels.append(panel)
 rows.append(np.concatenate(panels,axis=1));checks.append({'item':item,'product_id':pid,'view':'C1','split':'train','foreground_pixels':int(mask.sum()),'positive_cells':int(actual.sum()),'native_mask_and_API_cells_equal':True,'comparison':data['comparison']['status'],'selected_RT_boxes':len(boxes)})
connection.close();cv2.imwrite(str(out/'mv-mask-native-grid-model-comparison.jpg'),np.concatenate(rows,axis=0))
(out/'mv-visual-coordinate-checks.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks))
