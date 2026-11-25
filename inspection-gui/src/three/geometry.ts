import * as THREE from 'three'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'

export const box = (w:number,h:number,d:number) => new RoundedBoxGeometry(w,h,d,2,Math.min(w,h,d)*.12)
export function merge(geos: THREE.BufferGeometry[]) {
  const temporary=geos.map(g => {const n=g.index ? g.toNonIndexed() : g.clone();g.dispose();return n})
  const result = mergeGeometries(temporary,false)
  temporary.forEach(g=>g.dispose())
  // mergeGeometries copies attributes; release intermediate CPU buffers too.
  if (!result) throw new Error('Incompatible template geometry')
  return result
}
export function moved(g: THREE.BufferGeometry,x:number,y:number,z:number) {return g.translate(x,y,z)}
export function ring(radius:number,hole:number,depth:number,sides=48) {
  const shape=new THREE.Shape()
  for(let i=0;i<=sides;i++){const a=i/sides*Math.PI*2;const r=radius; if(i===0)shape.moveTo(Math.cos(a)*r,Math.sin(a)*r);else shape.lineTo(Math.cos(a)*r,Math.sin(a)*r)}
  const inner=new THREE.Path();inner.absarc(0,0,hole,0,Math.PI*2,true);shape.holes.push(inner)
  const g=new THREE.ExtrudeGeometry(shape,{depth,bevelEnabled:true,bevelSegments:1,bevelSize:Math.min(depth*.1,.025),bevelThickness:Math.min(depth*.1,.025),steps:1,curveSegments:32})
  g.translate(0,0,-depth/2);g.rotateX(-Math.PI/2);return g
}
export function frame(w:number,h:number,d:number,hole:number){
  const shape=new THREE.Shape();shape.moveTo(-w/2,-d/2);shape.lineTo(w/2,-d/2);shape.lineTo(w/2,d/2);shape.lineTo(-w/2,d/2);shape.closePath()
  const cut=new THREE.Path();cut.absarc(0,0,hole,0,Math.PI*2,true);shape.holes.push(cut)
  const g=new THREE.ExtrudeGeometry(shape,{depth:h,bevelEnabled:false,curveSegments:32});g.translate(0,0,-h/2);g.rotateX(-Math.PI/2);return g
}

export function radial(n:number,r:number,y:number,w:number,h:number,d:number){return merge(Array.from({length:n},(_,i)=>{const a=i/n*Math.PI*2;const g=box(w,h,d);g.rotateY(-a);g.translate(Math.cos(a)*r,y,Math.sin(a)*r);return g}))}

/** Rectangular connector opening: a real bore, not a dark painted rectangle. */
export function rectangularShell(w:number,h:number,d:number,wall:number){
  const contour=(width:number,height:number,reverse=false)=>{
    const shape=new THREE.Shape()
    const points=[[-width/2,-height/2],[width/2,-height/2],[width/2,height/2],[-width/2,height/2]]
    if(reverse)points.reverse()
    points.forEach(([x,y],i)=>i?shape.lineTo(x,y):shape.moveTo(x,y));shape.closePath();return shape
  }
  const shape=contour(w,h);shape.holes.push(contour(w-wall*2,h-wall*2,true))
  const g=new THREE.ExtrudeGeometry(shape,{depth:d,bevelEnabled:true,bevelSegments:2,bevelSize:wall*.12,bevelThickness:wall*.12,curveSegments:8})
  return g.translate(0,0,-d/2)
}
export function lathe(profile:[number,number][],segments=48){return new THREE.LatheGeometry(profile.map(([r,y])=>new THREE.Vector2(r,y)),segments)}
export function screw(radius:number,depth:number){
  return merge([new THREE.CylinderGeometry(radius,radius*.94,depth,16),moved(ring(radius*.82,radius*.67,depth*.12,24),0,depth*.48,0)])
}
export function screwSlot(radius:number,depth:number){return merge([moved(box(radius*1.3,depth*.1,radius*.16),0,depth*.51,0),moved(box(radius*.16,depth*.1,radius*1.3),0,depth*.51,0)])}
