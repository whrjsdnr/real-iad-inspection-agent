import { useStore } from '../store'

export function SourceBadge() {
  const source = useStore((s) => s.source)
  const connectionError = useStore((s) => s.connectionError)
  if (!source) {
    return (
      <span className="chip border-line bg-panel-raised text-faint">
        <span className="live-dot" style={{ background: 'var(--faint)', animation: 'none' }} />
        연결 중
      </span>
    )
  }
  if (source === 'api' && connectionError) {
    return <span className="chip border-fail/60 text-fail" title={connectionError}>API 연결 / 조회 오류</span>
  }
  if (source === 'api') {
    return (
      <span className="chip border-line bg-panel-raised text-muted">
        <span className="live-dot" />
        API
      </span>
    )
  }
  if (source === 'fixture') {
    return (
      <span className="chip border-dashed border-warn/60 bg-warn/5 text-warn">
        <span className="live-dot live-dot--warn" style={{ animation: 'none' }} />
        FIXTURE
      </span>
    )
  }
  return (
    <span
      className="chip border-dashed border-fail/60 bg-fail/5 text-fail"
      title={connectionError ?? 'API 호출 실패'}
    >
      <span className="live-dot" style={{ background: 'var(--fail)', animation: 'none' }} />
      FIXTURE 폭백
    </span>
  )
}

export function FallbackBanner() {
  const connectionError = useStore((s) => s.connectionError)
  if (!connectionError) return null
  return (
    <div className="empty-dashed px-3 py-2 font-mono text-[11px] text-warn">
      {connectionError}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton rounded-md ${className}`} />
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="empty-dashed flex h-full min-h-32 items-center justify-center p-6 text-center text-xs leading-relaxed text-faint">
      {children}
    </div>
  )
}
