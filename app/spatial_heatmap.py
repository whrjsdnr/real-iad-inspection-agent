"""Visualization-only, camera-separated grids from saved boxes/maps. No inference/DB writes."""
import json
import math
from pathlib import Path
import numpy as np
from .part_heatmap import polygon_mask
from .coordinates import Size

ROOT = Path(__file__).resolve().parents[1]


def validate_hierarchy(nodes):
    lookup = {(node['category'], node['region_id']): node for node in nodes}
    if len(lookup) != len(nodes):
        raise ValueError('Duplicate region ID')
    for node in nodes:
        seen = {node['region_id']}
        parent = node['parent_region_id']
        while parent is not None:
            if parent in seen or (node['category'], parent) not in lookup:
                raise ValueError('Missing parent or cyclic hierarchy')
            seen.add(parent)
            parent = lookup[(node['category'], parent)]['parent_region_id']
    return lookup


def extent(polygons):
    points = np.concatenate([np.asarray(polygon, float) for polygon in polygons])
    return [float(points[:,0].min()), float(points[:,1].min()), float(points[:,0].max()), float(points[:,1].max())]


def coverage(polygons, bounds, resolution):
    x0,y0,x1,y1 = bounds
    if x1 <= x0 or y1 <= y0:
        raise ValueError('Empty ROI')
    mask = np.zeros((resolution,resolution), bool)
    for polygon in polygons:
        transformed = [[(x-x0)*resolution/(x1-x0),(y-y0)*resolution/(y1-y0)] for x,y in polygon]
        mask |= polygon_mask(transformed, Size(resolution,resolution))
    return mask


def rt_grids(boxes, polygons, resolution, config):
    bounds = extent(polygons)
    valid = coverage(polygons, bounds, resolution)
    x0,y0,x1,y1 = bounds
    dx,dy = (x1-x0)/resolution,(y1-y0)/resolution
    yy,xx = np.meshgrid(np.arange(resolution)+.5,np.arange(resolution)+.5,indexing='ij')
    centers, area, confidence, gaussian, confidence_sum, box_hits = [np.zeros(valid.shape,float) for _ in range(6)]
    unique = {}
    for box in boxes:
        coords = tuple(box['bbox']); score = float(box['score'])
        if (len(coords)!=4 or not np.isfinite(coords).all() or not math.isfinite(score)
                or not 0<=score<=1 or coords[0]>=coords[2] or coords[1]>=coords[3]):
            raise ValueError('Invalid saved detection')
        unique[(coords,score)] = box
    count = 0
    for box in unique.values():
        bx0,by0,bx1,by1 = box['bbox']; score = box['score']
        left=np.maximum(x0+np.arange(resolution)*dx,bx0)
        right=np.minimum(x0+(np.arange(resolution)+1)*dx,bx1)
        top=np.maximum(y0+np.arange(resolution)*dy,by0)
        bottom=np.minimum(y0+(np.arange(resolution)+1)*dy,by1)
        overlap=np.maximum(0,bottom-top)[:,None]*np.maximum(0,right-left)[None,:]/(dx*dy)
        overlap*=valid
        if not overlap.any():
            continue
        count+=1
        area+=overlap;confidence+=overlap*score
        hit=overlap>0;box_hits+=hit;confidence_sum+=hit*score
        cx=((bx0+bx1)/2-x0)/dx;cy=((by0+by1)/2-y0)/dy
        ix,iy=int(math.floor(cx)),int(math.floor(cy))
        if 0<=ix<resolution and 0<=iy<resolution and valid[iy,ix]:
            centers[iy,ix]+=1
        sigma=config['gaussian_sigma_roi_fraction']*resolution
        distance=(xx-cx)**2+(yy-cy)**2
        gaussian+=score*np.exp(-distance/(2*sigma*sigma))*(distance<=(config['gaussian_support_sigma']*sigma)**2)*valid
    occupied=box_hits>0
    methods={'center_count':centers,'box_area':area,'confidence_area':confidence,'gaussian':gaussian,
             'product_occupancy':occupied.astype(float),
             'mean_confidence':np.divide(confidence_sum,box_hits,out=np.zeros_like(confidence_sum),where=box_hits>0)}
    return bounds,valid,methods,{'detection_count':count,'detected_products':int(occupied.any()),'observed_products':int(valid.any()),
                               'occupied_cell_count':int(occupied[valid].sum()),'observed_cell_count':int(valid.sum()),
                               'spatial_occupancy':float(occupied[valid].mean()) if valid.any() else None}


