"""Verify actual shared data over authenticated ASGI HTTP, without server lifespan."""
import asyncio,json,os,sys
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.validate_spatial_api import request
from app.team_api import app
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'team_integration_kit/samples'

async def main():
    token=os.environ['TEAM_ACCESS_TOKEN'];headers=[(b'authorization',('Bearer '+token).encode())]
    checks=[];OUT.mkdir(parents=True,exist_ok=True)
    queries=[('manifest','/sharing/manifest',{}),('items','/sharing/manifest',{}),
      ('parts','/catalog/parts',{'item':'toothbrush'}),('roi','/roi/templates',{'item':'toothbrush','view':'C1'}),
      ('products','/products',{'item':'toothbrush','limit':2}),
      ('views','/products/views',{'product_id':'toothbrush/NG/CH/S0001'}),
      ('findings','/products/findings',{'product_id':'toothbrush/NG/CH/S0001','view':'C1','min_confidence':.4}),
      ('map','/products/anomaly-map',{'product_id':'toothbrush/NG/CH/S0001','view':'C1','format':'metadata'}),
      ('map_array','/products/anomaly-map',{'product_id':'toothbrush/NG/CH/S0001','view':'C1','format':'array'}),
      ('map_unsupported','/products/anomaly-map',{'product_id':'zipper/NG/BX/S0002','view':'C1'}),
      ('spatial32','/parts/spatial-heatmap',{'item':'toothbrush','view':'C1','region_id':'bristle','resolution':32,'model':'rt'}),
      ('region_heatmap','/parts/heatmap',{'item':'toothbrush'}),
      ('fusion','/products/fusion',{'product_id':'toothbrush/NG/CH/S0001'}),
      ('performance','/performance/final',{}),('tools','/tools',{})]
    queries.extend([
      ('gt_catalog','/heatmaps/catalog',{}),
      ('gt_toothbrush','/heatmaps/ground-truth',{'item':'toothbrush','view':'C1','split':'train'}),
      ('gt_zipper','/heatmaps/ground-truth',{'item':'zipper','view':'C1','split':'train'}),
      ('gt_toothbrush_product','/heatmaps/ground-truth',{'item':'toothbrush','view':'C1','split':'train','product_id':'toothbrush/NG/CH/S0001'}),
      ('gt_zipper_missing_mask','/heatmaps/ground-truth',{'item':'zipper','view':'C2','split':'train','product_id':'zipper/NG/BX/S0002'}),
      ('gt_roi','/heatmaps/ground-truth',{'item':'toothbrush','view':'C1','split':'train','region_id':'bristle'})])
    for name,path,query in queries:
        code,body,duration=await request('/api'+path,urlencode(query),application=app,headers=headers)
        assert code==200,(path,code,body[:120])
        payload=json.loads(body)
        (OUT/(name+'.json')).write_text(json.dumps(payload,indent=2,ensure_ascii=False))
        checks.append({'sample':name,'path':'/api'+path,'query':query,'status':code,'asgi_ms':duration,'bytes':len(body)})
        print(name,code,len(body),flush=True)
    assert json.loads((OUT/'items.json').read_text())['items'].__len__()==30
    assert json.loads((OUT/'manifest.json').read_text())['products']==24000
    assert len(json.loads((OUT/'spatial32.json').read_text())['values'])==1024
    assert json.loads((OUT/'map_unsupported.json').read_text())['status']=='unsupported'
    gt=json.loads((OUT/'gt_toothbrush.json').read_text())
    assert gt['known_products']==335 and len(gt['values'])==4096 and gt['split']=='train'
    assert not gt['normal_products_included']
    missing=json.loads((OUT/'gt_zipper_missing_mask.json').read_text())
    assert missing['known_products']==0 and all(value is None for value in missing['values'])
    # Unauthorized requests cannot read data; no DB writes or inference are tested.
    code,_,_=await request('/api/products',application=app)
    assert code==401
    code,_,_=await request('/api/inference/run',application=app,headers=headers,method='POST')
    assert code in (404,405)
    code,body,_=await request('/api/openapi.json',application=app,headers=headers)
    assert code==200 and '/products/findings' in json.loads(body)['paths']
    # Browser preflight must work without exposing keys/cookies in a URL.
    code,_,_=await request('/api/products',application=app,method='OPTIONS',headers=[
        (b'origin',b'http://localhost:5173'),(b'access-control-request-method',b'GET'),
        (b'access-control-request-headers',b'authorization')])
    assert code==200
    summary={'status':'VERIFIED_AUTHENTICATED_ASGI_NO_NETWORK','checks':checks,'unauthenticated_status':401,
             'inference_unavailable':True,'cors_preflight':'passed','lifespan_executed':False,
             'network_verification':'BLOCKED_socket_EPERM','operational_PG_reads':'not_verified_in_sandbox'}
    (ROOT/'reports/gui_validation/spatial-urgent/team-data-validation.json').write_text(json.dumps(summary,indent=2))
    print('Verified shared actual-data requests:',len(checks))
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),45))
