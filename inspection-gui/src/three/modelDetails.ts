/** Display-only construction details. Every child stays under its original region.
 * No new inspection region, measurement, defect location or ROI is inferred. */
import * as THREE from 'three'
import type {PartDef} from './parts'
import type {MaterialKind,ProductTemplate} from './catalog'
import {box,merge,moved,ring,radial,rectangularShell,lathe,screw,screwSlot} from './geometry'

export interface DetailDef {
 detail_id:string
 material:MaterialKind
 makeGeometry:()=>THREE.BufferGeometry
}
const detail=(detail_id:string,material:MaterialKind,makeGeometry:()=>THREE.BufferGeometry):DetailDef=>({detail_id,material,makeGeometry})
const at=(g:THREE.BufferGeometry,x:number,y:number,z:number)=>moved(g,x,y,z)
function set(parts:PartDef[],id:string,details:DetailDef[],replacement?:()=>THREE.BufferGeometry){
 const part=parts.find(p=>p.region_id===id)
 if(!part)return
 part.details=details
 if(replacement)part.makeGeometry=replacement
}
function trace(points:[number,number,number][],radius=.008){return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p))),12,radius,5,false)}
function corners(w:number,d:number,y:number,make:()=>THREE.BufferGeometry){return merge([-1,1].flatMap(x=>[-1,1].map(z=>at(make(),x*w,y,z*d))))}

