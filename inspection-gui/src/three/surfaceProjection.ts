/** User-authorized display projection. Source values are never changed. */
import * as T from 'three'
import {gridPixels,type SpatialRaster} from './spatialGrid'
export type Axis='x'|'y'|'z'
export interface Projection {axes:[Axis,Axis];normal_sign:number;quarter_turns:number}
export interface SurfaceRegion extends SpatialRaster {region_id:string;label:string;source_bounds:[number,number,number,number];sample_products:number;unknown_products:number}
export interface SurfaceFrame {
 item:string;view:string;source:'ground_truth'|'rt'|'hvq';product_id:string|null;split:string|null;regions:SurfaceRegion[];
 version:string;scope:string;projection:Projection;front_facing_cos_min:number;zero_signal_opacity:number;
 hotspot_limit:number;hotspot_candidate_limit:number;user_authorized_approximate_projection:boolean
 render:{contour_levels:[number,number,number];contour_width:number;fade_start:number;fade_end:number;low_signal_alpha:number;high_signal_alpha:number;shape_shading:number;bristle_min_alpha:number}
}
export type Hit={region_id:string;label:string;index:number;column:number;row:number;value:number|null;count:number;point:[number,number,number]}
export function modelUV(point:T.Vector3,bounds:T.Box3,projection:Projection):[number,number]{
 const [a,b]=projection.axes
 let u=(point[a]-bounds.min[a])/Math.max(1e-9,bounds.max[a]-bounds.min[a])
 let v=1-(point[b]-bounds.min[b])/Math.max(1e-9,bounds.max[b]-bounds.min[b])
 for(let turn=0;turn<((projection.quarter_turns%4)+4)%4;turn++)[u,v]=[v,1-u]
 return [T.MathUtils.clamp(u,0,1),T.MathUtils.clamp(v,0,1)]
}
export function sourceToModel(u:number,v:number,bounds:T.Box3,projection:Projection):T.Vector3{
 for(let turn=0;turn<((projection.quarter_turns%4)+4)%4;turn++)[u,v]=[1-v,u]
 const [a,b]=projection.axes,normal=(['x','y','z'] as Axis[]).find(axis=>axis!==a&&axis!==b)!
 const point=new T.Vector3();point[a]=T.MathUtils.lerp(bounds.min[a],bounds.max[a],u)
 point[b]=T.MathUtils.lerp(bounds.min[b],bounds.max[b],1-v)
 point[normal]=projection.normal_sign>0?bounds.max[normal]:bounds.min[normal]
 return point
}
export function projectedGeometry(source:T.BufferGeometry,bounds:T.Box3,projection:Projection,minCos:number){
 const temporary=source.index?source.toNonIndexed():source.clone(),position=temporary.getAttribute('position'),normal=temporary.getAttribute('normal')
 const p:number[]=[],n:number[]=[],uv:number[]=[],a=new T.Vector3(),b=new T.Vector3(),c=new T.Vector3()
 const axis=(['x','y','z'] as Axis[]).find(axis=>!projection.axes.includes(axis))!
 for(let i=0;i<position.count;i+=3){
  a.fromBufferAttribute(position,i);b.fromBufferAttribute(position,i+1);c.fromBufferAttribute(position,i+2)
  const facing=b.clone().sub(a).cross(c.clone().sub(a)).normalize()[axis]*projection.normal_sign
  if(facing<minCos)continue
  for(let j=0;j<3;j++){
   const point=new T.Vector3().fromBufferAttribute(position,i+j);p.push(point.x,point.y,point.z)
   n.push(normal.getX(i+j),normal.getY(i+j),normal.getZ(i+j));uv.push(...modelUV(point,bounds,projection))
  }
 }
 temporary.dispose()
 const result=new T.BufferGeometry();result.setAttribute('position',new T.Float32BufferAttribute(p,3));result.setAttribute('normal',new T.Float32BufferAttribute(n,3));result.setAttribute('uv',new T.Float32BufferAttribute(uv,2));result.computeBoundingBox();result.computeBoundingSphere()
 return result
}
export function surfaceTexture(region:SurfaceRegion,zeroOpacity:number){
 if(!region.values.some((value,index)=>value!==null&&value>0&&region.valid_observation_counts[index]>0&&region.coverage_mask[index]))return null
 const pixels=gridPixels(region,1)
 for(let index=0;index<region.values.length;index++)if(region.values[index]===0)pixels[index*4+3]=Math.round(pixels[index*4+3]*zeroOpacity)
 const texture=new T.DataTexture(pixels,region.grid_width,region.grid_height,T.RGBAFormat,T.UnsignedByteType)
 texture.flipY=false;texture.colorSpace=T.SRGBColorSpace;texture.minFilter=texture.magFilter=T.NearestFilter;texture.needsUpdate=true
 return texture
}
/** Linear interpolation is display-only and excludes unknown samples by weight. */
export function surfaceFieldTextures(region:SurfaceRegion){
 const values=region.values.filter((value,index):value is number=>value!==null&&region.valid_observation_counts[index]>0&&!!region.coverage_mask[index])
 const min=values.length?Math.min(...values):0,max=values.length?Math.max(...values):0
 if(!(max>0))return null
 const field=new Uint8Array(region.grid_width*region.grid_height*4),coverage=new Uint8Array(field.length)
 region.values.forEach((value,index)=>{
  if(value===null||region.valid_observation_counts[index]<=0||!region.coverage_mask[index])return
  const normalized=max>min?(value-min)/(max-min):1
  field[index*4]=Math.round(normalized*255);field[index*4+3]=255
  coverage.set([255,255,255,255],index*4)
 })
 const signal=new T.DataTexture(field,region.grid_width,region.grid_height,T.RGBAFormat,T.UnsignedByteType)
 signal.minFilter=signal.magFilter=T.LinearFilter;signal.flipY=false;signal.needsUpdate=true
 const mask=new T.DataTexture(coverage,region.grid_width,region.grid_height,T.RGBAFormat,T.UnsignedByteType)
 mask.minFilter=mask.magFilter=T.NearestFilter;mask.flipY=false;mask.needsUpdate=true
 return {signal,mask,min,max,dispose:()=>{signal.dispose();mask.dispose()}}
}
export function mappedHotspots(geometries:T.BufferGeometry[],bounds:T.Box3,frame:SurfaceFrame,region:SurfaceRegion):Hit[]{
 const material=new T.MeshBasicMaterial({side:T.DoubleSide}),meshes=geometries.map(geometry=>new T.Mesh(geometry,material))
 meshes.forEach(mesh=>mesh.updateMatrixWorld(true))
 const axis=(['x','y','z'] as Axis[]).find(axis=>!frame.projection.axes.includes(axis))!
 const direction=new T.Vector3();direction[axis]=-frame.projection.normal_sign
 const distance=Math.max(1,bounds.getSize(new T.Vector3()).length()),ray=new T.Raycaster(),hits:Hit[]=[]
 const ranked=region.values.map((value,index)=>({value,index})).filter((cell):cell is {value:number;index:number}=>cell.value!==null&&cell.value>0&&region.valid_observation_counts[cell.index]>0&&!!region.coverage_mask[cell.index]).sort((a,b)=>b.value-a.value)
 for(const cell of ranked.slice(0,frame.hotspot_candidate_limit)){
  const column=cell.index%region.grid_width,row=Math.floor(cell.index/region.grid_width)
  const origin=sourceToModel((column+.5)/region.grid_width,(row+.5)/region.grid_height,bounds,frame.projection)
  origin[axis]+=frame.projection.normal_sign*distance;ray.set(origin,direction)
  const intersection=ray.intersectObjects(meshes,false)[0]
  if(!intersection)continue
  // Keep ranked markers spatially separate, without altering any source value.
  if(hits.some(hit=>Math.abs(hit.column-column)+Math.abs(hit.row-row)<=2))continue
  hits.push({region_id:region.region_id,label:region.label,index:cell.index,column,row,value:cell.value,count:region.valid_observation_counts[cell.index],point:intersection.point.toArray() as [number,number,number]})
  if(hits.length>=frame.hotspot_limit)break
 }
 material.dispose();return hits
}
