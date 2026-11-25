import { useEffect, useRef, useState } from 'react'
import { API_BASE } from '../config'

interface Msg {
  role: 'user' | 'agent'
  text: string
  mode?: string
}

/** LLM 에이전트 챗봇 패널. /chat 프록시 사용, 목 모드는 배너로 표시. */
export function ChatPanel() {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [llmMode, setLlmMode] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((d) => setLlmMode(d.llm?.mode ?? 'mock'))
      .catch(() => setLlmMode('mock'))
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [msgs, open])

  const send = async () => {
    const q = input.trim()
    if (!q || busy) return
    setInput('')
    setBusy(true)
    setMsgs((m) => [...m, { role: 'user', text: q }])
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      })
      const d = await res.json()
      setMsgs((m) => [
        ...m,
        {
          role: 'agent',
          text: d.answer ?? d.error?.message ?? '(응답 없음)',
          mode: d.mode,
        },
      ])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'agent', text: `백엔드 연결 실패: ${String(e)}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="glass p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button type="button" className="btn px-3 py-1 text-xs" onClick={() => setOpen(!open)}>
            {open ? '챗봇 접기' : '챗봇 열기'}
          </button>
          <span className="text-xs font-semibold text-slate-300">외관검사 에이전트 (Qwen)</span>
          {llmMode === 'mock' && (
            <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
              목 모드
            </span>
          )}
          {llmMode === 'real' && (
            <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
              Ollama 연결
            </span>
          )}
        </div>
        <span className="text-[10px] text-slate-500">
          도구 조회 결과에 근거해서만 답변 · 수치는 분자/분모 포함
        </span>
      </div>
      {open && (
        <div>
          <div ref={listRef} className="mb-2 h-56 space-y-2 overflow-y-auto rounded-lg bg-black/30 p-2">
            {msgs.length === 0 && (
              <div className="p-2 text-xs text-slate-500">
                예: "칫솔모에서 미탐률이 높았어?", "검수 대기 건수가 몇 개야?"
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                m.role === 'user'
                  ? 'ml-auto bg-accent-cyan/20 text-slate-100'
                  : 'bg-white/5 text-slate-200'
              }`}>
                {m.text}
              </div>
            ))}
            {busy && <div className="text-[10px] text-slate-500">에이전트가 도구를 조회하는 중…</div>}
          </div>
          <div className="flex gap-2">
            <input
              className="input flex-1 text-xs"
              placeholder="질문을 입력하세요"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
            />
            <button type="button" className="btn px-4 py-1 text-xs" onClick={send} disabled={busy}>
              전송
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
