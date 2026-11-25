import pytest
from concurrent.futures import ThreadPoolExecutor
from app.jobs import JobStore,JobConflict,QueueFull
from app.job_api import create_job_app

@pytest.fixture
def store(tmp_path):return JobStore(tmp_path/'jobs.sqlite',capacity=2)

def test_durable_idempotency_and_input_conflict(store):
    first,new=store.submit({'product':'p'},'key');assert new
    other,new=store.submit({'product':'p'},'second-key');assert not new and other['id']==first['id']
    reloaded=JobStore(store.path);assert reloaded.submit({'product':'p'},'key')[0]['id']==first['id']
    with pytest.raises(JobConflict):store.submit({'product':'different'},'second-key')

def test_claim_finish_failure_and_cancel(store):
    job,_=store.submit({'product':'p'},'a');assert job['state']=='QUEUED' and job['progress'] is None
    assert store.run_once(lambda p:{'input':p})
    result=store.get(job['id']);assert result['state']=='COMPLETED' and result['result']=={'input':{'product':'p'}}
    with pytest.raises(JobConflict):store.cancel(job['id'])
    bad,_=store.submit({'product':'bad'},'b')
    def fail(p):raise ValueError('deterministic test error')
    store.run_once(fail);assert store.get(bad['id'])['state']=='FAILED'
    cancelled,_=store.submit({'product':'cancel'},'c');store.cancel(cancelled['id']);assert store.get(cancelled['id'])['state']=='CANCELLED'
    assert not store.run_once(lambda p:pytest.fail('Cancelled job must not run'))

def test_queue_capacity_and_no_running_cancel(store):
    first,_=store.submit({'p':1},'1');store.submit({'p':2},'2')
    with pytest.raises(QueueFull):store.submit({'p':3},'3')
    running=store.claim();assert running['id']==first['id']
    with pytest.raises(JobConflict):store.cancel(running['id'])
    assert store.get(running['id'])['state']=='RUNNING'

def test_concurrent_registration_and_claim_exactly_once(store):
    with ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(lambda _:store.submit({'p':1},'same'),range(2)))
    assert sum(new for _,new in out)==1
    with ThreadPoolExecutor(max_workers=2) as pool:claims=list(pool.map(lambda _:store.claim(),range(2)))
    assert sum(job is not None for job in claims)==1

def test_job_api_contract_does_not_enable_an_inference_worker(store):
    app=create_job_app(store)
    assert '/inference/jobs' in app.openapi()['paths']
    endpoint=next(r.endpoint for r in app.routes if r.path=='/capabilities')
    assert endpoint()['inference_jobs'] is False


def test_jobs_never_use_operational_db(tmp_path):
    with pytest.raises(ValueError):JobStore(tmp_path/'inspection.db')
    with pytest.raises(ValueError):JobStore(tmp_path/'hvq_max16.sqlite')


def test_only_one_development_worker_may_own_queue(store):
    from app.jobs import JobWorker
    first=JobWorker(store,lambda p:p);second=JobWorker(store,lambda p:p)
    first.start()
    try:
        with pytest.raises(RuntimeError,match='already owns'):second.start()
    finally:
        first.close();first.thread.join(timeout=2)
    assert not first.thread.is_alive()


def test_job_api_submission_status_result_and_disabled_mode(store):
    import asyncio,json
    from fastapi import HTTPException
    class Request:
        headers={'Idempotency-Key':'request-one','content-type':'application/json'}
        async def json(self):return {'item':'usb','product_id':'test-only-product','record':False}
    app=create_job_app(store,processor=lambda p:{'test_only':True})
    endpoints={r.path:r.endpoint for r in app.routes if hasattr(r,'path')}
    response=asyncio.run(endpoints['/inference/jobs'](Request()))
    assert response.status_code==202 and response.headers['retry-after']=='2'
    job=json.loads(response.body)
    assert endpoints['/inference/job-keys/{key}']('request-one')['id']==job['id']
    assert endpoints['/inference/jobs/{job_id}/result'](job['id']).status_code==409
    store.run_once(lambda p:{'test_only':True})
    assert endpoints['/inference/jobs/{job_id}/result'](job['id'])=={'test_only':True}
    disabled=create_job_app(store)
    submit=next(r.endpoint for r in disabled.routes if getattr(r,'path',None)=='/inference/jobs')
    with pytest.raises(HTTPException) as e:asyncio.run(submit(Request()))
    assert e.value.status_code==503
