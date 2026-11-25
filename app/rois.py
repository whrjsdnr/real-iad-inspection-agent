"""ROI LUT: camera_id + 픽셀 bbox를 part_id로 매핑한다.

mapping_version 변경 시 LUT 구조를 버전업하고 MAPPING_VERSION 값을 올린다.
매핑 규칙: bbox 중심점을 포함하는 ROI 중 면적이 가장 작은 것을 선택,
없으면 "unknown".
"""
from __future__ import annotations

import json
from pathlib import Path

_CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config/parts_roi.json").read_text())
MAPPING_VERSION = _CONFIG["default_mapping_version"]
IMAGE_W = _CONFIG["mappings"][MAPPING_VERSION]["image_size"]["width"]
IMAGE_H = _CONFIG["mappings"][MAPPING_VERSION]["image_size"]["height"]
LUT = _CONFIG["mappings"][MAPPING_VERSION]["items"]


def rois_for(item: str, camera_id: str, mapping_version: str = MAPPING_VERSION):
    if mapping_version not in _CONFIG["mappings"]:
        raise ValueError(f"지원하지 않는 mapping_version: {mapping_version}")
    return _CONFIG["mappings"][mapping_version]["items"].get(item, {}).get(camera_id, [])


def map_bbox_to_part(
    item: str,
    camera_id: str,
    bbox: tuple[float, float, float, float],
    mapping_version: str = MAPPING_VERSION,
) -> str:
    x1, y1, x2, y2 = bbox
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    best: str | None = None
    best_area: float | None = None
    for part_id, (rx1, ry1, rx2, ry2) in rois_for(item, camera_id, mapping_version):
        if rx1 <= cx <= rx2 and ry1 <= cy <= ry2:
            area = (rx2 - rx1) * (ry2 - ry1)
            if best_area is None or area < best_area:
                best, best_area = part_id, area
    return best if best is not None else "unknown"
