import {useEffect,useMemo,useRef,useState} from 'react'
import {API_BASE,MIN_DENOMINATOR} from '../config'
import {useStore} from '../store'
import {gridTexture,gridRange,type SpatialRaster} from '../three/spatialGrid'
import {cssVar} from '../utils/tokens'
import {HEAT_GRADIENT_CSS} from '../utils/heat'
import {validateGroundTruth,canCompareGroundTruth} from '../three/groundTruth'
import {mvRead} from '../api/mvRead'
type Entry={item:string;view:string;product_id:string|null;id:string}
type Truth={item:string;view:string;split:string;product_id:string|null;grid_width:number;grid_height:number;
 source_image_width:number;source_image_height:number;
 positive_count:number[];known_count:number[];unknown_count:number[];coverage_mask:number[];
 defect_rate:(number|null)[];occupancy_positive:(number|null)[];mask_coverage:(number|null)[];
 known_products:number;unknown_products:number;positive_mask_products:number;product_count:number;
 image_url:string|null;mask_url:string|null;source:string;mapping_version:string;comparison:{status:string}|null}
type Detection={bbox:[number,number,number,number];confidence:number}
const address=(path:string)=>API_BASE.replace(/\/$/,'')+path

function TruthCanvas({data,metric,absolute,opacity,boxes,onCell}:{data:Truth;metric:'defect_rate'|'occupancy_positive'|'mask_coverage';absolute:boolean;opacity:number;boxes:Detection[];onCell:(index:number)=>void}){
 const canvas=useRef<HTMLCanvasElement>(null),[image,setImage]=useState<HTMLImageElement|null>(null),[imageError,setImageError]=useState(false)
 useEffect(()=>{
  setImage(null);setImageError(false);if(!data.image_url)return
  const image=new Image();let live=true;image.onload=()=>{if(live)setImage(image)};image.onerror=()=>{if(live)setImageError(true)};image.src=address(data.image_url)
  return ()=>{live=false;image.onload=null;image.onerror=null;image.src=''}
 },[data.image_url])
 useEffect(()=>{
  const node=canvas.current,ctx=node?.getContext('2d');if(!node||!ctx)return
  node.width=512;node.height=512;ctx.fillStyle=cssVar('--bg');ctx.fillRect(0,0,512,512)
  if(image)ctx.drawImage(image,0,0,512,512)
  const raster:SpatialRaster={grid_width:64,grid_height:64,values:data[metric],coverage_mask:data.coverage_mask,
   valid_observation_counts:data.known_count,aggregation_method:absolute?'product_occupancy':'mask_relative'}
  const texture=gridTexture(raster,opacity),pixels=new Uint8ClampedArray(texture.image.data)
  if(data.product_id)for(let index=0;index<data[metric].length;index++)if(data[metric][index]===0)pixels[index*4+3]=0
  const layer=document.createElement('canvas');layer.width=64;layer.height=64;const c=layer.getContext('2d')!
  c.putImageData(new ImageData(pixels,64,64),0,0);texture.dispose()
  if(data.known_products<MIN_DENOMINATOR){
   c.globalCompositeOperation='source-atop';c.strokeStyle=cssVar('--text');c.globalAlpha=.3
   for(let i=-64;i<128;i+=8){c.beginPath();c.moveTo(i,0);c.lineTo(i+64,64);c.stroke()}
  }
  ctx.imageSmoothingEnabled=false;ctx.drawImage(layer,0,0,512,512);layer.width=0;layer.height=0
  ctx.strokeStyle=cssVar('--signal');ctx.lineWidth=2
  // Both model boxes and source mask use the verified same 1024px source frame.
  for(const box of boxes){const [x0,y0,x1,y1]=box.bbox;ctx.strokeRect(x0*512/data.source_image_width,y0*512/data.source_image_height,(x1-x0)*512/data.source_image_width,(y1-y0)*512/data.source_image_height)}
  return ()=>{node.width=0;node.height=0}
 },[data,metric,absolute,opacity,boxes,image])
 return <>{imageError&&<p role="alert" className="text-warn">원본 영상 조회 실패 · 위치 정합 미확인</p>}<canvas ref={canvas} aria-label="실제 마스크 기반 64격자 지도" className="w-full max-w-[640px] rounded-md border border-line" onClick={event=>{const rect=event.currentTarget.getBoundingClientRect(),column=Math.floor((event.clientX-rect.left)/rect.width*64),row=Math.floor((event.clientY-rect.top)/rect.height*64);onCell(Math.min(63,row)*64+Math.min(63,column))}}/></>
}

