import {create} from 'zustand'
import {API_BASE} from '../config'
import {validateGuiAction,executeGuiAction,type GuiAction,type GuiPorts} from '../guiActions'
import {useStore} from '../store'
import {navigate} from '../router'
import {usePartHeatmap} from './partHeatmapStore'
type Focus=Extract<GuiAction,{type:'spatial_focus'}>
export const useSpatialFocus=create<{pending:Focus|null;set:(pending:Focus|null)=>void}>(set=>({pending:null,set:pending=>set({pending})}))
export async function openSpatialEvidence(value:unknown){
 const action=validateGuiAction(value,[],[])
 if(action.type!=='spatial_focus')throw new Error('공간 근거 명령이 아닙니다.')
 const response=await fetch(`${API_BASE}/parts/spatial/grid/${action.grid_id}?model=${action.model}&method=${action.method}`,{signal:AbortSignal.timeout(8000)})
 if(!response.ok)throw new Error(`공간 근거 조회 ${response.status}`)
 const data=await response.json()
 if(!useStore.getState().items.includes(data.item))throw new Error('등록되지 않은 품목')
 const noop=()=>undefined
 const ports:GuiPorts={category:noop,product:noop,camera:noop,region:noop,pose:noop,metric:noop,page:noop,spatial:focus=>{
  useSpatialFocus.getState().set(focus);usePartHeatmap.getState().setMode('model_signals');useStore.getState().setItem(data.item);navigate('#/dashboard')
 }}
 executeGuiAction(action,ports)
}
