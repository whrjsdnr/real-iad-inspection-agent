"""Read-only development gateway. No migrations, workers, inference or review writes.

Use a separate port and DATABASE_URL_READ. This module does not replace or restart
an operational API. All transactions are explicitly read-only, including SQLite.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,HTTPException
from sqlalchemy import event,text
from . import api as original
from .db import get_engine

READ_TOOLS=frozenset({'query_error_stats','compute_inspection_metrics','get_case_evidence','get_training_status','get_final_performance','query_spatial_evidence'})

@asynccontextmanager
async def lifespan(app):
    if not os.getenv('DATABASE_URL_READ'):
        raise RuntimeError('DATABASE_URL_READ is required; no fallback to an administrator connection')
    engine=get_engine('read')
    if engine.dialect.name=='postgresql':
        @event.listens_for(engine,'begin')
        def readonly_transaction(connection):connection.exec_driver_sql('SET TRANSACTION READ ONLY')
    elif engine.dialect.name=='sqlite':
        @event.listens_for(engine,'connect')
        def readonly_sqlite(connection,record):connection.execute('PRAGMA query_only=ON')
    else:raise RuntimeError('Unsupported read-only database backend')
    with engine.connect() as connection:connection.execute(text('SELECT 1'))
    yield

app=FastAPI(title='Inspection read-only development gateway',lifespan=lifespan)
GET_PATHS=frozenset({'/health','/metrics/snapshots','/evidence/{view_id}/image','/evidence/{view_id}/map','/status/overview','/performance/final','/fusion/runs','/items','/inference/sample_products','/parts/heatmap','/parts/evidence/{case_id}/{camera}'})
for route in original.app.routes:
    if getattr(route,'path',None)=='/performance/final':continue
    if getattr(route,'path',None) in GET_PATHS or (getattr(route,'path','').startswith('/parts/spatial/') and getattr(route,'methods',set())=={'GET'}) or (getattr(route,'path',None)=='/fusion/runs' and getattr(route,'methods',set())=={'GET'}):
        app.router.routes.append(route)
# FastAPI 0.165+는 include_router를 지연 확장(_IncludedRouter)으로 처리해
# 위 경로 복사에 잡히지 않으므로, 읽기 전용 부위 라우터는 이 게이트웨이에 직접 등록한다.
from .part_api import router as part_heatmap_router
app.include_router(part_heatmap_router)
from .shared_data_api import router as shared_data_router
app.include_router(shared_data_router)

@app.get('/tools')
async def tools():
    return {'tools':sorted(READ_TOOLS&original.TOOL_FUNCS.keys()),'schemas':[s for s in original.TOOL_SCHEMAS if s['function']['name'] in READ_TOOLS],'read_only':True}

@app.get('/performance/final')
async def performance_final():return original.performance_final()

@app.post('/tools/{tool_name}')
async def call_tool(tool_name:str,request:Request):
    if tool_name not in READ_TOOLS:raise HTTPException(403,'This development gateway permits read-only tools only')
    return await original.call_tool(tool_name,request)
