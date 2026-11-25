import { useEffect,useRef,useState } from 'react'
import { navigate } from '../router'
import { PRECISION_FRAME_TITLE,isPrecisionNavigation,precisionDocument } from './precisionDocument'

export function PrecisionIntro({onFallback}:{onFallback:()=>void}){
 const frame=useRef<HTMLIFrameElement>(null)
 const [ready,setReady]=useState(false)
 useEffect(()=>{
  const target=frame.current?.contentWindow??null
  const onMessage=(event:MessageEvent)=>{if(isPrecisionNavigation(event,target))navigate('#/dashboard')}
  window.addEventListener('message',onMessage)
  return ()=>{window.removeEventListener('message',onMessage);target?.postMessage({type:'inspect-precision:dispose'},'*')}
 },[])
 return <section className="w-full" aria-label="팀원 Precision 인트로">
  <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-panel px-4 py-3">
   <div><span className="font-mono text-xs text-ok">INSPECT AI · PRECISION STUDIO</span><p className="mt-1 text-xs text-muted">가상 플랜지와 5시점 카메라 시연 · 실제 검사 데이터가 아닙니다</p></div>
   <div className="flex flex-wrap gap-2"><button className="btn" onClick={onFallback}>기존 개념 인트로</button><button className="btn btn-active px-4 py-2" onClick={()=>navigate('#/dashboard')}>대시보드 시작하기 →</button></div>
  </div>
  {!ready&&<p className="mb-2 text-xs text-muted" role="status">Precision 시연을 불러오는 중… 대시보드는 바로 열 수 있습니다.</p>}
  <iframe ref={frame} title={PRECISION_FRAME_TITLE} srcDoc={precisionDocument} sandbox="allow-scripts" referrerPolicy="same-origin" onLoad={()=>setReady(true)} className="block h-[1120px] w-full rounded-xl border border-line md:h-[1030px] 2xl:h-[1100px]" />
  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-muted"><p>팀원 V6 디자인 반영 · 시연 속 결함·점수는 예시이며 카메라 배치는 개념도입니다.</p><button className="btn btn-active" onClick={()=>navigate('#/dashboard')}>검사 대시보드 열기</button></div>
 </section>
}
