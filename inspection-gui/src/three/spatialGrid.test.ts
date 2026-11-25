import {it,expect,vi} from 'vitest'
import {gridPixels,gridTexture,nativeCell,regionSnapshot,spatialTexture,type SpatialGrid} from './spatialGrid'
const grid={grid_width:2,grid_height:2,roi_bounds:[10,20,30,40],values:[0,1,null,99],
 coverage_mask:[1,1,1,0],valid_observation_counts:[1,1,0,1],aggregation_method:'product_occupancy'} as SpatialGrid
it('keeps zero detections visible but missing/outside pixels transparent',()=>{
 const pixels=gridPixels(grid,.5)
 expect(pixels[3]).toBe(128);expect(pixels[7]).toBe(128)
 expect(pixels[11]).toBe(0);expect(pixels[15]).toBe(0)
})
it('recovers native cursor cells and refuses coordinates outside ROI',()=>{
 expect(nativeCell(grid,11,21)?.value).toBe(0)
 expect(nativeCell(grid,31,21)).toBeNull()
 expect(nativeCell(grid,11,39)?.observed).toBe(0)
})
it('requires validated geometry/UV correspondence and releases a texture explicitly',()=>{
 expect(spatialTexture(grid,null)).toBeNull()
 expect(spatialTexture(grid,{verified:true,version:'v2'},'v1')).toBeNull()
 const texture=spatialTexture(grid,{verified:true,version:'v1'},'v1')!
 const dispose=vi.spyOn(texture,'dispose');texture.dispose();expect(dispose).toHaveBeenCalledTimes(1)
})
it('updates real spatial texture buffers without filling missing cells or recoloring the entire region',()=>{
 const first=gridTexture(grid,.5),changed=gridTexture({...grid,values:[1,0,null,99]},.8)
 expect(first.image.width).toBe(2);expect(first.image.height).toBe(2)
 expect(Array.from(first.image.data.slice(0,3))).not.toEqual(Array.from(first.image.data.slice(4,7)))
 expect(changed.image.data[3]).toBe(204);expect(changed.image.data[11]).toBe(0)
 expect(first.uuid).not.toBe(changed.uuid)
 const disposed=[vi.spyOn(first,'dispose'),vi.spyOn(changed,'dispose')];first.dispose();changed.dispose()
 expect(disposed.every(spy=>spy.mock.calls.length===1)).toBe(true)
})
it('builds legacy comparison only from the same RT parent-region evidence',()=>{
 const actual={...grid,status:'supported',model:'rt',region_id:'bristle',parent_region_id:null,mapping_version:'v1',
  stats:{observed_products:1,detected_products:1},product_id:'p',view_id:'C1'} as SpatialGrid
 expect(regionSnapshot(actual).rows[0]).toMatchObject({group:{part_id:'bristle'},num:1,den:1,rate:1})
 expect(regionSnapshot({...actual,parent_region_id:'bristle'}).rows).toEqual([])
 expect(regionSnapshot({...actual,model:'hvq'}).rows).toEqual([])
 expect(regionSnapshot(null).mapping_verified).toBe(false)
})
