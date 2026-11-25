import {expect,it} from 'vitest'
import {gridTexture,nativeCell,type SpatialGrid} from './spatialGrid'
const evidence=import.meta.glob('../../../reports/gui_validation/spatial-urgent/toothbrush-C1-32-api-response.json',{eager:true,import:'default'})
const saved=Object.values(evidence)[0] as SpatialGrid|undefined
it.skipIf(!saved)('turns the actual saved toothbrush C1 ASGI response into a nonuniform texture at verified box cells',()=>{
 const grid=saved!
 const texture=gridTexture(grid,.7)
 expect(texture.image.width).toBe(32);expect(texture.image.height).toBe(32)
 const first=nativeCell(grid,525.1854,199.9611)!
 const second=nativeCell(grid,704.8127,580.0580)!
 expect([first.column,first.row]).toEqual([17,7]);expect([second.column,second.row]).toEqual([26,26])
 expect(first.value).toBeGreaterThan(second.value!)
 const pixel=(index:number)=>Array.from(texture.image.data.slice(index*4,index*4+3))
 expect(pixel(first.index)).not.toEqual(pixel(0));expect(pixel(first.index)).not.toEqual(pixel(second.index))
 texture.dispose()
})
