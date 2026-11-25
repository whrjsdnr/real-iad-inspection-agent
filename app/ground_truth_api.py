"""Read-only adapter for the preserved MV Train-NG mask-presence artifacts."""
import gzip,json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
import numpy as np
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from .coordinates import Size
from .part_heatmap import fingerprint,polygon_mask
from .spatial_heatmap import ROOT

router=APIRouter(tags=['preserved MV ground truth'])
CACHE=ROOT/'reports/ground_truth_heatmaps'

@lru_cache(maxsize=2)
def _loaded(stamp):return json.loads((CACHE/'index.json').read_text())

def index():
    try:data=_loaded((CACHE/'index.json').stat().st_mtime_ns)
    except (OSError,ValueError):raise HTTPException(503,'MV 마스크 히트맵 가져오기 캐시 없음')
    if data['config_sha256']!=fingerprint(ROOT/'config/ground_truth_heatmaps.json'):
        raise HTTPException(409,'MV adapter 설정 변경 후 다시 가져오기가 필요합니다.')
    return data


@router.get('/heatmaps/catalog')
async def catalog(item:str|None=None):
    data=index();entries=[entry for entry in data['entries'] if not item or entry['item']==item]
    return {'version':data['version'],'available_splits':['train'],'normal_products_included':False,
            'rtdetr_visualization_threshold':json.loads((ROOT/'config/fusion_evaluation.json').read_text())['rtdetr_conf_threshold'],
            'grid_width':64,'grid_height':64,'entries':entries,
            'source':'MV/windows_preserved_20261111_v1/presence-v2',
            'ground_truth_endpoint':'/heatmaps/ground-truth','model_endpoint':'/parts/spatial-heatmap',
            'physical_surface_uv_verified':False}


def record(item,view,split,product_id):
    if split!='train':raise HTTPException(404,'기존 MV 히트맵은 Windows 보존 Train NG만 지원합니다.')
    entry=next((entry for entry in index()['entries'] if entry['item']==item and entry['view']==view
                and entry['product_id']==product_id),None)
    if not entry:raise HTTPException(404,'해당 품목/시점/제품의 기존 마스크 집계 없음')
    with gzip.open(CACHE/(entry['id']+'.json.gz'),'rt') as stream:return entry,json.load(stream)


def restrict_roi(data,region_id):
    if not region_id:return data
    config=json.loads((ROOT/'config/part_heatmap_regions.json').read_text())
    hierarchy=json.loads((ROOT/'config/spatial_regions.json').read_text())
    node=next((node for node in hierarchy['nodes'] if node['category']==data['item'] and node['region_id']==region_id),{})
    polygons=node.get('camera_rois',{}).get(data['view'])
    if not polygons:
        template=next((entry for entry in config['templates'] if entry['item']==data['item'] and entry['camera']==data['view']),{})
        region=next((region for region in template.get('regions',[]) if region['region_id']==region_id),None)
        if region:polygons=region.get('polygons') or [region['polygon']]
    if not polygons:raise HTTPException(404,'이 부위/시점의 원본 좌표 ROI가 등록되지 않았습니다.')
    width,height=data['source_image_width'],data['source_image_height'];mask=np.zeros((64,64),bool)
    for polygon in polygons:
        mask|=polygon_mask([[x*64/width,y*64/height] for x,y in polygon],Size(64,64))
    selected=mask.ravel().tolist()
    for key in ('positive_count','known_count','unknown_count'):
        data[key]=[value if valid else 0 for value,valid in zip(data[key],selected)]
    for key in ('defect_rate','occupancy_positive','mask_coverage'):
        data[key]=[value if valid else None for value,valid in zip(data[key],selected)]
    data['coverage_mask']=[int(valid and covered) for valid,covered in zip(selected,data['coverage_mask'])]
    data.update(region_id=region_id,roi_polygons=polygons,
                roi_filter='cell-center selection on existing full-frame 64 grid; boundary precision not increased')
    return data


@router.get('/heatmaps/ground-truth')
async def ground_truth(item:str,view:Literal['C1','C2','C3','C4','C5']='C1',split:str='train',
                       product_id:str|None=None,region_id:str|None=None):
    entry,data=record(item,view,split,product_id);data=restrict_roi(data,region_id)
    data={key:value for key,value in data.items() if key not in ('image_path','mask_path')}
    data.update(values=data['defect_rate'],observation_counts=data['known_count'],
                aggregation_metric='occupancy_known',grid_layout='row_major_y_down',
                image_url='/heatmaps/evidence?'+urlencode({'id':entry['id'],'kind':'image'}) if product_id else None,
                mask_url='/heatmaps/evidence?'+urlencode({'id':entry['id'],'kind':'mask'}) if product_id and data['known_products'] else None)
    return data


@router.get('/heatmaps/metadata')
async def metadata(item:str|None=None):
    data=index()
    return {key:value for key,value in data.items() if key!='entries'}|{
        'entries':[entry for entry in data['entries'] if not item or entry['item']==item],
        'scope_note':'Train NG provided-mask conditional distribution; not Test distribution or overall defect prevalence.'}


@router.get('/heatmaps/evidence')
async def evidence(id:str,kind:Literal['image','mask']='image'):
    entry=next((entry for entry in index()['entries'] if entry['id']==id and entry['product_id']),None)
    if not entry:raise HTTPException(404,'등록된 개별 마스크 근거 없음')
    _,data=record(entry['item'],entry['view'],'train',entry['product_id'])
    raw=data['image_path'] if kind=='image' else data['mask_path']
    if not raw:raise HTTPException(404,'이 시점의 제공 마스크 없음; unknown')
    path=Path(raw).resolve();cfg=json.loads((ROOT/'config/ground_truth_heatmaps.json').read_text())
    if not path.is_relative_to(Path(cfg['dataset_root']).resolve()):raise HTTPException(403,'허용된 자료 루트 밖의 경로')
    if not path.is_file():raise HTTPException(404,'원본 근거 파일 없음')
    if kind=='image' and fingerprint(path)!=data['comparison']['source_image_sha256']:raise HTTPException(409,'검증 후 원본 영상 변경')
    return FileResponse(path)
