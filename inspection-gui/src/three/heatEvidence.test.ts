import {it,expect} from 'vitest'
import {mappedHeatRow,regionEvidence} from './heatEvidence'
import type {StatsResponse} from '../types'
const stats:StatsResponse={item:'toothbrush',metric:'part_miss_rate',group_by:['part_id'],rows:[{group:{part_id:'handle'},num:0,den:20,rate:0,reason:null,stat_key:'k'}],order:'desc',limit:10,min_denominator:1,model_version:'real',mapping_version:null,definition_version:'metrics-v1'}
it('never projects a real rate without mapping provenance',()=>{
 expect(mappedHeatRow(stats,'handle')).toBeUndefined()
 expect(mappedHeatRow({...stats,mapping_verified:true},'handle')).toBeUndefined()
 expect(mappedHeatRow({...stats,mapping_version:'roi-v2',mapping_verified:true},'handle')?.rate).toBe(0)
})
it('does not attribute unknown 0/1 statistics to the handle',()=>{
 const unknown={...stats,rows:[{...stats.rows[0],group:{part_id:'unknown'},num:0,den:1,rate:0}]}
 expect(regionEvidence(unknown,'handle').status).toBe('unmapped')
 expect(regionEvidence(unknown,'handle').row).toBeUndefined()
 expect(mappedHeatRow({...unknown,mapping_verified:true,mapping_version:'v'},'unknown')).toBeUndefined()
})
it('separates loading, failed request, absent samples and missing mapping',()=>{
 expect(regionEvidence(stats,'handle',{loading:true}).status).toBe('loading')
 expect(regionEvidence(stats,'handle',{error:'offline'}).status).toBe('api_error')
 expect(regionEvidence({...stats,rows:[]},'handle').status).toBe('no_samples')
 expect(regionEvidence(stats,'handle').status).toBe('unverified')
 expect(regionEvidence(stats,'handle').row?.den).toBe(20)
 const verified={...stats,mapping_verified:true,mapping_version:'v'}
 expect(regionEvidence(verified,'handle').mappedRow?.rate).toBe(0)
 expect(regionEvidence(verified,'handle',{error:'offline'}).mappedRow).toBeUndefined()
 expect(regionEvidence(verified,'handle',{loading:true}).mappedRow).toBeUndefined()
})
it('rejects invalid denominator even with mapping proof',()=>{
 const invalid={...stats,mapping_verified:true,mapping_version:'v',rows:[{...stats.rows[0],den:NaN}]}
 expect(regionEvidence(invalid,'handle').status).toBe('no_denominator')
 expect(mappedHeatRow(invalid,'handle')).toBeUndefined()
})
it('explicit fixtures can demonstrate colors but unmapped/zero denominator stays neutral',()=>{
 expect(mappedHeatRow(stats,'handle',true)?.rate).toBe(0)
 expect(mappedHeatRow(stats,'unknown',true)).toBeUndefined()
 expect(mappedHeatRow({...stats,rows:[{...stats.rows[0],den:0,rate:null}]},'handle',true)).toBeUndefined()
})
