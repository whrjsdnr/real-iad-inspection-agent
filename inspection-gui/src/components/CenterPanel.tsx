import {useEffect} from 'react'
import {itemLabel,METRIC_DEFS} from '../config'
import {useStore} from '../store'
import {Scene} from '../three/Scene'
import {partsForItem} from '../three/parts'
import {useScenePreferences} from '../three/scenePreferences'
import {usePartHeatmap} from '../three/partHeatmapStore'
import {SceneControls} from './SceneControls'
import {formatNumDen,formatRate,rateToColor} from '../utils/heat'
import {SurfaceHUD} from './SurfaceHUD'

/** One 3D inspector. Image diagnostics stay in case evidence, outside this canvas. */
export function CenterPanel(){
 const filters=useStore(s=>s.filters),selected=useStore(s=>s.selectedPart),select=useStore(s=>s.selectPart)
 const reviewStats=useStore(s=>s.stats),reviewError=useStore(s=>s.statsError)
 const mode=useScenePreferences(s=>s.mode),signal=usePartHeatmap(),load=signal.load
 useEffect(()=>{if(mode==='heatmap'&&signal.mode==='model_signals')void load(filters.item,{modelVersion:filters.modelVersion,dateFrom:filters.dateFrom,dateTo:filters.dateTo})},[mode,signal.mode,load,filters.item,filters.modelVersion,filters.dateFrom,filters.dateTo])
 const stats=signal.mode==='model_signals'?(signal.data?.item===filters.item?signal.data:null):reviewStats?.item===filters.item?reviewStats:null
 const rows=stats?.rows??[],parts=partsForItem(filters.item)
 return <section className="glass flex min-h-0 flex-col">
  <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3"><strong className="text-sm text-tx">{itemLabel(filters.item)} · 3D 제품 검사</strong><span className="text-xs text-muted">회전 · 확대 · 표면 선택</span></header>
  <SceneControls/>
  <div className="precision-model-viewport relative h-[65vh] min-h-[460px] w-full flex-none"><Scene/><SurfaceHUD/></div>
  <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-3"><div className="flex gap-1" aria-label="3D 카메라 제어">{(['front','right','top','reset'] as const).map(pose=><button key={pose} className="btn" onClick={()=>window.dispatchEvent(new CustomEvent('inspection:camera',{detail:pose}))}>{({front:'정면',right:'측면',top:'위',reset:'초기화'})[pose]}</button>)}</div><span className="text-[11px] text-muted">제품군 근사 템플릿 · 실측 CAD 아님</span></div>
  {mode==='heatmap'&&<div className="space-y-3 border-t border-line p-4">
   <div className="flex flex-wrap gap-1"><button className={`btn ${signal.mode==='model_signals'?'btn-active':''}`} onClick={()=>signal.setMode('model_signals')}>모델 검출 집계</button><button className={`btn ${signal.mode==='review_metrics'?'btn-active':''}`} onClick={()=>signal.setMode('review_metrics')}>검수 확정 집계</button></div>
   <p className="text-xs text-muted">{signal.mode==='model_signals'?'검출 제품 / 관측 제품 · 부위당 단일 수치':METRIC_DEFS[filters.metric].definition}</p>
   {((signal.mode==='model_signals'&&signal.error)||(signal.mode==='review_metrics'&&reviewError))&&<p className="text-xs text-warn">집계 조회 실패 · 조건과 연결을 확인하세요.</p>}
   <div className="flex flex-wrap gap-2">{parts.map(part=>{const row=rows.find(row=>row.group.part_id===part.region_id);return <button key={part.region_id} className={`btn ${selected===part.region_id?'btn-active':''}`} onClick={()=>select(selected===part.region_id?null:part.region_id)}><span>{part.label}</span>{row&&<span style={{color:rateToColor(row.rate)}}>{formatRate(row.rate)} · {formatNumDen(row.num,row.den)}</span>}</button>})}</div>
  </div>}
 </section>
}
