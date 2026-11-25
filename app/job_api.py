"""Additive API factory for an isolated development port, never auto-deployed.

Processor is injected. Production inference remains disabled unless explicitly
provided by the administrator. Existing /inference/run contract is unchanged.
"""
from pathlib import Path
import hashlib,json
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict
from .jobs import JobStore,JobConflict,QueueFull,JobWorker

class ExistingInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    item:str
    product_id:str
    mode:str='existing'
    record:bool=False


def create_job_app(store:JobStore,processor=None,*,background=False):
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def lifespan(app):
        worker=JobWorker(store,processor) if processor and background else None
        if worker:worker.start()
        yield
        if worker:worker.close()
    app=FastAPI(title='Isolated GUI Jobs (development)',lifespan=lifespan)
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:15173','http://localhost:15173','http://127.0.0.1:5173','http://localhost:5173'],allow_methods=['GET','POST'],allow_headers=['Content-Type','Idempotency-Key'],expose_headers=['Location','Retry-After'])
    @app.get('/capabilities')
    def capabilities():return {'inference_jobs':processor is not None,'api_version':'gui-jobs-v1','isolated':True}
    @app.post('/inference/jobs')
    async def submit(request:Request):
        key=request.headers.get('Idempotency-Key','')
        if not key or len(key)>128:raise HTTPException(400,'Idempotency-Key is required')
        if processor is None:raise HTTPException(503,'Job worker is not enabled; no inference was registered')
        try:
            if request.headers.get('content-type','').startswith('multipart/form-data'):
                form=await request.form();item=str(form.get('item',''));mode=str(form.get('mode','upload'))
                if mode!='upload' or not item:raise ValueError('Upload requires item and mode=upload')
                payload={'item':item,'mode':'upload','record':False,'views':{}};identity={'item':item,'mode':'upload','files':{}}
                data={}
                for cam in ('C1','C2','C3','C4','C5'):
                    file=form.get(cam)
                    if not hasattr(file,'read'):raise ValueError('All C1-C5 files are required')
                    content=await file.read(10*1024*1024+1)
                    if not content or len(content)>10*1024*1024:raise ValueError('Each image must be 1 byte..10 MiB')
                    if not (content.startswith(b'\xff\xd8') or content.startswith(b'\x89PNG\r\n\x1a\n')):raise ValueError('JPEG/PNG signature required')
                    identity['files'][cam]=hashlib.sha256(content).hexdigest();data[cam]=content
                digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
                folder=store.path.parent/'gui-job-uploads'/digest;folder.mkdir(parents=True,exist_ok=True)
                for cam,content in data.items():
                    dest=folder/f'{cam}.image'
                    if not dest.exists():
                        import os,tempfile
                        fd,name=tempfile.mkstemp(dir=folder)
                        with os.fdopen(fd,'wb') as f:f.write(content)
                        os.replace(name,dest)
                    payload['views'][cam]=str(dest)
            else:
                validated=ExistingInput(**await request.json())
                if validated.mode!='existing' or validated.record:raise ValueError('Only non-recording existing-mode jobs are supported')
                payload=validated.model_dump();identity=payload
            job,created=store.submit(payload,key,identity=identity)
            return JSONResponse(job,status_code=202 if created else 200,headers={'Location':f'/inference/jobs/{job["id"]}','Retry-After':'2'})
        except JobConflict as e:raise HTTPException(409,str(e)) from e
        except QueueFull as e:raise HTTPException(429,str(e),headers={'Retry-After':'5'}) from e
        except (ValueError,TypeError) as e:raise HTTPException(400,str(e)) from e
    @app.get('/inference/job-keys/{key}')
    def by_key(key:str):
        with store.connection() as c:
            row=c.execute('SELECT job_id FROM gui_job_keys WHERE key=?',(key,)).fetchone()
        if row is None:raise HTTPException(404,'No job registered for this idempotency key')
        return store.get(row['job_id'])
    @app.get('/inference/jobs/{job_id}')
    def status(job_id:str):
        try:return store.get(job_id)
        except KeyError as e:raise HTTPException(404,'Unknown job') from e
    @app.get('/inference/jobs/{job_id}/result')
    def result(job_id:str):
        job=status(job_id)
        if job['state']!='COMPLETED':return JSONResponse({'state':job['state'],'error':job['error']},status_code=409)
        return job['result']
    @app.post('/inference/jobs/{job_id}/cancel')
    def cancel(job_id:str):
        try:return store.cancel(job_id)
        except KeyError as e:raise HTTPException(404,'Unknown job') from e
        except JobConflict as e:raise HTTPException(409,str(e)) from e
    return app


def disabled_app():
    import os
    return create_job_app(JobStore(Path(os.environ.get('GUI_JOB_DB','/tmp/inspection-gui-development/jobs.sqlite'))))
