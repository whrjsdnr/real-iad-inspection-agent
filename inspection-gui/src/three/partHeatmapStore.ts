import {create} from 'zustand'
import {API_BASE} from '../config'
import type {StatsRow,ViewId} from '../types'
export interface RegionSignalRow extends StatsRow {detection_count:number;hvq_roi_mean:number|null;source?:'gui_evidence'|'operational_findings';cameras?:string[]}
export interface RegionSignalView {
 camera:ViewId;width:number;height:number;image_url:string
 regions:{region_id:string;label:string;polygon:[number,number][];polygons?:[number,number][][]}[]
 detections:{bbox:[number,number,number,number];score:number;region_id:string|null}[]
 hvq_roi_mean:Record<string,number>;rtdetr_threshold:number
}
export interface PartHeatmapResponse {
 item:string;rows:RegionSignalRow[];mapping_verified:boolean;mapping_version:string
 mapping_scope:string;source_scope:string;sample_products:number;coverage:Record<string,string>
 operational_products?:number|null;operational_threshold?:number|null
 generated_at:string;definition:string;reason:string|null
 cases:{case_id:string;product_id:string;models:Record<string,string>;recorded_at:string;views:RegionSignalView[]}[]
}
type Filters={modelVersion:string;dateFrom:string;dateTo:string}
type State={
 mode:'model_signals'|'review_metrics';camera:ViewId|'all';data:PartHeatmapResponse|null;loading:boolean;error:string|null
 setMode:(mode:State['mode'])=>void;setCamera:(camera:State['camera'])=>void
 load:(item:string,filters:Filters)=>Promise<void>
}
let generation=0
export const usePartHeatmap=create<State>((set,get)=>({
 mode:'model_signals',camera:'all',data:null,loading:false,error:null,
 setMode:mode=>set({mode}),setCamera:camera=>set({camera}),
 load:async(item,filters)=>{
  const sequence=++generation
  set({loading:true,error:null,data:null})
  try{
   const params=new URLSearchParams({item,date_from:filters.dateFrom,date_to:filters.dateTo})
   if(filters.modelVersion)params.set('model_version',filters.modelVersion)
   if(get().camera!=='all')params.set('camera',get().camera)
   const response=await fetch(`${API_BASE}/parts/heatmap?${params}`,{signal:AbortSignal.timeout(8000)})
   if(!response.ok)throw new Error(`부위 근거 API ${response.status}`)
   const data=await response.json() as PartHeatmapResponse
   if(data.item!==item)throw new Error('다른 품목의 부위 응답을 차단했습니다.')
   if(sequence===generation)set({data,loading:false,error:null})
  }catch(error){if(sequence===generation)set({data:null,loading:false,error:error instanceof Error?error.message:String(error)})}
 }
}))
