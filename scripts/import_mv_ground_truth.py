"""Reuse validated MV presence-v2 numerical arrays; never write MV or infer a model."""
import ast,csv,gzip,hashlib,json,sqlite3,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.part_heatmap import fingerprint
from app.spatial_heatmap import ROOT


def legacy_coarse(path):
    tree=ast.parse(path.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='coarse_occupancy')
    namespace={'np':np};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    return namespace['coarse_occupancy']


def main():
    cv2.setNumThreads(1)
    cfg=json.loads((ROOT/'config/ground_truth_heatmaps.json').read_text());source=Path(cfg['source_run']);dataset=Path(cfg['dataset_root'])
    schema=json.loads((source/'heatmap_schema.json').read_text());policy=json.loads((source/'mask_policy.json').read_text())
    validation=json.loads((source/'heatmap_validation.json').read_text());run=json.loads((source/'run.json').read_text())
    assert schema['schema']=='presence-v2' and schema['grid']==64 and validation['errors']==0
    assert policy['validated'] and policy['threshold']==0 and policy['encoding']=='grayscale_uint8'
    keys=json.loads((source/'heatmap_groups.json').read_text());summary=list(csv.DictReader((source/'heatmap_summary.csv').open()))
    arrays={name:np.load(source/(name+'.npy'),mmap_mode='r',allow_pickle=False) for name in
            ('presence_count','occupancy_known','occupancy_positive','observation_count','area_fraction_sum')}
    assert all(a.shape==(len(keys),64,64) for a in arrays.values())
    for i,key in enumerate(keys):
        row=summary[i];assert key==[row['category'],row['defect_type'],row['view']]
        nk,np_=int(row['n_known']),int(row['n_positive']);count=arrays['presence_count'][i]
        assert np.isfinite(count).all() and (count>=0).all() and (count<=np_).all() and np.equal(count,np.floor(count)).all()
        assert np.all(arrays['observation_count'][i]==nk)
        for name,den in [('occupancy_known',nk),('occupancy_positive',np_)]:
            expected=count/den if den else np.full(count.shape,np.nan)
            assert np.allclose(expected,arrays[name][i],equal_nan=True)
    seen=set();duplicates=0;dimensions=Counter();groups=Counter();known=Counter();representatives=[];audit_rows=defaultdict(list)
    for row in csv.DictReader((source/'image_metadata_with_split.csv').open()):
        if row['split']!='train' or row['status']!='NG':continue
        key=(row['category'],row['defect_type'],row['view']);identity=(row['category'],row['view'],row['product_id'])
        duplicates+=identity in seen;seen.add(identity);groups[key]+=1;known[key]+=bool(row['mask_path'])
        dimensions[(int(row['width']),int(row['height']))]+=1
        if row['product_id'] in cfg['representative_products']:representatives.append(row)
        if (row['category'],row['defect_type'],row['view']) in [('toothbrush','CH','C1'),('zipper','BX','C1')]:audit_rows[key].append(row)
    assert duplicates==0 and len(dimensions)==1
    for i,key in enumerate(keys):
        assert groups[tuple(key)]==int(summary[i]['n_images']) and known[tuple(key)]==int(summary[i]['n_known'])
    coarse=legacy_coarse(Path(cfg['coarse_occupancy_source']));group_audits=[]
    for key,rows in audit_rows.items():
        count=np.zeros((64,64));n=0
        for row in rows:
            if not row['mask_path']:continue
            mask=cv2.imread(str(dataset/row['mask_path']),cv2.IMREAD_GRAYSCALE)
            assert mask is not None and mask.shape==(int(row['height']),int(row['width']))
            assert Path(row['mask_path']).stem==Path(row['image_path']).stem
            count+=coarse(mask>policy['threshold'],64);n+=1
        assert np.array_equal(count,arrays['presence_count'][keys.index(list(key))])
        group_audits.append({'group':key,'masks_rechecked':n,'exact_presence_count_equal':True})
    output=ROOT/cfg['cache_directory'];output.mkdir(exist_ok=True,parents=True)
    entries=[];width,height=next(iter(dimensions));minimum=json.loads((ROOT/'config/spatial_heatmap.json').read_text())['minimum_denominator']
    source_files=['heatmap_schema.json','heatmap_validation.json','heatmap_groups.json','heatmap_summary.csv','mask_policy.json','run.json']+[name+'.npy' for name in arrays]
    hashes={name:fingerprint(source/name) for name in source_files}
    def save(item,view,count,area,nk,np_,nu,products,defect_types,product_id=None,comparison=None,mask_path=None,image_path=None):
        mask=(nk>0)*np.ones((64,64),bool)
        def ratio(values,den):return [float(x)/den if den else None for x in np.asarray(values).ravel()]
        record={'item':item,'view':view,'split':'train','split_origin':run['config']['split_policy'],'product_id':product_id,
          'grid_width':64,'grid_height':64,'coordinate_system':'normalized_original_frame_xy_down',
          'source_image_width':width,'source_image_height':height,'product_count':products,
          'known_products':nk,'positive_mask_products':np_,'unknown_products':nu,'defect_types':defect_types,
          'positive_count':count.astype(int).ravel().tolist(),'known_count':[nk]*4096,'unknown_count':[nu]*4096,
          'defect_rate':ratio(count,nk),'occupancy_positive':ratio(count,np_),'mask_coverage':ratio(area,nk),
          'coverage_mask':mask.astype(int).ravel().tolist(),'annotation_coverage':nk/products if products else None,
          'aggregation_method':'legacy_coarse_occupancy_any_foreground_source_pixel',
          'mapping_version':cfg['version'],'source':'MV/windows_preserved_20261111_v1/presence-v2',
          'source_run_created_at':run['created'],'generated_at':datetime.now(timezone.utc).isoformat(),
          'scope':'individual_train_NG' if product_id else 'train_NG_with_provided_masks',
          'normal_products_included':False,'minimum_denominator':minimum,
          'sample_status':'insufficient_sample' if nk<minimum else 'supported',
          'mapping_status':'image_frame_only_physical_surface_uv_unverified','physical_surface_uv_verified':False,
          'comparison':comparison,'mask_binary_rule':'grayscale > 0; no component filtering',
          'definition':'positive_count/known_count conditional on provided Train NG masks, NOT overall inspection defect prevalence',
          'mask_coverage_definition':'sum foreground area fractions / known masks, not annotation availability',
          'image_path':image_path,'mask_path':mask_path}
        identity=hashlib.sha256(f'{item}:{view}:{product_id or "aggregate"}:train:{cfg["version"]}'.encode()).hexdigest()[:24]
        temporary=output/(identity+'.tmp');temporary.write_bytes(gzip.compress(json.dumps(record,separators=(',',':'),allow_nan=False).encode()));temporary.replace(output/(identity+'.json.gz'))
        entries.append({'id':identity,'item':item,'view':view,'split':'train','product_id':product_id,
                        'known_products':nk,'unknown_products':nu,'product_count':products,'comparison':comparison})
    for item,view in sorted({(k[0],k[2]) for k in keys}):
        ids=[i for i,key in enumerate(keys) if (key[0],key[2])==(item,view)]
        nk=sum(int(summary[i]['n_known']) for i in ids);np_=sum(int(summary[i]['n_positive']) for i in ids);nu=sum(int(summary[i]['n_unknown']) for i in ids)
        save(item,view,arrays['presence_count'][ids].sum(0),arrays['area_fraction_sum'][ids].sum(0),nk,np_,nu,nk+nu,[keys[i][1] for i in ids])
    score_cfg=json.loads((ROOT/'config/spatial_heatmap.json').read_text());db=sqlite3.connect(Path(score_cfg['source_score_cache']).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    for row in representatives:
        image=dataset/row['image_path'];path=dataset/row['mask_path'] if row['mask_path'] else None
        count=np.zeros((64,64));area=np.zeros((64,64));nk=0;np_=0
        if path:
            raw=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE);assert raw is not None and raw.shape==(height,width)
            mask=raw>0;count=coarse(mask,64);area=cv2.resize(mask.astype(np.float32),(64,64),interpolation=cv2.INTER_AREA);nk=1;np_=int(mask.any())
        match=db.execute('SELECT p.split,v.image_path FROM products p JOIN views v USING(product_id) WHERE p.product_id=? AND v.camera=?',(row['product_id'],row['view'])).fetchone()
        same=False
        if match:
            original=Path(match['image_path']);original=Path(score_cfg['dataset_root'])/original if not original.is_absolute() else original
            same=match['split']==row['split'] and original.is_file() and fingerprint(original)==fingerprint(image)
        comparison={'status':'verified_same_product_view_split_source_image' if same and nk else 'unsupported_missing_mask_or_split_image_mismatch',
                    'model_cache_split':match['split'] if match else None,'mask_split':row['split'],'source_image_sha256':fingerprint(image)}
        save(row['category'],row['view'],count,area,nk,np_,1-nk,1,[row['defect_type']],row['product_id'],comparison,
             str(path) if path else None,str(image))
    db.close()
    report={'version':cfg['version'],'entries':entries,'source_files_sha256':hashes,'schema':schema,'source_validation':validation,
      'source_run_created_at':run['created'],'imported_at':datetime.now(timezone.utc).isoformat(),
      'metadata_audit':{'train_NG_rows':sum(dimensions.values()),'duplicate_product_view_rows':duplicates,
                        'original_dimensions':list(dimensions.keys()),'declared_product_identity_only':True},
      'representative_group_mask_audits':group_audits,'config_sha256':fingerprint(ROOT/'config/ground_truth_heatmaps.json'),
      'legacy_coarse_source_sha256':fingerprint(cfg['coarse_occupancy_source'])}
    tmp=output/'index.tmp';tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2));tmp.replace(output/'index.json')
    print(json.dumps({'records':len(entries),'aggregate_item_views':len(entries)-len(representatives),'representative_product_views':len(representatives),'mask_audits':group_audits}))

if __name__=='__main__':main()
