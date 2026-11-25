import asyncio,json
from fastapi import FastAPI
from app.surface_api import router,crop_truth
from scripts.validate_spatial_api import request

def test_truth_crop_preserves_native_cell_values_and_unknowns():
    # Synthetic unit input only; never included in operational/cache data.
    data={'grid_width':4,'grid_height':4,'source_image_width':40,'source_image_height':40,
          'defect_rate':[None,.1,.2,.3]*4,'known_count':[0,10,10,10]*4,'known_products':10,'unknown_products':2}
    region={'polygons':[[[10,10],[30,10],[30,30],[10,30]]]}
    result=crop_truth(data,region)
    assert result['grid_width']==result['grid_height']==2
    assert result['values']==[.1,.2,.1,.2] and result['valid_observation_counts']==[10]*4
    assert result['source_bounds']==[10.,10.,30.,30.]

def test_actual_surface_endpoints_use_saved_data_and_explicit_display_scope():
    app=FastAPI();app.include_router(router)
    async def run():
        code,body,_=await request('/heatmaps/surface','item=toothbrush&view=C1&source=ground_truth',application=app)
        data=json.loads(body)
        assert code==200 and data['scope']=='visualization_only_approximate'
        assert data['user_authorized_approximate_projection'] and not data['physical_alignment_verified']
        head=next(region for region in data['regions'] if region['region_id']=='bristle')
        assert len(set(head['values']))>1 and head['sample_products']==335
        assert len(head['values'])==head['grid_width']*head['grid_height']
        code,body,_=await request('/heatmaps/surface','item=zipper&view=C3&source=ground_truth',application=app)
        assert code==200 and json.loads(body)['regions']
        code,body,_=await request('/heatmaps/surface-layout','item=zipper',application=app)
        assert code==200 and next(source for source in json.loads(body)['sources'] if source['id']=='hvq')['available']
        code,_,_=await request('/heatmaps/surface','item=toothbrush&view=C9',application=app)
        assert code==422
    asyncio.run(run())


def test_saved_rt_and_hvq_use_same_product_and_nonuniform_real_map():
    app=FastAPI();app.include_router(router)
    async def run():
        payloads=[]
        for source in ('rt','hvq'):
            code,body,_=await request('/heatmaps/surface',f'item=zipper&view=C1&source={source}',application=app)
            data=json.loads(body)
            assert code==200 and data['status']=='supported'
            assert data['regions'] and all(region['sample_products']==1 for region in data['regions'])
            payloads.append(data)
        assert payloads[0]['product_id']==payloads[1]['product_id']
        assert payloads[0]['split']==payloads[1]['split']
        values=[v for r in payloads[1]['regions'] for v in r['values'] if v is not None]
        assert len(set(values))>1
        assert all(r['data_source']=='saved_batch5_map_cache' for r in payloads[1]['regions'])
    asyncio.run(run())
