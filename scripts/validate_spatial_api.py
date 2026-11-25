"""Exercise real cached data through ASGI HTTP without sockets or app startup hooks."""
import asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from app.spatial_api import index,router,grid
from app.spatial_heatmap import ROOT
app=FastAPI()
app.include_router(router)


async def request(path,query='',application=app,headers=None,method='GET'):
    messages=[];received=False;complete=asyncio.Event()
    async def receive():
        nonlocal received
        if not received:
            received=True
            return {'type':'http.request','body':b'','more_body':False}
        await complete.wait()
        return {'type':'http.disconnect'}
    async def send(message):
        messages.append(message)
        if message['type']=='http.response.body' and not message.get('more_body',False):complete.set()
    scope={'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1','method':method,'scheme':'http',
           'path':path,'raw_path':path.encode(),'query_string':query.encode(),'headers':headers or [],
           'server':('test',80),'client':('127.0.0.1',1),'root_path':''}
    start=time.perf_counter();await application(scope,receive,send)
    status=next(message['status'] for message in messages if message['type']=='http.response.start')
    body=b''.join(message.get('body',b'') for message in messages if message['type']=='http.response.body')
    return status,body,(time.perf_counter()-start)*1000


async def main():
    data=index();checks=[]
    for item,region in [('toothbrush','bristle'),('zipper','teeth')]:
        for resolution in (16,32,64,128):
            entry=next(entry for entry in data['entries'] if entry['item']==item and entry['region_id']==region and entry['camera']=='C1' and '/NG/' in entry['product_id'] and entry['resolution']==resolution)
            for model,method in [('rt','gaussian'),('hvq','mean')]:
                print(item,resolution,model,'ASGI request',flush=True)
                code,body,elapsed=await request('/parts/spatial/grid/'+entry['grid_id'],f'model={model}&method={method}')
                assert code==200,(code,body[:100])
                payload=json.loads(body)
                assert payload['product_id']==entry['product_id'] and payload['view_id']=='C1'
                if payload['status']=='supported':assert len(payload['values'])==resolution*resolution
                else:assert payload['values']==[]
                checks.append({'item':item,'resolution':resolution,'model':model,'status':payload['status'],'asgi_handler_ms':elapsed,'response_bytes':len(body)})
    output=ROOT/'reports/gui_validation/spatial/asgi-real-data-validation.json'
    output.write_text(json.dumps({'status':'VERIFIED_ASGI_NO_NETWORK','note':'No lifespan, migrations, model jobs or production writes. Timing excludes network/browser.','checks':checks},indent=2))
    print('Verified',len(checks),'real cached ASGI responses')


def direct():
    data=index();checks=[]
    for item,region in [('toothbrush','bristle'),('zipper','teeth')]:
        for resolution in (16,32,64,128):
            entry=next(entry for entry in data['entries'] if entry['item']==item and entry['region_id']==region and entry['camera']=='C1' and '/NG/' in entry['product_id'] and entry['resolution']==resolution)
            for model,method in [('rt','gaussian'),('hvq','mean')]:
                started=time.perf_counter();response=grid(entry['grid_id'],model,method)
                encoded=json.dumps(response,allow_nan=False).encode()
                assert response['view_id']=='C1' and response['product_id']==entry['product_id']
                if response['status']=='supported':assert len(response['values'])==resolution**2
                else:assert response['values']==[]
                checks.append({'item':item,'resolution':resolution,'model':model,'status':response['status'],'handler_ms':(time.perf_counter()-started)*1000,'response_bytes':len(encoded)})
    (ROOT/'reports/gui_validation/spatial/handler-real-data-validation.json').write_text(json.dumps({'status':'VERIFIED_DIRECT_HANDLER_ONLY','note':'Not a network/ASGI/browser timing. ASGI worker timeout is recorded separately.','checks':checks},indent=2))
    print('Verified',len(checks),'real cached handler responses; HTTP/ASGI validation is separate')

if __name__=='__main__':
    if '--direct' in sys.argv:direct()
    else:asyncio.run(asyncio.wait_for(main(),timeout=60))
