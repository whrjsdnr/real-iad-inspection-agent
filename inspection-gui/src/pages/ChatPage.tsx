import { useEffect, useRef, useState } from 'react'
import { SendHorizonal } from 'lucide-react'
import { API_BASE } from '../config'
import { dashboardFocusLink } from '../router'
import { GuiContextControls } from '../components/GuiContextControls'
import { useStore } from '../store'
import {SpatialEvidenceLink} from '../components/SpatialEvidenceLink'

interface Msg {
  role: 'user' | 'agent'
  text: string
  mode?: string
}

/** 실데이터 제품 ID 패턴 — 답변 속 근거를 대시보드 사례 뷰 링크로 바꾼다. */
const PRODUCT_ID_RE =
  /\b([a-z][a-z0-9_]*\/(?:NG|OK)\/[A-Z]{1,6}\/S\d{3,})\b|\b([a-z][a-z0-9_]*_(?:defect|normal)_\d{3,})\b|spatial:\/\/([a-f0-9]{24})\/(rt|hvq)\/([a-z_]+)/g

function linkify(text: string): React.ReactNode[] {
  const out: React.ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null
  let k = 0
  PRODUCT_ID_RE.lastIndex = 0
  while ((m = PRODUCT_ID_RE.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if(m[3]){out.push(<SpatialEvidenceLink key={k++} gridId={m[3]} model={m[4]} method={m[5]}/>);last=m.index+m[0].length;continue}
    const id = m[1] ?? m[2]
    out.push(
      <a
        key={k++}
        href={dashboardFocusLink(id)}
        className="font-mono text-signal underline decoration-dotted underline-offset-2 hover:opacity-80"
        title="대시보드 사례 뷰로 이동"
      >
        {id}
      </a>,
    )
    last = m.index + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

/** 에이전트 챗봇 메뉴 — 좌측 액센트 버블, 도구 조회 스켈레톤, 하단 고정 입력. */
export function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [llmMode, setLlmMode] = useState<string | null>(null)
  const [backendDown, setBackendDown] = useState(false)
  const [readOnly,setReadOnly]=useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((d) => {setLlmMode(d.llm?.mode ?? 'mock');setReadOnly(d.read_only===true);useStore.setState({readOnly:d.read_only===true,...(d.read_only?{reviewMode:false}:{})})})
      .catch(() => setLlmMode('offline'))
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [msgs])

  const send = async () => {
    const q = input.trim()
    if (!q || busy || readOnly) return
    setInput('')
    setBusy(true)
    setMsgs((m) => [...m, { role: 'user', text: q }])
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: `[GUI 선택 컨텍스트: ${JSON.stringify({category:useStore.getState().filters.item,product:useStore.getState().filters.productId,region:useStore.getState().selectedPart})}]\n${q}` }),
        signal: AbortSignal.timeout(60000),
      })
      const d = await res.json()
      if (!res.ok) throw new Error(d.error?.message ?? `HTTP ${res.status}`)
      setBackendDown(false)
      setMsgs((m) => [
        ...m,
        { role: 'agent', text: d.answer ?? '(응답 없음)', mode: d.mode },
      ])
    } catch (e) {
      setBackendDown(true)
      setMsgs((m) => [
        ...m,
        {
          role: 'agent',
          text: `백엔드 연결 실패: ${String(e)}\n백엔드(FastAPI) 기동 여부를 확인하세요.`,
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  const mode = llmMode ?? 'unknown'
  const querySpace=async()=>{
    setBusy(true)
    try{
      const state=useStore.getState()
      const response=await fetch(`${API_BASE}/tools/query_spatial_evidence`,{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(8000),body:JSON.stringify({item:state.filters.item,product_id:state.filters.productId==='all'?null:state.filters.productId,region_id:state.selectedPart,camera:state.viewer.open?state.viewer.view:'C1',model:'rt',limit:5})})
      const data=await response.json()
      if(!response.ok)throw new Error(data.error?.message??`공간 근거 ${response.status}`)
      const text=data.status==='supported'?`저장 근거: ${data.product_id} / ${data.view_id} / ${data.region_id}\n검출 제품 ${data.stats.detected_products}/${data.stats.observed_products} · ${data.sample_status==='insufficient_sample'?'표본 부족':'표본 상태 확인'}\n상위 공간 신호 ${data.hotspots.map((p:{column:number;row:number;value:number})=>`(${p.column},${p.row}) ${p.value.toFixed(3)}`).join(', ')}\n${data.evidence_link}\n개별 제품의 모델 신호이며 확정 불량률/공식 퓨전 판정이 아닙니다.`:`공간 근거 미지원/미조회: ${data.reason}`
      setMsgs(messages=>[...messages,{role:'agent',text,mode:'저장 근거 조회'}])
    }catch(error){setMsgs(messages=>[...messages,{role:'agent',text:String(error),mode:'조회 실패'}])}
    finally{setBusy(false)}
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-140px)] w-full max-w-3xl flex-col py-2">
      <div className="motion-rise mb-2 flex items-center gap-2" style={{ ['--i' as string]: 0 }}>
        <h1 className="font-mono text-[11px] font-semibold uppercase tracking-wide2 text-tx">
          외관검사 에이전트
        </h1>
        {mode !== 'real' ? (
          <span className="chip border-dashed border-warn/60 bg-warn/5 text-warn">
            <span className="live-dot live-dot--warn" style={{ animation: 'none' }} />
            {readOnly?'팀 공유 · 읽기 전용':mode === 'mock' ? 'LLM 미연결 · 도구 직접 응답' : mode === 'offline' ? '서버 연결 실패' : '연결 확인 중'}
          </span>
        ) : (
          <span className="chip border-line bg-panel-raised text-ok">
            <span className="live-dot" />
            Ollama 연결
          </span>
        )}
        {backendDown && (
          <span className="chip border-dashed border-fail/60 bg-fail/5 text-fail">
            백엔드 오프라인
          </span>
        )}
        <span className="ml-auto font-mono text-[9px] uppercase tracking-label text-faint">
          도구 근거 답변 · 분자/분모 포함
        </span>
      </div>

      <GuiContextControls />
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted"><button className="btn" disabled={busy} onClick={()=>void querySpace()}>선택 부위 공간 근거 조회</button>{readOnly&&<span>공유 모드에서는 저장 근거 조회를 사용하세요. 추론·검수 쓰기는 제공하지 않습니다.</span>}</div>
      <div
        ref={listRef}
        className="motion-rise glass flex-1 space-y-2 overflow-y-auto p-3"
        style={{ ['--i' as string]: 1 }}
        aria-live="polite"
      >
        {msgs.length === 0 && (
          <div className="space-y-1 p-2 font-mono text-[11px] text-faint">
            <p>예시 질문:</p>
            <ul className="list-inside list-disc space-y-0.5">
              <li>칫솔모에서 미탐률이 높았어?</li>
              <li>검수 대기 건수가 몇 개야?</li>
              <li>최종 성능 F1이랑 기준선이랑 비교해줘</li>
            </ul>
          </div>
        )}
        {msgs.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] whitespace-pre-wrap rounded-r-md rounded-bl-md border-l-2 px-3 py-2 text-xs leading-relaxed ${
              m.role === 'user'
                ? 'ml-auto border-l-signal/70 bg-signal/10 text-tx'
                : 'border-l-line bg-panel-raised/80 text-muted'
            }`}
          >
            {m.role === 'agent' ? linkify(m.text) : m.text}
            {m.mode && (
              <div className="mt-1 font-mono text-[8px] uppercase tracking-label text-faint">
                {m.mode}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="space-y-1.5">
            <div className="skeleton h-3.5 w-2/3 rounded" />
            <div className="skeleton h-3.5 w-1/2 rounded" />
            <div className="font-mono text-[9px] uppercase tracking-label text-faint">
              도구 조회 중…
            </div>
          </div>
        )}
      </div>

      <div className="motion-rise mt-2 flex gap-2" style={{ ['--i' as string]: 2 }}>
        <input
          className="input flex-1"
          placeholder={readOnly?'읽기 전용 공유 · 위 공간 근거 조회를 사용하세요':'질문을 입력하세요 (Enter)'}
          disabled={readOnly}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <button
          type="button"
          className="cta-glow inline-flex items-center gap-1.5 rounded-md px-4 py-1.5 font-mono text-xs font-semibold"
          onClick={send}
          disabled={busy||readOnly}
        >
          <SendHorizonal size={14} strokeWidth={1.5} aria-hidden />
          전송
        </button>
      </div>
    </div>
  )
}
