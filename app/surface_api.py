"""Display-only approximate template projections, explicitly authorized by user.
No physical registration claim, inference, decisions, or source-array changes.
"""
import json
import numpy as np
from fastapi import APIRouter,HTTPException
from .spatial_heatmap import ROOT
from .part_heatmap import polygon_mask
from .coordinates import Size
from . import ground_truth_api as gt,spatial_api as spatial
from .shared_data_api import database,stored_map,image_path
from .spatial_heatmap import build_grid
from .part_heatmap import fingerprint
router=APIRouter(tags=['display template surface'])

def representative(item,view,product_id=None):
    with database() as connection:
        query="SELECT v.*,p.split,p.truth FROM views v JOIN products p USING(product_id) WHERE p.category=? AND v.camera=?"
        args=[item,view]
        if product_id:query+=' AND p.product_id=?';args.append(product_id)
        query+=" ORDER BY CASE WHEN v.map_path IS NOT NULL AND v.map_path!='' THEN 0 ELSE 1 END,CASE WHEN p.truth='defect' THEN 0 ELSE 1 END,p.product_id LIMIT 32"
        rows=[dict(row) for row in connection.execute(query,args)]
    for row in rows:
        mapping=stored_map(row)
        if mapping:return row,mapping
    return (rows[0],None) if rows else (None,None)

def model_regions(item,view,source,product_id):
    row,mapping=representative(item,view,product_id)
    if not row:return [],None,None
    if source=='hvq' and not mapping:return [],row['product_id'],row['split']
    config=json.loads((ROOT/'config/spatial_heatmap.json').read_text())
    contract=json.loads((ROOT/'config/fusion_evaluation.json').read_text())
    boxes=[{'bbox':box['bbox'],'score':float(box.get('confidence',box.get('score',0)))} for box in json.loads(row['boxes_json'])]
    boxes=[box for box in boxes if box['score']>=contract['rtdetr_conf_threshold']]
    image=image_path(row);width,height=row['width'],row['height']
    record={'item':item,'product_id':row['product_id'],'camera':view,'models':{},'source':'saved_batch5_view',
        'image_path':str(image),'image_sha256':mapping['image_sha256'] if mapping else fingerprint(image),
        'original_size':[width,height],'detections':boxes if source=='rt' else [],'map_path':mapping['path'] if source=='hvq' and mapping else None}
    candidates=regions(item,view)
    if not candidates:candidates=[{'region_id':'__whole_template__','label':'전체 외형','polygons':[[[0,0],[width,0],[width,height],[0,height]]]}]
    output=[]
    for region in candidates:
        data=build_grid(record,region|{'parent_region_id':None},32,config);values=data[source]
        if values['status']!='supported':continue
        method='confidence_area' if source=='rt' else 'mean'
        output.append(region|{'grid_width':32,'grid_height':32,'values':values['values'][method],
            'valid_observation_counts':values['valid_observation_counts'],'coverage_mask':data['coverage_mask'],
            'source_bounds':data['roi_bounds'],'aggregation_method':method,'sample_products':1,'unknown_products':0,
            'native_map_size':values.get('native_map_size'),'data_source':mapping['source'] if source=='hvq' else 'saved_batch5_boxes'})
    return output,row['product_id'],row['split']

def settings(item,view):
    config=json.loads((ROOT/'config/surface_projection.json').read_text())
    value=config['default']|config['items'].get(item,{})
    value['quarter_turns']=value.get('views',{}).get(view,value.get('quarter_turns',0))
    return {key:config[key] for key in ('version','scope','user_authorized_approximate_projection','default_opacity','front_facing_cos_min','zero_signal_opacity','hotspot_limit','hotspot_candidate_limit','render')}|{'projection':value}

def regions(item,view):
    config=json.loads((ROOT/'config/part_heatmap_regions.json').read_text())
    hierarchy=json.loads((ROOT/'config/spatial_regions.json').read_text())
    template=next((row for row in config['templates'] if row['item']==item and row['camera']==view),{})
    result={row['region_id']:{'region_id':row['region_id'],'label':row['label'],'polygons':row.get('polygons') or [row['polygon']]} for row in template.get('regions',[])}
    for node in hierarchy['nodes']:
        if node['category']==item and not node['parent_region_id'] and view in node.get('camera_rois',{}):
            result[node['region_id']]={'region_id':node['region_id'],'label':node['display_name'],'polygons':node['camera_rois'][view]}
    return list(result.values())

