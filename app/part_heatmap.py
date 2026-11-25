"""Native-image ROI aggregation of stored model evidence. Never writes inspection DB."""
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np
from .coordinates import Size, Transform

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'config/part_heatmap_regions.json'


def fingerprint(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _region_polygons(region):
    """region 항목의 폴리곤 목록 — 'polygon'(단일) 또는 'polygons'(다중)."""
    if 'polygons' in region:
        return region['polygons']
    return [region['polygon']]


def region_for_box(box, regions, width, height):
    if len(box) != 4 or not all(math.isfinite(value) for value in box):
        return None
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        return None
    point = ((x1+x2)/2, (y1+y2)/2)
    matches = [region['region_id'] for region in regions
               if any(cv2.pointPolygonTest(np.asarray(poly, np.float32), point, False) >= 0
                      for poly in _region_polygons(region))]
    return matches[0] if len(matches) == 1 else None


def polygon_mask(polygon, size):
    """Sample map pixel centers against continuous polygon edge coordinates."""
    x, y = np.meshgrid(np.arange(size.width)+.5, np.arange(size.height)+.5)
    inside = np.zeros((size.height, size.width), bool)
    previous = polygon[-1]
    for current in polygon:
        x0, y0 = previous
        x1, y1 = current
        if y1 != y0:
            inside ^= ((y0 > y) != (y1 > y)) & (x < (x1-x0)*(y-y0)/(y1-y0)+x0)
        previous = current
    return inside


def _validate_regions(regions, width, height):
    if width <= 0 or height <= 0 or len({r['region_id'] for r in regions}) != len(regions):
        raise ValueError('Invalid image size or duplicate region ID')
    for region in regions:
        if not region['region_id'] or region['region_id'] in ('unknown', 'unmapped'):
            raise ValueError('Unmapped labels cannot be registered regions')
        if ('polygon' in region) == ('polygons' in region):
            raise ValueError("region에는 'polygon' 또는 'polygons' 중 하나가 필요합니다")
        for polygon in _region_polygons(region):
            polygon = np.asarray(polygon, float)
            if (polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3 or not np.isfinite(polygon).all()
                    or (polygon < 0).any() or (polygon > [width, height]).any()
                    or abs(cv2.contourArea(polygon.astype(np.float32))) == 0):
                raise ValueError('Invalid native polygon')


def _load_config(config_path):
    config = json.loads(Path(config_path).read_text())
    if config['scope'] != 'exact_image_sha256':
        raise ValueError('Only reviewed native-coordinate profiles are enabled')
    lookup = {}
    for profile in config['profiles']:
        width, height = profile['image_size']
        if profile['coordinate_space'] != 'original_pixels' or profile['review'] != 'assistant_visual_checked_exact_sample':
            raise ValueError('Missing native coordinate review')
        _validate_regions(profile['regions'], width, height)
        key = (profile['item'], profile['camera'], profile['image_sha256'])
        if key in lookup:
            raise ValueError('Duplicate image profile')
        lookup[key] = profile
    templates = {}
    for template in config.get('templates', []):
        width, height = template['image_size']
        if template['coordinate_space'] != 'original_pixels' or template['review'] != 'assistant_visual_checked_template':
            raise ValueError('Missing native coordinate template review')
        if len(template.get('framing_checks', [])) < 1:
            raise ValueError('Template requires at least one framing check image')
        _validate_regions(template['regions'], width, height)
        key = (template['item'], template['camera'])
        if key in templates:
            raise ValueError('Duplicate item/camera template')
        templates[key] = template
    return config, lookup, templates


def _contract_threshold():
    """확정 퓨전 계약의 RT 사전 임계값 (config 파일만 사용)."""
    profile = json.loads((ROOT/'config/fusion_evaluation.json').read_text())
    value = float(profile['rtdetr_conf_threshold'])
    if not 0 <= value <= 1:
        raise ValueError('Invalid contract RT threshold')
    return value


def _derive_operational(templates, threshold):
    """운영 저장 근거(public.findings, 읽기 전용)를 등록 ROI에 배정해 품목×부위로 집계한다.

    num = 부위 ROI 내에 RT-DETR 검출(계약 사전 임계값 이상)이 있는 제품 수
    den = 해당 부위 ROI가 등록된 칼라의 촬영 근거가 있는 제품 수 (유일 제품)
    HVQ 공간 맵은 운영 백필에 보존하지 않으므로 집계하지 않는다 (있는 척 금지).
    """
    from sqlalchemy import text
    from .db import get_engine
    engine = get_engine('read')
    items = {}
    with engine.connect() as conn:
        for (item, camera), template in sorted(templates.items()):
            width, height = template['image_size']
            views = conn.execute(text(
                'SELECT product_id, width, height FROM public.inspection_views '
                'WHERE item=:item AND camera_id=:camera'),
                {'item': item, 'camera': camera}).all()
            observed = {v.product_id for v in views if (v.width, v.height) == (width, height)}
            if not observed:
                continue
            detections = conn.execute(text(
                'SELECT product_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2, score '
                'FROM public.findings WHERE item=:item AND camera_id=:camera '
                "AND kind='rtdetr_box' AND score >= :threshold"),
                {'item': item, 'camera': camera, 'threshold': threshold}).all()
            entry = items.setdefault(item, {'products_observed': set(), 'regions': {}})
            entry['products_observed'] |= observed
            for region in template['regions']:
                entry['regions'].setdefault(region['region_id'], {'hit': set(), 'count': 0, 'cameras': set()})
            for row in detections:
                if row.product_id not in observed:
                    continue
                box = (row.bbox_x1, row.bbox_y1, row.bbox_x2, row.bbox_y2)
                region_id = region_for_box(box, template['regions'], width, height)
                if region_id:
                    agg = entry['regions'][region_id]
                    agg['hit'].add(row.product_id)
                    agg['count'] += 1
                    agg['cameras'].add(camera)
    summary = {}
    for item, entry in items.items():
        observed = entry['products_observed']
        regions = {}
        for region_id, agg in entry['regions'].items():
            den = len(observed)
            regions[region_id] = {'num': len(agg['hit']), 'den': den,
                                  'rate': len(agg['hit'])/den if den else None,
                                  'detection_count': agg['count'],
                                  'cameras': sorted(agg['cameras'])}
        summary[item] = {'products_observed': len(observed), 'regions': regions}
    return {'threshold': threshold,
            'source': 'public.findings read-only (batch evidence layer; HVQ spatial maps not stored operationally)',
            'items': summary}


def derive(evidence_root=None, config_path=CONFIG):
    config, lookup, templates = _load_config(config_path)
    gui_cases = _derive_gui_cases(config, lookup, templates, evidence_root)
    operational = _derive_operational(templates, _contract_threshold())
    return {'version': config['version'], 'mapping_scope': config['scope'],
            'template_scope': config.get('template_scope', 'item_camera_size_framing_checked'),
            'root_config_sha256': fingerprint(ROOT/'config/fusion.json') if config.get('threshold_source') == 'root_fusion_config' else None,
            'config_sha256': fingerprint(config_path), 'generated_at': datetime.now(timezone.utc).isoformat(),
            'source_scope': 'stored_gui_evidence_exact_image_samples + operational_findings_templates',
            'cases': gui_cases, 'operational': operational,
            'templates': [{'item': t['item'], 'camera': t['camera'],
                           'reference_image': t.get('reference_image'),
                           'framing_checks': [f.get('image') for f in t.get('framing_checks', [])],
                           'regions': t['regions'], 'coverage': t.get('coverage', {})}
                          for t in templates.values()]}


def _derive_gui_cases(config, lookup, templates, evidence_root):
    groups = {}
    paths = sorted(Path(evidence_root or ROOT/'gui_evidence').glob('*/result.json'))
    for path in paths:
        report = json.loads(path.read_text())
        views = report.get('views', {})
        if set(views) != {'C1', 'C2', 'C3', 'C4', 'C5'}:
            continue
        if any(not Path(view['image_path']).is_file() for view in views.values()):
            continue
        hashes = tuple(fingerprint(views[camera]['image_path']) for camera in sorted(views))
        key = (report['item'], hashes)
        # Uploaded byte-identical copies must not increase product support.
        rank = sum('/dataset/' in view['image_path'] for view in views.values())
        if key not in groups or rank > groups[key][0]:
            groups[key] = (rank, path, report, hashes)
    cases = []
    for _, path, report, hashes in groups.values():
        case_id = hashlib.sha256((report['item']+''.join(hashes)).encode()).hexdigest()[:24]
        case = {'case_id': case_id, 'product_id': report['product_id'], 'item': report['item'],
                'models': report.get('models', {}), 'source_report': str(path.resolve()),
                'recorded_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), 'views': []}
        for index, camera in enumerate(sorted(report['views'])):
            view = report['views'][camera]
            profile = lookup.get((report['item'], camera, hashes[index]))
            from_template = False
            if not profile:
                template = templates.get((report['item'], camera))
                if template and [view['width'], view['height']] == template['image_size']:
                    profile, from_template = template, True
            if not profile:
                continue
            width, height = profile['image_size']
            if [view['width'], view['height']] != [width, height]:
                continue
            image = cv2.imread(view['image_path'])
            if image is None or image.shape[:2] != (height, width):
                continue
            threshold = (json.loads((ROOT/'config/fusion.json').read_text())['rtdetr']['conf_threshold']
                         if config.get('threshold_source') == 'root_fusion_config'
                         else report.get('product', {}).get('rtdetr_conf_threshold'))
            if threshold is None or not math.isfinite(threshold) or not 0 <= threshold <= 1:
                continue
            detections = []
            for detection in view.get('detections', []):
                if not math.isfinite(detection['score']) or not threshold <= detection['score'] <= 1:
                    continue
                region = region_for_box(detection['bbox'], profile['regions'], width, height)
                detections.append({**detection, 'region_id': region})
            native_map = None
            map_path = Path(view.get('map_npy', ''))
            if map_path.is_file():
                candidate = np.load(map_path, allow_pickle=False).squeeze()
                if candidate.ndim == 2 and np.isfinite(candidate).all():
                    native_map = candidate
            roi_means = {}
            for region in profile['regions']:
                if native_map is not None:
                    transform = Transform.resize('original', 'saved_hvq_map', Size(width, height),
                        Size(native_map.shape[1], native_map.shape[0]), provenance=config['transform_provenance'])
                    mask = np.zeros(native_map.shape, bool)
                    for poly in _region_polygons(region):
                        mask |= polygon_mask(transform.polygon(poly), transform.target_size)
                    if mask.any():
                        roi_means[region['region_id']] = float(native_map[mask].mean())
            case['views'].append({'camera': camera, 'image_path': view['image_path'], 'image_sha256': hashes[index],
                'width': width, 'height': height, 'regions': profile['regions'], 'coverage': profile.get('coverage', {}),
                'template': from_template,
                'detections': detections, 'hvq_roi_mean': roi_means, 'rtdetr_threshold': threshold})
        if case['views']:
            cases.append(case)
    return cases


def load_artifact():
    path = Path(os.getenv('PART_HEATMAP_REPORT', str(ROOT/'reports/part_heatmap/latest.json')))
    try:
        artifact = json.loads(path.read_text())
        if (artifact.get('config_sha256') == fingerprint(CONFIG)
                and (not artifact.get('root_config_sha256') or artifact['root_config_sha256'] == fingerprint(ROOT/'config/fusion.json'))):
            return artifact
    except (OSError, json.JSONDecodeError):
        pass
    return None


def summarize_artifact(artifact, item, camera=None, model_version=None, date_from=None, date_to=None):
    cases = []
    for source in artifact['cases']:
        if source['item'] != item or (model_version and model_version not in source['models'].values()):
            continue
        if date_from and source['recorded_at'][:10] < date_from[:10]:
            continue
        if date_to and source['recorded_at'][:10] > date_to[:10]:
            continue
        views = [view for view in source['views'] if not camera or view['camera'] == camera]
        # Detect stale images instead of painting evidence for replaced assets.
        def current(view):
            try:
                return fingerprint(view['image_path']) == view['image_sha256']
            except OSError:
                return False
        views = [view for view in views if current(view)]
        if views:
            cases.append({**source, 'views': views})
    support, positives, counts, means, coverage = {}, {}, {}, {}, {}
    for case in cases:
        for view in case['views']:
            coverage.update(view['coverage'])
            for region in view['regions']:
                region_id = region['region_id']
                support.setdefault(region_id, set()).add(case['case_id'])
                means.setdefault(region_id, []).extend([view['hvq_roi_mean'][region_id]] if region_id in view['hvq_roi_mean'] else [])
            for detection in view['detections']:
                region_id = detection['region_id']
                if region_id:
                    positives.setdefault(region_id, set()).add(case['case_id'])
                    counts[region_id] = counts.get(region_id, 0)+1
    rows = []
    for region_id, products in support.items():
        num, den = len(positives.get(region_id, set())), len(products)
        scores = means.get(region_id, [])
        rows.append({'group': {'part_id': region_id}, 'num': num, 'den': den, 'rate': num/den,
                     'reason': None, 'stat_key': region_id, 'detection_count': counts.get(region_id, 0),
                     'hvq_roi_mean': sum(scores)/len(scores) if scores else None,
                     'source': 'gui_evidence'})
    operational_products = None
    operational = artifact.get('operational') or {}
    item_ops = (operational.get('items') or {}).get(item) or {}
    if item_ops:
        operational_products = item_ops.get('products_observed')
        for region_id, agg in (item_ops.get('regions') or {}).items():
            if camera and camera not in agg.get('cameras', []):
                continue
            rows.append({'group': {'part_id': region_id}, 'num': agg['num'], 'den': agg['den'],
                         'rate': agg['rate'], 'reason': None,
                         'stat_key': f'operational:{region_id}',
                         'detection_count': agg.get('detection_count'),
                         'hvq_roi_mean': None, 'source': 'operational_findings',
                         'cameras': agg.get('cameras', [])})
    public_cases = []
    for case in cases:
        public_views = []
        for view in case['views']:
            public_views.append({key: value for key, value in view.items() if key not in ('image_path', 'image_sha256')}
            )
            public_views[-1]['image_url'] = f"/parts/evidence/{case['case_id']}/{view['camera']}"
        public_cases.append({key: value for key, value in case.items() if key not in ('source_report', 'views')} | {'views': public_views})
    return {'item': item, 'metric': 'part_detection_frequency', 'mapping_version': artifact['version'],
            'mapping_scope': artifact['mapping_scope'], 'mapping_verified': bool(rows), 'rows': rows,
            'source_scope': artifact['source_scope'], 'sample_products': len(cases),
            'operational_products': operational_products,
            'operational_threshold': operational.get('threshold'),
            'coverage': coverage,
            'generated_at': artifact['generated_at'], 'cases': public_cases,
            'definition': '부위에 RT-DETR 검출이 있는 제품 / ROI로 관측한 제품 (운영 근거: 계약 RT 사전 임계값 이상). 확정 불량률이 아님.',
            'reason': None if rows else 'no_registered_evidence_for_filters'}
