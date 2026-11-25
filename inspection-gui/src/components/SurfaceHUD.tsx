import {useSurfaceStore} from '../three/surfaceStore'
import {useScenePreferences} from '../three/scenePreferences'
import {useStore} from '../store'
export function SurfaceHUD(){
 const mode=useScenePreferences(s=>s.mode),item=useStore(s=>s.filters.item),state=useSurfaceStore()
 if(mode!=='surface'||state.data?.item!==item)return null
 const frame=state.data,hits=Object.values(state.hotspots).flat().sort((a,b)=>(b.value??0)-(a.value??0)).slice(0,3)
 const samples=Math.max(0,...frame.regions.map(region=>region.sample_products))
 const focus=(hit:typeof hits[number])=>{state.setFocus(hit);const normal=['x','y','z'].find(axis=>!frame.projection.axes.includes(axis as 'x'|'y'|'z'));window.dispatchEvent(new CustomEvent('inspection:camera',{detail:normal==='z'?'front':normal==='y'?'top':'right'}))}
 return <div className="pointer-events-none absolute inset-0 z-10" aria-label="표면 검사 오버레이">
  <div className="absolute left-5 top-5 border-l-2 border-signal bg-panel/85 px-4 py-3 backdrop-blur-md"><span className="font-mono text-[9px] tracking-[.2em] text-signal">SURFACE INSPECTION</span><strong className="mt-1 block text-base text-tx">{item.replaceAll('_',' ').toUpperCase()}</strong><div className="mt-2 flex gap-4 font-mono text-[10px] text-muted"><span>VIEW <b className="text-tx">{frame.view}</b></span><span>REGIONS <b className="text-tx">{frame.regions.length}</b></span><span>N <b className="text-tx">{samples.toLocaleString()}</b></span></div><p className="mt-1 text-[9px] text-faint">{frame.source==='ground_truth'?'MASK PRESENCE / TRAIN NG':frame.source==='rt'?'DETECTION DENSITY / RT-DETR':'ANOMALY FIELD / HVQ'}</p>{frame.product_id&&<p className="mt-1 font-mono text-[9px] text-muted">{frame.product_id} · {frame.split}</p>}</div>
  <div className="absolute bottom-6 right-5 flex gap-2 rounded border border-line/70 bg-panel/85 p-3 backdrop-blur-md"><div className="h-40 w-2 rounded-full" style={{background:'linear-gradient(to top,var(--heat-ok),var(--heat-warn),var(--heat-fail))'}}/><div className="flex h-40 flex-col justify-between font-mono text-[9px] text-muted"><span>HIGH</span><span>RELATIVE<br/>SIGNAL</span><span>LOW</span></div></div>
  {!!hits.length&&<div className="absolute bottom-5 left-5 flex flex-col gap-1.5">{hits.map((hit,index)=><button key={`${hit.region_id}:${hit.index}`} className="pointer-events-auto flex items-center gap-3 rounded border border-line bg-panel/90 px-3 py-2 text-left backdrop-blur-md transition-colors hover:border-signal" onClick={()=>focus(hit)}><span className="font-mono text-[10px] text-signal">H{String(index+1).padStart(2,'0')}</span><span className="text-xs text-muted">{hit.label}</span><strong className="ml-3 font-mono text-xs text-tx">{frame.source==='ground_truth'?`${((hit.value??0)*100).toFixed(1)}%`:hit.value?.toFixed(3)}</strong></button>)}</div>}
 </div>
}
