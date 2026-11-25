import {it,expect,vi} from 'vitest'
import {releaseDetachedRenderer,rendererKey,type RendererOwner} from './rendererLifetime'
function owner(connected:boolean):RendererOwner{return {domElement:{isConnected:connected,dataset:{}},setAnimationLoop:vi.fn(),renderLists:{dispose:vi.fn()},dispose:vi.fn(),forceContextLoss:vi.fn()}}
it('uses separate React/Canvas identities for every category including rapid repeats',()=>{
 expect(rendererKey('toothbrush')).not.toBe(rendererKey('sim_card_set'))
 expect(rendererKey('sim_card_set')).toBe(rendererKey('sim_card_set'))
 expect(rendererKey('a:b')).not.toBe(rendererKey('a'))
})
it('synchronously releases detached resources once, instead of waiting for R3F delayed cleanup',()=>{
 const renderer=owner(false)
 expect(releaseDetachedRenderer(renderer)).toBe(true)
 expect(renderer.setAnimationLoop).toHaveBeenCalledWith(null)
 expect(renderer.renderLists.dispose).toHaveBeenCalledTimes(1)
 expect(renderer.dispose).toHaveBeenCalledTimes(1)
 expect(renderer.forceContextLoss).toHaveBeenCalledTimes(1)
 expect(releaseDetachedRenderer(renderer)).toBe(false)
 expect(renderer.dispose).toHaveBeenCalledTimes(1)
})
it('does not destroy a live canvas during React StrictMode effect cleanup/replay',()=>{
 const renderer=owner(true)
 expect(releaseDetachedRenderer(renderer)).toBe(false)
 expect(renderer.dispose).not.toHaveBeenCalled()
 expect(renderer.forceContextLoss).not.toHaveBeenCalled()
 renderer.domElement.isConnected=false
 expect(releaseDetachedRenderer(renderer)).toBe(true)
})
it('a stale canvas cleanup cannot dispose the next category renderer',()=>{
 const old=owner(false),current=owner(true)
 releaseDetachedRenderer(old)
 expect(current.dispose).not.toHaveBeenCalled()
 expect(releaseDetachedRenderer(current)).toBe(false)
})
