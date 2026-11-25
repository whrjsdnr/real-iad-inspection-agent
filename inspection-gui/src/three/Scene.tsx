import { Html, OrbitControls, ContactShadows } from '@react-three/drei'
import { Canvas, useThree } from '@react-three/fiber'
import { Component, Suspense, memo, useEffect, useId, useLayoutEffect, useMemo, useRef, type ReactNode } from 'react'
import * as THREE from 'three'
import { useStore } from '../store'
import type {MaterialKind} from './catalog'
import { formatNumDen, formatRate } from '../utils/heat'
import { partsForItem, templateBounds, type PartDef } from './parts'
import { cssVar } from '../utils/tokens'
import { USE_FIXTURE } from '../config'
import { regionEvidence } from './heatEvidence'
import {useScenePreferences} from './scenePreferences'
import {heatAppearance} from './heatAppearance'
import {StudioEnvironment} from './StudioEnvironment'
import {modelViewDirection} from './modelView'
import {releaseDetachedRenderer,rendererKey} from './rendererLifetime'
import {usePartHeatmap} from './partHeatmapStore'
import {brushContext} from './brushContext'
import type {DetailDef} from './modelDetails'
import {regionSnapshot,type SpatialGrid} from './spatialGrid'
import {ProjectedRegion} from './ProjectedRegion'

export class SceneBoundary extends Component<{children:ReactNode},{failed:boolean}> {
  state={failed:false}
  static getDerivedStateFromError(){return {failed:true}}
  render(){return this.state.failed?<div role="status" className="p-6 text-muted">3D 렌더링을 사용할 수 없습니다. 부위 목록과 검사 상세는 계속 사용할 수 있습니다.</div>:this.props.children}
}
const SURFACES={plastic:[.46,.04],metal:[.28,.85],rubber:[.88,0],board:[.65,.12],wood:[.78,0],ceramic:[.24,.02],contact:[.3,.78]} as const

function CategoryFrameReset({item}:{item:string}){
 const {gl,invalidate}=useThree()
 useLayoutEffect(()=>{gl.autoClear=true;gl.renderLists.dispose();gl.clear(true,true,true);invalidate()},[item,gl,invalidate])
 return null
}
function CameraFit({radius,item}:{radius:number;item:string}){
  const {camera,controls,invalidate,size}=useThree()
  useEffect(()=>{
    const ctl=controls as unknown as {target:THREE.Vector3;update:()=>void}|undefined
    const vertical=THREE.MathUtils.degToRad(36/2),horizontal=Math.atan(Math.tan(vertical)*size.width/size.height)
    const distance=radius/Math.sin(Math.min(vertical,horizontal))*1.1
    const set=(pose:string)=>{camera.position.copy(new THREE.Vector3(...modelViewDirection(item,pose)).normalize().multiplyScalar(distance));camera.lookAt(0,0,0);ctl?.target.set(0,0,0);ctl?.update();invalidate()}
    set('reset')
    const onPose=(event:Event)=>set((event as CustomEvent<string>).detail)
    window.addEventListener('inspection:camera',onPose)
    return ()=>window.removeEventListener('inspection:camera',onPose)
  },[camera,controls,invalidate,radius,item,size.width,size.height])
  return null
}
function Surface({geometry,material,heat,muted,name}:{name?:string;geometry:THREE.BufferGeometry;material:MaterialKind;heat:ReturnType<typeof heatAppearance>;muted:boolean}){
 const [roughness,metalness]=SURFACES[material]
 return <>
  <mesh geometry={geometry} name={name} userData={{detail_id:name}} castShadow receiveShadow>
   <meshStandardMaterial color={cssVar(muted?'--material-muted':`--material-${material}`)} roughness={muted ? .85 : roughness} metalness={muted?0:metalness} envMapIntensity={material==='metal'||material==='contact' ? .9 : .5}/>
  </mesh>
  {heat.enabled&&<mesh geometry={geometry} renderOrder={3} raycast={()=>undefined}>
    <meshBasicMaterial color={heat.color!} transparent={heat.opacity<1} opacity={heat.opacity} toneMapped={false} depthWrite={false} polygonOffset polygonOffsetFactor={-1} polygonOffsetUnits={-1}/>
  </mesh>}
 </>
}

function ContextSurface({definition}:{definition:DetailDef}){
 const geometry=useMemo(()=>definition.makeGeometry(),[definition])
 useEffect(()=>()=>geometry.dispose(),[geometry])
 return <Surface geometry={geometry} material={definition.material} heat={{enabled:false,color:null,opacity:0}} muted={false}/>
}

