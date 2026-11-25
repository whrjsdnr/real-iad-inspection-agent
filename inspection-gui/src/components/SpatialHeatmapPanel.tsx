import {useEffect,useMemo,useRef,useState} from 'react'
import {API_BASE,MIN_DENOMINATOR} from '../config'
import {useStore} from '../store'
import {gridTexture,gridRange,nativeCell,type SpatialGrid} from '../three/spatialGrid'
import {HEAT_GRADIENT_CSS,rateToColor} from '../utils/heat'
import {useSpatialFocus} from '../three/spatialActions'
import {cssVar} from '../utils/tokens'
type Entry={grid_id:string;item:string;product_id:string;camera:string;region_id:string;parent_region_id:string|null;label:string;resolution:number;hvq_status:string;recommended_rt_resolution?:number;recommended_hvq_resolution?:number|null}
type Index={entries:Entry[];physical_surface_mapping:string}
const RT_METHODS={gaussian:'Gaussian 위치 밀도',center_count:'박스 중심점',box_area:'박스 면적 누적',confidence_area:'Confidence 가중 면적',product_occupancy:'제품 공간 점유',mean_confidence:'평균 Confidence'}
const HVQ_METHODS={mean:'이상 점수 평균',max:'이상 점수 최대',percentile:'이상 점수 백분위'}
const address=(path:string)=>API_BASE.replace(/\/$/,'')+path

