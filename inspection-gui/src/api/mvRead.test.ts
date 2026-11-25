import {it,expect,vi,afterEach} from 'vitest'
import {mvRead} from './mvRead'
afterEach(()=>vi.unstubAllGlobals())
it('distinguishes missing router from missing training data and preserves URL/body',async()=>{
 const url='/api/heatmaps/catalog?item=toothbrush'
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Not Found'}),{status:404})))
 await expect(mvRead(url,new AbortController().signal)).rejects.toMatchObject({kind:'route_not_registered',message:expect.stringContaining(url)})
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'기존 MV는 Train NG만 지원'}),{status:404})))
 await expect(mvRead(url,new AbortController().signal)).rejects.toMatchObject({kind:'data_not_found'})
})
it('returns actual arrays unchanged and never requests a fixture fallback',async()=>{
 const payload={values:[0,.2,null],known_count:[10,10,0]};const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify(payload)))
 vi.stubGlobal('fetch',fetcher)
 expect(await mvRead('/api/heatmaps/ground-truth',new AbortController().signal)).toEqual(payload)
 expect(fetcher).toHaveBeenCalledTimes(1)
})
