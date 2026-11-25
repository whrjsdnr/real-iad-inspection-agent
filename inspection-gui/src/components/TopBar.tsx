import { useEffect, useState } from 'react'
import { API_BASE, itemLabel } from '../config'
import { useLiveClock } from '../hooks/useCountUp'
import { useStore } from '../store'
import { VIEW_IDS, type ViewId } from '../types'
import { SourceBadge } from './bits'

/** 뷰파인더 스타일 C1~C5 인디케이터 — 사례 뷰어가 열린 경우 현재 칼라 하이라이트. */
function Viewfinder() {
  const viewer = useStore((s) => s.viewer)
  const setViewerView = useStore((s) => s.setViewerView)
  const open = viewer.open
  return (
    <div className="flex items-center gap-1" role="group" aria-label="칼라 인디케이터">
      {VIEW_IDS.map((vid: ViewId) => {
        const active = open && viewer.view === vid
        return (
          <button
            key={vid}
            type="button"
            aria-pressed={active}
            disabled={!open}
            title={open ? `칼라 ${vid}` : '사례 뷰어를 열어 칼라를 표시합니다'}
            onClick={() => setViewerView(vid)}
            className={`relative h-6 w-9 rounded-sm border font-mono text-[9px] tracking-label transition-colors duration-150 ${
              active
                ? 'border-signal/70 bg-signal/10 text-signal'
                : 'border-line bg-panel-raised text-faint hover:border-faint/60'
            } ${open ? '' : 'opacity-60'}`}
          >
            {/* 뷰파인더 코너 마크 */}
            <span aria-hidden className="pointer-events-none absolute inset-0">
              <i className="absolute left-0 top-0 h-1.5 w-1.5 border-l border-t border-current opacity-70" />
              <i className="absolute right-0 top-0 h-1.5 w-1.5 border-r border-t border-current opacity-70" />
              <i className="absolute bottom-0 left-0 h-1.5 w-1.5 border-b border-l border-current opacity-70" />
              <i className="absolute bottom-0 right-0 h-1.5 w-1.5 border-b border-r border-current opacity-70" />
            </span>
            {vid}
          </button>
        )
      })}
    </div>
  )
}

/** 고정 미션 헤더 — 좌: 품목 / 중: C1~C5 뷰파인더 / 우: 시계·백엔드 상태. */
export function TopBar() {
  const clock = useLiveClock()
  const [backend, setBackend] = useState<'up' | 'down' | 'unknown'>('unknown')
  const [llmMode, setLlmMode] = useState<string | null>(null)
  const item = useStore((s) => s.filters.item)
  const items = useStore((s) => s.items)
  const readOnly=useStore(state=>state.readOnly)

  useEffect(() => {
    let alive = true
    const tick = () =>
      fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
        .then((r) => {
          if (!alive) return
          setBackend(r.ok ? 'up' : 'down')
          return r.json()
        })
        .then((d) => {if(alive&&d){setLlmMode(d.llm?.mode ?? null);useStore.setState({readOnly:d.read_only===true,...(d.read_only?{reviewMode:false}:{})})}})
        .catch(() => alive && setBackend('down'))
    void tick()
    const t = setInterval(tick, 30000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  return (
    <header className="glass flex flex-wrap items-center gap-x-5 gap-y-2 border-line bg-panel/95 px-4 py-2.5 backdrop-blur-md">
      <div className="mr-auto flex items-baseline gap-3">
        <span className="text-[13px] font-semibold tracking-wide2 text-tx">
          외관검사 관제
        </span>
        <span className="font-mono text-[10px] uppercase tracking-label text-faint">
          {itemLabel(item)}
          <span className="ml-1 text-faint/70">({items.length} 품목)</span>
        </span>
      </div>

      <Viewfinder />

      <div className="flex items-center gap-3">
        <span className="font-mono text-[11px] tabular-nums text-muted" aria-label="시계">
          {clock}
        </span>
        <span className="flex items-center gap-1.5" title="백엔드 연결 상태">
          <span
            className={`live-dot ${backend === 'down' ? 'live-dot--warn' : ''}`}
            style={backend !== 'up' ? { background: 'var(--faint)', animation: 'none' } : undefined}
          />
          <span className="font-mono text-[9px] uppercase tracking-label text-faint">
            {backend === 'up' ? 'live' : backend === 'down' ? 'down' : '···'}
          </span>
        </span>
        <SourceBadge />
        {readOnly&&<span className="text-xs text-muted">팀 공유 · 읽기 전용</span>}
        {llmMode === 'mock' && (
          <span className="chip border-dashed border-warn/60 bg-warn/5 text-warn">
            LLM 미연결 · 직접 도구
          </span>
        )}
      </div>
    </header>
  )
}
