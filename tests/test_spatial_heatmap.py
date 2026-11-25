import json
from pathlib import Path
import numpy as np
import pytest
from app.spatial_heatmap import build_grid,rt_grids,hvq_grids,validate_hierarchy

CONFIG={'minimum_denominator':10,'gaussian_sigma_roi_fraction':.04,'gaussian_support_sigma':3,'percentile':95}
POLYGONS=[[[0,0],[64,0],[64,64],[0,64]]]


def test_hierarchy_rejects_missing_parent_cycle_and_duplicate_ids():
    root={'category':'brush','region_id':'bristle','parent_region_id':None}
    child={'category':'brush','region_id':'tip','parent_region_id':'bristle'}
    assert len(validate_hierarchy([root,child]))==2
    for nodes in ([child],[root,root],[{**root,'parent_region_id':'tip'},child]):
        with pytest.raises(ValueError):validate_hierarchy(nodes)


def test_duplicate_boxes_do_not_multiply_occupancy_or_product_count():
    box={'bbox':[16,16,32,32],'score':.8}
    bounds,mask,values,stats=rt_grids([box,box],POLYGONS,16,CONFIG)
    assert stats['detection_count']==1 and stats['detected_products']==stats['observed_products']==1
    assert values['product_occupancy'].max()==1 and values['product_occupancy'].sum()==16
    assert values['center_count'].sum()==1 and mask.all()
    assert values['mean_confidence'][values['product_occupancy']>0].tolist()==pytest.approx([.8]*16)


def test_gaussian_is_masked_and_zero_signal_is_not_unobserved():
    triangles=[[[0,0],[64,0],[0,64]]]
    _,mask,values,stats=rt_grids([{'bbox':[8,8,16,16],'score':1.}],triangles,32,CONFIG)
    assert not values['gaussian'][~mask].any()
    assert values['gaussian'].max()>0 and stats['observed_products']==1
    _,mask,empty,stats=rt_grids([],triangles,32,CONFIG)
    assert mask.any() and empty['gaussian'].sum()==0 and stats['detected_products']==0


def test_native_map_pixel_centers_and_sparse_high_resolution_are_preserved():
    maps,counts,size=hvq_grids(np.arange(16,dtype=float).reshape(4,4),POLYGONS,[0,0,64,64],16,[64,64],95)
    assert counts.sum()==16 and (counts>0).sum()==16 and size==[4,4]
    assert maps['max'].max()==15 and maps['mean'][counts>0].sum()==120
    # Display bins without source samples are never filled by interpolation.
    assert not counts[0,0]


def test_missing_map_is_unsupported_and_cameras_never_merge(tmp_path):
    record={'item':'zipper','product_id':'p1','camera':'C3','models':{'rt':'epoch15'},
            'source':'stored_test','image_path':'test.jpg','image_sha256':'sha','original_size':[64,64],
            'detections':[],'map_path':None}
    region={'region_id':'teeth','parent_region_id':None,'polygons':POLYGONS}
    result=build_grid(record,region,16,CONFIG)
    assert result['view_id']=='C3' and result['aggregation_scope']=='individual_product_single_camera'
    assert result['hvq']['status']=='unsupported' and result['hvq']['values']=={}
    assert sum(result['rt']['valid_observation_counts'])==256 and not any(result['rt']['values']['gaussian'])
    assert result['sample_status']=='insufficient_sample'


def test_known_map_recovers_roi_and_tracks_valid_observations(tmp_path):
    path=tmp_path/'map.npy';np.save(path,np.ones((1,8,8)))
    record={'item':'toothbrush','product_id':'p','camera':'C1','models':{},'source':'fixture',
            'image_path':'x','image_sha256':'x','original_size':[64,64],'detections':[],'map_path':str(path)}
    region={'region_id':'bristle','parent_region_id':None,'polygons':POLYGONS}
    result=build_grid(record,region,16,CONFIG)
    assert result['hvq']['status']=='supported'
    assert sum(result['hvq']['valid_observation_counts'])==64
    assert result['hvq']['values']['mean'].count(None)==192
