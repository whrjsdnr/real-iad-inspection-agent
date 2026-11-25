"""Bounded, read-only exports of existing batch evidence and ROI configuration.

This router never creates tables, runs a model or activates a fusion report.
Stored batch scores and report-only fusion verdicts are explicitly separate.
"""
import csv
import json
import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,HTTPException,Query
from fastapi.responses import FileResponse
from .part_heatmap import fingerprint,region_for_box
from .spatial_heatmap import ROOT

router=APIRouter(tags=['shared saved evidence'])
@router.get('/sharing/kit')
async def integration_kit():
    path=ROOT/'team_integration_kit.zip'
    if not path.is_file():raise HTTPException(503,'공유 패키지가 아직 생성되지 않았습니다.')
    return FileResponse(path,filename='team_integration_kit.zip',media_type='application/zip')
CONFIG=ROOT/'config/spatial_heatmap.json'

def configuration():return json.loads(CONFIG.read_text())

@contextmanager
def database():
    path=Path(configuration()['source_score_cache'])
    if not path.is_file():raise HTTPException(503,'저장 batch 점수 캐시 없음')
    connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    connection.row_factory=sqlite3.Row
    try:
        connection.execute('PRAGMA query_only=ON')
        yield connection
    finally:connection.close()


def clean(value):
    """Export config without local absolute filenames or model asset paths."""
    if isinstance(value,dict):return {key:clean(item) for key,item in value.items()}
    if isinstance(value,list):return [clean(item) for item in value]
    if isinstance(value,str) and value.startswith('/'):
        root=Path(configuration()['dataset_root'])
        try:return str(Path(value).relative_to(root))
        except ValueError:return Path(value).name
    return value


def roi_config():return json.loads((ROOT/'config/part_heatmap_regions.json').read_text())


def parts_catalog(item=None):
    config=roi_config();hierarchy=json.loads((ROOT/'config/spatial_regions.json').read_text())
    mesh_catalog=ROOT/'config/mesh_parts_catalog.json'
    entries={(entry['item'],entry['region_id']):dict(entry) for entry in json.loads(mesh_catalog.read_text())['parts']
             if not item or entry['item']==item} if mesh_catalog.is_file() else {}
    for template in config['templates']:
        category=template['item']
        if item and category!=item:continue
        for region in template['regions']:
            key=(category,region['region_id'])
            entry=entries.setdefault(key,{'item':category,'region_id':region['region_id'],'parent_region_id':None,
                'display_name':region['label'],'supported_views':[],'mapping_status':'image_roi_template_physical_uv_unverified'})
            entry['supported_views'].append(template['camera'])
            entry['mapping_status']='image_roi_template_physical_uv_unverified'
    for node in hierarchy['nodes']:
        if item and node['category']!=item:continue
        key=(node['category'],node['region_id'])
        entry=entries.setdefault(key,{'item':node['category'],'region_id':node['region_id'],
             'parent_region_id':node['parent_region_id'],'display_name':node['display_name'],
             'supported_views':node.get('supported_views',[]),'mapping_status':node['mapping_status']})
        entry['supported_views']=list(set(entry['supported_views'])|set(node.get('camera_rois',{})))
        entry['mesh_part_id']=node.get('mesh_part_id',node['region_id'])
    for entry in entries.values():entry['supported_views']=sorted(set(entry['supported_views']))
    return {'mapping_version':hierarchy['version'],'parts':list(entries.values()),
            'physical_surface_uv_verified':False,'note':'ROI envelope is not a calibrated visibility/occlusion mask.'}


@router.get('/catalog/parts')
async def catalog_parts(item:str|None=None):return parts_catalog(item)


