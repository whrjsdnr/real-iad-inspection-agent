import {it,expect} from 'vitest'
import {validateGroundTruth,canCompareGroundTruth,truthRaster,type GroundTruthRaster} from './groundTruth'
import {gridTexture} from './spatialGrid'
const files=import.meta.glob('../../../team_integration_kit/samples/gt_*.json',{eager:true,import:'default'})
const actual=Object.entries(files).find(([path])=>path.endsWith('/gt_toothbrush.json'))?.[1] as GroundTruthRaster|undefined
it.skipIf(!actual)('uses the preserved Train NG counts in the actual shared response, not a replicated scalar',()=>{
 validateGroundTruth(actual!,'toothbrush','C1')
 expect(actual!.known_products).toBe(335);expect(new Set(actual!.defect_rate).size).toBeGreaterThan(1)
 const texture=gridTexture(truthRaster(actual!),.7);expect(texture.image.width).toBe(64);texture.dispose()
 expect(canCompareGroundTruth(actual!)).toBe(false) // aggregate is not one product
 expect(()=>validateGroundTruth({...actual!,split:'test'},'toothbrush','C1')).toThrow()
})
it('requires a matching product, view, split and image proof before model/mask overlay',()=>{
 const record={product_id:'toothbrush/p',known_products:1,split:'train',comparison:{status:'verified_same_product_view_split_source_image',
  model_cache_split:'train',mask_split:'train',source_image_sha256:'a'.repeat(64)}} as GroundTruthRaster
 expect(canCompareGroundTruth(record)).toBe(true)
 expect(canCompareGroundTruth({...record,known_products:0})).toBe(false)
 expect(canCompareGroundTruth({...record,comparison:{...record.comparison!,model_cache_split:'test'}})).toBe(false)
})
