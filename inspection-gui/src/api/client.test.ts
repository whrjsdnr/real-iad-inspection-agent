import {it,expect,vi,afterEach} from 'vitest'
import {queryErrorStatsClient,getCaseEvidenceClient,computeInspectionMetricsClient} from './client'

afterEach(()=>{vi.unstubAllGlobals();vi.unstubAllEnvs()})
it('API network failure produces no fixture inspection cases or rates',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('network disconnected')))
 const stats=await queryErrorStatsClient({item:'toothbrush',metric:'part_miss_rate',dateFrom:'2026-11-01',dateTo:'2026-11-30',modelVersion:''})
 expect(stats.data.rows).toEqual([]);expect(stats.error).toContain('network disconnected');expect(stats.source).toBe('api')
 const cases=await getCaseEvidenceClient({productId:'does-not-exist'});expect(cases.data.cases).toEqual([]);expect(cases.data.count).toBe(0)
 const metrics=await computeInspectionMetricsClient({item:'toothbrush',partId:null,dateFrom:'2026-11-01',dateTo:'2026-11-30',modelVersion:'',reviewState:'confirmed'})
 for(const m of Object.values(metrics.data.metrics)){expect(m.rate).toBeNull();expect(m.reason).toBe('backend_unavailable')}
})
it('API empty result remains empty without implying offline or normal verdict',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({cases:[],count:0,limit:20,filters:{},model_version:null,mapping_version:null,definition_version:'metrics-v1'}))))
 const out=await getCaseEvidenceClient({productId:'empty'});expect(out.error).toBeUndefined();expect(out.data.cases).toEqual([])
})

it('fixture inspection data is available only through explicit fixture mode',async()=>{
 vi.resetModules();vi.stubEnv('VITE_USE_FIXTURE','true')
 const client=await import('./client');const result=await client.getCaseEvidenceClient({productId:'fixture'})
 expect(result.source).toBe('fixture')
})
