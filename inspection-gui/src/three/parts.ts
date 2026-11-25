import * as THREE from 'three'
import { PRODUCT_TEMPLATES, type MaterialKind, type ProductTemplate } from './catalog'
import {box,merge,moved,ring,frame,radial} from './geometry'
import {withModelDetails,type DetailDef} from './modelDetails'

export interface PartDef {
  category: string
  part_id: string
  region_id: string
  label: string
  position: [number, number, number]
  material: MaterialKind
  mapping: 'unverified'
  details?: DetailDef[]
  makeGeometry: () => THREE.BufferGeometry
}
const cache = new Map<string, readonly PartDef[]>()
function part(id:string,label:string,material:MaterialKind,makeGeometry:()=>THREE.BufferGeometry,position:[number,number,number]=[0,0,0]):PartDef {
  return {category:'',part_id:id,region_id:id,label,material,makeGeometry,position,mapping:'unverified'}
}

function generate(t:ProductTemplate):PartDef[]{
  const [w,h,d]=t.size;const m=t.material;const r=w/2
  switch(t.family){
    case 'brush': return [
      part('neck','목',m,()=>{const g=new THREE.CylinderGeometry(.065,.1,.7,16);g.translate(0,.12,0);return g}),
      part('bristle','헤드 / 칫솔모',m,()=>merge([moved(box(.47,.72,.16),0,.76,0),...Array.from({length:24},(_,i)=>{const g=new THREE.CylinderGeometry(.022,.025,.2,6);g.rotateX(Math.PI/2);g.translate((i%4-1.5)*.095,.51+Math.floor(i/4)*.09,.16);return g})])),
    ]
    case 'ring': return [part('body','환형 본체',m,()=>ring(r,t.hole ?? r*.5,h,t.form==='nut'?6:48)),
      ...(t.ribs ? [part('rim','리브 / 테두리',m,()=>radial(t.ribs!,r*.84,h/2,.07,.07,.13))]:[]),
      ...(t.form==='plug'?[part('collar','돌출 칼라',m,()=>moved(ring(r*.5,t.hole!,h*.6),0,h*.6,0))]:[])]
    case 'disc': return [part(t.form==='toy'?'surface':'body','본체',m,()=>{const g=new THREE.CylinderGeometry(t.form==='dome'?r*.75:r,r,h,48);g.scale(1,1,d/w);return g}),
      part(t.form==='toy'?'edge':'rim','외곽 테두리',t.form==='battery'?'metal':m,()=>moved(ring(r*.99,r*.89,.04),0,h/2,0)),
      ...(t.ribs?[part(t.form==='toy'?'joint':'ribs','리브 / 돌출부',m,()=>radial(t.ribs!,r*.87,h/2+.03,.06,.07,.11))]:[]),
      ...(t.form==='regulator'?[part('hub','중심 허브',m,()=>moved(new THREE.CylinderGeometry(.17,.21,.2,24),0,.2,0))]:[])]
    case 'frame':return [part('body','프레임',m,()=>frame(w,h,d,t.hole ?? .3)),
      ...(t.form==='rails'?[part('rails','측면 레일',m,()=>merge([moved(box(w,.13,.17),0,h/2,d/2),moved(box(w,.13,.17),0,h/2,-d/2)]))]:[]),
      ...(t.form==='pyramid'?[part('ribs','보강 대각 리브',m,()=>merge([box(w*.85,.12,.08).rotateY(Math.PI/4),box(w*.85,.12,.08).rotateY(-Math.PI/4)]))]:[]),
      ...(t.form==='sim'?[part('tab','연결 탭',m,()=>moved(box(.18,.06,d*.9),w*.53,0,0))]:[])]
    case 'block':return [part('body','본체',m,()=>box(w,h,d)),
      ...(t.form==='battery'?[part('contacts','접점','contact',()=>merge(Array.from({length:t.pins!},(_,i)=>moved(box(.17,.03,.15),(i-1)*.23,h/2,d*.4))))]:[]),
      ...(t.form==='brick'?[part('grooves','표면 홈',m,()=>merge(Array.from({length:4},(_,i)=>moved(box(w*.98,.02,.025),0,h/2,(i-1.5)*d*.2))))]:[])]
    case 'connector':return [part('housing','커넥터 하우징',m,()=>t.form==='switch'?new THREE.CylinderGeometry(r,r,h,32):box(w,h,d)),
      part('interface','체결 / 인터페이스',t.form==='jack'?'rubber':'metal',()=>{
        if(t.form==='jack'){const g=ring(.25,.15,.4);g.rotateZ(Math.PI/2);g.translate(-w*.6,0,0);return g}
        if(t.form==='terminal')return merge(Array.from({length:t.pins!},(_,i)=>moved(new THREE.CylinderGeometry(.1,.1,.04,16),(i-(t.pins!-1)/2)*w/(t.pins!+.2),h/2+.02,d*.2)))
        if(t.form==='switch')return moved(new THREE.CylinderGeometry(r*.9,r*.9,.1,32),0,h/2+.04,0)
        return moved(frame(w*.8,.2,d*.35,.16),0,.03,-d*.57)
      }),
      part('pins','전기 접점','contact',()=>merge(Array.from({length:t.pins??4},(_,i)=>moved(box(.045,.22,.07),(i-((t.pins??4)-1)/2)*w/((t.pins??4)+1),-h*.6,d*.24))))]
    case 'board':return [part('substrate','기판 / 패키지',m,()=>box(w,h,d)),
      part('contacts','핀 / 접점','contact',()=>merge(Array.from({length:t.pins??8},(_,i)=>{const side=i%2?1:-1;const x=(Math.floor(i/2)-(t.pins!/2-1)/2)*w/(t.pins!/2);return moved(box(.06,.05,.24),x,0,side*d*.57)}))),
      ...(t.form==='pcb'?[part('components','실장 부품','rubber',()=>merge([moved(box(.48,.13,.42),0,.1,0),moved(box(.25,.17,.3),-.45,.14,-.4),moved(new THREE.CylinderGeometry(.15,.15,.22,16),.4,.13,.4)]))]:[])]
    case 'bead':return [part('body','구슬 본체',m,()=>{
      const points=Array.from({length:19},(_,i)=>{const a=(i/18)*Math.PI;return new THREE.Vector2(Math.max(t.hole??.2,Math.sin(a)*r),Math.cos(a)*h/2)})
      return new THREE.LatheGeometry(points,40)
    })]
    case 'zipper':return [part('tape','양측 테이프','rubber',()=>merge([moved(box(.22,.04,d),-.31,0,0),moved(box(.22,.04,d),.31,0,0)])),part('teeth','교차 체인','metal',()=>merge(Array.from({length:t.ribs??18},(_,i)=>moved(box(.32,.13,.09),i%2?.08:-.08,.06,(i/(t.ribs!-1)-.5)*d)))),part('slider','슬라이더','metal',()=>moved(box(.45,.22,.38),0,.1,d*.25))]
  }
}
export const PARTS_BY_ITEM:Record<string,readonly PartDef[]>={}
export function partsForItem(item:string):readonly PartDef[]{
  if(!cache.has(item)){
    const parts=PRODUCT_TEMPLATES[item]?withModelDetails(PRODUCT_TEMPLATES[item],generate(PRODUCT_TEMPLATES[item])):[part('whole','외형 미정의 / 매핑 미확인','plastic',()=>box(1.5,.8,1))]
    for(const definition of parts){definition.category=item;if(definition.details)Object.freeze(definition.details);Object.freeze(definition)}
    cache.set(item,Object.freeze(parts))
  }
  return cache.get(item)!
}
for(const item of Object.keys(PRODUCT_TEMPLATES)) PARTS_BY_ITEM[item]=partsForItem(item)
export function templateBounds(parts:readonly PartDef[],context:readonly DetailDef[]=[]){
  const bounds=new THREE.Box3()
  for(const p of parts)for(const make of [p.makeGeometry,...(p.details??[]).map(detail=>detail.makeGeometry)]){const g=make();g.computeBoundingBox();bounds.union(g.boundingBox!.clone().translate(new THREE.Vector3(...p.position)));g.dispose()}
  for(const detail of context){const g=detail.makeGeometry();g.computeBoundingBox();bounds.union(g.boundingBox!);g.dispose()}
  const center=bounds.getCenter(new THREE.Vector3());const size=bounds.getSize(new THREE.Vector3());return {center,size,radius:size.length()/2}
}