export const ProductPart = memo(function ProductPart({def,evidence,selected,hovered,onSelect,onHover,wholeBounds}:{wholeBounds?:THREE.Box3;def:PartDef;evidence:ReturnType<typeof regionEvidence>;selected:boolean;hovered:boolean;onSelect:()=>void;onHover:(v:boolean)=>void}){
  const row=evidence.mappedRow
  const mode=useScenePreferences(s=>s.mode),intensity=useScenePreferences(s=>s.intensity)
  const surfaces=useMemo(()=>[{id:def.region_id,material:def.material,geometry:def.makeGeometry()},...(def.details??[]).map(detail=>({id:detail.detail_id,material:detail.material,geometry:detail.makeGeometry()}))],[def])
  useEffect(()=>()=>{surfaces.forEach(s=>s.geometry.dispose());document.body.style.cursor='default'},[surfaces])
  const geometry=surfaces[0].geometry,heat=heatAppearance(row,mode,intensity)
  const edges=useMemo(()=>selected||hovered||heat.enabled?new THREE.EdgesGeometry(geometry,28):null,[geometry,selected,hovered,heat.enabled])
  useEffect(()=>()=>edges?.dispose(),[edges])
  const labelPosition=useMemo(()=>{geometry.computeBoundingBox();const b=geometry.boundingBox!,c=b.getCenter(new THREE.Vector3());return [c.x,b.max.y+.13,c.z] as [number,number,number]},[geometry])
  return <group name={`${def.category}:${def.region_id}`} position={def.position} userData={{category:def.category,region_id:def.region_id}} onClick={e=>{e.stopPropagation();if(mode!=='surface')onSelect()}} onPointerOver={e=>{e.stopPropagation();onHover(true);document.body.style.cursor='pointer'}} onPointerOut={()=>{onHover(false);document.body.style.cursor='default'}}>
    {surfaces.map(surface=><Surface key={`${def.category}:${def.region_id}:${surface.id}`} geometry={surface.geometry} name={surface.id} material={surface.material} heat={heat} muted={mode==='heatmap'&&!heat.enabled}/>)}
    {mode==='surface'&&<ProjectedRegion item={def.category} regionId={def.region_id} surfaces={surfaces} wholeBounds={wholeBounds}/>}
    {edges&&<lineSegments geometry={edges} renderOrder={4}><lineBasicMaterial color={cssVar(selected?'--text':'--signal')} toneMapped={false} transparent opacity={selected ? .95 : hovered ? .65 : .32}/></lineSegments>}
    {mode!=='surface'&&(hovered||selected)&&<Html center position={labelPosition} zIndexRange={[30,0]}><div className="pointer-events-none min-w-44 rounded-lg border border-line bg-panel px-3 py-2 shadow-xl"><strong className="block text-xs text-tx">{def.label}</strong>{row?<><span className="mt-1 block font-mono text-lg font-semibold" style={{color:heat.color??'var(--text)'}}>{formatRate(row.rate)}</span><span className="font-mono text-[11px] text-muted">{formatNumDen(row.num,row.den)} · 분자 / 분모</span><p className="mt-1 max-w-64 text-[11px] text-muted">{evidence.detail}</p></>:<div className="mt-1 max-w-64 text-[11px] text-muted"><p>{evidence.message}</p><p className="mt-1">{evidence.detail}</p>{evidence.status==='unverified'&&evidence.row&&<p className="mt-1 font-mono">저장 집계 {formatRate(evidence.row.rate)} · {formatNumDen(evidence.row.num,evidence.row.den)}</p>}</div>}</div></Html>}
  </group>
})