@router.get('/heatmaps/surface-layout')
async def layout(item:str):
    views=sorted({entry['view'] for entry in gt.index()['entries'] if entry['item']==item and entry['product_id'] is None})
    rt_views=[];hv_views=[]
    for view in ('C1','C2','C3','C4','C5'):
        row,mapping=representative(item,view)
        if row:rt_views.append(view)
        if mapping:hv_views.append(view)
    return {'item':item,'sources':[
      {'id':'ground_truth','label':'실제 마스크 · Train NG','views':views,'available':bool(views),'reason':None if views else 'saved_mask_distribution_missing'},
      {'id':'rt','label':'RT-DETR 검출 분포','views':rt_views,'available':bool(rt_views),'reason':None if rt_views else 'saved_spatial_box_grid_missing'},
      {'id':'hvq','label':'HVQ 실제 이상 맵','views':hv_views,'available':bool(hv_views),'reason':None if hv_views else 'raw_anomaly_map_not_saved'}],**settings(item,views[0] if views else 'C1')}

def crop_truth(data,region):
    width,height=data['grid_width'],data['grid_height'];iw,ih=data['source_image_width'],data['source_image_height']
    points=np.asarray([point for polygon in region['polygons'] for point in polygon])
    x0=max(0,int(np.floor(points[:,0].min()*width/iw)));x1=min(width,int(np.ceil(points[:,0].max()*width/iw)))
    y0=max(0,int(np.floor(points[:,1].min()*height/ih)));y1=min(height,int(np.ceil(points[:,1].max()*height/ih)))
    if x0>=x1 or y0>=y1:return None
    mask=np.zeros((height,width),bool)
    for polygon in region['polygons']:mask|=polygon_mask([[x*width/iw,y*height/ih] for x,y in polygon],Size(width,height))
    mask=mask[y0:y1,x0:x1].ravel()
    values=np.asarray(data['defect_rate'],object).reshape(height,width)[y0:y1,x0:x1].ravel()
    counts=np.asarray(data['known_count']).reshape(height,width)[y0:y1,x0:x1].ravel()
    return {'grid_width':x1-x0,'grid_height':y1-y0,'values':[value if valid else None for value,valid in zip(values,mask)],
      'valid_observation_counts':np.where(mask,counts,0).astype(int).tolist(),'coverage_mask':mask.astype(int).tolist(),
      'source_bounds':[x0*iw/width,y0*ih/height,x1*iw/width,y1*ih/height],
      'aggregation_method':'mask_presence_frequency','sample_products':data['known_products'],'unknown_products':data['unknown_products']}

@router.get('/heatmaps/surface')
async def surface(item:str,view:str='C1',source:str='ground_truth',product_id:str|None=None):
    if view not in ('C1','C2','C3','C4','C5') or source not in ('ground_truth','rt','hvq'):raise HTTPException(422,'지원하지 않는 시점/데이터 종류')
    output=[];product=None;split=None
    if source=='ground_truth':
        _,data=gt.record(item,view,'train',product_id);product=data['product_id'];split=data['split']
        for region in regions(item,view):
            raster=crop_truth(data,region)
            if raster:output.append(region|raster)
        if not output or (not any(value is not None and value>0 for region in output for value in region['values']) and any(value is not None and value>0 for value in data['defect_rate'])):
            output=[{'region_id':'__whole_template__','label':'전체 외형',
                'grid_width':data['grid_width'],'grid_height':data['grid_height'],'values':data['defect_rate'],
                'valid_observation_counts':data['known_count'],'coverage_mask':data['coverage_mask'],
                'source_bounds':[0,0,data['source_image_width'],data['source_image_height']],
                'aggregation_method':'mask_presence_frequency','sample_products':data['known_products'],'unknown_products':data['unknown_products']}]
    else:
        output,product,split=model_regions(item,view,source,product_id)
    return {'item':item,'view':view,'source':source,'product_id':product,'split':split,'regions':output,
            'projection_domain':'whole_template' if output and output[0]['region_id']=='__whole_template__' else 'roi_regions',
            'status':'supported' if output else 'unavailable','physical_alignment_verified':False,
            'mapping_note':'User-authorized approximate surface projection for display, not measured physical localization.',**settings(item,view)}
