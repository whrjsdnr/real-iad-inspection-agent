"""Local cached-evidence preview. No DB startup, inference, reviews or production hooks."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .spatial_api import router

ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title='Saved spatial evidence preview',docs_url=None,redoc_url=None)
api=FastAPI()
api.include_router(router)
from .ground_truth_api import router as ground_truth_router
api.include_router(ground_truth_router)
from .surface_api import router as surface_router
api.include_router(surface_router)
from .shared_data_api import router as shared_data_router,database
api.include_router(shared_data_router)

@api.get('/items')
async def items():
    with database() as connection:
        return {'items':[row[0] for row in connection.execute('SELECT DISTINCT category FROM products ORDER BY category')]}

@api.get('/health')
async def health():return {'status':'ok','read_only':True,'source':'saved_spatial_cache','llm':{'mode':'unavailable'}}

app.mount('/api',api)
app.mount('/',StaticFiles(directory=str(ROOT/'inspection-gui/dist'),html=True,check_dir=False))
