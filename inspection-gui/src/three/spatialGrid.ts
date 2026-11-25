import {DataTexture,RGBAFormat,UnsignedByteType,NearestFilter,SRGBColorSpace} from 'three'
import {rateToColor} from '../utils/heat'
export interface SpatialGrid {
 item:string;product_id:string;view_id:string;region_id:string;parent_region_id:string|null
 grid_width:number;grid_height:number;roi_bounds:[number,number,number,number];roi_polygons:[number,number][][]
 original_size:[number,number];image_url:string;status:string;reason:string|null;values:(number|null)[]
 valid_observation_counts:number[];coverage_mask:number[];native_map_size?:[number,number]
 aggregation_method:string;sample_status:string;model:'rt'|'hvq';mapping_status:string
 mapping_version:string
 region_value?:number|null
 stats:{detection_count:number;detected_products:number;observed_products:number;spatial_occupancy:number|null;occupied_cell_count:number;observed_cell_count:number}
}
/** Legacy region-color comparison from this exact saved product, never a map. */
export function regionSnapshot(grid:SpatialGrid|null){
 const eligible=grid?.status==='supported'&&grid.model==='rt'&&!grid.parent_region_id&&grid.stats.observed_products>0
 return {mapping_verified:!!eligible,mapping_version:grid?.mapping_version??'',
  source_scope:'single_product_image_roi_box_signal',rows:eligible?[{
   group:{part_id:grid.region_id},num:grid.stats.detected_products,den:grid.stats.observed_products,
   rate:grid.stats.detected_products/grid.stats.observed_products,reason:null,
   stat_key:`spatial-region:${grid.product_id}:${grid.view_id}:${grid.region_id}`,
  }]:[]}
}
export type SpatialRaster=Pick<SpatialGrid,'grid_width'|'grid_height'|'values'|'valid_observation_counts'|'coverage_mask'|'aggregation_method'>
export function gridRange(grid:SpatialRaster):[number,number]{
 const values=grid.values.filter((value,index):value is number=>value!==null&&Number.isFinite(value)&&grid.valid_observation_counts[index]>0&&!!grid.coverage_mask[index])
 if(!values.length)return [0,0]
 if(grid.aggregation_method==='product_occupancy')return [0,1]
 return [Math.min(...values),Math.max(...values)]
}
export function gridPixels(grid:SpatialRaster,opacity:number){
 const [min,max]=gridRange(grid),pixels=new Uint8ClampedArray(grid.grid_width*grid.grid_height*4)
 for(let index=0;index<grid.values.length;index++){
  const value=grid.values[index]
  if(value===null||!Number.isFinite(value)||!grid.coverage_mask[index]||!(grid.valid_observation_counts[index]>0))continue
  const color=rateToColor(max>min?(value-min)/(max-min):0)
  const rgb=[1,3,5].map(offset=>parseInt(color.slice(offset,offset+2),16))
  pixels.set([...rgb,Math.round(Math.min(1,Math.max(0,opacity))*255)],index*4)
 }
 return pixels
}
export function nativeCell(grid:SpatialGrid,x:number,y:number){
 const [x0,y0,x1,y1]=grid.roi_bounds
 const column=Math.floor((x-x0)/(x1-x0)*grid.grid_width),row=Math.floor((y-y0)/(y1-y0)*grid.grid_height)
 if(column<0||row<0||column>=grid.grid_width||row>=grid.grid_height)return null
 const index=row*grid.grid_width+column
 return {column,row,index,value:grid.values[index],observed:grid.valid_observation_counts[index]??0,covered:!!grid.coverage_mask[index]}
}
/** UV existence alone never enables a physical surface projection. */
export function canProjectSurface(mapping:{verified:boolean;version:string}|null,geometryVersion:string|undefined){
 return !!mapping?.verified&&!!mapping.version&&mapping.version===geometryVersion
}
/** Image-plane texture; this function never authorizes product-surface mapping. */
export function gridTexture(grid:SpatialRaster,opacity=1){
 const texture=new DataTexture(gridPixels(grid,opacity),grid.grid_width,grid.grid_height,RGBAFormat,UnsignedByteType)
 texture.colorSpace=SRGBColorSpace
 texture.minFilter=NearestFilter;texture.magFilter=NearestFilter;texture.needsUpdate=true
 return texture
}
export function spatialTexture(grid:SpatialGrid,verifiedMapping:{verified:boolean;version:string}|null,geometryVersion?:string){
 if(!canProjectSurface(verifiedMapping,geometryVersion))return null
 return gridTexture(grid) // owner must dispose on replacement/unmount
}
