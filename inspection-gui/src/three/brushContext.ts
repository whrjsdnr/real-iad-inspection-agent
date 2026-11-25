/** Unobserved template context, never an inspection region or a heat surface. */
import * as THREE from 'three'
import {box,merge,moved} from './geometry'
import type {DetailDef} from './modelDetails'
export const brushContext:readonly DetailDef[]=[
 {detail_id:'unobserved-handle-body',material:'plastic',makeGeometry:()=>moved(new THREE.CapsuleGeometry(.165,1.55,6,20).scale(1,1,.62),0,-1.1,0)},
 {detail_id:'unobserved-handle-grip',material:'rubber',makeGeometry:()=>moved(new THREE.CapsuleGeometry(.118,.84,5,16).scale(1,1,.14),0,-1.04,.105)},
 {detail_id:'unobserved-handle-ridges',material:'plastic',makeGeometry:()=>merge(Array.from({length:8},(_,i)=>moved(box(.17,.025,.014),0,-1.4+i*.1,.125)))},
]
