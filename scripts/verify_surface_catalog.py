"""Verify/export all 30x5 actual GT surface fields without any server startup."""
import asyncio,json,sys
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from app.surface_api import router
from app.ground_truth_api import index
from scripts.validate_spatial_api import request
ROOT=Path(__file__).resolve().parents[1];app=FastAPI();app.include_router(router)
async def main():
    items=sorted({entry['item'] for entry in index()['entries']});checks=[]
    out=ROOT/'team_integration_kit/surface_frames';out.mkdir(exist_ok=True)
    for item in items:
        code,body,_=await request('/heatmaps/surface-layout',urlencode({'item':item}),application=app)
        layout=json.loads(body);assert code==200 and next(source for source in layout['sources'] if source['id']=='ground_truth')['views']==['C1','C2','C3','C4','C5']
        for view in ('C1','C2','C3','C4','C5'):
            code,body,elapsed=await request('/heatmaps/surface',urlencode({'item':item,'view':view,'source':'ground_truth'}),application=app)
            data=json.loads(body);assert code==200 and data['regions'] and data['scope']=='visualization_only_approximate'
            assert data['user_authorized_approximate_projection'] and data['physical_alignment_verified'] is False
            assert data['split']=='train'
            for region in data['regions']:
                assert len(region['values'])==len(region['coverage_mask'])==region['grid_width']*region['grid_height']
                assert all(value is None or 0<=value<=1 for value in region['values'])
            (out/f'{item}-{view}-ground_truth.json').write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False))
            checks.append({'item':item,'view':view,'status':code,'regions':len(data['regions']),'domain':data['projection_domain'],'asgi_ms':elapsed,
                           'positive_cells':sum(value is not None and value>0 for region in data['regions'] for value in region['values'])})
        print(item,'5 views verified',flush=True)
    # Same saved representative product for RT/HVQ; no model inference.
    model_checks=[]
    for item in items:
        for view in ('C1','C2','C3','C4','C5'):
            pair=[]
            for source in ('rt','hvq'):
                code,body,_=await request('/heatmaps/surface',urlencode({'item':item,'view':view,'source':source}),application=app)
                data=json.loads(body);assert code==200 and data['regions']
                (out/f'{item}-{view}-{source}.json').write_text(json.dumps(data,separators=(',',':')))
                pair.append(data['product_id']);model_checks.append({'item':item,'view':view,'source':source,'status':code,'product_id':data['product_id']})
            assert pair[0]==pair[1]
        print(item,'RT/HVQ same-product saved maps verified',flush=True)
    result={'status':'VERIFIED_ASGI_NO_NETWORK','categories':len(items),'GT_item_views':len(checks),'checks':checks,'model_checks':model_checks,'inference_executed':False,'physical_alignment_verified':False}
    (ROOT/'reports/gui_validation/spatial-urgent/surface-catalog-validation.json').write_text(json.dumps(result,indent=2))
    print('Verified',len(items),'categories /',len(checks),'GT views; saved RT/HVQ separately')
asyncio.run(main())
