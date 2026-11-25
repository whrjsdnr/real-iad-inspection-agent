"""Precompute spatial views from existing SQLite boxes/NPY maps. Never runs a model."""
import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.spatial_heatmap import build_grid, validate_hierarchy, ROOT
from app.part_heatmap import fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--items',nargs='+',default=['toothbrush','zipper'])
    parser.add_argument('--all-registered',action='store_true')
    args=parser.parse_args()
    config=json.loads((ROOT/'config/spatial_heatmap.json').read_text())
    roi=json.loads((ROOT/'config/part_heatmap_regions.json').read_text())
    hierarchy=json.loads((ROOT/'config/spatial_regions.json').read_text())
    nodes=validate_hierarchy(hierarchy['nodes'])
    contract=json.loads((ROOT/'config/fusion_evaluation.json').read_text())
    names=['config/spatial_heatmap.json','config/spatial_regions.json','config/part_heatmap_regions.json','config/fusion_evaluation.json','config/fusion.json']
    config_hashes={name:fingerprint(ROOT/name) for name in names}
    algorithm_hash=fingerprint(ROOT/'app/spatial_heatmap.py')
    models=json.loads((ROOT/'config/fusion.json').read_text())['model_versions']
    templates={(row['item'],row['camera']):row for row in roi.get('templates',[])}
    items=sorted({key[0] for key in templates}) if args.all_registered else args.items
    maps={}
    for path in sorted((ROOT/'gui_evidence').glob('*/result.json')):
        report=json.loads(path.read_text())
        for camera,view in report.get('views',{}).items():
            file=Path(view.get('map_npy',''))
            image=Path(view['image_path'])
            if file.is_file() and image.is_file():maps[(report['product_id'],camera)]=(str(file),fingerprint(image))
    connection=sqlite3.connect('file:'+config['source_score_cache']+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    out=ROOT/'reports/spatial_heatmap';out.mkdir(parents=True,exist_ok=True)
    entries=[];views={};measurements=[];status=[]
    try:
        for item in items:
            selected=[]
            for truth in ('defect','normal'):
                row=connection.execute('SELECT product_id FROM products WHERE category=? AND truth=? AND status=\'COMPLETED\' ORDER BY product_id LIMIT 1',(item,truth)).fetchone()
                if row:selected.append(row[0])
            for product in selected:
                for view in connection.execute('SELECT * FROM views WHERE product_id=? ORDER BY camera',(product,)):
                    camera=view['camera'];template=templates.get((item,camera))
                    if not template:
                        native=hierarchy.get('native_references',{}).get(item,{}).get(camera)
                        parents=[node for node in hierarchy['nodes'] if node['category']==item and node['parent_region_id'] is None and camera in node.get('camera_rois',{})]
                        if native and parents:
                            template={'image_size':native['image_size'],'regions':[{'region_id':node['region_id'],'label':node['display_name'],'polygons':node['camera_rois'][camera]} for node in parents]}
                    if not template:
                        status.append({'item':item,'product_id':product,'camera':camera,'status':'mapping_pending','reason':'native_roi_not_registered'})
                        continue
                    image=Path(view['image_path'])
                    if not image.is_absolute():image=Path(config['dataset_root'])/image
                    if not image.is_file() or [view['width'],view['height']]!=template['image_size']:
                        status.append({'item':item,'product_id':product,'camera':camera,'status':'mapping_failed','reason':'image_missing_or_dimensions_mismatch'})
                        continue
                    image_hash=fingerprint(image)
                    view_key=hashlib.sha256((product+camera+image_hash).encode()).hexdigest()[:24]
                    detections=[{'bbox':box['bbox'],'score':float(box.get('confidence',box.get('score',0)))} for box in json.loads(view['boxes_json'])]
                    detections=[box for box in detections if box['score']>=contract['rtdetr_conf_threshold']]
                    saved_map=maps.get((product,camera))
                    map_path=saved_map[0] if saved_map and saved_map[1]==image_hash else view['map_path'] or None
                    if map_path and not Path(map_path).is_absolute():map_path=str((Path(config['source_score_cache']).resolve().parent/map_path).resolve())
                    record={'item':item,'product_id':product,'camera':camera,'models':models,'image_path':str(image),
                            'image_sha256':image_hash,'original_size':[view['width'],view['height']],
                            'source':'saved_batch5_box_cache','detections':detections,
                            'map_path':map_path}
                    views[view_key]={'image_path':str(image),'image_sha256':image_hash,'item':item,'product_id':product,'camera':camera,
                                     'detections':detections,'original_size':record['original_size']}
                    regions=[]
                    for parent in template['regions']:
                        node=nodes.get((item,parent['region_id']),{})
                        polygons=node.get('camera_rois',{}).get(camera) or parent.get('polygons') or [parent['polygon']]
                        regions.append({'region_id':parent['region_id'],'parent_region_id':None,'label':node.get('display_name',parent['label']),'polygons':polygons})
                    for node in hierarchy['nodes']:
                        if node['category']==item and node['parent_region_id'] and camera in node.get('camera_rois',{}):
                            regions.append({'region_id':node['region_id'],'parent_region_id':node['parent_region_id'],'label':node['display_name'],'polygons':node['camera_rois'][camera]})
                    for region in regions:
                        for resolution in config['resolutions']:
                            start=time.perf_counter();grid=build_grid(record,region,resolution,config)
                            grid.update(mapping_version=hierarchy['version'],source_image_id=view_key,updated_at=datetime.now(timezone.utc).isoformat())
                            grid_id=hashlib.sha256(f"{view_key}:{region['region_id']}:{resolution}:{fingerprint(ROOT/'config/spatial_regions.json')}".encode()).hexdigest()[:24]
                            encoded=json.dumps(grid,separators=(',',':'),allow_nan=False).encode();packed=gzip.compress(encoded)
                            temporary_grid=out/f'{grid_id}.tmp'
                            temporary_grid.write_bytes(packed);temporary_grid.replace(out/f'{grid_id}.json.gz')
                            support=sum(grid['hvq']['valid_observation_counts'])
                            valid=sum(grid['coverage_mask'])
                            entries.append({'grid_id':grid_id,'item':item,'product_id':product,'camera':camera,'region_id':region['region_id'],
                                            'parent_region_id':region['parent_region_id'],'label':region['label'],'resolution':resolution,
                                            'image_id':view_key,'hvq_status':grid['hvq']['status'],'hvq_native_bin_coverage':support/valid if valid else 0})
                            entries[-1]['native_roi_size']=[grid['roi_bounds'][2]-grid['roi_bounds'][0],grid['roi_bounds'][3]-grid['roi_bounds'][1]]
                            measurements.append({'grid_id':grid_id,'item':item,'camera':camera,'region_id':region['region_id'],'resolution':resolution,
                                                 'compute_ms':(time.perf_counter()-start)*1000,'json_bytes':len(encoded),'gzip_bytes':len(packed),
                                                 'hvq_native_bin_coverage':support/valid if valid else None,'valid_cells':valid})
                    print(f'{item} {product} {camera}: saved spatial grids',flush=True)
    finally:connection.close()
    for entry in entries:
        related=[candidate for candidate in entries if candidate['image_id']==entry['image_id'] and candidate['region_id']==entry['region_id']]
        rt_res=[candidate['resolution'] for candidate in related if candidate['resolution']<=min(config['candidate_resolution'],*entry['native_roi_size'])]
        hv_res=[candidate['resolution'] for candidate in related if candidate['hvq_status']=='supported' and candidate['resolution']<=config['candidate_resolution'] and candidate['hvq_native_bin_coverage']>=config['minimum_native_bin_coverage']]
        entry['recommended_rt_resolution']=max(rt_res) if rt_res else min(config['resolutions'])
        entry['recommended_hvq_resolution']=max(hv_res) if hv_res else None
    if config_hashes!={name:fingerprint(ROOT/name) for name in names}:
        raise ValueError('Configuration changed during derive; previous index was retained')
    index={'version':config['version'],'updated_at':datetime.now(timezone.utc).isoformat(),
           'entries':entries,'views':views,'status':status,'cross_camera_registration':'unverified',
           'cross_product_registration':'unverified_individual_only','physical_surface_mapping':'unverified_use_2d',
           'config_hashes':config_hashes,'algorithm_hash':algorithm_hash}
    temporary=out/'index.tmp';temporary.write_text(json.dumps(index,ensure_ascii=False));temporary.replace(out/'index.json')
    (out/'resolution-benchmark.json').write_text(json.dumps(measurements,indent=2))
    print(json.dumps({'grids':len(entries),'views':len(views),'unsupported_views':len(status),'index':str(out/'index.json')}))


if __name__=='__main__':main()
