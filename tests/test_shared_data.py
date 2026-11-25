import asyncio
import json
import sqlite3
import pytest
from fastapi import FastAPI
from app import shared_data_api as api
from scripts.validate_spatial_api import request


@pytest.fixture()
def saved_source(tmp_path,monkeypatch):
    path=tmp_path/'isolated-test.sqlite'
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE products(product_id TEXT,category TEXT,split TEXT,truth TEXT,status TEXT,hvq_max REAL,rtdetr_max REAL,completed_at TEXT)')
        c.execute('CREATE TABLE views(product_id TEXT,camera TEXT,image_path TEXT,hvq REAL,rtdetr REAL,width INT,height INT,boxes_json TEXT,map_path TEXT)')
        for product in ('toothbrush/test-only-a','toothbrush/test-only-b'):
            c.execute('INSERT INTO products VALUES(?,?,?,?,?,?,?,?)',(product,'toothbrush','test','normal','COMPLETED',1.,.8,'2026-11-25'))
            c.execute('INSERT INTO views VALUES(?,?,?,?,?,?,?,?,?)',(product,'C1','missing-test-image.jpg',1.,.8,64,64,json.dumps([{'bbox':[1,2,8,10],'confidence':.8,'class_id':4}]),''))
    config=tmp_path/'test-source.json';config.write_text(json.dumps({'source_score_cache':str(path),'dataset_root':str(tmp_path)}))
    monkeypatch.setattr(api,'CONFIG',config)
    app=FastAPI();app.include_router(api.router)
    return app


def test_readonly_connection_cannot_modify_cached_source(saved_source):
    with api.database() as c:
        assert c.execute('SELECT count(*) FROM products').fetchone()[0]==2
        with pytest.raises(sqlite3.OperationalError):c.execute('DELETE FROM products')


def test_products_findings_pagination_and_sql_parameters(saved_source):
    async def run():
        code,body,_=await request('/products','limit=1',application=saved_source);first=json.loads(body)
        assert code==200 and first['total']==2 and len(first['products'])==1
        _,body,_=await request('/products','limit=1&offset=1',application=saved_source)
        assert json.loads(body)['products'][0]['product_id']!=first['products'][0]['product_id']
        code,body,_=await request('/products/findings','product_id=toothbrush%2Ftest-only-a&view=C1&min_confidence=.4',application=saved_source)
        row=json.loads(body)['findings'][0]
        assert code==200 and row['confidence']==.8 and row['bbox']==[1,2,8,10]
        assert row['region_id'] is None  # mismatched ROI dimensions stay unmapped
        code,body,_=await request('/products/findings','product_id=toothbrush%2Ftest-only-a&view=C1&min_confidence=.9',application=saved_source)
        assert code==200 and json.loads(body)['total']==0
        code,_,_=await request('/products','limit=101',application=saved_source);assert code==422
        code,_,_=await request('/products/views',"product_id=%27%20OR%201%3D1",application=saved_source);assert code==404
    asyncio.run(run())


def test_missing_maps_and_coordinate_provenance_are_explicit(saved_source):
    async def run():
        query='product_id=toothbrush%2Ftest-only-a&view=C1'
        code,body,_=await request('/products/anomaly-map',query,application=saved_source)
        assert code==200 and json.loads(body)['status']=='unsupported'
        _,body,_=await request('/products/views',query,application=saved_source)
        row=json.loads(body)['views'][0]
        assert row['coordinate_transform']['per_record_transform_metadata'] is None
        assert row['coordinate_transform']['physical_uv_mapping']=='unverified'
    asyncio.run(run())


def test_catalog_preserves_mesh_ids_and_hierarchy_without_claiming_uv_registration():
    catalog=api.parts_catalog('toothbrush')
    ids={row['region_id'] for row in catalog['parts']}
    assert {'neck','bristle','bristle_tip'}<=ids and 'handle' not in ids
    assert catalog['physical_surface_uv_verified'] is False


def test_relative_saved_map_uses_score_cache_directory_and_validates_image(saved_source,tmp_path):
    import numpy as np
    image=tmp_path/'source.jpg';image.write_bytes(b'isolated source fixture')
    folder=tmp_path/'maps';folder.mkdir();np.save(folder/'saved.npy',np.ones((1,2,2),dtype=np.float32))
    stat=image.stat()
    row={'product_id':'test-only/source','camera':'C1','image_path':str(image),
         'map_path':'maps/saved.npy','source_fingerprint':f'stat:{stat.st_size}:{stat.st_mtime_ns}'}
    data=api.stored_map(row)
    assert data['path']==str(folder/'saved.npy') and data['source']=='saved_batch5_map_cache'
    assert data['image_sha256']==api.fingerprint(image)
    assert api.stored_map(row|{'source_fingerprint':'stat:0:0'}) is None
    assert api.stored_map(row|{'map_path':'../outside.npy'}) is None


def test_map_product_filter_does_not_claim_all_products_have_maps(saved_source):
    async def run():
        code,body,_=await request('/products','maps_only=true',application=saved_source)
        assert code==200 and json.loads(body)['total']==0
    asyncio.run(run())
