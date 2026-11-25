import { Canvas } from '@react-three/fiber'
import { Html, OrbitControls } from '@react-three/drei'
import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { ProductPart,SceneBoundary } from './Scene'
import { partsForItem,templateBounds } from './parts'
import { cssVar } from '../utils/tokens'

const CAMERAS:[number,number,number][]=[[-2.4,1.6,1.8],[2.4,1.6,1.8],[-2.4,1.6,-1.8],[2.4,1.6,-1.8],[0,3.2,.1]]
function IndustrialCamera({position,index,phase}:{position:[number,number,number];index:number;phase:number}){
  const geometry=useMemo(()=>{const p=new THREE.Vector3(...position);const a=[[-.5,.35,-.45],[.5,.35,-.45],[.5,.35,.45],[-.5,.35,.45]];const points:THREE.Vector3[]=[];for(let i=0;i<4;i++){points.push(p,new THREE.Vector3(...a[i] as [number,number,number]));points.push(new THREE.Vector3(...a[i] as [number,number,number]),new THREE.Vector3(...a[(i+1)%4] as [number,number,number]))}return new THREE.BufferGeometry().setFromPoints(points)},[position])
  useEffect(()=>()=>geometry.dispose(),[geometry])
  const quaternion=useMemo(()=>new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(new THREE.Vector3(0,.5,0),new THREE.Vector3(...position),new THREE.Vector3(0,1,0))),[position])
  return <group>
    {phase>=1&&<lineSegments geometry={geometry}><lineBasicMaterial color={cssVar(phase>=2?'--ok':'--faint')} transparent opacity={phase>=2?.27:.12}/></lineSegments>}
    <group position={position} quaternion={quaternion}>
      <mesh><boxGeometry args={[.38,.3,.34]}/><meshStandardMaterial color={cssVar('--material-metal')} roughness={.4} metalness={.65}/></mesh>
      <mesh position={[0,0,.24]} rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[.11,.13,.17,16]}/><meshStandardMaterial color={cssVar('--material-rubber')} roughness={.6}/></mesh>
    </group>
    <Html position={[position[0],position[1]+.28,position[2]]} center zIndexRange={[10,0]}><span className="whitespace-nowrap rounded border border-line bg-panel px-2 py-1 font-mono text-[10px] text-muted">C{index+1} · {phase<2?'대기':phase<3?'촬영 연출':'완료 연출'}</span></Html>
  </group>
}
export function IntroScene({phase}:{phase:number}){
  const parts=useMemo(()=>partsForItem('toothbrush'),[]),bounds=useMemo(()=>templateBounds(parts),[parts])
  return <SceneBoundary><Canvas style={{height:'100%'}} frameloop="demand" dpr={[1,1.25]} camera={{position:[5.6,4.3,6.7],fov:40}} gl={{powerPreference:'low-power'}} fallback={<p className="p-6 text-muted">WebGL 미지원. 아래 단계에서 검사 흐름을 확인하세요.</p>}>
    <color attach="background" args={[cssVar('--bg')]}/><ambientLight intensity={1.2}/><directionalLight position={[2,6,4]} intensity={2}/>
    <mesh position={[0,-.05,0]}><cylinderGeometry args={[1.25,1.35,.16,48]}/><meshStandardMaterial color={cssVar('--material-rubber')} roughness={.7} metalness={.3}/></mesh>
    <group position={[0,.8,0]} rotation={[Math.PI/2,0,Math.PI/5]} scale={.55}><group position={[-bounds.center.x,-bounds.center.y,-bounds.center.z]}>{parts.map(def=><ProductPart key={def.region_id} def={def} evidence={{status:'demonstration',message:'검사 부위 강조 시연',detail:'실제 검사 결과가 아닌 개념적 연출입니다.',row:undefined,mappedRow:undefined}} selected={phase>=6&&def.part_id==='bristle'} hovered={false} onSelect={()=>undefined} onHover={()=>undefined}/>)}</group></group>
    {phase>=1&&CAMERAS.map((position,index)=><IndustrialCamera key={index} position={position} index={index} phase={phase}/>)}
    {phase>=3&&<mesh position={[0,.67,0]}><boxGeometry args={[.7,.35,1.7]}/><meshBasicMaterial color={cssVar('--signal')} wireframe/></mesh>}
    {phase>=4&&<mesh position={[.35,.7,.3]} scale={[.35,.12,.45]}><sphereGeometry args={[1,16,12]}/><meshBasicMaterial color={cssVar('--warn')} transparent opacity={.35} depthWrite={false}/></mesh>}
    <OrbitControls enablePan={false} minDistance={5} maxDistance={12} maxPolarAngle={Math.PI/2.1}/>
  </Canvas></SceneBoundary>
}
