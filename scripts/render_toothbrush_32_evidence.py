"""Render actual API-array evidence, explicitly not browser screenshots."""
import json,re
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'reports/gui_validation/spatial-urgent'
grid=json.loads((out/'toothbrush-C1-32-api-response.json').read_text())
source=json.loads((out/'toothbrush-C1-source.json').read_text())
image=cv2.imread(source['image_path'])
assert image is not None
style=(ROOT/'inspection-gui/src/styles/tokens.css').read_text()
def color(token):
 value=re.search(re.escape(token)+r'\s*:\s*#([0-9a-fA-F]{6})',style).group(1)
 return np.asarray([int(value[i:i+2],16) for i in (4,2,0)])
mask=np.asarray(grid['coverage_mask'],np.uint8).reshape(32,32)
values=np.asarray([v if v is not None else 0 for v in grid['values']]).reshape(32,32)
x0,y0,x1,y1=map(round,grid['roi_bounds']);results=[]
for flat,name in [(True,'region-single-value'),(False,'spatial-confidence-area-32')]:
 scaled=np.ones_like(values)*grid['region_value'] if flat else values/max(float(values.max()),1e-12)
 low,mid,high=color('--heat-ok'),color('--heat-warn'),color('--heat-fail')
 heat=np.where((scaled<.5)[:,:,None],low+(mid-low)*np.minimum(scaled*2,1)[:,:,None],mid+(high-mid)*np.maximum(scaled*2-1,0)[:,:,None]).astype(np.uint8)
 heat=cv2.resize(heat,(x1-x0,y1-y0),interpolation=cv2.INTER_NEAREST)
 valid=cv2.resize(mask,(x1-x0,y1-y0),interpolation=cv2.INTER_NEAREST).astype(bool)
 result=image.copy();crop=result[y0:y1,x0:x1];crop[valid]=(.3*crop[valid]+.7*heat[valid]).astype(np.uint8)
 frame=np.zeros((1080,1024,3),np.uint8);frame[56:]=result
 cv2.putText(frame,name+' | same product C1 | NOT a browser capture',(12,32),cv2.FONT_HERSHEY_SIMPLEX,.6,color('--text').tolist(),1)
 cv2.imwrite(str(out/(name+'.png')),frame);results.append(frame)
cv2.imwrite(str(out/'same-product-before-after-32.jpg'),np.concatenate(results,axis=1))
proof=image.copy()
for box in grid['source_detections']:
 bx0,by0,bx1,by1=map(round,box['bbox']);cv2.rectangle(proof,(bx0,by0),(bx1,by1),color('--heat-warn').tolist(),2)
 cx,cy=round((bx0+bx1)/2),round((by0+by1)/2);cv2.drawMarker(proof,(cx,cy),color('--text').tolist(),cv2.MARKER_CROSS,18,2)
for polygon in grid['roi_polygons']:cv2.polylines(proof,[np.asarray(polygon,np.int32)],True,color('--heat-ok').tolist(),2)
cv2.imwrite(str(out/'native-roi-box-proof.png'),proof)
print('Rendered actual 32x32 response and native ROI/box evidence; no browser was used.')
