/** Portable Three.js adapter, shared with teammates as an ESM library. */
import * as T from 'three'
import {projectedGeometry,surfaceFieldTextures,mappedHotspots,type SurfaceFrame,type Hit} from './surfaceProjection'
import {surfaceMaterial} from './surfaceShader'
import defaults from '../../../config/surface_projection.json'
export {projectedGeometry,modelUV,sourceToModel,surfaceFieldTextures,mappedHotspots} from './surfaceProjection'
export {surfaceMaterial} from './surfaceShader'
export type {SurfaceFrame,SurfaceRegion,Projection,Hit} from './surfaceProjection'
export interface RegionMesh {mesh:T.Mesh;region_id:string;detail_id?:string}
export function collectRegionMeshes(root:T.Object3D):RegionMesh[]{
 const result:RegionMesh[]=[]
 root.traverse(object=>{
  const mesh=object as T.Mesh
  if(!mesh.isMesh||object.userData.displaySurfaceOverlay)return
  let owner:T.Object3D|null=object
  while(owner&&!owner.userData.region_id&&owner!==root){if(owner.userData.displaySurfaceOverlay)return;owner=owner.parent}
  if(typeof owner?.userData.region_id==='string')result.push({mesh,region_id:owner.userData.region_id,detail_id:object.userData.detail_id})
 })
 return result
}
export function applyDisplaySurface(root:T.Object3D,sources:RegionMesh[],frame:SurfaceFrame,opacity=defaults.default_opacity){
 if(frame.scope!=='visualization_only_approximate'||!frame.user_authorized_approximate_projection)throw new Error('Display projection authorization missing')
 root.updateMatrixWorld(true)
 const inverse=root.matrixWorld.clone().invert(),overlay=new T.Group();overlay.name='display-surface-overlay';overlay.userData.displaySurfaceOverlay=true
 const geometries:T.BufferGeometry[]=[],materials:T.ShaderMaterial[]=[],fields:NonNullable<ReturnType<typeof surfaceFieldTextures>>[]=[]
 let disposed=false
 const dispose=()=>{if(disposed)return;disposed=true;root.remove(overlay);geometries.forEach(value=>value.dispose());materials.forEach(value=>value.dispose());fields.forEach(value=>value.dispose())}
 const local=sources.map(source=>({ ...source,geometry:source.mesh.geometry.clone().applyMatrix4(inverse.clone().multiply(source.mesh.matrixWorld))}))
 const wholeBounds=new T.Box3();local.forEach(source=>{source.geometry.computeBoundingBox();wholeBounds.union(source.geometry.boundingBox!)})
 const hotspots:Hit[]=[]
 try{
  const whole=frame.regions.find(region=>region.region_id==='__whole_template__')
  const groups=new Map<string,typeof local>()
  for(const source of local){const list=groups.get(source.region_id)??[];list.push(source);groups.set(source.region_id,list)}
  for(const [regionId,parts] of groups){
   const candidate=frame.regions.find(region=>region.region_id===regionId)??whole;if(!candidate)continue
   const region=whole?{...candidate,region_id:regionId}:candidate,field=surfaceFieldTextures(region);if(!field)continue;fields.push(field)
   const bounds=whole?wholeBounds:new T.Box3();if(!whole)parts.forEach(part=>bounds.union(part.geometry.boundingBox!))
   const shaders=[surfaceMaterial(field,frame,region),surfaceMaterial(field,frame,region,true)];materials.push(...shaders)
   shaders.forEach(shader=>shader.uniforms.uOpacity.value=opacity)
   const projected:T.BufferGeometry[]=[]
   for(const part of parts){
    const filament=part.detail_id==='bristle-filaments'||part.mesh.userData.surface_role==='bristles'
    const geometry=projectedGeometry(part.geometry,bounds,frame.projection,filament?-1:frame.front_facing_cos_min)
    geometries.push(geometry);projected.push(geometry)
    const mesh=new T.Mesh(geometry,shaders[filament?1:0]);mesh.renderOrder=3;mesh.userData={displaySurfaceOverlay:true,region_id:regionId,source:frame.source,view:frame.view};overlay.add(mesh)
   }
   hotspots.push(...mappedHotspots(projected,bounds,frame,region))
  }
  root.add(overlay)
 }catch(error){dispose();throw error}
 finally{local.forEach(source=>source.geometry.dispose())}
 return {overlay,hotspots,setOpacity:(value:number)=>materials.forEach(material=>material.uniforms.uOpacity.value=T.MathUtils.clamp(value,0,1)),dispose}
}
