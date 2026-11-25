import type {SpatialRaster} from './spatialGrid'
export interface GroundTruthRaster {
 item:string;view:string;split:string;product_id:string|null;grid_width:number;grid_height:number;
 defect_rate:(number|null)[];known_count:number[];coverage_mask:number[];known_products:number;
 comparison:{status:string;model_cache_split?:string;mask_split?:string;source_image_sha256?:string}|null
}
export function validateGroundTruth(data:GroundTruthRaster,item:string,view:string,product?:string){
 if(data.item!==item||data.view!==view||data.split!=='train'||(product&&data.product_id!==product))throw new Error('마스크 응답의 품목/제품/시점/분할 불일치')
 if(data.grid_width!==64||data.grid_height!==64||data.defect_rate?.length!==4096||data.known_count?.length!==4096||data.coverage_mask?.length!==4096)throw new Error('마스크 격자 형상 불일치')
 return data
}
export function canCompareGroundTruth(data:GroundTruthRaster){
 const match=data.comparison
 return !!data.product_id&&data.known_products>0&&data.split==='train'&&match?.status==='verified_same_product_view_split_source_image'&&
  match.model_cache_split===data.split&&match.mask_split===data.split&&/^[a-f0-9]{64}$/.test(match.source_image_sha256??'')
}
export function truthRaster(data:GroundTruthRaster,absolute=false):SpatialRaster{
 return {grid_width:64,grid_height:64,values:data.defect_rate,valid_observation_counts:data.known_count,
  coverage_mask:data.coverage_mask,aggregation_method:absolute?'product_occupancy':'mask_relative'}
}