@router.get('/roi/templates')
async def roi_templates(item:str|None=None,view:Literal['C1','C2','C3','C4','C5']|None=None,
    region_id:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=100)):
    cfg=roi_config();rows=[]
    for template in cfg['templates']:
        if (item and template['item']!=item) or (view and template['camera']!=view):continue
        entry=dict(template)
        if region_id:entry['regions']=[region for region in entry['regions'] if region['region_id']==region_id]
        if entry['regions']:rows.append(clean(entry))
    return {'version':cfg['version'],'coordinate_space':'original_pixels','total':len(rows),'offset':offset,'limit':limit,
            'templates':rows[offset:offset+limit],'physical_surface_uv_verified':False}


@router.get('/roi/templates/{item}')
async def roi_item(item:str,view:Literal['C1','C2','C3','C4','C5']|None=None,region_id:str|None=None,
    offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=100)):
    return await roi_templates(item,view,region_id,offset,limit)


@router.get('/roi/hierarchy')
async def roi_hierarchy(item:str|None=None):
    result=clean(json.loads((ROOT/'config/spatial_regions.json').read_text()))
    if item:
        result['nodes']=[node for node in result['nodes'] if node['category']==item]
        result['native_references']={key:value for key,value in result.get('native_references',{}).items() if key==item}
    return result


