import { useState } from 'react'
import {useStore} from '../store'
import {partsForItem} from '../three/parts'
import {validateGuiAction,executeGuiAction} from '../guiActions'
import {navigate,dashboardFocusLink} from '../router'

export function GuiContextControls(){
 const filters=useStore(s=>s.filters),items=useStore(s=>s.items),part=useStore(s=>s.selectedPart)
 const [trace,setTrace]=useState('')
 const perform=(value:unknown)=>{
  try{
   const action=validateGuiAction(value,items,partsForItem(filters.item).map(p=>p.region_id))
   const store=useStore.getState()
   executeGuiAction(action,{category:store.setItem,product:v=>navigate(dashboardFocusLink(v)),camera:store.setViewerView,region:v=>{store.selectPart(v);navigate('#/dashboard')},pose:v=>{navigate('#/dashboard');setTimeout(()=>window.dispatchEvent(new CustomEvent('inspection:camera',{detail:v})),300)},metric:store.setMetric,page:v=>navigate(`#/${v}`)})
   setTrace(`GUI 실행: ${action.type}`)
  }catch(error){setTrace(String(error))}
 }
 return <section className="glass mb-3 space-y-2 p-3 text-xs text-muted" aria-label="GUI 컨텍스트 및 제어">
  <p>현재 선택 · {filters.item} / {filters.productId==='all'?'제품 미선택':filters.productId} / {part??'부위 미선택'}</p>
  <div className="flex flex-wrap gap-2"><select className="control" aria-label="챗봇 제품군 선택" value={filters.item} onChange={e=>perform({type:'select_category',category:e.target.value})}>{items.map(item=><option key={item}>{item}</option>)}</select>
  <select className="control" aria-label="챗봇 부위 강조" value={part??''} onChange={e=>perform({type:'highlight_region',region_id:e.target.value})}><option value="" disabled>부위 강조</option>{partsForItem(filters.item).map(p=><option key={p.region_id} value={p.region_id}>{p.label}</option>)}</select>
  <button className="btn" onClick={()=>perform({type:'navigate',page:'dashboard'})}>검사 상세로 이동</button>
  </div>{trace&&<p role="status" className="font-mono text-[10px]">{trace}</p>}
 </section>
}
