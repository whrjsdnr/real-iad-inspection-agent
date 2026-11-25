import {useState} from 'react'
import {API_BASE,MIN_DENOMINATOR} from '../config'
import {useStore} from '../store'
import {usePartHeatmap} from '../three/partHeatmapStore'
import {partsForItem} from '../three/parts'
import {formatRate,formatNumDen,rateToColor} from '../utils/heat'
import {VIEW_IDS} from '../types'

type RegionDef={region_id:string;label:string;polygon:[number,number][];polygons?:[number,number][][]}
const regionPolys=(region:RegionDef):[number,number][][]=>region.polygons??[region.polygon]

export function PartSignalPanel(){
 const {data,error,loading,camera,setCamera}=usePartHeatmap()
 const item=useStore(s=>s.filters.item),selectedPart=useStore(s=>s.selectedPart),selectPart=useStore(s=>s.selectPart)
 const [caseId,setCaseId]=useState<string|null>(null)
 if(loading)return <p role="status" className="text-xs text-muted">등록된 부위의 모델 근거를 조회하고 있습니다.</p>
 if(error)return <p role="alert" className="text-xs text-warn">{error} · 서버의 부위 API 반영 여부를 확인하세요. 예시 결과로 대체하지 않습니다.</p>
 if(!data||data.item!==item)return <p className="text-xs text-muted">등록 부위 근거 미조회</p>
 const parts=partsForItem(item),entry=data.cases.find(c=>c.case_id===caseId)??data.cases[0]
 const view=camera==='all'?entry?.views[0]:entry?.views.find(v=>v.camera===camera)
 return <div className="space-y-3">
  <div className="flex flex-wrap gap-1" role="group" aria-label="부위 근거 카메라">{(['all',...VIEW_IDS] as const).map(value=><button key={value} className={`btn ${camera===value?'btn-active':''}`} onClick={()=>setCamera(value)}>{value==='all'?'전체 시점':value}</button>)}</div>
  <p className="text-xs text-muted">{data.definition}</p>
  <p className="text-xs text-warn">GUI 등록 표본 {data.sample_products} 제품{data.operational_products?` · 운영 근거 ${data.operational_products} 제품(의심 건수, 확정 불량률 아님)`:''} · 원본 해시가 일치하는 ROI만 적용.</p>
  <div className="grid grid-cols-2 gap-2">{data.rows.map(row=><button key={row.stat_key} onClick={()=>selectPart(row.group.part_id)} className="rounded-lg border border-line border-l-4 p-3 text-left" style={{borderLeftColor:rateToColor(row.rate),background:`color-mix(in srgb, ${rateToColor(row.rate)} 20%, var(--panel))`}}>
   <strong className="block text-xs text-tx">{parts.find(part=>part.part_id===row.group.part_id)?.label??row.group.part_id}</strong>
   {row.rate===null
    ?<span className="mt-1 block text-xs text-muted">분모 0 — 집계 불가</span>
    :<><span className="mt-1 block font-mono text-2xl" style={{color:rateToColor(row.rate)}}>{formatRate(row.rate)}</span>
      <span className="block text-xs text-muted">검출 제품 / 관측 제품 {formatNumDen(row.num,row.den)}</span></>}
   <span className="block text-xs text-muted">검출 박스 {row.detection_count}개 · HVQ ROI 평균 {row.hvq_roi_mean?.toFixed(2)??'없음'} (원시값)</span>
   <span className="block text-[10px] uppercase tracking-wide2 text-faint">{row.source==='operational_findings'?`운영 근거${row.cameras?.length?` · ${row.cameras.join('/')}`:''} · RT≥${data.operational_threshold}`:'GUI 등록 표본'}</span>
   {row.den<MIN_DENOMINATOR&&<span className="block text-xs text-warn">표본 부족 · 모집단 성능으로 해석하지 마세요.</span>}
  </button>)}</div>
  {!data.rows.length&&<p role="status" className="text-xs text-muted">현재 품목·카메라·모델·기간의 등록 ROI 근거가 없습니다.</p>}
  {entry&&<div className="space-y-2">
   <label className="block text-xs text-muted">원본 근거 제품<select aria-label="부위 근거 제품" className="ml-2 max-w-full rounded border border-line bg-panel p-1 text-tx" value={entry.case_id} onChange={event=>setCaseId(event.target.value)}>{data.cases.map(c=><option key={c.case_id} value={c.case_id}>{c.product_id}</option>)}</select></label>
   {view&&<><p className="text-xs text-muted">{view.camera} · ROI 윤곽 + 저장 검출 · RT 임계값 {view.rtdetr_threshold}</p><svg role="img" aria-label="실제 원본 이미지의 부위 ROI와 검출 근거" viewBox={`0 0 ${view.width} ${view.height}`} className="max-h-96 w-full rounded-lg border border-line bg-panel">
    <image href={`${API_BASE.replace(/\/$/,'')}${view.image_url}`} width={view.width} height={view.height}/>
    {view.regions.flatMap(region=>regionPolys(region).map((poly,index)=><polygon key={`${region.region_id}-${index}`} points={poly.map(point=>point.join(',')).join(' ')} fill="none" stroke="var(--ok)" strokeWidth={selectedPart===region.region_id?7:4}/>))}
    {view.detections.map((detection,index)=><rect key={index} x={detection.bbox[0]} y={detection.bbox[1]} width={detection.bbox[2]-detection.bbox[0]} height={detection.bbox[3]-detection.bbox[1]} fill="none" stroke="var(--signal)" strokeWidth={4}/>)}
   </svg><p className="break-all text-xs text-muted">{Object.values(entry.models).join(' · ')} · 근거 기록 {entry.recorded_at}</p></>}
  </div>}
 </div>
}
