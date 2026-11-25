import {it,expect,vi,afterEach} from 'vitest'
afterEach(()=>{vi.unstubAllGlobals();vi.resetModules()})
it('does not turn an idempotency conflict into another job result',async()=>{
 let pointer=''
 vi.stubGlobal('localStorage',{setItem:(_key:string,value:string)=>{pointer=value},getItem:()=>pointer})
 const fetch=vi.fn()
  .mockResolvedValueOnce(new Response(JSON.stringify({paths:{'/inference/jobs':{},'/inference/job-keys/{key}':{}}})))
  .mockResolvedValue(new Response('Idempotency conflict',{status:409}))
 vi.stubGlobal('fetch',fetch)
 const {submitJob}=await import('./jobs')
 const form=new FormData();form.set('mode','existing');form.set('item','usb');form.set('product_id','isolated-product')
 await expect(submitJob(form,'fixed-key')).rejects.toThrow('Idempotency conflict')
 expect(fetch).toHaveBeenCalledTimes(2)
 expect(pointer).toContain('fixed-key')
})