def hvq_grids(array, polygons, bounds, resolution, original_size, percentile):
    data=np.asarray(array).squeeze()
    if data.ndim!=2 or not np.isfinite(data).all():
        raise ValueError('Stored map must be a finite 2D array')
    height,width=data.shape
    native_roi=np.zeros(data.shape,bool)
    for polygon in polygons:
        scaled=[[x*width/original_size[0],y*height/original_size[1]] for x,y in polygon]
        native_roi|=polygon_mask(scaled,Size(width,height))
    yy,xx=np.nonzero(native_roi)
    x=(xx+.5)*original_size[0]/width;y=(yy+.5)*original_size[1]/height
    x0,y0,x1,y1=bounds
    gx=np.floor((x-x0)/(x1-x0)*resolution).astype(int);gy=np.floor((y-y0)/(y1-y0)*resolution).astype(int)
    selected=(gx>=0)&(gx<resolution)&(gy>=0)&(gy<resolution)
    bins=gy[selected]*resolution+gx[selected];values=data[yy[selected],xx[selected]]
    counts=np.bincount(bins,minlength=resolution*resolution).reshape(resolution,resolution)
    means=np.zeros(counts.shape);maximum=np.zeros(counts.shape);quantile=np.zeros(counts.shape)
    for index in np.unique(bins):
        samples=values[bins==index];iy,ix=divmod(int(index),resolution)
        means[iy,ix]=samples.mean();maximum[iy,ix]=samples.max();quantile[iy,ix]=np.percentile(samples,percentile)
    return {'mean':means,'max':maximum,'percentile':quantile},counts,[width,height]


def serialize(values, valid):
    return [float(value) if observed else None for value,observed in zip(values.ravel(),valid.ravel())]


def build_grid(record, region, resolution, config):
    polygons=region['polygons']
    bounds,mask,rt,stats=rt_grids(record['detections'],polygons,resolution,config)
    output={'item':record['item'],'product_id':record['product_id'],'view_id':record['camera'],
            'region_id':region['region_id'],'parent_region_id':region.get('parent_region_id'),
            'grid_width':resolution,'grid_height':resolution,'roi_bounds':bounds,'roi_polygons':polygons,
            'coverage_mask':mask.astype(int).ravel().tolist(),'model_version':record['models'],
            'mapping_status':'image_roi_only_physical_surface_unverified','aggregation_scope':'individual_product_single_camera',
            'source':record['source'],'source_image':record['image_path'],'image_sha256':record['image_sha256'],
            'original_size':record['original_size'],'stats':stats,
            'rt':{'status':'supported','values':{key:serialize(values,mask & (rt['product_occupancy']>0) if key=='mean_confidence' else mask) for key,values in rt.items()},
                  'valid_observation_counts_by_method':{'mean_confidence':((rt['product_occupancy']>0)&mask).astype(int).ravel().tolist()},
                  'region_value':stats['detected_products']/stats['observed_products'] if stats['observed_products'] else None,
                  'valid_observation_counts':mask.astype(int).ravel().tolist(),
                  'note':'Box extent and Gaussian density are visualization proxies, not defect masks.'},
            'hvq':{'status':'unsupported','reason':'saved_anomaly_map_missing','values':{},'valid_observation_counts':[0]*mask.size},
            'sample_status':'insufficient_sample' if stats['observed_products']<config['minimum_denominator'] else 'supported'}
    map_path=record.get('map_path')
    if map_path and Path(map_path).is_file():
        grids,counts,native=hvq_grids(np.load(map_path,allow_pickle=False),polygons,bounds,resolution,
                                     record['original_size'],config['percentile'])
        valid=(counts>0)&mask
        output['hvq']={'status':'supported','reason':None,'values':{key:serialize(values,valid) for key,values in grids.items()},
                       'region_value':float((grids['mean']*counts).sum()/counts.sum()) if counts.sum() else None,
                       'valid_observation_counts':valid.astype(int).ravel().tolist(),
                       'native_sample_counts':counts.ravel().tolist(),'native_map_size':native,
                       'note':'Only native map pixel centers contribute. Empty high-resolution bins stay unobserved.'}
    return output
