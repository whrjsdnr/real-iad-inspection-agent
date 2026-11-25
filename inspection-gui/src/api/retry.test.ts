import {it,expect,vi} from 'vitest'
import {requestJson,retryDelay,HttpError} from './retry'

it('backs off with bounded jitter and respects Retry-After',()=>{
 expect(retryDelay(0,null,()=>0)).toBe(200)
 expect(retryDelay(1,null,()=>1)).toBe(800)
 expect(retryDelay(0,'3',()=>0)).toBe(3000)
 expect(retryDelay(0,new Date(5000).toUTCString(),()=>0,1000)).toBe(4000)
})
it('retries transient GET but never permanent input/permission errors',async()=>{
 const send=vi.fn().mockResolvedValueOnce(new Response('',{status:503})).mockResolvedValue(new Response('{"ok":true}'))
 const sleep=vi.fn().mockResolvedValue(undefined)
 expect(await requestJson('url',{}, {fetch:send,sleep,random:()=>0})).toEqual({ok:true});expect(sleep).toHaveBeenCalledTimes(1)
 for(const status of [400,401,403,404,422]){const permanent=vi.fn().mockResolvedValue(new Response('',{status}));await expect(requestJson('url',{}, {fetch:permanent,sleep})).rejects.toBeInstanceOf(HttpError);expect(permanent).toHaveBeenCalledTimes(1)}
})
it('does not repeat an unkeyed mutation',async()=>{
 const send=vi.fn().mockRejectedValue(new TypeError('network'))
 await expect(requestJson('url',{method:'POST'},{fetch:send})).rejects.toThrow('network');expect(send).toHaveBeenCalledTimes(1)
})
it('keyed POST retries the same body/key and stops at limit',async()=>{
 const send=vi.fn().mockRejectedValue(new TypeError('network')),sleep=vi.fn().mockResolvedValue(undefined)
 await expect(requestJson('url',{method:'POST',headers:{'Idempotency-Key':'same'},body:'same'},{fetch:send,sleep})).rejects.toThrow('network')
 expect(send).toHaveBeenCalledTimes(4)
 for(const [,init] of send.mock.calls){expect(init.body).toBe('same');expect(init.headers['Idempotency-Key']).toBe('same')}
})
it('does not shorten a server Retry-After beyond the total deadline',async()=>{
 const send=vi.fn().mockResolvedValue(new Response('',{status:429,headers:{'Retry-After':'120'}})),sleep=vi.fn()
 await expect(requestJson('url',{}, {fetch:send,sleep})).rejects.toBeInstanceOf(HttpError);expect(sleep).not.toHaveBeenCalled()
})
it('honors caller cancellation',async()=>{
 const abort=new AbortController();abort.abort(new Error('navigation'))
 const send=vi.fn();await expect(requestJson('url',{signal:abort.signal},{fetch:send})).rejects.toThrow('navigation');expect(send).not.toHaveBeenCalled()
})
