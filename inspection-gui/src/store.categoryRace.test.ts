import {beforeEach,it,expect,vi} from 'vitest'
import type {CaseResponse,MetricsResponse,StatsResponse} from './types'
vi.mock('./api/client',()=>({checkHealth:vi.fn(),listItems:vi.fn(),queryErrorStatsClient:vi.fn(),computeInspectionMetricsClient:vi.fn(),getCaseEvidenceClient:vi.fn()}))
import {useStore} from './store'
import {queryErrorStatsClient,computeInspectionMetricsClient,getCaseEvidenceClient} from './api/client'
function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(r=>{resolve=r});return {promise,resolve}}
const initial=useStore.getState()
const stats=(item:string):StatsResponse=>({item,metric:'part_miss_rate',group_by:['part_id'],rows:[],order:'desc',limit:10,min_denominator:1,model_version:'real',mapping_version:null,definition_version:'metrics-v1'})
beforeEach(()=>{vi.clearAllMocks();useStore.setState({...initial,filters:{...initial.filters,item:'toothbrush'},statsCache:{},cardsCache:{}},true)})
it('immediately clears old-category data and rejects late case/metric responses',async()=>{
 const oldCases=deferred<{data:CaseResponse;source:'api'}>(),oldCards=deferred<{data:MetricsResponse;source:'api'}>(),newStats=deferred<{data:StatsResponse;source:'api'}>()
 vi.mocked(getCaseEvidenceClient).mockReturnValue(oldCases.promise)
 vi.mocked(computeInspectionMetricsClient).mockReturnValue(oldCards.promise)
 vi.mocked(queryErrorStatsClient).mockReturnValue(newStats.promise)
 useStore.setState({stats:stats('toothbrush'),selectedPart:'bristle',hoveredPart:'bristle'})
 const casesPromise=useStore.getState().loadCases('old-category-key'),cardsPromise=useStore.getState().loadMetricCards()
 useStore.getState().setItem('sim_card_set')
 expect(useStore.getState().stats).toBeNull();expect(useStore.getState().selectedPart).toBeNull();expect(useStore.getState().hoveredPart).toBeNull()
 oldCases.resolve({source:'api',data:{cases:[],count:9,limit:20,filters:{item:'toothbrush'},model_version:'real',mapping_version:null,definition_version:'metrics-v1'}})
 oldCards.resolve({source:'api',data:{filters:{item:'toothbrush'},metrics:{} as MetricsResponse['metrics'],model_version:'real',mapping_version:null,definition_version:'metrics-v1'}})
 await Promise.all([casesPromise,cardsPromise])
 expect(useStore.getState().cases).toBeNull();expect(useStore.getState().metricCards).toBeNull()
 newStats.resolve({source:'api',data:stats('sim_card_set')});await Promise.resolve();await Promise.resolve()
 expect(useStore.getState().stats?.item).toBe('sim_card_set')
})
it('cannot overwrite the latest category after rapid A→B→A→B switches',async()=>{
 const reads=Array.from({length:3},()=>deferred<{data:StatsResponse;source:'api'}>())
 reads.forEach(read=>vi.mocked(queryErrorStatsClient).mockReturnValueOnce(read.promise))
 useStore.getState().setItem('sim_card_set');useStore.getState().setItem('toothbrush');useStore.getState().setItem('sim_card_set')
 reads[1].resolve({source:'api',data:stats('toothbrush')});await Promise.resolve();expect(useStore.getState().stats).toBeNull()
 reads[2].resolve({source:'api',data:stats('sim_card_set')});await Promise.resolve();await Promise.resolve()
 reads[0].resolve({source:'api',data:stats('sim_card_set')});await Promise.resolve()
 expect(useStore.getState().filters.item).toBe('sim_card_set');expect(useStore.getState().stats?.item).toBe('sim_card_set')
})
it('explicit statistics refresh bypasses cached rows and surfaces API failure',async()=>{
 vi.mocked(queryErrorStatsClient).mockResolvedValue({source:'api',data:stats('toothbrush')})
 await useStore.getState().loadStats()
 expect(vi.mocked(queryErrorStatsClient)).toHaveBeenCalledTimes(1)
 await useStore.getState().loadStats()
 expect(vi.mocked(queryErrorStatsClient)).toHaveBeenCalledTimes(1)
 vi.mocked(queryErrorStatsClient).mockResolvedValue({source:'api',data:stats('toothbrush'),error:'API offline'})
 await useStore.getState().loadStats(true)
 expect(vi.mocked(queryErrorStatsClient)).toHaveBeenCalledTimes(2)
 expect(useStore.getState().statsError).toBe('API offline')
})
it('read-only sharing cannot enable review write mode',()=>{
 useStore.setState({readOnly:true,reviewMode:false})
 useStore.getState().setReviewMode(true)
 expect(useStore.getState().reviewMode).toBe(false)
 useStore.setState({readOnly:false});useStore.getState().setReviewMode(true)
 expect(useStore.getState().reviewMode).toBe(true)
})

it('switches cached-evidence categories without calling an unrelated central metrics API',()=>{
 useStore.getState().setItem('zipper',false)
 expect(useStore.getState().filters.item).toBe('zipper')
 expect(useStore.getState().stats).toBeNull()
 expect(vi.mocked(queryErrorStatsClient)).not.toHaveBeenCalled()
})