export function withModelDetails(t:ProductTemplate,parts:PartDef[]):PartDef[]{
 const [w,h,d]=t.size,r=w/2,m=t.material
 if(t.family==='brush'){
  set(parts,'neck',[
   detail('neck-collar','rubber',()=>at(new THREE.CylinderGeometry(.082,.108,.085,20),0,-.16,0)),
   detail('neck-ridge','plastic',()=>at(box(.07,.46,.06),.025,.14,.05)),
  ],()=>{
   const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(0,-.2,0),new THREE.Vector3(.025,.1,0),new THREE.Vector3(0,.45,.015)])
   return new THREE.TubeGeometry(curve,20,.075,16,false)
  })
  set(parts,'bristle',[
   detail('head-inlay','rubber',()=>merge(Array.from({length:28},(_,tuft)=>
    at(new THREE.CylinderGeometry(.034,.034,.012,10).rotateX(Math.PI/2),(tuft%4-1.5)*.09,.49+Math.floor(tuft/4)*.09,.088)))),
   detail('bristle-filaments','rubber',()=>merge(Array.from({length:28},(_,tuft)=>Array.from({length:7},(_,filament)=>{
    const angle=filament/7*Math.PI*2, x=(tuft%4-1.5)*.09+Math.cos(angle)*.017, y=.49+Math.floor(tuft/4)*.09+Math.sin(angle)*.017
    const length=.20+(tuft%4===0||tuft%4===3?.025:0)
    return at(new THREE.CylinderGeometry(.006,.007,length,6).rotateX(Math.PI/2),x,y,.095+length/2)
   })).flat())),
   detail('head-back-seam','rubber',()=>at(new THREE.CapsuleGeometry(.19,.41,5,16).scale(1,1,.025),0,.76,-.08)),
  ],()=>at(new THREE.CapsuleGeometry(.225,.42,6,20).scale(1,1,.34),0,.76,0))
 }
 if(t.family==='connector'){
  const housing=parts.find(p=>p.region_id==='housing')!
  housing.details=[
   detail('housing-parting-line','rubber',()=>merge([at(box(w*.96,.012,d*.96),0,h*.27,0),at(box(w*.96,.012,d*.96),0,-h*.27,0)])),
   detail('mould-grip-ribs',m,()=>merge(Array.from({length:6},(_,i)=>at(box(.018,.025,d*.86),(i-2.5)*w*.12,h/2+.008,0)))),
  ]
  if(t.form==='usb'||t.form==='adapter'){
   set(parts,'interface',[
    detail('connector-tongue','board',()=>at(box(w*.62,.07,d*.36),0,-.015,-d*.48)),
    detail('gold-contact-fingers','contact',()=>merge(Array.from({length:t.pins??4},(_,i)=>at(box(w*.08,.012,d*.23),(i-((t.pins??4)-1)/2)*w*.14,.03,-d*.53)))),
    detail('shell-retention-slots','rubber',()=>merge([-1,1].map(x=>at(box(w*.14,.012,d*.11),x*w*.22,.142,-d*.53)))),
   ],()=>at(rectangularShell(w*.86,.3,d*.45,.038),0,.03,-d*.55))
  }else if(t.form==='jack'){
   set(parts,'interface',[
    detail('socket-retention-ring','metal',()=>at(ring(.27,.205,.035).rotateZ(Math.PI/2),-w*.74,0,0)),
    detail('socket-inner-sleeve','contact',()=>at(ring(.18,.135,.32).rotateZ(Math.PI/2),-w*.58,0,0)),
   ])
  }else if(t.form==='terminal'){
   set(parts,'interface',[
    detail('cross-screw-slots','rubber',()=>merge(Array.from({length:t.pins!},(_,i)=>at(screwSlot(.1,.04),(i-(t.pins!-1)/2)*w/(t.pins!+.2),h/2+.02,d*.2)))),
    detail('wire-entry-bores','rubber',()=>merge(Array.from({length:t.pins!},(_,i)=>at(new THREE.CylinderGeometry(.07,.07,.02,16).rotateX(Math.PI/2),(i-(t.pins!-1)/2)*w/(t.pins!+.2),0,-d*.51)))),
    detail('terminal-separators',m,()=>merge(Array.from({length:t.pins!-1},(_,i)=>at(box(.025,h*.35,d*.85),(i-(t.pins!-2)/2)*w/(t.pins!+.2),h*.52,0)))),
   ])
  }else if(t.form==='switch'){
   set(parts,'interface',[
    detail('rocker-face','plastic',()=>at(box(w*.56,.07,d*.55).rotateX(.16),0,h/2+.09,0)),
    detail('power-marking','ceramic',()=>merge([at(ring(.1,.075,.009),0,h/2+.145,-.08),at(box(.025,.01,.13),0,h/2+.153,-.08)])),
   ])
  }
  set(parts,'pins',[detail('pin-solder-shoulders','metal',()=>merge(Array.from({length:t.pins??4},(_,i)=>at(box(.085,.04,.11),(i-((t.pins??4)-1)/2)*w/((t.pins??4)+1),-h*.5,d*.24))))])
 }
 if(t.family==='board'){
  const chip=t.form==='chip'
  set(parts,'substrate',[
   detail('board-edge-laminate',chip?'rubber':'contact',()=>at(box(w*.96,.012,d*.96),0,-h*.32,0)),
   ...(chip?[detail('pin-one-dimple','plastic',()=>at(new THREE.CylinderGeometry(.04,.04,.008,16),-w*.36,h*.52,-d*.23))]:[
    detail('mounting-eyelets','contact',()=>corners(w*.4,d*.4,h/2+.015,()=>ring(.075,.045,.02,20))),
    detail('copper-traces','contact',()=>merge(Array.from({length:6},(_,i)=>trace([[-w*.4,.045,-d*.33+i*.17],[-w*.19,.045,-d*.33+i*.17],[w*.07,.045,-d*.22+i*.14],[w*.38,.045,-d*.22+i*.14]],.008)))),
    detail('smd-passives','metal',()=>merge(Array.from({length:8},(_,i)=>at(box(.065,.055,.1),(i%4-1.5)*.2,.075,-.55+Math.floor(i/4)*1.05)))),
   ]),
  ])
  set(parts,'contacts',[
   detail('pin-knees','metal',()=>merge(Array.from({length:t.pins??8},(_,i)=>{const side=i%2?1:-1;const x=(Math.floor(i/2)-((t.pins??8)/2-1)/2)*w/((t.pins??8)/2);return at(box(.06,.12,.055),x,-.035,side*d*.66)}))),
  ])
  if(!chip)set(parts,'components',[
   detail('chip-contact-legs','contact',()=>merge(Array.from({length:12},(_,i)=>at(box(.035,.035,.09),(Math.floor(i/2)-2.5)*.075,.075,(i%2?1:-1)*.24)))),
   detail('capacitor-cap','metal',()=>at(new THREE.CylinderGeometry(.13,.13,.012,24),.4,.246,.4)),
   detail('port-socket','metal',()=>at(rectangularShell(.3,.22,.35,.025),-.45,.1,-.7)),
  ])
 }
 if(t.family==='disc'){
  const bodyId=t.form==='toy'?'surface':'body'
  set(parts,bodyId,[
   detail('sidewall-turning-grooves',m,()=>merge(Array.from({length:4},(_,i)=>{const g=ring(r*.999,r*.977,.009);g.scale(1,1,d/w);return at(g,0,-h*.33+i*h*.2,0)}))),
   ...(t.form==='battery'?[
    detail('positive-terminal','metal',()=>at(new THREE.CylinderGeometry(r*.79,r*.8,.025,48),0,h/2+.01,0)),
    detail('terminal-isolator','rubber',()=>at(ring(r*.88,r*.82,.015),0,h/2-.008,0)),
    detail('positive-engraving','rubber',()=>merge([at(box(.2,.003,.025),0,h/2+.024,0),at(box(.025,.003,.2),0,h/2+.024,0)])),
   ]:[]),
   ...(t.form==='cap'?[
    detail('inner-lip',m,()=>at(ring(r*.94,r*.85,.07),0,-h*.48,0)),
    detail('upper-concentric-relief',m,()=>at(ring(r*.65,r*.63,.015),0,h/2+.012,0)),
   ]:[]),
   ...(t.form==='pill'?[
    detail('pill-score-line','rubber',()=>at(box(w*.66,.003,.018),0,h/2+.008,0)),
   ]:[]),
   ...(t.form==='toy'?[
    detail('bun-seam','rubber',()=>at(ring(r*.985,r*.95,.055),0,0,0)),
    detail('top-seed-relief','ceramic',()=>merge(Array.from({length:14},(_,i)=>{const a=i*2.4,rr=r*.72*Math.sqrt((i+1)/15);return at(box(.035,.015,.08).rotateY(a),Math.cos(a)*rr,h/2+.015,Math.sin(a)*rr)}))),
   ]:[]),
   ...(t.form==='stick'||t.form==='dome'?[
    detail('wood-growth-rings','wood',()=>merge(Array.from({length:4},(_,i)=>at(ring(r*(.22+i*.16),r*(.22+i*.16)-.008,.003),0,h/2+.006,0)))),
   ]:[]),
  ])
  if(t.form==='battery')parts.find(p=>p.region_id==='body')!.makeGeometry=()=>lathe([[0,-h/2],[r*.93,-h/2],[r,-h*.28],[r,h*.23],[r*.96,h/2],[0,h/2]])
  if(t.form==='cap')parts.find(p=>p.region_id==='body')!.makeGeometry=()=>lathe([[0,h/2],[r*.94,h/2],[r,h*.32],[r,-h/2],[r*.88,-h/2],[r*.88,h*.2],[0,h*.2]])
 }
 if(t.family==='ring'){
  set(parts,'body',[
   detail('bore-lip',m,()=>at(ring((t.hole??r*.5)+.035,t.hole??r*.5,.025),0,h/2+.008,0)),
   detail('outer-rim-relief',m,()=>at(ring(r*.98,r*.93,.018),0,h/2+.008,0)),
   ...(t.form==='nut'?[detail('nut-face-inset','plastic',()=>at(ring(r*.79,(t.hole??r*.5)+.07,.012,6),0,h/2+.018,0))]:[]),
   ...(t.form==='tape'?[detail('paper-core','plastic',()=>ring((t.hole??.6)+.035,t.hole??.6,h*.97)),detail('winding-layers','wood',()=>merge(Array.from({length:4},(_,i)=>at(ring(r*(.84+i*.035),r*(.84+i*.035)-.006,.003),0,h/2+.005,0))))]:[]),
  ])
  if(t.form==='smooth')parts.find(p=>p.region_id==='body')!.makeGeometry=()=>new THREE.TorusGeometry((r+(t.hole??.5))/2,(r-(t.hole??.5))/2,16,64).rotateX(Math.PI/2)
  if(t.form==='plug')set(parts,'collar',[detail('collar-ribbing',m,()=>radial(12,(t.hole??.28)+.075,h*.73,.025,h*.3,.035))])
 }
 if(t.family==='frame'){
  set(parts,'body',[
   ...(t.form==='sim'?[detail('tray-edge-lip',m,()=>at(rectangularShell(w*.974,d*.979,.012,.045).rotateX(-Math.PI/2),0,h/2+.008,0))]:[detail('aperture-collar',m,()=>at(ring((t.hole??.3)+.035,t.hole??.3,.025),0,h/2+.01,0))]),
   ...(t.form!=='sim'?[
    detail('fastener-heads','metal',()=>corners(w*.38,d*.36,h/2+.015,()=>screw(.045,.025))),
    detail('fastener-slots','rubber',()=>corners(w*.38,d*.36,h/2+.015,()=>screwSlot(.045,.025))),
   ]:[detail('sim-stamped-relief','contact',()=>merge([at(box(w*.88,.016,.025),0,h/2,-d*.42),at(box(.025,.016,d*.8),-w*.43,h/2,0)]))]),
  ])
  if(t.form==='sim')parts.find(p=>p.region_id==='body')!.makeGeometry=()=>rectangularShell(w,d,h,.13).rotateX(-Math.PI/2)
  if(t.form==='rails')set(parts,'rails',[detail('rail-end-stops','rubber',()=>corners(w*.41,d*.5,h*.59,()=>box(.14,.07,.15)))])
 }
 if(t.family==='block'){
  set(parts,'body',[
   detail('mould-edge-seam',m,()=>at(box(w*.99,.008,d*.99),0,h*.15,0)),
   ...(t.form==='battery'?[
    detail('battery-pouch-seal','plastic',()=>merge([at(box(w*.96,.025,.025),0,h/2,d*.45),at(box(.025,.025,d*.9),-w*.47,h/2,0),at(box(.025,.025,d*.9),w*.47,h/2,0)])),
    detail('battery-contact-recess','rubber',()=>at(box(w*.65,.04,.14),0,h*.32,d*.45)),
   ]:[]),
   ...(t.form==='eraser'?[detail('eraser-mould-strip','plastic',()=>at(box(w*.78,.008,d*.92),0,h/2+.005,0))]:[]),
   ...(t.form==='brick'?[detail('wood-grain','wood',()=>merge(Array.from({length:7},(_,i)=>trace([[-w*.45,h/2+.008,(i-3)*d*.115],[-w*.1,h/2+.009,(i-3)*d*.115+.018],[w*.45,h/2+.008,(i-3)*d*.115]],.004))))]:[]),
  ])
 }
 if(t.family==='bead')set(parts,'body',[
  detail('bore-rims','wood',()=>merge([at(ring((t.hole??.22)+.04,t.hole??.22,.025),0,h*.48,0),at(ring((t.hole??.22)+.04,t.hole??.22,.025),0,-h*.48,0)])),
 ])
 if(t.family==='zipper'){
  set(parts,'teeth',[detail('interlocking-tooth-crowns','metal',()=>merge(Array.from({length:t.ribs??18},(_,i)=>at(box(.17,.06,.09),i%2?.11:-.11,.145,(i/((t.ribs??18)-1)-.5)*d))))])
  set(parts,'slider',[
   detail('slider-top-yoke','metal',()=>at(rectangularShell(.29,.35,.08,.055).rotateX(Math.PI/2),0,.28,d*.25)),
   detail('zipper-pull-tab','metal',()=>at(rectangularShell(.23,.55,.045,.05).rotateX(Math.PI/2).rotateY(.15),0,.34,d*.25+.32)),
  ])
  set(parts,'tape',[detail('tape-edge-stitching','plastic',()=>merge(Array.from({length:20},(_,i)=>[-1,1].map(side=>at(box(.028,.013,.04),side*.31,.03,(i/19-.5)*d))).flat()))])
 }
 return parts
}
