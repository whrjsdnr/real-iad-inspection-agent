"""GET-only local Vite transport to existing MV APIs. No server/DB/model startup."""
import asyncio,base64,json,sys
from pathlib import Path
from urllib.parse import parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI,HTTPException
from app.ground_truth_api import router,evidence
from app.shared_data_api import router as shared_router
from app.shared_data_api import integration_kit
from app.surface_api import router as surface_router
from scripts.validate_spatial_api import request

ALLOWED={'/heatmaps/catalog','/heatmaps/ground-truth','/heatmaps/metadata','/heatmaps/evidence','/products/findings','/heatmaps/surface','/heatmaps/surface-layout','/sharing/kit'}
app=FastAPI();app.include_router(router);app.include_router(shared_router)
app.include_router(surface_router)
async def main():
    data=json.loads(sys.stdin.read());path=data.get('path','');query=data.get('query','')
    if path not in ALLOWED:raise ValueError('Path not allowed in local MV bridge')
    if path in ('/heatmaps/evidence','/sharing/kit'):
        args=parse_qs(query)
        try:
            kind=args.get('kind',['image'])[0]
            if kind not in ('image','mask'):raise HTTPException(422,'Invalid evidence kind')
            response=await integration_kit() if path=='/sharing/kit' else await evidence(args.get('id',[''])[0],kind)
            result={'status':200,'file':str(response.path),'filename':response.filename,'content_type':response.media_type or 'application/octet-stream'}
        except HTTPException as error:
            result={'status':error.status_code,'body':base64.b64encode(json.dumps({'detail':error.detail}).encode()).decode(),'content_type':'application/json'}
    else:
        code,body,_=await request(path,query,application=app)
        result={'status':code,'body':base64.b64encode(body).decode(),'content_type':'application/json'}
    sys.stdout.write(json.dumps(result));sys.stdout.flush()
if __name__=='__main__':
    try:asyncio.run(asyncio.wait_for(main(),12))
    except Exception as error:
        sys.stdout.write(json.dumps({'status':503,'body':base64.b64encode(json.dumps({'detail':'Local MV API bridge failed: '+type(error).__name__}).encode()).decode(),'content_type':'application/json'}))
        sys.exit(1)