function GridCanvas({grid,extra,opacity,flat,selected,onPick,onHover}:{grid:SpatialGrid;extra?:SpatialGrid|null;opacity:number;flat:boolean;selected:ReturnType<typeof nativeCell>;onPick:(x:number,y:number)=>void;onHover:(x:number,y:number)=>void}){
 const canvas=useRef<HTMLCanvasElement>(null)
 const hoverFrame=useRef<number|null>(null)
 const [sourceImage,setSourceImage]=useState<HTMLImageElement|null>(null)
 const [imageError,setImageError]=useState(false)
 useEffect(()=>{
  let live=true;const image=new Image();setSourceImage(null);setImageError(false)
  image.onload=()=>{if(live)setSourceImage(image)}
  image.onerror=()=>{if(live)setImageError(true)}
  image.src=address(grid.image_url)
  return ()=>{live=false;image.onload=null;image.onerror=null;image.src=''}
 },[grid.image_url])
 useEffect(()=>()=>{if(hoverFrame.current!==null)cancelAnimationFrame(hoverFrame.current)},[])
 useEffect(()=>{
  const element=canvas.current;if(!element)return
  const context=element.getContext('2d');if(!context)return
  if(!sourceImage)return
  const draw=()=>{
   const start=performance.now(),[width,height]=grid.original_size
   element.width=width;element.height=height;context.drawImage(sourceImage,0,0,width,height)
   for(const layer of [grid,...(extra?.status==='supported'?[extra]:[])]){
   if(layer.status==='supported'&&opacity>0){
    const source=document.createElement('canvas');source.width=layer.grid_width;source.height=layer.grid_height
    const sourceContext=source.getContext('2d')!
    // CPU Canvas fallback uses the same DataTexture buffer as the validated UV
    // path. This image-plane rendering is not a product-surface projection.
    const texture=gridTexture(layer,extra?.status==='supported'?opacity/2:opacity)
    const pixels=new Uint8ClampedArray(texture.image.data)
    if(flat){
     const range=gridRange(layer),raw=layer.region_value??0
     const color=rateToColor(layer.model==='rt'?raw:range[1]>range[0]?(raw-range[0])/(range[1]-range[0]):0)
     for(let i=0;i<pixels.length;i+=4)if(pixels[i+3]){pixels[i]=parseInt(color.slice(1,3),16);pixels[i+1]=parseInt(color.slice(3,5),16);pixels[i+2]=parseInt(color.slice(5,7),16)}
    }
    sourceContext.putImageData(new ImageData(pixels,layer.grid_width,layer.grid_height),0,0)
    texture.dispose()
    if(layer.valid_observation_counts.some(count=>count>0&&count<MIN_DENOMINATOR)){
     const hatch=document.createElement('canvas');hatch.width=8;hatch.height=8
     const h=hatch.getContext('2d')!;h.strokeStyle=cssVar('--text');h.globalAlpha=.2
     h.beginPath();h.moveTo(0,8);h.lineTo(8,0);h.stroke()
     sourceContext.globalCompositeOperation='source-atop';sourceContext.fillStyle=sourceContext.createPattern(hatch,'repeat')!
     sourceContext.fillRect(0,0,source.width,source.height);hatch.width=0;hatch.height=0
    }
    const [x0,y0,x1,y1]=layer.roi_bounds
    context.imageSmoothingEnabled=false
    context.drawImage(source,x0,y0,x1-x0,y1-y0)
    source.width=0;source.height=0
   }
   }
   if(selected){
    const [x0,y0,x1,y1]=grid.roi_bounds,x=x0+(selected.column+.5)*(x1-x0)/grid.grid_width,y=y0+(selected.row+.5)*(y1-y0)/grid.grid_height
    context.strokeStyle=cssVar('--text');context.lineWidth=2;context.beginPath();context.moveTo(x-10,y);context.lineTo(x+10,y);context.moveTo(x,y-10);context.lineTo(x,y+10);context.stroke()
   }
   Reflect.set(window,'__spatialRenderMs',performance.now()-start)
  }
  draw()
  return ()=>{element.width=0;element.height=0}
 },[grid,extra,opacity,flat,selected,sourceImage])
 return <>{imageError&&<p role="alert" className="text-xs text-warn">원본 영상 조회 실패 · 공간 지도와 영상의 위치 대조를 완료할 수 없습니다.</p>}<canvas ref={canvas} aria-label={flat?'동일 제품의 부위 단색 비교':'실제 검사 근거의 공간 히트맵'} className="w-full rounded-md border border-line bg-panel" onMouseMove={event=>{
  const rect=event.currentTarget.getBoundingClientRect(),x=(event.clientX-rect.left)/rect.width*grid.original_size[0],y=(event.clientY-rect.top)/rect.height*grid.original_size[1]
  if(hoverFrame.current!==null)cancelAnimationFrame(hoverFrame.current)
  hoverFrame.current=requestAnimationFrame(()=>{hoverFrame.current=null;onHover(x,y)})
 }} onClick={event=>{const rect=event.currentTarget.getBoundingClientRect();onPick((event.clientX-rect.left)/rect.width*grid.original_size[0],(event.clientY-rect.top)/rect.height*grid.original_size[1])}}/></>
}

