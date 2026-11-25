import {useEffect,useMemo} from 'react'
import {Html} from '@react-three/drei'
import {useThree} from '@react-three/fiber'
import * as T from 'three'
import {useSurfaceStore} from './surfaceStore'
import {projectedGeometry,surfaceFieldTextures,mappedHotspots,type Hit} from './surfaceProjection'
import {surfaceMaterial} from './surfaceShader'
import {cssVar} from '../utils/tokens'
import {MIN_DENOMINATOR} from '../config'

export function ProjectedRegion({item,regionId,surfaces,wholeBounds}:{item:string;regionId:string;surfaces:{id:string;geometry:T.BufferGeometry}[];wholeBounds?:T.Box3}){
 const invalidate=useThree(state=>state.invalidate)
 const raw=useSurfaceStore(s=>s.data),opacity=useSurfaceStore(s=>s.opacity),selected=useSurfaceStore(s=>s.selected)
 const register=useSurfaceStore(s=>s.register),select=useSurfaceStore(s=>s.select)
 const frame=raw?.item===item?raw:null
 const region=useMemo(()=>{const own=frame?.regions.find(region=>region.region_id===regionId);if(own)return own;const whole=frame?.regions.find(region=>region.region_id==='__whole_template__');return whole?{...whole,region_id:regionId}:undefined},[frame,regionId])
 const bounds=useMemo(()=>{if(frame?.regions.some(region=>region.region_id==='__whole_template__')&&wholeBounds)return wholeBounds;const box=new T.Box3();for(const surface of surfaces){surface.geometry.computeBoundingBox();box.union(surface.geometry.boundingBox!)}return box},[surfaces,frame,wholeBounds])
 const geometries=useMemo(()=>frame&&region?surfaces.map(surface=>projectedGeometry(surface.geometry,bounds,frame.projection,surface.id==='bristle-filaments'?-1:frame.front_facing_cos_min)):[],[frame,region,surfaces,bounds])
 useEffect(()=>()=>geometries.forEach(geometry=>geometry.dispose()),[geometries])
 const fields=useMemo(()=>region?surfaceFieldTextures(region):null,[region])
 useEffect(()=>()=>fields?.dispose(),[fields])
 const material=useMemo(()=>fields&&frame&&region?surfaceMaterial(fields,frame,region):null,[fields,frame,region])
 const filamentMaterial=useMemo(()=>fields&&frame&&region?surfaceMaterial(fields,frame,region,true):null,[fields,frame,region])
 useEffect(()=>()=>material?.dispose(),[material])
 useEffect(()=>()=>filamentMaterial?.dispose(),[filamentMaterial])
 useEffect(()=>{for(const shader of [material,filamentMaterial])if(shader)shader.uniforms.uOpacity.value=opacity;invalidate()},[material,filamentMaterial,opacity,invalidate])
 const hotspots=useMemo(()=>frame&&region&&fields?mappedHotspots(geometries,bounds,frame,region):[],[frame,region,fields,geometries,bounds])
 useEffect(()=>{if(!frame||!region)return;register(regionId,hotspots);return ()=>register(regionId,[])},[frame,region,regionId,register,hotspots])
 if(!frame||!region)return null
 const picked=selected?.region_id===regionId?selected:null
 const radius=bounds.getSize(new T.Vector3()).length()*.012
 const marker=picked??hotspots[0]
 const normal=new T.Vector3();normal[(['x','y','z'] as const).find(axis=>!frame.projection.axes.includes(axis))!]=frame.projection.normal_sign
 const orientation=new T.Quaternion().setFromUnitVectors(new T.Vector3(0,0,1),normal)
 return <group name={`display-surface:${item}:${regionId}`} userData={{displaySurfaceOverlay:true,projection:frame.scope,mapping_version:frame.version,source:frame.source,view:frame.view}}>
  {material&&geometries.map((geometry,index)=><mesh key={index} geometry={geometry} renderOrder={3} onClick={event=>{
   event.stopPropagation();if(!event.uv)return
   const column=Math.min(region.grid_width-1,Math.max(0,Math.floor(event.uv.x*region.grid_width)))
   const row=Math.min(region.grid_height-1,Math.max(0,Math.floor(event.uv.y*region.grid_height))),index=row*region.grid_width+column
   const point=event.object.worldToLocal(event.point.clone()).toArray() as [number,number,number]
   select({region_id:regionId,label:region.label,index,column,row,value:region.values[index]??null,count:region.valid_observation_counts[index]??0,point} as Hit)
  }}>
   <primitive object={surfaces[index].id==='bristle-filaments'?(filamentMaterial??material):material} attach="material"/>
  </mesh>)}
  {marker&&<group position={marker.point} quaternion={orientation}>
   <mesh position={[0,0,radius]} renderOrder={5} raycast={()=>undefined}><ringGeometry args={[radius*1.55,radius*1.9,32]}/><meshBasicMaterial color={cssVar('--signal')} toneMapped={false}/></mesh>
   <mesh position={[0,0,radius]} raycast={()=>undefined}><sphereGeometry args={[radius*.35,10,8]}/><meshBasicMaterial color={cssVar('--text')} toneMapped={false}/></mesh>
   <Html occlude center position={[radius*3,radius*3,radius*2]} zIndexRange={[35,0]}><div className="pointer-events-none relative ml-20 -mt-8 min-w-40 border-l-2 border-signal bg-panel/95 px-3 py-2 shadow-xl backdrop-blur-sm"><span className="absolute -left-9 top-6 h-px w-9 origin-right rotate-[-35deg] bg-signal"/><span className="font-mono text-[9px] tracking-widest text-signal">H01 / {frame.view}</span><strong className="mt-1 block text-xs text-tx">{marker.label}</strong><p className="mt-1 font-mono text-lg text-tx">{marker.value===null?'—':frame.source==='ground_truth'?`${(marker.value*100).toFixed(1)}%`:marker.value.toFixed(3)}</p><p className="text-[10px] text-muted">관측 {marker.count} · {marker.count<MIN_DENOMINATOR?'표본 부족':frame.source==='ground_truth'?'마스크 위치 빈도':'유효 관측'} · ({marker.column},{marker.row})</p></div></Html>
  </group>}
 </group>
}
