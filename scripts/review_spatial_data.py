"""Generate actual-image audit sheets (not browser screenshots), no inference."""
import gzip,json,re,sqlite3,sys
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.spatial_heatmap import ROOT


def main():
    config=json.loads((ROOT/'config/spatial_heatmap.json').read_text())
    rois=json.loads((ROOT/'config/part_heatmap_regions.json').read_text())
    templates={(entry['item'],entry['camera']):entry for entry in rois['templates']}
    tokens=(ROOT/'inspection-gui/src/styles/tokens.css').read_text()
    def color(name):
        value=re.search(re.escape(name)+r'\s*:\s*#([0-9a-fA-F]{6})',tokens).group(1)
        return np.array([int(value[i:i+2],16) for i in (4,2,0)],float)
    out=ROOT/'reports/spatial_heatmap';out.mkdir(exist_ok=True)
    connection=sqlite3.connect('file:'+config['source_score_cache']+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    items=[row[0] for row in connection.execute('SELECT DISTINCT category FROM products ORDER BY category')]
    sheets=[]
    for item in items:
        product=connection.execute("SELECT product_id FROM products WHERE category=? AND truth='normal' ORDER BY product_id LIMIT 1",(item,)).fetchone()[0]
        row_canvas=np.zeros((225,1000,3),np.uint8)
        for index,view in enumerate(connection.execute('SELECT * FROM views WHERE product_id=? ORDER BY camera',(product,))):
            image=Path(view['image_path']);image=image if image.is_absolute() else Path(config['dataset_root'])/image
            pixels=cv2.imread(str(image))
            if pixels is None:continue
            template=templates.get((item,view['camera']))
            if template:
                for region in template['regions']:
                    for polygon in region.get('polygons') or [region['polygon']]:
                        cv2.polylines(pixels,[np.asarray(polygon,np.int32)],True,color('--ok').tolist(),5)
            row_canvas[25:,index*200:(index+1)*200]=cv2.resize(pixels,(200,200))
            cv2.putText(row_canvas,f"{item} {view['camera']} {'ROI' if template else 'UNREGISTERED'}",(index*200+2,17),cv2.FONT_HERSHEY_SIMPLEX,.32,color('--text').tolist(),1)
        sheets.append(row_canvas)
    connection.close()
    for page in range(0,len(sheets),5):cv2.imwrite(str(out/f'roi-survey-{page//5+1:02}.jpg'),np.concatenate(sheets[page:page+5],axis=0))
    index=json.loads((out/'index.json').read_text())
    rows=[]
    for item,region in [('toothbrush','bristle'),('zipper','teeth')]:
        entry=next(row for row in index['entries'] if row['item']==item and '/NG/' in row['product_id'] and row['camera']=='C1' and row['region_id']==region and row['resolution']==64)
        with gzip.open(out/f"{entry['grid_id']}.json.gz",'rt') as stream:grid=json.load(stream)
        original=cv2.imread(grid['source_image']);panels=[]
        for model,method,flat in [('rt','gaussian',True),('rt','gaussian',False),('hvq','mean',False)]:
            image=original.copy();source=grid[model]
            if source['status']=='supported':
                values=np.array([0 if value is None else value for value in source['values'][method]]).reshape(64,64)
                valid=np.array(source['valid_observation_counts']).reshape(64,64)>0
                valid&=np.array(grid['coverage_mask']).reshape(64,64)>0
                lo,hi=values[valid].min(),values[valid].max()
                scale=np.zeros_like(values) if hi==lo else (values-lo)/(hi-lo)
                if flat:scale[:]=grid['stats']['detected_products']/max(1,grid['stats']['observed_products'])
                first=color('--heat-ok');last=color('--heat-fail')
                heat=(first[None,None,:]*(1-scale[:,:,None])+last[None,None,:]*scale[:,:,None]).astype(np.uint8)
                x0,y0,x1,y1=map(round,grid['roi_bounds'])
                layer=cv2.resize(heat,(x1-x0,y1-y0),interpolation=cv2.INTER_NEAREST)
                mask=cv2.resize(valid.astype(np.uint8),(x1-x0,y1-y0),interpolation=cv2.INTER_NEAREST).astype(bool)
                crop=image[y0:y1,x0:x1];crop[mask]=(.35*crop[mask]+.65*layer[mask]).astype(np.uint8)
            panel=np.zeros((550,512,3),np.uint8);panel[38:]=cv2.resize(image,(512,512))
            title='SAME ROI / SINGLE VALUE' if flat else f'{model.upper()} {method} / {source["status"]}'
            cv2.putText(panel,title,(8,25),cv2.FONT_HERSHEY_SIMPLEX,.5,color('--text').tolist(),1);panels.append(panel)
        rows.append(np.concatenate(panels,axis=1))
    cv2.imwrite(str(out/'primary-spatial-comparison.jpg'),np.concatenate(rows,axis=0))
    # Keep native-image semantic subdivisions auditable independently of the GUI.
    hierarchy_rows=[]
    for item in ['toothbrush','zipper']:
        panels=[]
        for camera in ['C1','C2','C3','C4','C5']:
            entries=[entry for entry in index['entries'] if entry['item']==item and '/NG/' in entry['product_id']
                     and entry['camera']==camera and entry['resolution']==16]
            if not entries:continue
            with gzip.open(out/f"{entries[0]['grid_id']}.json.gz",'rt') as stream:first=json.load(stream)
            image=cv2.imread(first['source_image'])
            for entry in entries:
                with gzip.open(out/f"{entry['grid_id']}.json.gz",'rt') as stream:grid=json.load(stream)
                ink=color('--heat-warn' if entry['parent_region_id'] else '--heat-ok').tolist()
                for polygon in grid['roi_polygons']:
                    points=np.asarray(polygon,np.int32);cv2.polylines(image,[points],True,ink,3)
                    x,y=points.min(axis=0)
                    cv2.putText(image,entry['region_id'],(int(x)+3,int(y)+18),cv2.FONT_HERSHEY_SIMPLEX,.48,ink,1)
            panel=np.zeros((350,320,3),np.uint8);panel[30:]=cv2.resize(image,(320,320))
            cv2.putText(panel,item+' '+camera,(8,20),cv2.FONT_HERSHEY_SIMPLEX,.5,color('--text').tolist(),1)
            panels.append(panel)
        hierarchy_rows.append(np.concatenate(panels,axis=1))
    cv2.imwrite(str(out/'primary-hierarchical-roi-overlay.jpg'),np.concatenate(hierarchy_rows,axis=0))
    print('Actual-image review sheets saved; these are not live browser screenshots.')


if __name__=='__main__':main()
