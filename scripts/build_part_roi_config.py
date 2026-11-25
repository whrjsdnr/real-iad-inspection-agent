"""part_roi_templates.py의 템플릿 데이터를 config/part_heatmap_regions.json에 병합한다.

- 참조/프레이밍 확인 이미지 존재와 실제 크기를 검증한다.
- 폴리곤은 app.part_heatmap._load_config의 검증을 통과해야 한다.
- 기존 exact-image profiles는 그대로 보존한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from scripts.part_roi_templates import TEMPLATES  # noqa: E402

CONFIG = ROOT / 'config/part_heatmap_regions.json'


def _check_image(path: str, want: tuple[int, int]) -> None:
    file = Path(path)
    if not file.is_file():
        raise SystemExit(f'이미지가 없습니다: {path}')
    image = cv2.imread(str(file))
    if image is None or image.shape[1] != want[0] or image.shape[0] != want[1]:
        raise SystemExit(f'이미지 크기 불일치: {path} -> {None if image is None else image.shape}')


def main() -> None:
    config = json.loads(CONFIG.read_text())
    seen = set()
    templates = []
    for entry in TEMPLATES:
        key = (entry['item'], entry['camera'])
        if key in seen:
            raise SystemExit(f'중복 템플릿: {key}')
        seen.add(key)
        size = tuple(entry['image_size'])
        _check_image(entry['reference_image'], size)
        for check in entry['framing_checks']:
            _check_image(check, size)
        templates.append({
            'item': entry['item'],
            'camera': entry['camera'],
            'image_size': list(size),
            'reference_image': entry['reference_image'],
            'reference_sha256': None,
            'coordinate_space': 'original_pixels',
            'review': 'assistant_visual_checked_template',
            'framing_checks': [{'image': check, 'note': 'same_fixture_framing'} for check in entry['framing_checks']],
            'regions': entry['regions'],
            'coverage': entry.get('coverage', {}),
            'note': entry.get('note', ''),
        })
    previous = {t['item'] for t in config.get('templates', [])}
    config['templates'] = templates
    config['template_scope'] = 'item_camera_size_framing_checked'
    config['template_review'] = 'assistant_visual_checked_template_requires_framing_check_image'
    config['version'] = 'part-heatmap-native-samples-v2'
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')

    from app.part_heatmap import _load_config
    loaded, _, loaded_templates = _load_config(CONFIG)
    items = sorted({t['item'] for t in templates})
    print(json.dumps({'version': loaded['version'], 'templates': len(loaded_templates),
                      'items': items, 'items_total': len(items),
                      'replaced_previous_items': sorted(previous)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
