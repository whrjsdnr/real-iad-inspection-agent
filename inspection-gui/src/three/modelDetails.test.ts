import {describe,it,expect} from 'vitest'
import * as THREE from 'three'
import {PRODUCT_TEMPLATES} from './catalog'
import {partsForItem,templateBounds} from './parts'
import {rectangularShell} from './geometry'
import {brushContext} from './brushContext'

describe('detailed product meshes',()=>{
 it('keeps unobserved handle context outside inspection region IDs and includes it only in full-view bounds',()=>{
  const parts=partsForItem('toothbrush'),head=templateBounds(parts),full=templateBounds(parts,brushContext)
  expect(parts.map(part=>part.region_id)).toEqual(['neck','bristle'])
  expect(full.size.y).toBeGreaterThan(head.size.y)
  expect(brushContext.some(detail=>detail.detail_id.includes('ridges'))).toBe(true)
  for(const detail of brushContext){const g=detail.makeGeometry();expect(Array.from(g.getAttribute('position').array).every(Number.isFinite)).toBe(true);g.dispose()}
 })
 for(const category of Object.keys(PRODUCT_TEMPLATES))it(`${category}: details remain finite, bounded and tied to stable regions`,()=>{
  const parts=partsForItem(category),bounds=templateBounds(parts)
  let triangles=0,details=0
  const global=new THREE.Box3().setFromCenterAndSize(bounds.center,bounds.size)
  for(const part of parts){
   expect(part.part_id).toBe(part.region_id)
   expect(new Set(part.details?.map(d=>d.detail_id)??[]).size).toBe(part.details?.length??0)
   for(const factory of [part.makeGeometry,...(part.details??[]).map(d=>d.makeGeometry)]){
    const geometry=factory();geometry.computeBoundingBox()
    expect(Array.from(geometry.getAttribute('position').array).every(Number.isFinite)).toBe(true)
    expect(global.containsBox(geometry.boundingBox!.clone().translate(new THREE.Vector3(...part.position)))).toBe(true)
    triangles+=(geometry.index?.count??geometry.getAttribute('position').count)/3;geometry.dispose()
   }
   details+=part.details?.length??0
  }
  expect(details).toBeGreaterThan(0);expect(triangles).toBeLessThan(45000)
 })
 it('brush filament and connector-shell structures are genuinely geometric',()=>{
  const head=partsForItem('toothbrush').find(p=>p.region_id==='bristle')!
  const filaments=head.details!.find(d=>d.detail_id==='bristle-filaments')!.makeGeometry()
  expect(filaments.getAttribute('position').count).toBeGreaterThan(1000);filaments.dispose()
  const shell=rectangularShell(1,.4,.7,.04)
  const contour=(shell.parameters as {shapes?:THREE.Shape}).shapes
  expect(contour?.holes.length).toBe(1);shell.dispose()
  expect(partsForItem('usb').find(p=>p.region_id==='interface')?.details?.some(d=>d.detail_id==='gold-contact-fingers')).toBe(true)
 })
})

it('SIM template never shares toothbrush regions, details or mutable cached lists',()=>{
 for(let i=0;i<20;i++){
  const brush=partsForItem('toothbrush'),sim=partsForItem('sim_card_set')
  expect(sim.map(p=>p.region_id)).toEqual(['body','tab'])
  expect(sim.every(p=>p.category==='sim_card_set')).toBe(true)
  expect(brush.every(p=>p.category==='toothbrush')).toBe(true)
  expect(sim.flatMap(p=>p.details?.map(d=>d.detail_id)??[])).not.toContain('bristle-filaments')
  expect(Object.isFrozen(sim)).toBe(true)
  expect(sim.every(Object.isFrozen)).toBe(true)
  const first=sim[0].makeGeometry(),second=brush[0].makeGeometry()
  expect(first.uuid).not.toBe(second.uuid);expect(first.getAttribute('position').array).not.toBe(second.getAttribute('position').array)
  first.dispose();second.dispose()
 }
})

it('SIM body is a thin rectangular tray aperture rather than a circular part or toothbrush',()=>{
 const body=partsForItem('sim_card_set').find(p=>p.region_id==='body')!,geometry=body.makeGeometry()
 expect(geometry).toBeInstanceOf(THREE.ExtrudeGeometry)
 const extruded=geometry as THREE.ExtrudeGeometry,shape=extruded.parameters.shapes as THREE.Shape
 expect(shape.holes).toHaveLength(1)
 geometry.computeBoundingBox();const size=geometry.boundingBox!.getSize(new THREE.Vector3())
 expect(size.y).toBeLessThan(.12);expect(size.x).toBeGreaterThan(1.4);expect(size.z).toBeGreaterThan(1.8)
 expect(body.details?.some(d=>d.detail_id==='tray-edge-lip')).toBe(true)
 expect(body.details?.some(d=>d.detail_id==='aperture-collar')).toBe(false)
 geometry.dispose()
})
