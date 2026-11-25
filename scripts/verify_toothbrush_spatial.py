"""Actual saved toothbrush C1 -> 32x32 ASGI response; no model, DB writes or lifespan."""
import asyncio
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.validate_spatial_api import request
from app.spatial_api import index

OUT=Path(__file__).resolve().parents[1]/'reports/gui_validation/spatial-urgent'

async def main():
    code,body,elapsed=await request('/parts/spatial-heatmap',
        'item=toothbrush&view=C1&region_id=bristle&model=rt&resolution=32&method=confidence_area')
    assert code==200,(code,body[:200])
    result=json.loads(body)
    assert result['grid_width']==result['grid_height']==32
    assert len(result['values'])==1024 and len(result['values_2d'])==32
    assert all(len(row)==32 for row in result['values_2d'])
    assert len(set(result['values']))>1,'Spatial data collapsed into one region scalar'
    assert result['view']=='C1' and result['source_detections']
    x0,y0,x1,y1=result['roi_bounds'];centers=[]
    for detection in result['source_detections']:
        bx0,by0,bx1,by1=detection['bbox'];x=(bx0+bx1)/2;y=(by0+by1)/2
        column=math.floor((x-x0)/(x1-x0)*32);row=math.floor((y-y0)/(y1-y0)*32)
        if 0<=column<32 and 0<=row<32 and result['coverage_mask'][row*32+column]:
            assert result['center_counts'][row*32+column]>=1
            centers.append({'native_center':[x,y],'column':column,'row':row,'score':detection['score']})
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'toothbrush-C1-32-api-response.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    entry=next(entry for entry in index()['entries'] if entry['grid_id']==result['grid_id'])
    source=index()['views'][entry['image_id']]
    (OUT/'toothbrush-C1-source.json').write_text(json.dumps(source,indent=2,ensure_ascii=False))
    summary={'status':'VERIFIED_ASGI_NO_NETWORK','product_id':result['product_id'],'grid':[32,32],
             'distinct_values':len(set(result['values'])),'nonzero_cells':sum(v is not None and v>0 for v in result['values']),
             'stats':result['stats'],'verified_box_center_cells':centers,'asgi_ms':elapsed,
             'physical_surface_uv':'unverified','browser':'blocked_socket_EPERM','response_bytes':len(body)}
    from app.spatial_preview import app as preview
    from app.api import app as central
    route_checks=[]
    query='item=toothbrush&view=C1&region_id=bristle&model=rt&resolution=32&method=confidence_area'
    # HTTP scopes only: never enter central lifespan (migration/worker startup).
    for name,application,path in [('preview',preview,'/api/parts/spatial-heatmap'),('central_no_lifespan',central,'/parts/spatial-heatmap')]:
        status,payload,duration=await request(path,query,application=application)
        parsed=json.loads(payload);assert status==200 and parsed['values']==result['values']
        route_checks.append({'application':name,'path':path,'status':status,'asgi_ms':duration})
    summary['mounted_route_checks']=route_checks
    (OUT/'toothbrush-C1-summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),15))
