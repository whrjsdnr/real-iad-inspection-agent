import {create} from 'zustand'
import {API_BASE} from '../config'
import {mvRead} from '../api/mvRead'
import type {SurfaceFrame,Hit} from './surfaceProjection'
import defaults from '../../../config/surface_projection.json'
type Source='ground_truth'|'rt'|'hvq'
type Layout={item:string;sources:{id:Source;label:string;views:string[];available:boolean;reason:string|null}[];default_opacity:number}
interface State {
 item:string;source:Source;view:string;opacity:number;layout:Layout|null;data:SurfaceFrame|null;loading:boolean;error:string|null;
 selected:Hit|null;focus:Hit|null;hotspots:Record<string,Hit[]>;
 load:(item:string)=>Promise<void>;refresh:()=>Promise<void>;setSource:(source:Source)=>void;setView:(view:string)=>void;
 setOpacity:(opacity:number)=>void;select:(hit:Hit|null)=>void;setFocus:(hit:Hit)=>void;register:(region:string,hits:Hit[])=>void
}
let generation=0,controller:AbortController|null=null
const address=(path:string)=>API_BASE.replace(/\/$/,'')+path
export const useSurfaceStore=create<State>((set,get)=>({
 item:'',source:'ground_truth',view:'C1',opacity:.88,layout:null,data:null,loading:false,error:null,selected:null,focus:null,hotspots:{},
 load:async item=>{
  if(get().item===item&&get().layout&&get().data?.version===defaults.version&&get().data?.render?.bristle_min_alpha===defaults.render.bristle_min_alpha)return
  const id=++generation;controller?.abort();controller=new AbortController();const signal=controller.signal
  set({item,layout:null,data:null,loading:true,error:null,selected:null,focus:null,hotspots:{}})
  try{
   const layout=await mvRead<Layout>(address('/heatmaps/surface-layout?'+new URLSearchParams({item})),signal,'3D 표면 목록')
   if(id!==generation)return
   const source=layout.sources.some(source=>source.id===get().source&&source.available&&source.views.length)?get().source:layout.sources.find(source=>source.available&&source.views.length)?.id
   if(!source){set({layout,loading:false});return}
   const choice=layout.sources.find(entry=>entry.id===source)!,view=choice.views.includes(get().view)?get().view:choice.views[0]
   set({layout,source,view,opacity:layout.default_opacity});await get().refresh()
  }catch(error){if(id===generation&&!signal.aborted)set({loading:false,error:String(error)})}
 },
 refresh:async()=>{
  const {item,source,view}=get();if(!item)return
  const id=++generation;controller?.abort();controller=new AbortController();const signal=controller.signal
  set({loading:true,error:null,data:null,selected:null,focus:null,hotspots:{}})
  try{
   const data=await mvRead<SurfaceFrame>(address('/heatmaps/surface?'+new URLSearchParams({item,source,view})),signal,'3D 표면 데이터')
   if(id!==generation||signal.aborted)return
   if(data.item!==item||data.view!==view||data.source!==source)throw new Error('표면 응답의 품목/시점/데이터 종류 불일치')
   if(!data.user_authorized_approximate_projection)throw new Error('표시용 표면 투영 설정 없음')
   set({data,loading:false})
  }catch(error){if(id===generation&&!signal.aborted)set({loading:false,error:String(error)})}
 },
 setSource:source=>{const choice=get().layout?.sources.find(entry=>entry.id===source);if(!choice?.available||!choice.views.length)return;set({source,view:choice.views.includes(get().view)?get().view:choice.views[0]});void get().refresh()},
 setView:view=>{if(!get().layout?.sources.find(entry=>entry.id===get().source)?.views.includes(view))return;set({view});void get().refresh()},
 setOpacity:opacity=>{if(Number.isFinite(opacity))set({opacity:Math.max(0,Math.min(1,opacity))})},
 select:selected=>set({selected}),setFocus:focus=>set({focus,selected:focus}),register:(region,hits)=>set(state=>({hotspots:{...state.hotspots,[region]:hits}})),
}))
