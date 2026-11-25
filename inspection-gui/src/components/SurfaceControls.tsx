import {useEffect} from 'react'
import {useStore} from '../store'
import {useSurfaceStore} from '../three/surfaceStore'
import {HEAT_GRADIENT_CSS} from '../utils/heat'
import {API_BASE,MIN_DENOMINATOR} from '../config'
export function SurfaceControls(){
 const item=useStore(s=>s.filters.item),state=useSurfaceStore(),load=state.load
 useEffect(()=>{void load(item)},[item,load])
 const choice=state.layout?.sources.find(source=>source.id===state.source)
 const selected=state.selected,region=state.data?.regions.find(region=>region.region_id===selected?.region_id)
 return <div className="w-full space-y-2 border-t border-line pt-3" aria-label="3D 표면 히트맵 제어">
  <div className="flex flex-wrap items-center gap-2">
   {state.layout&&state.layout.sources.some(source=>source.available)&&<><select className="btn" aria-label="3D 표면 데이터" value={state.source} onChange={e=>state.setSource(e.target.value as typeof state.source)}>{state.layout.sources.map(source=><option key={source.id} value={source.id} disabled={!source.available}>{source.label}{!source.available?source.id==='hvq'?' · 원시 맵 미저장':' · 데이터 미등록':''}</option>)}</select>
   <select className="btn" aria-label="3D 표면 데이터 시점" value={state.view} onChange={e=>state.setView(e.target.value)}>{choice?.views.map(view=><option key={view}>{view}</option>)}</select></>}
   <label className="flex items-center gap-2 text-xs text-muted">투명도<input aria-label="3D 표면 투명도" type="range" min="0" max="1" step=".05" value={state.opacity} onChange={e=>state.setOpacity(Number(e.target.value))}/><span>{Math.round(state.opacity*100)}%</span></label>
   <span className="rounded border border-line px-2 py-1 text-[10px] text-muted">근사 표면 투영 · 표시용</span>
   <a className="btn ml-auto" href={`${API_BASE.replace(/\/$/,'')}/sharing/kit`} download>팀 공유 패키지 ↓</a>
  </div>
  {state.layout?.sources.some(source=>source.id==='hvq'&&!source.available)&&<p className="text-[10px] text-faint">현재 조회 범위에서 검증된 HVQ 원시 맵을 찾지 못했습니다. 점수를 공간 분포로 대체하지 않습니다.</p>}
  {state.source!=='ground_truth'&&state.data?.product_id&&<p className="text-[10px] text-faint">실제 맵이 저장된 대표 제품 · {state.data.product_id} · 전체 제품군 집계가 아닙니다.</p>}
  <div className="flex flex-wrap items-center gap-3 text-xs text-muted"><span>부위별 상대 강도</span><span className="inline-block h-2 w-32 rounded" style={{background:HEAT_GRADIENT_CSS}}/><span>낮음 → 높음 · 미관측은 원래 재질</span>{state.source==='ground_truth'&&<span>Train NG 마스크 분포 · 운영 불량률과 별도</span>}</div>
  {state.loading&&<p role="status" className="text-xs text-muted">실제 공간 데이터를 표면에 반영 중…</p>}
  {state.error&&<p role="alert" className="text-xs text-warn">표면 데이터 조회 실패 <button className="btn" onClick={()=>void state.load(item)}>재시도</button></p>}
  {state.layout&&!state.loading&&!state.layout.sources.some(source=>source.available)&&<p className="text-xs text-muted">이 품목의 표면 표시 데이터가 아직 등록되지 않았습니다.</p>}
  {selected&&<div className="rounded border border-line bg-bg px-3 py-2 text-xs text-tx"><strong>{selected.label} · 셀 ({selected.column},{selected.row})</strong><span className="ml-3">{selected.value===null?'미관측':`공간 값 ${selected.value.toFixed(5)}`} · 관측 {selected.count}{selected.count<MIN_DENOMINATOR?' · 표본 부족':''}</span>{region&&<span className="ml-3 text-muted">제품 표본 {region.sample_products} · unknown {region.unknown_products}</span>}</div>}
  {!selected&&!state.loading&&!state.error&&<p className="text-xs text-muted">표면의 색상 영역을 클릭하면 실제 격자값과 관측 수를 확인할 수 있습니다.</p>}
 </div>
}
