import { describe,it,expect } from 'vitest'
import { PRODUCT_TEMPLATES } from './catalog'
import { partsForItem,templateBounds } from './parts'

describe('product family geometry',()=>{
  for(const category of Object.keys(PRODUCT_TEMPLATES))it(`${category}: stable regions, finite bounded geometry and triangle budget`,()=>{
    const parts=partsForItem(category)
    expect(partsForItem(category)).toBe(parts)
    expect(new Set(parts.map(p=>p.region_id)).size).toBe(parts.length)
    let triangles=0
    for(const p of parts){const g=p.makeGeometry();const positions=g.getAttribute('position');expect(Array.from(positions.array).every(Number.isFinite)).toBe(true);triangles+=(g.index?.count??positions.count)/3;expect(p.region_id).toBe(p.part_id);g.dispose()}
    const bounds=templateBounds(parts);expect(bounds.radius).toBeGreaterThan(0);expect(bounds.radius).toBeLessThan(5);expect(triangles).toBeLessThan(45000)
  })
  it('removes the unobserved handle and preserves remaining IDs',()=>{
    expect(partsForItem('toothbrush').map(p=>p.part_id)).toEqual(['neck','bristle'])
    expect(partsForItem('toy').map(p=>p.part_id)).toEqual(['surface','edge','joint'])
  })
  it('unrecognized categories remain unmapped',()=>expect(partsForItem('unsupported')[0].mapping).toBe('unverified'))
})
