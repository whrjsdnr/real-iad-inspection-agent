"""Read precomputed grids only; no scanning the operational DB in HTTP requests."""
import gzip
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from .part_heatmap import fingerprint
from .spatial_heatmap import ROOT

router=APIRouter()
CACHE=ROOT/'reports/spatial_heatmap'


@lru_cache(maxsize=2)
def _index_modified(stamp):
    return json.loads((CACHE/'index.json').read_text())


def index():
    try:return _index_modified((CACHE/'index.json').stat().st_mtime_ns)
    except (OSError,json.JSONDecodeError):raise HTTPException(503,'저장된 공간 히트맵 캐시가 없습니다.')


def public_index(item:str|None=None):
    data=index()
    return {key:value for key,value in data.items() if key!='views'} | {'entries':[entry for entry in data['entries'] if not item or entry['item']==item]}


def grid(grid_id:str,model:Literal['rt','hvq']='rt',method:str='gaussian'):
    data=index()
    if not any(entry['grid_id']==grid_id for entry in data['entries']):raise HTTPException(404,'등록된 공간 지도 없음')
    for name,expected in data['config_hashes'].items():
        if fingerprint(ROOT/name)!=expected:raise HTTPException(409,'ROI 또는 설정 변경 후 공간 캐시 재생성이 필요합니다.')
    if data.get('algorithm_hash') and data['algorithm_hash']!=fingerprint(ROOT/'app/spatial_heatmap.py'):
        raise HTTPException(409,'공간 계산 코드 변경 후 캐시 재생성이 필요합니다.')
    with gzip.open(CACHE/f'{grid_id}.json.gz','rt') as stream:record=json.load(stream)
    source=record[model]
    if source['status']=='supported' and method not in source['values']:raise HTTPException(400,'지원하지 않는 공간 집계 방식')
    result={key:value for key,value in record.items() if key not in ('rt','hvq','source_image')}
    return result | {'model':model,'aggregation_method':method,'status':source['status'],'reason':source.get('reason'),
                     'values':source['values'].get(method,[]),'valid_observation_counts':source.get('valid_observation_counts_by_method',{}).get(method,source['valid_observation_counts']),
                     'native_map_size':source.get('native_map_size'),'native_sample_counts':source.get('native_sample_counts'),
                     'region_value':source.get('region_value'),
                     'note':source.get('note'),'image_url':f"/parts/spatial/image/{record['source_image_id']}"}


def spatial_heatmap(item='toothbrush',view='C1',region_id='bristle',model='rt',product_id=None,resolution=32,method='confidence_area'):
    """A bounded lookup of one saved product/view. Never aggregate different views."""
    entries=[entry for entry in index()['entries'] if entry['item']==item and entry['camera']==view
             and entry['region_id']==region_id and entry['resolution']==resolution
             and (product_id is None or entry['product_id']==product_id)]
    if not entries:raise HTTPException(404,'해당 제품·카메라·부위의 저장 공간 지도가 없습니다.')
    entry=entries[0];result=grid(entry['grid_id'],model,method)
    counts=result['valid_observation_counts']
    result.update(grid_id=entry['grid_id'],view=view,observation_counts=counts,
                  coordinate_system='original_image_pixels',grid_layout='row_major_y_down',
                  rate_supported=False,observation_scope='image_roi_envelope_not_calibrated_surface_visibility')
    if result['status']!='supported':return result
    result['values_2d']=[result['values'][row*resolution:(row+1)*resolution] for row in range(resolution)]
    # Keep the actual RT evidence accessible beside the visualization. This does
    # not change the saved cache, product decision, ROI or fusion policy.
    if model=='rt':
        import numpy as np
        with gzip.open(CACHE/f"{entry['grid_id']}.json.gz",'rt') as stream:saved=json.load(stream)
        result['center_counts']=saved['rt']['values']['center_count']
        result['detected_product_counts']=saved['rt']['values']['product_occupancy']
        result['confidence_weighted_area']=saved['rt']['values']['confidence_area']
        result['mean_confidence']=saved['rt']['values']['mean_confidence']
        evidence=index()['views'][saved['source_image_id']]
        unique={(tuple(box['bbox']),box['score']):box for box in evidence['detections']}
        x0,y0,x1,y1=saved['roi_bounds'];yy,xx=np.indices((resolution,resolution))
        left=x0+xx*(x1-x0)/resolution;right=left+(x1-x0)/resolution
        top=y0+yy*(y1-y0)/resolution;bottom=top+(y1-y0)/resolution
        mask=np.asarray(saved['coverage_mask'],bool).reshape(resolution,resolution)
        hits=np.zeros((resolution,resolution),int);contributing=[]
        for box in unique.values():
            bx0,by0,bx1,by1=box['bbox']
            overlap=(left<bx1)&(right>bx0)&(top<by1)&(bottom>by0)&mask
            if overlap.any():hits+=overlap;contributing.append(box)
        result['box_occupancy_counts']=[int(value) if covered else None for value,covered in zip(hits.ravel(),mask.ravel())]
        result['source_detections']=contributing
        result['unobserved_mask']=[not bool(count) for count in counts]
    return result


# These small cached reads need no thread-worker/DB/inference job. Keep the pure
# functions callable by tools and tests; expose async ASGI endpoints separately.
@router.get('/parts/spatial/index')
async def index_endpoint(item:str|None=None):return public_index(item)


@router.get('/parts/spatial/grid/{grid_id}')
async def grid_endpoint(grid_id:str,model:Literal['rt','hvq']='rt',method:str='gaussian'):
    return grid(grid_id,model,method)


@router.get('/parts/spatial-heatmap')
async def spatial_heatmap_endpoint(item:str='toothbrush',view:Literal['C1','C2','C3','C4','C5']='C1',
    region_id:str='bristle',model:Literal['rt','hvq']='rt',product_id:str|None=None,
    resolution:int=32,method:str='confidence_area'):
    if resolution not in (16,32,64,128):raise HTTPException(422,'지원하는 해상도는16,32,64,128입니다.')
    return spatial_heatmap(item,view,region_id,model,product_id,resolution,method)


@router.get('/parts/spatial/image/{image_id}')
def image(image_id:str):
    view=index()['views'].get(image_id)
    if not view:raise HTTPException(404,'원본 근거 없음')
    try:
        if fingerprint(view['image_path'])!=view['image_sha256']:raise HTTPException(409,'원본 이미지가 변경되었습니다.')
        return FileResponse(view['image_path'],media_type='image/jpeg')
    except OSError:raise HTTPException(404,'원본 이미지 없음')
