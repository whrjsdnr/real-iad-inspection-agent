"""Bounded spatial evidence tools. No LLM-generated coordinates, SQL or grids."""
from .spatial_api import index,grid


def query_spatial_evidence(*,item,product_id=None,camera='C1',region_id=None,model='rt',method=None,resolution=64,limit=5):
    if model not in ('rt','hvq') or camera not in ('C1','C2','C3','C4','C5') or not 1<=limit<=20:
        raise ValueError('Invalid spatial query')
    candidates=[entry for entry in index()['entries'] if entry['item']==item and entry['camera']==camera and entry['resolution']==resolution
                and (not product_id or entry['product_id']==product_id) and (not region_id or entry['region_id']==region_id)]
    if not candidates:return {'status':'unsupported','reason':'no_registered_saved_spatial_evidence','item':item,'hotspots':[]}
    entry=candidates[0];method=method or ('gaussian' if model=='rt' else 'mean')
    result=grid(entry['grid_id'],model,method)
    answer={key:result[key] for key in ('item','product_id','view_id','region_id','parent_region_id','status','reason','stats','mapping_status','sample_status')}
    answer.update(model=model,method=method,available_products=sorted({entry['product_id'] for entry in candidates}),
                  note='Individual product/single camera. Ranked model signals, not confirmed defects or official fusion.',
                  evidence_link=f"spatial://{entry['grid_id']}/{model}/{method}")
    if result['status']!='supported':return answer | {'hotspots':[]}
    valid=[(value,position) for position,value in enumerate(result['values']) if value is not None and result['valid_observation_counts'][position]>0]
    valid.sort(reverse=True)
    x0,y0,x1,y1=result['roi_bounds'];width=result['grid_width'];height=result['grid_height']
    answer['hotspots']=[{'value':value,'column':position%width,'row':position//width,
                        'native_pixel_center':[x0+(position%width+.5)*(x1-x0)/width,y0+(position//width+.5)*(y1-y0)/height],
                        'valid_observations':result['valid_observation_counts'][position]}
                       for value,position in valid[:limit] if value>0]
    return answer
