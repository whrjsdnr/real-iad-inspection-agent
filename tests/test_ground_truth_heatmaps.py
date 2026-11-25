import asyncio,json
import pytest
from fastapi import FastAPI,HTTPException
from app import ground_truth_api as api
from scripts.validate_spatial_api import request


def test_source_train_only_array_contract_and_unknown_masks(monkeypatch):
    record={'item':'toothbrush','view':'C1','split':'train','product_id':None,'image_path':'private','mask_path':None,
            'defect_rate':[.5,None],'positive_count':[1,0],'known_count':[2,0],'unknown_count':[1,3],
            'coverage_mask':[1,0],'known_products':2}
    monkeypatch.setattr(api,'record',lambda *args:({'id':'id'},record.copy()))
    app=FastAPI();app.include_router(api.router)
    async def run():
        code,body,_=await request('/heatmaps/ground-truth','item=toothbrush',application=app)
        data=json.loads(body)
        assert code==200 and data['values']==[.5,None] and data['observation_counts']==[2,0]
        assert 'image_path' not in data and data['image_url'] is None
    asyncio.run(run())


def test_no_test_or_validation_distribution_is_invented():
    for split in ['test','validation']:
        with pytest.raises(HTTPException) as error:api.record('toothbrush','C1',split,None)
        assert error.value.status_code==404


def test_roi_masks_cells_without_interpolating_or_filling_unknowns():
    data={'item':'toothbrush','view':'C1','source_image_width':1024,'source_image_height':1024,
          'positive_count':[1]*4096,'known_count':[2]*4096,'unknown_count':[3]*4096,
          'defect_rate':[.5]*4096,'occupancy_positive':[.5]*4096,'mask_coverage':[.2]*4096,'coverage_mask':[1]*4096}
    result=api.restrict_roi(data,'bristle')
    assert result['coverage_mask'][0]==0 and result['defect_rate'][0] is None and result['known_count'][0]==0
    assert any(value==.5 for value in result['defect_rate'])
    with pytest.raises(HTTPException):api.restrict_roi(data,'unregistered')