export function SpatialHeatmapPanel({initialModel='rt',onGridChange}:{initialModel?:'rt'|'hvq'|'overlay';onGridChange?:(grid:SpatialGrid|null)=>void}={}){
 const item=useStore(state=>state.filters.item)
 const [index,setIndex]=useState<Index|null>(null),[error,setError]=useState<string|null>(null)
 const [product,setProduct]=useState(''),[camera,setCamera]=useState('C1'),[region,setRegion]=useState(''),[resolution,setResolution]=useState(32)
 const [model,setModel]=useState<'rt'|'hvq'|'overlay'>(initialModel),[method,setMethod]=useState(initialModel==='hvq'?'mean':'confidence_area'),[opacity,setOpacity]=useState(.7)
 const [overlay,setOverlay]=useState<SpatialGrid|null>(null)
 const [grid,setGrid]=useState<SpatialGrid|null>(null),[loading,setLoading]=useState(false),[zoom,setZoom]=useState(false)
 const [picked,setPicked]=useState<ReturnType<typeof nativeCell>>(null)
 const [hovered,setHovered]=useState<ReturnType<typeof nativeCell>>(null)
 useEffect(()=>{setModel(initialModel);setMethod(initialModel==='hvq'?'mean':'confidence_area')},[initialModel])
 useEffect(()=>{onGridChange?.(grid);return ()=>onGridChange?.(null)},[grid,onGridChange])
 useEffect(()=>{
  const controller=new AbortController();setIndex(null);setGrid(null);setError(null)
  fetch(address(`/parts/spatial/index?item=${encodeURIComponent(item)}`),{signal:controller.signal}).then(response=>{if(!response.ok)throw new Error(`공간 API ${response.status}`);return response.json()}).then(data=>setIndex(data)).catch(e=>{if(!controller.signal.aborted)setError(String(e))})
  return ()=>controller.abort()
 },[item])
 const entries=index?.entries??[]
 const focus=useSpatialFocus(state=>state.pending)
 useEffect(()=>{
  if(!focus||!index)return
  const entry=index.entries.find(entry=>entry.grid_id===focus.grid_id)
  if(!entry)return
  setProduct(entry.product_id);setCamera(entry.camera);setRegion(entry.region_id);setResolution(entry.resolution)
  setModel(focus.model);setMethod(focus.method);useSpatialFocus.getState().set(null)
 },[focus,index])
 const products=[...new Set(entries.map(entry=>entry.product_id))]
 const selectedProduct=products.includes(product)?product:products[0]
 const cameras=[...new Set(entries.filter(entry=>entry.product_id===selectedProduct).map(entry=>entry.camera))]
 const selectedCamera=cameras.includes(camera)?camera:cameras[0]
 const regions=[...new Map(entries.filter(entry=>entry.product_id===selectedProduct&&entry.camera===selectedCamera).map(entry=>[entry.region_id,entry])).values()]
 const selectedRegion=regions.some(entry=>entry.region_id===region)?region:regions[0]?.region_id
 const selected=entries.find(entry=>entry.product_id===selectedProduct&&entry.camera===selectedCamera&&entry.region_id===selectedRegion&&entry.resolution===resolution)
 useEffect(()=>{
  if(!selected){setGrid(null);return}
  const controller=new AbortController();setLoading(true);setPicked(null);setHovered(null);setGrid(null);setError(null)
  const start=performance.now()
  const read=async(selectedModel:'rt'|'hvq',selectedMethod:string)=>{
   const params=new URLSearchParams({item:selected.item,product_id:selected.product_id,view:selected.camera,region_id:selected.region_id,resolution:String(selected.resolution),model:selectedModel,method:selectedMethod})
   const response=await fetch(address(`/parts/spatial-heatmap?${params}`),{signal:controller.signal})
   if(!response.ok)throw new Error(`공간 지도 ${response.status}`)
   return await response.json() as SpatialGrid
  }
  Promise.all([read(model==='overlay'?'rt':model,method),model==='overlay'?read('hvq','mean'):Promise.resolve(null)]).then(([data,extra])=>{
   if(controller.signal.aborted)return
   if(data.product_id!==selected.product_id||data.view_id!==selected.camera||data.region_id!==selected.region_id)throw new Error('공간 응답의 제품/시점/부위 불일치')
   setGrid(data);setOverlay(extra);Reflect.set(window,'__spatialApiMs',performance.now()-start)
  }).catch(e=>{if(!controller.signal.aborted)setError(String(e))}).finally(()=>{if(!controller.signal.aborted)setLoading(false)})
  return ()=>controller.abort()
 },[selected,model,method])
 const hotspots=useMemo(()=>grid?.values.map((value,index)=>({value,index})).filter((cell):cell is {value:number;index:number}=>cell.value!==null&&cell.value>0&&Number.isFinite(cell.value)&&grid.valid_observation_counts[cell.index]>0).sort((a,b)=>b.value-a.value).slice(0,5)??[],[grid])
 const range=grid?gridRange(grid):[0,0]
 const pick=(x:number,y:number)=>{if(grid)setPicked(nativeCell(grid,x,y))}
 const hover=(x:number,y:number)=>{if(grid)setHovered(nativeCell(grid,x,y))}
 return <section className="mt-4 space-y-3 rounded-lg border border-line bg-panel p-3" aria-label="세부 공간 히트맵">
  <h3 className="text-sm font-semibold text-tx">세부 공간 히트맵 · 개별 제품 / 단일 카메라</h3>
  <p className="text-xs text-muted">기간·검수 필터와 별도의 저장 근거 제품 선택입니다. 3D 물리 표면 대응 미검증 → 원본 영상의 2D 공간 지도로 표시합니다. 박스 내부 전체가 실제 불량 마스크라는 의미는 아닙니다.</p>
  {error&&<p role="alert" className="text-xs text-warn">{error} · 저장된 공간 캐시/API 반영을 확인하세요.</p>}
  {!entries.length&&!error&&<p role="status" className="text-xs text-muted">이 품목의 등록 공간 근거가 없습니다. 가상의 공간 패턴은 표시하지 않습니다.</p>}
  {!!entries.length&&<>
   <div className="flex flex-wrap gap-2">
    <select aria-label="공간 근거 제품" className="btn max-w-full" value={selectedProduct} onChange={e=>setProduct(e.target.value)}>{products.map(p=><option key={p}>{p}</option>)}</select>
    <select aria-label="공간 카메라" className="btn" value={selectedCamera} onChange={e=>setCamera(e.target.value)}>{cameras.map(c=><option key={c}>{c}</option>)}</select>
    <select aria-label="세부 부위" className="btn" value={selectedRegion} onChange={e=>setRegion(e.target.value)}>{regions.map(r=><option key={r.region_id} value={r.region_id}>{r.parent_region_id?'↳ ':''}{r.label}</option>)}</select>
    <select aria-label="공간 해상도" className="btn" value={resolution} onChange={e=>setResolution(Number(e.target.value))}>{[16,32,64,128].map(r=><option key={r} value={r}>{r}×{r}</option>)}</select>
    <select aria-label="공간 모델" className="btn" value={model} onChange={e=>{const value=e.target.value as 'rt'|'hvq'|'overlay';setModel(value);setMethod(value==='hvq'?'mean':'gaussian')}}><option value="rt">RT-DETR 위치 분포</option><option value="hvq">HVQ 실제 이상 맵</option><option value="overlay">두 모델 시각적 중첩</option></select>
    <select aria-label="공간 집계 방법" className="btn" value={method} onChange={e=>setMethod(e.target.value)}>{Object.entries(model==='hvq'?HVQ_METHODS:RT_METHODS).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select>
   </div>
   {selected&&<p className="text-xs text-muted">원시 정보 기준 권장: RT {selected.recommended_rt_resolution??64}×{selected.recommended_rt_resolution??64} · HVQ {selected.recommended_hvq_resolution?`${selected.recommended_hvq_resolution}×${selected.recommended_hvq_resolution}`:'실제 맵 미지원 또는 희소'} <button className="btn" onClick={()=>setResolution(model==='hvq'?(selected.recommended_hvq_resolution??16):(selected.recommended_rt_resolution??64))}>권장 해상도 적용</button></p>}
   <div className="flex flex-wrap items-center gap-3 text-xs text-muted"><label>투명도 <input aria-label="공간 히트맵 투명도" type="range" min="0" max="1" step="0.05" value={opacity} onChange={e=>setOpacity(Number(e.target.value))}/></label><button className="btn" onClick={()=>setOpacity(opacity?0:.7)}>{opacity?'히트맵 숨김':'히트맵 표시'}</button><button className="btn" onClick={()=>setZoom(!zoom)}>{zoom?'비교 크기로':'확대 보기'}</button></div>
   {loading&&<p role="status" className="text-xs text-muted">저장된 공간 지도 조회 중…</p>}
   {grid?.status==='unsupported'&&<p role="status" className="text-xs text-warn">실제 저장 Anomaly Map 없음 · 공간 지도 미지원. 스칼라 점수로 대체하지 않습니다.</p>}
   {model==='overlay'&&<p className="text-xs text-warn">RT 공간 신호와 HVQ 평균의 시각적 중첩 · 공식 퓨전 판정이 아닙니다.{overlay?.status==='unsupported'?' 이 제품은 실제 HVQ 맵이 없어 RT만 표시됩니다.':''}</p>}
   {method==='gaussian'&&<p className="text-xs text-warn">Gaussian은 실제 박스 중심의 검출 밀도를 부드럽게 표현하는 시각화이며 실제 불량 영역이나 불량 마스크가 아닙니다.</p>}
   {grid?.status==='supported'&&<>
    <div className={`grid gap-3 ${zoom?'grid-cols-1':'md:grid-cols-2'}`}><div><p className="mb-1 text-xs text-muted">동일 제품 · 부위 단색 비교</p><GridCanvas grid={grid} extra={model==='overlay'?overlay:null} opacity={opacity} flat selected={picked} onPick={pick} onHover={hover}/></div><div><p className="mb-1 text-xs text-muted">부위 내부 공간 분포 · 클릭하여 근거 선택</p><GridCanvas grid={grid} extra={model==='overlay'?overlay:null} opacity={opacity} flat={false} selected={picked} onPick={pick} onHover={hover}/></div></div>
    {hovered&&<p className="text-xs text-muted">Hover ({hovered.column},{hovered.row}) · {hovered.value==null?'원시 공간 표본 없음':hovered.value.toFixed(4)} · 관측 {hovered.observed}</p>}
    <p className="text-xs text-muted">현재 제품·부위 상대 색상 {range[0].toFixed(3)} ~ {range[1].toFixed(3)} <span className="inline-block h-2 w-28 rounded" style={{background:HEAT_GRADIENT_CSS}}/> · 빈 칸은 미관측/원시 맵 표본 없음 · 최근접 표시, 보간 없음 · 검출 밀도 0은 정상 판정이 아닙니다.</p>
    <p className="text-xs text-warn">관측 제품 {grid.stats.observed_products} / 최소 표본 {MIN_DENOMINATOR} · {grid.stats.observed_products<MIN_DENOMINATOR?'표본 부족':''} · 확정 불량률/공식 퓨전 판정이 아닙니다.</p>
    <p className="text-xs text-muted">검출 {grid.stats.detection_count}개 · 검출 제품 {grid.stats.detected_products}/{grid.stats.observed_products} · 박스 격자 점유 {grid.stats.spatial_occupancy==null?'—':`${(grid.stats.spatial_occupancy*100).toFixed(1)}% (${grid.stats.occupied_cell_count}/${grid.stats.observed_cell_count}셀)`}{grid.native_map_size?` · 원시 맵 ${grid.native_map_size.join('×')}`:''} · ROI 영상 관측 기준이며 물리 표면의 발생률·불량률이 아닙니다.</p>
    {picked&&<p className="text-xs text-tx">선택 셀 ({picked.column},{picked.row}) · {!picked.covered?'ROI 외부 / 미관측':!picked.observed?'이 해상도의 원시 공간 표본 없음':picked.value===null?'관측됐으나 이 집계의 유효 값 없음':`값 ${picked.value.toFixed(4)} · 유효 관측 ${picked.observed}${picked.value===0?' · 관측된 검출/신호 0':''}`}</p>}
    <div className="flex flex-wrap gap-1 text-xs text-muted"><span>공간 신호 상위 셀</span>{hotspots.map((cell,i)=><button className="btn" key={cell.index} onClick={()=>setPicked({column:cell.index%grid.grid_width,row:Math.floor(cell.index/grid.grid_width),index:cell.index,value:cell.value,observed:grid.valid_observation_counts[cell.index],covered:true})}>{i+1}. ({cell.index%grid.grid_width},{Math.floor(cell.index/grid.grid_width)}) {cell.value.toFixed(2)}</button>)}</div>
   </>}
  </>}
 </section>
}
