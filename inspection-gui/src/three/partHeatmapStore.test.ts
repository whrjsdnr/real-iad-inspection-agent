import {afterEach,it,expect,vi} from 'vitest'
import {usePartHeatmap} from './partHeatmapStore'
const filters={modelVersion:'',dateFrom:'2026-11-01',dateTo:'2026-11-30'}
afterEach(()=>{vi.unstubAllGlobals();usePartHeatmap.setState({data:null,error:null,loading:false,camera:'all'})})
it('does not replace unavailable or empty part evidence with fixture rates',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('offline')))
 await usePartHeatmap.getState().load('toothbrush',filters)
 expect(usePartHeatmap.getState().data).toBeNull();expect(usePartHeatmap.getState().error).toBe('offline')
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({item:'toothbrush',rows:[],cases:[],mapping_verified:false}))))
 await usePartHeatmap.getState().load('toothbrush',filters)
 expect(usePartHeatmap.getState().data?.rows).toEqual([])
})
it('rejects stale category responses and preserves camera/model/date filters',async()=>{
 let finish!:(response:Response)=>void
 const old=new Promise<Response>(resolve=>{finish=resolve})
 const send=vi.fn().mockReturnValueOnce(old).mockResolvedValueOnce(new Response(JSON.stringify({item:'usb',rows:[],cases:[]})))
 vi.stubGlobal('fetch',send)
 usePartHeatmap.setState({camera:'C3'})
 const prior=usePartHeatmap.getState().load('toothbrush',filters)
 await usePartHeatmap.getState().load('usb',{...filters,modelVersion:'rt15'})
 finish(new Response(JSON.stringify({item:'toothbrush',rows:[],cases:[]})));await prior
 expect(usePartHeatmap.getState().data?.item).toBe('usb')
 expect(send.mock.calls[1][0]).toContain('camera=C3');expect(send.mock.calls[1][0]).toContain('model_version=rt15')
 expect(send.mock.calls[1][0]).toContain('date_from=2026-11-01')
})
