/** Whitelisted structured GUI commands. No JS, SQL, eval, or arbitrary URLs. */
import type { Metric,ViewId } from './types'
export type GuiAction =
 |{type:'select_category';category:string}
 |{type:'select_product';product_id:string}
 |{type:'select_camera';camera:ViewId}
 |{type:'highlight_region';region_id:string}
 |{type:'rotate_camera';pose:'front'|'right'|'top'|'reset'}
 |{type:'heatmap';metric:Metric}
 |{type:'navigate';page:'dashboard'|'inference'|'chat'}
 |{type:'spatial_focus';grid_id:string;model:'rt'|'hvq';method:string}
export function validateGuiAction(input:unknown,categories:string[],regions:string[]):GuiAction {
 if(!input||typeof input!=='object'||Array.isArray(input))throw new Error('GUI 명령 형식 오류')
 const v=input as Record<string,unknown>
 if(v.type==='spatial_focus'){
  if(Object.keys(v).sort().join(',')!=='grid_id,method,model,type'||typeof v.grid_id!=='string'||! /^[a-f0-9]{24}$/.test(v.grid_id))throw new Error('공간 근거 ID 오류')
  const methods=v.model==='rt'?['gaussian','center_count','box_area','confidence_area','product_occupancy','mean_confidence']:v.model==='hvq'?['mean','max','percentile']:[]
  if(typeof v.method!=='string'||!methods.includes(v.method))throw new Error('등록되지 않은 공간 모델/집계')
  return input as GuiAction
 }
 const fields:Record<string,string>={select_category:'category',select_product:'product_id',select_camera:'camera',highlight_region:'region_id',rotate_camera:'pose',heatmap:'metric',navigate:'page'}
 const field=fields[String(v.type)]
 if(!field||Object.keys(v).sort().join(',')!==['type',field].sort().join(','))throw new Error('등록되지 않은 GUI 명령')
 const value=v[field]
 const sets:Record<string,string[]>={select_category:categories,select_camera:['C1','C2','C3','C4','C5'],highlight_region:regions,rotate_camera:['front','right','top','reset'],heatmap:['confirmed_defect_rate','part_miss_rate','part_false_alarm_rate','capture_process_failure_rate'],navigate:['dashboard','inference','chat']}
 if(typeof value!=='string'||(sets[String(v.type)]&&!sets[String(v.type)].includes(value))||!value.trim()||value.length>512)throw new Error('GUI 명령 매개변수 오류')
 return input as GuiAction
}
export interface GuiPorts {
 category:(v:string)=>void;product:(v:string)=>void;camera:(v:ViewId)=>void
 region:(v:string)=>void;pose:(v:string)=>void;metric:(v:Metric)=>void;page:(v:string)=>void
 spatial?:(action:Extract<GuiAction,{type:'spatial_focus'}>)=>void
}
export function executeGuiAction(action:GuiAction,ports:GuiPorts){
 switch(action.type){
  case 'select_category':return ports.category(action.category)
  case 'select_product':return ports.product(action.product_id)
  case 'select_camera':return ports.camera(action.camera)
  case 'highlight_region':return ports.region(action.region_id)
  case 'rotate_camera':return ports.pose(action.pose)
  case 'heatmap':return ports.metric(action.metric)
  case 'navigate':return ports.page(action.page)
  case 'spatial_focus':if(!ports.spatial)throw new Error('공간 GUI 포트 없음');return ports.spatial(action)
 }
}
