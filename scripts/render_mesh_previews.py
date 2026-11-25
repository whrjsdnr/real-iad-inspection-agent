"""Software geometry review from actual exported mesh vertices, NOT a GUI screenshot.

Input is generated from parts.ts with esbuild/Node. No model inference or DB use.
"""
import json,re,sys
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'inspection-gui/src/styles/tokens.css').read_text()
def color(name):
 value=re.search(re.escape(name)+r'\s*:\s*(#[0-9a-fA-F]{6})',source).group(1)
 return np.array([int(value[i:i+2],16) for i in (1,3,5)],float)
models=json.loads(Path(sys.argv[1]).read_text())
width,height=1200,((len(models)+3)//4)*350+140
canvas=np.zeros((height,width,3),np.uint8);canvas[:]=color('--bg')[::-1]
cv2.putText(canvas,'DISPLAY MESH REVIEW - SOFTWARE PROJECTION, NOT LIVE GUI',(20,28),cv2.FONT_HERSHEY_SIMPLEX,.55,color('--muted')[::-1].tolist(),1,cv2.LINE_AA)
forward=np.array([.85,.7,1.]);forward/=np.linalg.norm(forward)
right=np.cross([0,1,0],forward);right/=np.linalg.norm(right);up=np.cross(forward,right)
light=np.array([-.3,.8,.5]);light/=np.linalg.norm(light)
for index,model in enumerate(models):
 forward=np.array(model.get('view',[.85,.7,1.]));forward/=np.linalg.norm(forward)
 right=np.cross([0,1,0],forward);right/=np.linalg.norm(right);up=np.cross(forward,right)
 cx=(index%4)*300;cy=50+(index//4)*350
 faces=[];center=np.array(model['center'])
 spans=[]
 for surface in model['surfaces']:
  points=np.array(surface['vertices']).reshape(-1,3)+surface['position']-center
  projected=np.c_[points@right,points@up,points@forward]
  spans.append(projected)
 allpoints=np.concatenate(spans);scale=min(250/np.ptp(allpoints[:,0]),285/np.ptp(allpoints[:,1]))*.92
 for surface,projected in zip(model['surfaces'],spans):
  tris=(np.array(surface['vertices']).reshape(-1,3)+surface['position']-center).reshape(-1,3,3)
  normals=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);length=np.linalg.norm(normals,axis=1);normals/=np.maximum(length[:,None],1e-12)
  visible=normals@forward>0
  rgb=color('--material-'+surface['material'])
  for n,tri,original,show in zip(normals,projected.reshape(-1,3,3),tris,visible):
   if not show:continue
   shade=.48+.52*max(0,float(n@light))
   c=np.clip(rgb*shade,0,255)[::-1].tolist()
   points=np.c_[cx+150+tri[:,0]*scale,cy+175-tri[:,1]*scale].astype(np.int32)
   faces.append((float(np.mean(original@forward)),points,c))
 for _,points,c in sorted(faces,key=lambda f:f[0]):cv2.fillConvexPoly(canvas,points,c,lineType=cv2.LINE_AA)
 cv2.putText(canvas,model['category'],(cx+15,cy+20),cv2.FONT_HERSHEY_SIMPLEX,.5,color('--text')[::-1].tolist(),1,cv2.LINE_AA)
 cv2.line(canvas,(cx+10,cy+335),(cx+290,cy+335),color('--faint')[::-1].tolist(),1)
cv2.putText(canvas,'GEOMETRY ONLY / NO DEFECT VALUES OR ROI PROJECTION',(20,height-40),cv2.FONT_HERSHEY_SIMPLEX,.5,color('--muted')[::-1].tolist(),1,cv2.LINE_AA)
output=ROOT/'reports/gui_validation/detail3d/geometry-review.png';cv2.imwrite(str(output),canvas);print(output)