@router.get('/products')
async def products(item:str|None=None,product_id:str|None=None,status:str|None=None,maps_only:bool=False,
    offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    clauses=[];args=[]
    for column,value in [('category',item),('product_id',product_id),('status',status)]:
        if value is not None:clauses.append(column+'=?');args.append(value)
    if maps_only:clauses.append("EXISTS(SELECT 1 FROM views v WHERE v.product_id=products.product_id AND v.map_path IS NOT NULL AND v.map_path!='')")
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    with database() as connection:
        total=connection.execute('SELECT count(*) FROM products'+where,args).fetchone()[0]
        rows=connection.execute('SELECT product_id,category,split,truth,status,hvq_max,rtdetr_max,completed_at FROM products'+where+' ORDER BY product_id LIMIT ? OFFSET ?',[*args,limit,offset]).fetchall()
    return {'source':'saved_batch5_score_cache','total':total,'offset':offset,'limit':limit,'products':[dict(row) for row in rows],
            'score_semantics':'Raw saved columns, not normalized fusion scores. Does not replace operational DB verdicts.'}


def saved_views(product_id,view=None):
    with database() as connection:
        exists=connection.execute('SELECT 1 FROM products WHERE product_id=?',(product_id,)).fetchone()
        if not exists:raise HTTPException(404,'저장 제품 없음')
        rows=connection.execute('SELECT * FROM views WHERE product_id=?'+(' AND camera=?' if view else '')+' ORDER BY camera',
                                (product_id,view) if view else (product_id,)).fetchall()
    return [dict(row) for row in rows]


def image_path(row):
    base=Path(configuration()['dataset_root']).resolve();path=Path(row['image_path'])
    path=(base/path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(base):raise HTTPException(403,'원본 자료 루트 밖의 경로')
    return path


@lru_cache(maxsize=2)
def gui_maps(stamp):
    rows={}
    for file in (ROOT/'gui_evidence').glob('*/result.json'):
        data=json.loads(file.read_text())
        for view,record in data.get('views',{}).items():
            path=Path(record.get('map_npy','')).resolve();image=Path(record['image_path']).resolve()
            if path.is_relative_to((ROOT/'gui_evidence').resolve()) and path.is_file() and image.is_file():
                rows.setdefault((data['product_id'],view),[]).append({'path':str(path),'image_sha256':fingerprint(image)})
    return rows


def stored_map(row):
    raw=row.get('map_path')
    if raw:
        base=Path(configuration()['source_score_cache']).resolve().parent
        path=(base/raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
        image=image_path(row)
        if path.is_relative_to(base) and path.suffix=='.npy' and path.is_file() and image.is_file():
            expected=row.get('source_fingerprint','')
            stat=image.stat();actual=f'stat:{stat.st_size}:{stat.st_mtime_ns}'
            if not expected or expected==actual:
                return {'path':str(path),'image_sha256':fingerprint(image),'source':'saved_batch5_map_cache'}
    folder=ROOT/'gui_evidence'
    files=list(folder.glob('*/result.json'));stamp=max((file.stat().st_mtime_ns for file in files),default=0)
    candidates=gui_maps(stamp).get((row['product_id'],row['camera']),[])
    if candidates and image_path(row).is_file():
        digest=fingerprint(image_path(row))
        for data in candidates:
            if digest==data['image_sha256']:return data|{'source':'saved_gui_map_exact_source_image_sha256'}
    return None


@router.get('/products/views')
async def views(product_id:str,view:Literal['C1','C2','C3','C4','C5']|None=None):
    result=[]
    for row in saved_views(product_id,view):
        mapping=stored_map(row)
        result.append({'product_id':product_id,'view':row['camera'],'width':row['width'],'height':row['height'],
          'hvq_score':row['hvq'],'hvq_score_semantics':'source views.hvq; matched toothbrush GUI sample agrees with heatmap_mean, cohort provenance not independently verified',
          'rtdetr_score':row['rtdetr'],'bbox_coordinate_space':'original_pixels_xyxy',
          'image_supported':image_path(row).is_file(),'anomaly_map_status':('supported_saved_batch_map' if mapping['source']=='saved_batch5_map_cache' else 'supported_exact_image_sha') if mapping else 'unsupported_no_verified_saved_map',
          'coordinate_transform':{'original_size':[row['width'],row['height']],
              'bbox_output':'original pixel xyxy restored by orig_sizes in batch_fusion/inference postprocess',
              'model_preprocess_reference':'direct_resize_in_inference_code','per_record_transform_metadata':None,'crop':None,'letterbox':None,
              'anomaly_map_transform':'full_frame_direct_resize_224' if mapping else None,
              'camera_extrinsics':None,'product_alignment':'unverified','physical_uv_mapping':'unverified'}})
    return {'source':'saved_batch5_score_cache','product_id':product_id,'views':result}


@router.get('/products/findings')
async def findings(product_id:str,view:Literal['C1','C2','C3','C4','C5']|None=None,model:Literal['rt']='rt',
    region_id:str|None=None,min_confidence:float=Query(0,ge=0,le=1),offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500)):
    templates={(entry['item'],entry['camera']):entry for entry in roi_config()['templates']};rows=[]
    for row in saved_views(product_id,view):
        template=templates.get((product_id.split('/')[0],row['camera']))
        regions=template['regions'] if template and template['image_size']==[row['width'],row['height']] else []
        for number,box in enumerate(json.loads(row['boxes_json'])):
            confidence=float(box.get('confidence',box.get('score',0)))
            if confidence<min_confidence:continue
            region=region_for_box(box['bbox'],regions,row['width'],row['height']) if regions else None
            if region_id and region_id!=region:continue
            rows.append({'product_id':product_id,'view':row['camera'],'detection_index':number,'bbox':box['bbox'],
                         'confidence':confidence,'class_id':box.get('class_id',box.get('label')),'region_id':region,
                         'mapping_status':'center_in_unique_image_roi' if region else 'unmapped','coordinate_space':'original_pixels_xyxy'})
    return {'source':'saved_batch5_box_cache','product_id':product_id,'model':model,'total':len(rows),'offset':offset,'limit':limit,
            'findings':rows[offset:offset+limit],'note':'Stored detections, not confirmed defects. ROI-center assignment differs from spatial box-area overlap.'}


@router.get('/products/image')
async def original_image(product_id:str,view:Literal['C1','C2','C3','C4','C5']):
    rows=saved_views(product_id,view)
    if not rows or not image_path(rows[0]).is_file():raise HTTPException(404,'원본 영상 없음')
    return FileResponse(image_path(rows[0]))


@router.get('/products/anomaly-map')
async def anomaly_map(product_id:str,view:Literal['C1','C2','C3','C4','C5'],format:Literal['metadata','array','npy']='metadata'):
    import numpy as np
    rows=saved_views(product_id,view);mapping=stored_map(rows[0]) if rows else None
    if not mapping:return {'status':'unsupported','reason':'no_verified_saved_anomaly_map','product_id':product_id,'view':view}
    path=Path(mapping['path'])
    data=np.asarray(np.load(path,allow_pickle=False)).squeeze()
    if data.ndim!=2 or not np.isfinite(data).all():raise HTTPException(409,'저장 맵 형상/값 검증 실패')
    if format=='npy':return FileResponse(path,filename='saved-anomaly-map.npy',media_type='application/octet-stream')
    response={'status':'supported','product_id':product_id,'view':view,'grid_width':data.shape[1],'grid_height':data.shape[0],
              'source':mapping['source'],'original_size':[rows[0]['width'],rows[0]['height']],
              'coordinate_transform':'full_frame_direct_resize','physical_surface_uv_verified':False}
    if format=='array':response['values']=data.tolist()
    return response


@lru_cache(maxsize=1)
def predictions(stamp):
    path=ROOT/'reports/final_performance_minmax/all_predictions.csv'
    with path.open() as stream:
        fields=('category','split','truth','rt_normalized','hvq_normalized','fusion_score','threshold','margin','binary_verdict','verdict')
        return {row['product_id']:{key:row[key] for key in fields} for row in csv.DictReader(stream)}


@router.get('/products/fusion')
async def fusion(product_id:str):
    path=ROOT/'reports/final_performance_minmax/all_predictions.csv'
    if not path.is_file():raise HTTPException(503,'저장된 계약 평가 CSV 없음')
    row=predictions(path.stat().st_mtime_ns).get(product_id)
    if not row:raise HTTPException(404,'계약 보고서에 해당 제품 없음')
    policy=json.loads((ROOT/'config/fusion_evaluation.json').read_text())
    row={key:float(value) if key in ('rt_normalized','hvq_normalized','fusion_score','threshold','margin') else value for key,value in row.items()}
    return {'product_id':product_id,'source':'saved_report_only_predictions','database_run_activated':False,
            'contract_version':policy['version'],'weights':policy['weights'],'result':row,
            'operational_verdict_status':'not_replaced_or_verified_against_current_DB_run'}


@router.get('/sharing/manifest')
async def manifest():
    with database() as connection:
        products=connection.execute('SELECT count(*) FROM products').fetchone()[0]
        views=connection.execute('SELECT count(*) FROM views').fetchone()[0]
        items=[row[0] for row in connection.execute('SELECT DISTINCT category FROM products ORDER BY category')]
        map_views,map_products=connection.execute("SELECT count(*),count(DISTINCT product_id) FROM views WHERE map_path IS NOT NULL AND map_path!=''").fetchone()
    return {'source':'existing_saved_batch5_readonly_cache','products':products,'views':views,
      'items':items,
      'saved_map_references':{'views':map_views,'products':map_products,'discovery':'GET /products?maps_only=true',
          'note':'Reference counts; per-view anomaly-map endpoint verifies file and source image before serving.'},
      'roi_templates':len(roi_config()['templates']),'models':json.loads((ROOT/'config/fusion.json').read_text())['model_versions'],
      'fusion_contract':json.loads((ROOT/'config/fusion_evaluation.json').read_text()),
      'scope':{'stored_scores':'all cached products','spatial_grids':'precomputed representative products only',
               'anomaly_maps':'saved batch maps resolved relative to score-cache directory and source-validated; exact-image GUI maps are fallback','physical_surface_uv':'unverified; user-authorized display projection available',
               'operational_DB_decisions':'use existing central tools; cached report verdicts are separate'},
      'reuse_existing':['/items','/parts/heatmap','/parts/spatial-heatmap','/performance/final','/tools'],
      'schemas_or_decisions_modified':False}
