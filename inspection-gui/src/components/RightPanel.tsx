import { useMemo } from 'react'
import { METRIC_DEFS } from '../config'
import { useStore } from '../store'
import type { Case, Metric, Rate, ReviewState } from '../types'
import { formatRate } from '../utils/heat'
import { EmptyState, Skeleton } from './bits'

function MetricCard({ metric, rate, active }: { metric: Metric; rate: Rate | undefined; active: boolean }) {
  const def = METRIC_DEFS[metric]
  return (
    <div
      className={`border-b border-line/70 px-3 py-2 ${active ? 'border-l-2 border-l-signal bg-signal/5' : ''}`}
      aria-label={`${def.label} 지표 카드`}
    >
      <div className="flex items-center justify-between gap-1">
        <span className="font-mono text-[10px] uppercase tracking-label text-faint">{def.label}</span>
        {def.perAttempt && (
          <span className="font-mono text-[8px] uppercase tracking-label text-warn">
            시도 기준
          </span>
        )}
      </div>
      {rate ? (
        <>
          <div
            className={`mt-1 font-mono text-lg font-semibold tabular-nums ${
              rate.rate == null ? 'text-faint' : 'text-tx'
            }`}
          >
            {formatRate(rate.rate)}
          </div>
          <div className="mt-0.5 font-mono text-[10px] tabular-nums text-faint">
            {rate.num} / {rate.den}
          </div>
          {rate.rate == null && (
            <div className="mt-0.5 font-mono text-[9px] text-faint">
              분모 없음 · {rate.reason ?? 'denominator_zero'}
            </div>
          )}
        </>
      ) : (
        <div className="mt-1 font-mono text-[11px] text-faint">불러오는 중…</div>
      )}
    </div>
  )
}

function TruthPredBadge({ kind, value }: { kind: 'truth' | 'pred'; value: string | null }) {
  const color =
    value === 'defect'
      ? 'text-fail'
      : value === 'normal'
        ? 'text-ok'
        : 'text-faint'
  const label = value ?? '—'
  return (
    <span className={`chip border-current/40 bg-transparent font-mono text-[9px] uppercase tracking-label ${color}`}>
      {kind === 'truth' ? '실제' : '예측'} {label}
    </span>
  )
}

function CaseCard({ c, onClick }: { c: Case; onClick: () => void }) {
  const severity = c.truth_label === 'defect' && c.prediction !== 'defect'
  return (
    <button
      type="button"
      onClick={onClick}
      className={`glass block w-full border-l-2 p-3 text-left transition-colors duration-150 hover:border-l-signal/70 ${
        severity ? 'border-l-fail/60' : c.attempt_status ? 'border-l-warn/60' : 'border-l-transparent'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-semibold text-tx">{c.product_id}</span>
        <span className="flex shrink-0 gap-1">
          <TruthPredBadge kind="truth" value={c.truth_label} />
          <TruthPredBadge kind="pred" value={c.prediction} />
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-faint">
        <span>cam {c.camera_id ?? '—'}</span>
        {c.attempt_status && <span className="text-warn">status {c.attempt_status}</span>}
        <span>{c.model_version}</span>
        <span>box {c.box_ids.length}</span>
      </div>
    </button>
  )
}

/** 우측 근거 패널: 지표 카드 + 사례 리스트. */
export function RightPanel() {
  const filters = useStore((s) => s.filters)
  const selectedPart = useStore((s) => s.selectedPart)
  const metricCards = useStore((s) => s.metricCards)
  const metricCardsLoading = useStore((s) => s.metricCardsLoading)
  const cardReviewState = useStore((s) => s.cardReviewState)
  const setCardReviewState = useStore((s) => s.setCardReviewState)
  const cases = useStore((s) => s.cases)
  const casesLoading = useStore((s) => s.casesLoading)
  const openCase = useStore((s) => s.openCase)

  const isCapture = METRIC_DEFS[filters.metric].perAttempt === true
  const showCards = selectedPart !== null || isCapture
  const cardState: ReviewState =
    filters.reviewState === 'all' ? cardReviewState : filters.reviewState === 'pending' ? 'pending' : 'confirmed'

  const list = useMemo(() => {
    const all = cases?.cases ?? []
    return filters.productId === 'all'
      ? all
      : all.filter((c) => c.product_id === filters.productId)
  }, [cases, filters.productId])

  const partLabel = selectedPart ?? (isCapture ? '품목 전체' : null)

  return (
    <aside className="glass flex min-h-0 flex-col gap-3 p-4">
      <div className="border-b border-line pb-3"><p className="mb-1 font-mono text-[10px] tracking-label text-signal">INSPECTION EVIDENCE</p><h2 className="text-sm font-semibold text-tx">부위별 검사 근거</h2></div>
      {!showCards ? (
        <EmptyState>
          3D 부위 지도 또는 좌측 부위 목록에서 부위를 선택하면
          <br />
          지표 카드와 2D 근거 사례가 열립니다.
        </EmptyState>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-mono text-[10px] uppercase tracking-label text-faint">
              선택 부위:{' '}
              <span className="font-semibold text-muted">{partLabel}</span>
            </div>
            {filters.reviewState === 'all' && (
              <div className="flex gap-1" role="group" aria-label="카드 검수 상태">
                {(['confirmed', 'pending'] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`btn px-2 py-0.5 text-[9px] uppercase tracking-label ${cardState === s ? 'btn-active' : ''}`}
                    onClick={() => setCardReviewState(s)}
                  >
                    {s === 'confirmed' ? '확정' : '검수 전'}
                  </button>
                ))}
              </div>
            )}
          </div>

          {metricCardsLoading || !metricCards ? (
            <div className="glass divide-y divide-line/70">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="mx-3 my-2 h-12" />
              ))}
            </div>
          ) : (
            <div className="glass divide-y divide-line/70">
              {(Object.keys(METRIC_DEFS) as Metric[]).map((m) => (
                <MetricCard
                  key={m}
                  metric={m}
                  rate={metricCards[cardState]?.metrics[m]}
                  active={m === filters.metric}
                />
              ))}
            </div>
          )}

          {filters.reviewState !== 'confirmed' && (
            <div className="empty-dashed px-3 py-2 font-mono text-[10px] leading-relaxed text-warn">
              검수 전 의심 포함 — 카드는 한 번에 하나의 검수 상태만 표시합니다
              (pending과 confirmed를 섞지 않음).
            </div>
          )}

          <section className="flex min-h-0 flex-col">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-mono text-[10px] font-semibold uppercase tracking-wide2 text-faint">
                사례{list.length > 0 ? ` (${list.length}/${cases?.count ?? 0})` : ''}
              </h2>
              <span className="font-mono text-[9px] uppercase tracking-label text-faint">
                검수 확정 기준
              </span>
            </div>
            {casesLoading && !cases ? (
              <Skeleton className="h-40" />
            ) : list.length === 0 ? (
              <EmptyState>조건에 맞는 사례가 없습니다.</EmptyState>
            ) : (
              <ul className="flex flex-col gap-2 xl:max-h-[34vh] xl:overflow-y-auto xl:pr-1">
                {list.map((c) => (
                  <li key={`${c.product_id}-${c.camera_id ?? 'x'}`}>
                    <CaseCard
                      c={c}
                      onClick={() => {
                        const idx = cases?.cases.indexOf(c) ?? 0
                        openCase(idx)
                      }}
                    />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </aside>
  )
}