export function GroundTruthHeatmapPanel({compare=false}:{compare?:boolean}){
 const item=useStore(s=>s.filters.item)
 const [catalog,setCatalog]=useState<{entries:Entry[];rtdetr_visualization_threshold:number}|null>(null)
 const [view,setView]=useState('C1'),[product,setProduct]=useState(''),[individual,setIndividual]=useState(compare)
 const [data,setData]=useState<Truth|null>(null),[error,setError]=useState<string|null>(null),[loading,setLoading]=useState(false)
 const [boxes,setBoxes]=useState<Detection[]>([]),[opacity,setOpacity]=useState(.8),[absolute,setAbsolute]=useState(false)
 const [metric,setMetric]=useState<'defect_rate'|'occupancy_positive'|'mask_coverage'>('defect_rate'),[picked,setPicked]=useState<number|null>(null)
 useEffect(()=>setIndividual(compare),[compare])
 useEffect(()=>{
  const controller=new AbortController();setCatalog(null);setData(null);setError(null)
  mvRead<{entries:Entry[];rtdetr_visualization_threshold:number}>(address(`/heatmaps/catalog?item=${encodeURIComponent(item)}`),controller.signal).then(setCatalog).catch(e=>{if(!controller.signal.aborted)setError(String(e))})
  return ()=>controller.abort()
 },[item])
 const products=[...new Set(catalog?.entries.filter(entry=>entry.product_id).map(entry=>entry.product_id!)??[])]
 const chosen=products.includes(product)?product:products[0]
 useEffect(()=>{
  if(!catalog)return
  if((individual||compare)&&!chosen){setData(null);setError('이 품목의 개별 마스크 비교 표본이 아직 등록되지 않았습니다. 품목 집계 모드를 사용하세요.');return}
  const controller=new AbortController();setLoading(true);setData(null);setBoxes([]);setError(null);setPicked(null)
  const params=new URLSearchParams({item,view,split:'train'});if(individual||compare)params.set('product_id',chosen)
  mvRead<Truth>(address(`/heatmaps/ground-truth?${params}`),controller.signal,'MV 마스크 지도').then(async result=>{
   validateGroundTruth(result,item,view,individual||compare?chosen:undefined)
   if(controller.signal.aborted)return
   setData(result)
   if(compare&&canCompareGroundTruth(result)){
    const query=new URLSearchParams({product_id:result.product_id!,view,min_confidence:String(catalog.rtdetr_visualization_threshold),limit:'500'})
    const response=await fetch(address(`/products/findings?${query}`),{signal:controller.signal});if(!response.ok)throw new Error(`비교 박스 API ${response.status}`)
    const findings=await response.json();if(!controller.signal.aborted)setBoxes(findings.findings)
   }
  }).catch(e=>{if(!controller.signal.aborted)setError(String(e))}).finally(()=>{if(!controller.signal.aborted)setLoading(false)})
  return ()=>controller.abort()
 },[item,view,catalog,chosen,individual,compare])
 const range=useMemo(()=>data?gridRange({grid_width:64,grid_height:64,values:data[metric],coverage_mask:data.coverage_mask,valid_observation_counts:data.known_count,aggregation_method:absolute?'product_occupancy':'mask_relative'}):[0,0],[data,metric,absolute])
 return <section className="space-y-3 rounded-lg border border-line bg-panel p-4" aria-label="MV 실제 마스크 위치 분포">
  <h2 className="text-sm font-semibold text-tx">A · 실제 불량 마스크 위치 분포 {compare?'＋ B · 동일 제품 RT 검출 비교':''}</h2>
  <p className="text-xs text-warn">기존 MV Train NG 분석 재사용 · 운영 추론 결과/전체 불량률/Test 분포가 아닙니다. 카메라 간 합산과 3D 물리 표면 투영은 하지 않습니다. 64격자는 원본 양성 픽셀이 하나라도 있는 셀이며 정밀 결함 경계가 아닙니다.</p>
  <div className="flex flex-wrap gap-2">
   <select className="btn" aria-label="마스크 카메라" value={view} onChange={e=>setView(e.target.value)}>{['C1','C2','C3','C4','C5'].map(v=><option key={v}>{v}</option>)}</select>
   <select className="btn" aria-label="마스크 집계 범위" value={individual||compare?'product':'aggregate'} disabled={compare} onChange={e=>setIndividual(e.target.value==='product')}><option value="aggregate">품목별 Train NG 집계</option><option value="product">개별 실제 마스크 표본</option></select>
   {(individual||compare)&&<select className="btn max-w-full" aria-label="마스크 표본 제품" value={chosen??''} onChange={e=>setProduct(e.target.value)}>{products.map(p=><option key={p}>{p}</option>)}</select>}
   <select className="btn" aria-label="마스크 분모 지표" value={metric} onChange={e=>setMetric(e.target.value as typeof metric)}><option value="defect_rate">제공 마스크 기준 위치 빈도</option><option value="occupancy_positive">양성 마스크 조건 위치 빈도</option><option value="mask_coverage">평균 전경 면적 비율</option></select>
   <label className="flex items-center gap-1 text-xs text-muted"><input type="checkbox" checked={absolute} onChange={e=>setAbsolute(e.target.checked)}/>절대 색상 0–1</label>
   <label className="flex items-center gap-1 text-xs text-muted">투명도<input aria-label="마스크 히트맵 투명도" type="range" min="0" max="1" step=".05" value={opacity} onChange={e=>setOpacity(Number(e.target.value))}/></label>
  </div>
  {loading&&<p role="status" className="text-xs text-muted">기존 64×64 수치 조회 중…</p>}
  {error&&<p role="alert" className="text-xs text-warn">{error} · 가상 분포로 대체하지 않습니다.</p>}
  {data&&data.item===item&&data.view===view&&data.product_id===((individual||compare)?chosen:null)&&<>
   <p className="text-xs text-muted">분할 {data.split} · {data.view} · NG 제품 {data.product_count} · 제공 마스크 {data.known_products} · 양성 마스크 {data.positive_mask_products} · unknown {data.unknown_products} · {data.known_products<MIN_DENOMINATOR?'표본 부족':'최소 분모 충족'} · 원본 {data.source_image_width}×{data.source_image_height} / 격자64²</p>
   {!data.known_products?<p className="text-sm text-warn">제공 마스크 없음 · unknown입니다. 정상 위치 또는 0%로 표시하지 않습니다.</p>:<TruthCanvas key={`${data.item}:${data.product_id??"aggregate"}:${data.view}`} data={data} metric={metric} absolute={absolute} opacity={opacity} boxes={boxes} onCell={setPicked}/>}
   <p className="text-xs text-muted">{absolute?'절대':'현재 지도 상대'} 색상 범위 {range[0].toFixed(4)}–{range[1].toFixed(4)} <span className="inline-block h-2 w-28" style={{background:HEAT_GRADIENT_CSS}}/> · x → / y ↓ · 미관측 투명 · 표본 부족 사선 · 최근접 표시</p>
   {picked!==null&&<p className="text-xs text-tx">셀 ({picked%64},{Math.floor(picked/64)}) · 불량 위치 관측 {data.positive_count[picked]} / 제공 마스크 {data.known_count[picked]} · unknown {data.unknown_count[picked]} · 선택 지표 {data[metric][picked]?.toFixed(5)??'미관측'}</p>}
   {compare&&<p className="text-xs text-warn">{canCompareGroundTruth(data)?`동일 제품·시점·train·원본 SHA 일치 확인 · 주황 박스 ${boxes.length}개는 RT 예측, 격자 색은 실제 마스크입니다. 비교는 공식 퓨전이 아닙니다.`:'마스크/분할/원본 일치 미확인 → 모델 신호를 겹치지 않습니다.'}</p>}
   {data.mask_url&&<a className="text-xs text-signal underline" href={address(data.mask_url)} target="_blank" rel="noreferrer">실제 제공 마스크 PNG 원본</a>}
  </>}
 </section>
}
