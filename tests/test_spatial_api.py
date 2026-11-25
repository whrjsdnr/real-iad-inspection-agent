import gzip
import json
import pytest
from fastapi import HTTPException
from app import spatial_api


def test_cached_api_keeps_models_separate_and_never_synthesizes_missing_map(tmp_path,monkeypatch):
    entry={'grid_id':'registered','item':'zipper'}
    data={'entries':[entry],'views':{},'config_hashes':{},'version':'v1'}
    monkeypatch.setattr(spatial_api,'index',lambda:data)
    monkeypatch.setattr(spatial_api,'CACHE',tmp_path)
    record={'item':'zipper','source_image':'private/file.jpg','source_image_id':'image1',
            'rt':{'status':'supported','values':{'center_count':[0.,1.]},'valid_observation_counts':[1,1]},
            'hvq':{'status':'unsupported','reason':'saved_anomaly_map_missing','values':{},'valid_observation_counts':[0,0]}}
    with gzip.open(tmp_path/'registered.json.gz','wt') as stream:json.dump(record,stream)
    result=spatial_api.grid('registered','rt','center_count')
    assert result['values']==[0.,1.] and 'source_image' not in result
    missing=spatial_api.grid('registered','hvq','mean')
    assert missing['status']=='unsupported' and missing['values']==[]
    with pytest.raises(HTTPException) as error:spatial_api.grid('../private','rt','center_count')
    assert error.value.status_code==404
    with pytest.raises(HTTPException):spatial_api.grid('registered','rt','invalid_method')


def test_precomputed_cache_rejects_changed_roi_config(tmp_path,monkeypatch):
    file=tmp_path/'roi.json';file.write_text('{}')
    monkeypatch.setattr(spatial_api,'ROOT',tmp_path)
    monkeypatch.setattr(spatial_api,'index',lambda:{'entries':[{'grid_id':'grid'}],'config_hashes':{'roi.json':'old-hash'}})
    with pytest.raises(HTTPException) as error:spatial_api.grid('grid')
    assert error.value.status_code==409


def test_spatial_tool_reports_real_cells_and_no_population_claim(monkeypatch):
    from app import spatial_tools
    monkeypatch.setattr(spatial_tools,'index',lambda:{'entries':[{'grid_id':'id','item':'zipper','product_id':'p','camera':'C1','resolution':64,'region_id':'teeth'}]})
    result={'item':'zipper','product_id':'p','view_id':'C1','region_id':'teeth','parent_region_id':None,
            'status':'supported','reason':None,'stats':{'observed_products':1},'mapping_status':'image_roi_only','sample_status':'insufficient_sample',
            'values':[0.,2.,None,1.],'valid_observation_counts':[1,1,0,1],'roi_bounds':[0,0,100,100],'grid_width':2,'grid_height':2}
    monkeypatch.setattr(spatial_tools,'grid',lambda *args:result)
    response=spatial_tools.query_spatial_evidence(item='zipper',limit=1)
    assert response['hotspots']==[{'value':2.,'column':1,'row':0,'native_pixel_center':[75.,25.],'valid_observations':1}]
    assert response['sample_status']=='insufficient_sample' and response['evidence_link']=='spatial://id/rt/gaussian'
