"""Read stored GUI inference results; write ONLY separate audit artifacts."""
import base64,collections,hashlib,html,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.rois import map_bbox_to_part,rois_for
from app.coordinates import map_registered_bbox
ROOT=Path(__file__).resolve().parents[1]

def main():
    rows=[];seen=set();cards=[]
    for path in sorted((ROOT/'gui_evidence').glob('*/result.json')):
        report=json.loads(path.read_text())
        for cam,view in report.get('views',{}).items():
            image=Path(view['image_path'])
            if not image.is_file():continue
            fingerprint=hashlib.sha256(image.read_bytes()).hexdigest()
            key=(fingerprint,cam)
            if key in seen:continue
            seen.add(key)
            rects=[]
            for box in view.get('detections',[]):
                bbox=box['bbox'];before=map_bbox_to_part(report['item'],cam,bbox,mapping_version='roi-lut-v1')
                after=map_registered_bbox(report['item'],cam,bbox,registration=None,mapping_version='roi-lut-v1')
                rows.append({'item':report['item'],'camera':cam,'image_sha256':fingerprint,'bbox':bbox,'before_recorded_rule':before,'after':after['part_id'],'reason':after['reason']})
                x1,y1,x2,y2=bbox
                rects.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" fill="none" stroke="var(--signal)" stroke-width="3"/>')
            encoded=base64.b64encode(image.read_bytes()).decode()
            rois=''.join(f'<rect x="{r[0]}" y="{r[1]}" width="{r[2]-r[0]}" height="{r[3]-r[1]}" fill="none" stroke="var(--ok)"/><text x="{r[0]}" y="{r[1]+14}" fill="var(--text)">{html.escape(part)}</text>' for part,r in rois_for(report['item'],cam,'roi-lut-v1'))
            cards.append(f'<article><h2>{html.escape(report["item"])} / {cam}</h2><p>원본 {view["width"]}×{view["height"]} · 저장된 RT-DETR 원본 좌표 박스. LUT 겹침은 미검증이므로 적용하지 않음.</p><svg viewBox="0 0 {view["width"]} {view["height"]}"><image width="{view["width"]}" height="{view["height"]}" href="data:image/jpeg;base64,{encoded}"/>{"".join(rects)}</svg><p>별도 LUT 기준면 (640×480) — 원본과 등록 관계 미확인</p><svg viewBox="0 0 640 480">{rois}</svg></article>')
    groups={}
    for row in rows:
        key=row['item']+'/'+row['camera'];g=groups.setdefault(key,{'detections':0,'before_unknown':0,'after_unknown':0,'unverified':0});g['detections']+=1;g['before_unknown']+=row['before_recorded_rule']=='unknown';g['after_unknown']+=row['after']=='unknown';g['unverified']+=1
    result={'source':'stored gui_evidence/*/result.json; no inference rerun; no DB writes','unique_images':len(seen),'detections':len(rows),'categories':sorted({r['item'] for r in rows}),'groups':groups,'rows':rows,'registration_verified':False,'note':'Before uses legacy rule with no registration. After rejects unsupported registration; higher unknown is intentional, not improved detection performance.'}
    out=ROOT/'reports/gui_validation';(out/'roi_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    tokens=(ROOT/'inspection-gui/src/styles/tokens.css').read_text()
    (out/'roi_overlay.html').write_text('<!doctype html><meta charset="utf-8"><title>ROI coordinate audit</title><style>'+tokens+'body{background:var(--bg);color:var(--text);font:14px system-ui;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}svg{width:100%;max-height:420px;background:var(--panel)}article{min-width:0}p{color:var(--muted)}</style><h1>읽기 전용 좌표 정합성 검증</h1><p>원본 검사값 변경 없음. 모델 리사이즈와 LUT 등록은 별개입니다.</p><main>'+''.join(cards)+'</main>')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows',)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
