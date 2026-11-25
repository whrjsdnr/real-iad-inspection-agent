"""Aggregate existing model detections and maps using exact-image reviewed ROIs."""
import base64
import html
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.part_heatmap import derive, ROOT


def main():
    artifact = derive()
    out = ROOT/'reports/part_heatmap'
    out.mkdir(parents=True, exist_ok=True)
    temporary = out/'latest.tmp'
    temporary.write_text(json.dumps(artifact, ensure_ascii=False, indent=2))
    temporary.replace(out/'latest.json')
    cards = []
    for case in artifact['cases']:
        for view in case['views']:
            image = base64.b64encode(Path(view['image_path']).read_bytes()).decode()
            def render_polygon(poly):
                return f'<polygon points="{" ".join(f"{x},{y}" for x,y in poly)}"/>'
            polygons = ''.join(render_polygon(poly) + f'<text x="{poly[0][0]}" y="{poly[0][1]}">{html.escape(region["region_id"])}</text>'
                               for region in view['regions'] for poly in ([region['polygon']] if 'polygon' in region else region['polygons']))
            boxes = ''.join(f'<rect x="{d["bbox"][0]}" y="{d["bbox"][1]}" width="{d["bbox"][2]-d["bbox"][0]}" height="{d["bbox"][3]-d["bbox"][1]}"/>' for d in view['detections'])
            cards.append(f'<article><h2>{html.escape(case["product_id"])} · {view["camera"]}</h2><svg viewBox="0 0 {view["width"]} {view["height"]}"><image width="{view["width"]}" height="{view["height"]}" href="data:image/jpeg;base64,{image}"/><g class="roi">{polygons}</g><g class="boxes">{boxes}</g></svg></article>')
    for template in artifact.get('templates', []):
        ref = template.get('reference_image')
        if not ref or not Path(ref).is_file():
            continue
        image = base64.b64encode(Path(ref).read_bytes()).decode()
        w, h = 1024, 1024
        polygons = ''.join(f'<polygon points="{" ".join(f"{x},{y}" for x,y in poly)}"/><text x="{poly[0][0]}" y="{poly[0][1]}">{html.escape(region["region_id"])}</text>'
                           for region in template['regions'] for poly in ([region['polygon']] if 'polygon' in region else region['polygons']))
        checks = ''.join(f'<img src="data:image/jpeg;base64,{base64.b64encode(Path(c).read_bytes()).decode()}" width="220">' for c in (template.get('framing_checks') or [])[:2] if c and Path(c).is_file())
        cards.append(f'<article><h2>TEMPLATE {html.escape(template["item"])} · {template["camera"]}</h2><svg viewBox="0 0 {w} {h}"><image width="{w}" height="{h}" href="data:image/jpeg;base64,{image}"/><g class="roi">{polygons}</g></svg><div class="checks">{checks}</div></article>')
    tokens = (ROOT/'inspection-gui/src/styles/tokens.css').read_text()
    (out/'roi-native-overlay.html').write_text('<!doctype html><meta charset="utf-8"><title>Native ROI verification</title><style>'+tokens+'body{background:var(--bg);color:var(--text);font:14px system-ui}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}svg{width:100%}.roi polygon{stroke:var(--ok);stroke-width:4;fill:none}.roi text{fill:var(--ok);font:28px monospace}.boxes rect{fill:none;stroke:var(--signal);stroke-width:3}.checks img{margin:4px;border:1px solid var(--line)}</style><h1>실제 원본 좌표 ROI · 저장 모델 검출</h1><p>다각형: 확인한 부위 ROI(템플릿은 품목×칩라 공용) / 사각형: 기등록 근거의 임계값 이상 검출. 프레이밍 확인 이미지는 각 카드 하단.</p><main>'+''.join(cards)+'</main>')
    ops = artifact.get('operational', {}).get('items', {})
    print(json.dumps({'cases': len(artifact['cases']), 'views': sum(len(case['views']) for case in artifact['cases']),
                      'template_items': sorted({t['item'] for t in artifact.get('templates', [])}),
                      'operational_items': len(ops),
                      'report': str(out/'latest.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
