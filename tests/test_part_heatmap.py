import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi import HTTPException
from app.part_heatmap import derive, region_for_box, summarize_artifact, polygon_mask
from app.coordinates import Size


def setup_evidence(tmp_path):
    profiles, views = [], {}
    for camera in ('C1', 'C2', 'C3', 'C4', 'C5'):
        image = tmp_path/f'{camera}.jpg'
        cv2.imwrite(str(image), np.full((64, 64, 3), 80, np.uint8))
        map_path = tmp_path/f'{camera}.npy'
        np.save(map_path, np.full((1, 8, 8), 2., np.float32))
        profiles.append({'item': 'toothbrush', 'camera': camera,
                         'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                         'image_size': [64, 64], 'coordinate_space': 'original_pixels',
                         'review': 'assistant_visual_checked_exact_sample', 'coverage': {'neck': 'not_annotated'},
                         'regions': [{'region_id': 'bristle', 'polygon': [[0, 0], [32, 0], [32, 32], [0, 32]]}]})
        views[camera] = {'width': 64, 'height': 64, 'image_path': str(image), 'map_npy': str(map_path),
                         'detections': [{'bbox': [5, 5, 15, 15], 'score': .8 if camera != 'C2' else .2},
                                        {'bbox': [50, 50, 60, 60], 'score': .9}]}
    root = tmp_path/'evidence'
    for alias in ('a', 'b'):
        directory = root/alias
        directory.mkdir(parents=True)
        (directory/'result.json').write_text(json.dumps({'item': 'toothbrush', 'product_id': 'p0', 'models': {'rtdetr': 'rt15'},
                                                        'product': {'rtdetr_conf_threshold': .55}, 'views': views}))
    config = tmp_path/'config.json'
    config.write_text(json.dumps({'scope': 'exact_image_sha256', 'version': 'test-v1',
                                  'transform_provenance': 'explicit direct resize fixture', 'profiles': profiles}))
    return root, config


def test_real_region_assignment_boundary_outside_and_ambiguity():
    regions = [{'region_id': 'head', 'polygon': [[0, 0], [32, 0], [32, 32], [0, 32]]}]
    assert region_for_box([28, 5, 36, 15], regions, 64, 64) == 'head'
    assert region_for_box([50, 50, 60, 60], regions, 64, 64) is None
    assert region_for_box([5, 5, 15, 15], regions+regions, 64, 64) is None
    assert region_for_box([-1, 0, 2, 4], regions, 64, 64) is None


def test_map_roi_uses_pixel_centers_not_inclusive_vertex_rounding():
    mask = polygon_mask([[0, 0], [4, 0], [4, 4], [0, 4]], Size(8, 8))
    assert mask.sum() == 16
    assert mask[:4, :4].all() and not mask[4:, :].any()


def test_five_views_and_uploaded_copies_do_not_multiply_product_count(tmp_path):
    root, config = setup_evidence(tmp_path)
    artifact = derive(root, config)
    assert len(artifact['cases']) == 1
    summary = summarize_artifact(artifact, 'toothbrush')
    row = summary['rows'][0]
    assert (row['num'], row['den'], row['detection_count']) == (1, 1, 4)
    assert row['hvq_roi_mean'] == 2.
    assert summary['mapping_verified'] and summary['mapping_scope'] == 'exact_image_sha256'
    assert 'image_path' not in summary['cases'][0]['views'][0]
    zero = summarize_artifact(artifact, 'toothbrush', camera='C2')['rows'][0]
    assert zero['num'] == 0 and zero['den'] == 1
    assert summarize_artifact(artifact, 'usb')['rows'] == []
    assert summarize_artifact(artifact, 'toothbrush', model_version='wrong-model')['rows'] == []
    assert summarize_artifact(artifact, 'toothbrush', date_to='2000-01-01')['rows'] == []


def test_replaced_original_is_not_silently_reused(tmp_path):
    root, config = setup_evidence(tmp_path)
    artifact = derive(root, config)
    Path(artifact['cases'][0]['views'][0]['image_path']).write_bytes(b'not the original')
    summary = summarize_artifact(artifact, 'toothbrush', camera='C1')
    assert summary['rows'] == [] and not summary['mapping_verified']


def test_invalid_registration_is_rejected(tmp_path):
    root, config = setup_evidence(tmp_path)
    data = json.loads(config.read_text())
    data['profiles'][0]['regions'][0]['polygon'][0][0] = -1
    config.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='polygon'):
        derive(root, config)


def test_evidence_route_restricts_case_and_camera(tmp_path, monkeypatch):
    from app import part_api
    from fastapi.responses import FileResponse
    root, config = setup_evidence(tmp_path)
    artifact = derive(root, config)
    monkeypatch.setattr(part_api, 'load_artifact', lambda: artifact)
    case_id = artifact['cases'][0]['case_id']
    assert isinstance(part_api.image(case_id, 'C1'), FileResponse)
    with pytest.raises(HTTPException) as error:
        part_api.image('../etc', 'passwd')
    assert error.value.status_code == 404
