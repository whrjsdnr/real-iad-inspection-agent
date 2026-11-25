/** The detached canvas owns its renderer. Never dispose a live StrictMode probe. */
export interface RendererOwner {
 domElement:{isConnected:boolean;dataset:DOMStringMap}
 setAnimationLoop:(callback:null)=>void
 renderLists:{dispose:()=>void}
 dispose:()=>void
 forceContextLoss:()=>void
}
const released=new WeakSet<object>()
export function releaseDetachedRenderer(renderer:RendererOwner):boolean{
 if(renderer.domElement.isConnected||released.has(renderer))return false
 released.add(renderer)
 renderer.setAnimationLoop(null)
 renderer.renderLists.dispose()
 renderer.dispose()
 renderer.forceContextLoss()
 return true
}
export function rendererKey(category:string){return JSON.stringify(['inspection-category',category])}