function CategoryScene({item,snapshot}:{item:string;snapshot?:SpatialGrid|null}){
  const rawStats=useStore(s=>s.stats),selected=useStore(s=>s.selectedPart),hovered=useStore(s=>s.hoveredPart),select=useStore(s=>s.selectPart),hover=useStore(s=>s.hoverPart)
  const reviewLoading=useStore(s=>s.statsLoading),reviewError=useStore(s=>s.statsError)
  const signal=usePartHeatmap()
  const fullBrush=useScenePreferences(s=>s.fullBrush)
  const signalMode=signal.mode==='model_signals'
  const stats=snapshot!==undefined?regionSnapshot(snapshot?.item===item?snapshot:null):signalMode?(signal.data?.item===item?signal.data:null):(rawStats?.item===item?rawStats:null)
  const loading=snapshot!==undefined?false:signalMode?signal.loading:reviewLoading,error=snapshot!==undefined?null:signalMode?signal.error:reviewError
  const parts=useMemo(()=>partsForItem(item),[item])
  const context=item==='toothbrush'&&fullBrush?brushContext:[]
  const bounds=useMemo(()=>templateBounds(parts,item==='toothbrush'&&fullBrush?brushContext:[]),[parts,item,fullBrush])
  const wholeBounds=useMemo(()=>new THREE.Box3().setFromCenterAndSize(bounds.center,bounds.size),[bounds])
  const renderer=useRef<THREE.WebGLRenderer|null>(null)
  const identity=useId()
  useLayoutEffect(()=>()=>{
    const owned=renderer.current
    if(owned)queueMicrotask(()=>{
      if(!owned.domElement.isConnected){
        Reflect.deleteProperty(owned.domElement,'__inspectionScene')
        releaseDetachedRenderer(owned)
      }
    })
  },[])
  const floor=-bounds.size.y/2-.055,stageRadius=Math.max(.7,Math.max(bounds.size.x,bounds.size.z)*.72)
  return <SceneBoundary><div className="h-full w-full" data-category-scene={item} data-renderer-owner={identity}><Canvas
    onCreated={({gl,scene})=>{
      renderer.current=gl
      gl.domElement.dataset.inspectionCategory=item
      gl.domElement.dataset.rendererOwner=identity
      if(import.meta.env.DEV)Object.defineProperty(gl.domElement,'__inspectionScene',{value:scene,configurable:true})
    }} style={{height:'100%',width:'100%'}} frameloop="demand" camera={{position:[4,3,5],fov:36,near:.05,far:100}} dpr={[1,1.5]} gl={{antialias:true,powerPreference:'low-power'}} fallback={<div className="p-4 text-muted">WebGL 미지원 — 부위 목록을 사용하세요.</div>}>
    <color attach="background" args={[cssVar('--bg')]} />
    <Suspense fallback={null}>
      <StudioEnvironment/><CategoryFrameReset item={item}/>
      <ambientLight intensity={.6}/><hemisphereLight intensity={.6} color={cssVar('--text')} groundColor={cssVar('--material-rubber')}/><directionalLight position={[4,7,5]} intensity={2.1}/><directionalLight position={[-4,2,-2]} intensity={.9}/>
      <group key={item} name={`inspection-product:${item}`} userData={{category:item,inspectionProduct:true}} position={[-bounds.center.x,-bounds.center.y,-bounds.center.z]}>{parts.map(def=><ProductPart key={`${item}:${def.region_id}`} def={def} wholeBounds={wholeBounds} evidence={regionEvidence(stats,def.region_id,{loading,error,fixture:USE_FIXTURE})} selected={selected===def.part_id} hovered={hovered===def.part_id} onSelect={()=>{if(useStore.getState().filters.item===item)select(selected===def.part_id?null:def.part_id)}} onHover={on=>{if(useStore.getState().filters.item===item)hover(on?def.part_id:null)}}/>) }<group name="unobserved-template-context" userData={{inspectionRegion:false}}>{context.map(definition=><ContextSurface key={definition.detail_id} definition={definition}/>)}</group></group>
      <group position={[0,floor,0]}>
        <mesh><cylinderGeometry args={[stageRadius,stageRadius*1.04,.09,48]}/><meshStandardMaterial color={cssVar('--material-stage')} metalness={.65} roughness={.36}/></mesh>
        <mesh position={[0,.047,0]} rotation={[-Math.PI/2,0,0]}><ringGeometry args={[stageRadius*.95,stageRadius*.96,64]}/><meshBasicMaterial color={cssVar('--signal')} transparent opacity={.55} toneMapped={false}/></mesh>
      </group>
      <ContactShadows key={`${item}:${fullBrush}`} frames={1} position={[0,floor+.05,0]} opacity={.35} scale={stageRadius*3} blur={2} far={bounds.size.y+1}/>
      <OrbitControls makeDefault enableDamping dampingFactor={.12} minDistance={bounds.radius*1.2} maxDistance={bounds.radius*10}/><CameraFit radius={bounds.radius} item={item}/>
    </Suspense>
  </Canvas></div></SceneBoundary>
}

/** Never reconcile different product categories inside the same Canvas/root. */
export function Scene({snapshot}:{snapshot?:SpatialGrid|null}={}){
 const category=useStore(state=>state.filters.item)
 return <CategoryScene key={rendererKey(category)} item={category} snapshot={snapshot}/>
}
