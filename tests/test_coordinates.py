import numpy as np
import pytest
from app.coordinates import Size,Transform,normalized,map_registered_bbox,UnverifiedTransform


def test_resize_is_explicit_and_invertible():
    t=Transform.resize('original','rt',Size(1024,1024),Size(640,640),provenance='inference.py direct Resize')
    np.testing.assert_allclose(t.inverse().bbox(t.bbox([100,200,300,600])),[100,200,300,600])
    assert t.points([[1024,1024]]) == [[640,640]]
    with pytest.raises(UnverifiedTransform):Transform.resize('o','m',Size(10,10),Size(20,20),provenance='')


def test_letterbox_padding_crop_and_polygon():
    t=Transform.crop_resize_pad('o','m',Size(1000,800),Size(640,640),crop=[100,100,900,700],scale=[.8,.8],padding=[0,80,0,80],provenance='test explicit pipeline')
    np.testing.assert_allclose(t.polygon([[100,100],[900,700]]),[[0,80],[640,560]])
    np.testing.assert_allclose(t.inverse().points([[0,80],[640,560]]),[[100,100],[900,700]])
    assert not t.valid([[-1,2]])
    with pytest.raises(ValueError):t.bbox([4,2,1,5])


def test_normalized_chain():
    t=normalized('o','n',Size(100,50),provenance='explicit normalization')
    assert t.bbox([0,0,50,50]) == [0,0,.5,1]
    assert t.then(t.inverse()).bbox([0,0,50,50]) == [0,0,50,50]


def test_warp_map_and_remove_padding():
    t=Transform.crop_resize_pad('o','p',Size(2,2),Size(4,4),crop=[0,0,2,2],scale=[1,1],padding=[1,1,1,1],provenance='test padding')
    source=np.array([[1,2],[3,4]],np.float32)
    padded=t.warp_map(source,mask=True)
    np.testing.assert_array_equal(padded[1:3,1:3],source)
    np.testing.assert_array_equal(t.inverse().warp_map(padded,mask=True),source)


def test_lut_without_registration_stays_unknown_even_same_dimensions():
    result=map_registered_bbox('toothbrush','C1',[200,30,440,170],registration=None,mapping_version='roi-lut-v1')
    assert result['part_id']=='unknown' and result['status']=='unverified'
    registered=Transform.resize('original','lut',Size(640,480),Size(640,480),provenance='synthetic test identity, not production proof')
    assert map_registered_bbox('toothbrush','C1',[200,30,440,170],registration=registered,mapping_version='roi-lut-v1')['part_id']=='bristle'
    assert map_registered_bbox('toothbrush','C1',[0,0,10,10],registration=registered,mapping_version='roi-lut-v1')['part_id']=='unknown'


def test_registration_must_match_lut_reference_and_image_bounds():
    wrong=Transform.resize('o','lut',Size(640,480),Size(1024,1024),provenance='synthetic mismatch')
    assert map_registered_bbox('toothbrush','C1',[200,30,440,170],registration=wrong,mapping_version='roi-lut-v1')['reason']=='lut_dimensions_mismatch'
    identity=Transform.resize('o','lut',Size(640,480),Size(640,480),provenance='synthetic identity')
    assert map_registered_bbox('toothbrush','C1',[-1,0,30,30],registration=identity,mapping_version='roi-lut-v1')['reason']=='outside_original_bounds'
    # Native bristle top-left boundary; area-positive box centered exactly there.
    result=map_registered_bbox('toothbrush','C1',[199,29,201,31],registration=identity,mapping_version='roi-lut-v1')
    assert result['part_id']=='bristle'
