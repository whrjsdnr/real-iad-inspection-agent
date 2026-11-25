import asyncio
import gzip
import json
from app import spatial_api
from app.spatial_heatmap import build_grid
from scripts.validate_spatial_api import request


def test_32_grid_asgi_preserves_local_boxes_counts_and_masks(tmp_path,monkeypatch):
    config={'minimum_denominator':10,'gaussian_sigma_roi_fraction':.04,'gaussian_support_sigma':3,'percentile':95}
    box={'bbox':[8,8,16,16],'score':.8}
    # Explicitly synthetic unit-test input, never added to the real cache or UI.
    record={'item':'toothbrush','product_id':'test-only','camera':'C1','models':{},'source':'unit_test',
            'image_path':'test-only.jpg','image_sha256':'test','original_size':[64,64],
            'detections':[box,box,{'bbox':[70,70,80,80],'score':.9}],'map_path':None}
    region={'region_id':'bristle','parent_region_id':None,'polygons':[[[0,0],[64,0],[0,64]]]}
    saved=build_grid(record,region,32,config)
    saved.update(source_image_id='image',mapping_version='test-roi')
    data={'entries':[{'grid_id':'grid','item':'toothbrush','product_id':'test-only','camera':'C1',
                     'region_id':'bristle','resolution':32}],
          'views':{'image':record},'config_hashes':{}}
    monkeypatch.setattr(spatial_api,'index',lambda:data);monkeypatch.setattr(spatial_api,'CACHE',tmp_path)
    with gzip.open(tmp_path/'grid.json.gz','wt') as stream:json.dump(saved,stream)
    async def verify():
        code,body,_=await request('/parts/spatial-heatmap','item=toothbrush&view=C1&region_id=bristle&resolution=32')
        result=json.loads(body)
        assert code==200 and len(result['values'])==1024
        assert len(result['values_2d'])==32 and all(len(row)==32 for row in result['values_2d'])
        assert result['stats']['detection_count']==1
        assert sum(v or 0 for v in result['center_counts'])==1
        assert max(v for v in result['box_occupancy_counts'] if v is not None)==1
        assert result['source_detections']==[box]
        assert any(result['unobserved_mask']) and result['rate_supported'] is False
        assert result['values'][5*32+5]>.7 and result['values'][0]==0
        assert result['values'][-1] is None and result['observation_counts'][-1]==0
        code,_,_=await request('/parts/spatial-heatmap','view=C6')
        assert code==422
        code,_,_=await request('/parts/spatial-heatmap','view=C2')
        assert code==404
        code,_,_=await request('/parts/spatial-heatmap','resolution=31')
        assert code==422
        code,legacy,_=await request('/parts/spatial/grid/grid','model=rt&method=confidence_area')
        assert code==200 and json.loads(legacy)['values']==result['values']
    asyncio.run(verify())
