import { METRIC_DEFS, MIN_DENOMINATOR } from '../config'
import { useStore } from '../store'
import { partsForItem } from '../three/parts'
import { formatNumDen, formatRate, isInterpretationCaution, rateToColor } from '../utils/heat'
import { Skeleton } from './bits'
import {regionEvidence} from '../three/heatEvidence'

/** 좌측 필터 패널: 지표 정의, 키보드 탐색 가능한 부위 목록, 해석 주의 경고. */
export function LeftPanel() {
  const filters = useStore((s) => s.filters)
  const rawStats = useStore((s) => s.stats)
  const stats=rawStats?.item===filters.item?rawStats:null
  const statsLoading = useStore((s) => s.statsLoading)
  const statsError = useStore((s) => s.statsError)
  const selectedPart = useStore((s) => s.selectedPart)
  const selectPart = useStore((s) => s.selectPart)

  const parts = partsForItem(filters.item)
  const metric = METRIC_DEFS[filters.metric]
  const cautionParts = parts.filter((p) => {
    const row = stats?.rows.find((r) => r.group.part_id === p.part_id)
    return isInterpretationCaution(row?.den ?? null)
  })

  return (
    <aside className="glass flex flex-col gap-4 p-4">
      <section>
        <h2 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-wide2 text-faint">
          지표 정의
        </h2>
        <div className="glass p-3">
          <div className="font-mono text-xs font-semibold text-tx">{metric.label}</div>
          <div className="mt-0.5 font-mono text-[10px] text-faint">
            {filters.metric}
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted">
            {metric.definition}
          </p>
          {metric.perAttempt && (
            <p className="mt-2 font-mono text-[10px] leading-relaxed text-warn">
              시도 건수 기준 — 제품×부위 지표와 단위가 다릅니다.
            </p>
          )}
        </div>
      </section>

      <section>
        <h2 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-wide2 text-faint">
          부위 목록
        </h2>
        {statsLoading && !stats ? (
          <Skeleton className="h-28" />
        ) : (
          <ul className="flex flex-col gap-1.5" role="listbox" aria-label="부위 목록">
            {parts.map((p) => {
              const row = stats?.rows.find((r) => r.group.part_id === p.part_id)
              const active = selectedPart === p.part_id
              return (
                <li key={p.part_id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={active}
                    onClick={() => selectPart(active ? null : p.part_id)}
                    className={`btn w-full justify-between ${active ? 'btn-active' : ''}`}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        aria-hidden
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: rateToColor(row?.rate ?? null) }}
                      />
                      {p.label}
                    </span>
                    <span className="font-mono text-[11px] text-muted">
                      {row
                        ? `${formatNumDen(row.num, row.den)} · ${formatRate(row.rate)}`
                        : regionEvidence(stats,p.part_id,{loading:statsLoading,error:statsError}).message}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
        <p className="mt-2 text-[10px] leading-relaxed text-faint">
          Tab으로 이동, Enter로 선택 — 3D 부위 클릭과 동일하게 동작합니다.
        </p>
      </section>

      {cautionParts.length > 0 && (
        <div className="empty-dashed px-3 py-2 font-mono text-[10px] leading-relaxed text-warn">
          분모가 작아 해석 주의 (분모 &lt; {MIN_DENOMINATOR}):{' '}
          {cautionParts.map((p) => p.part_id).join(', ')}
        </div>
      )}

      {filters.reviewState !== 'confirmed' && (
        <div className="empty-dashed px-3 py-2 font-mono text-[10px] leading-relaxed text-warn">
          검수 전(pending) 데이터가 포함될 수 있습니다. 확정 전 수치는 검수 확정과 섞어
          해석하지 마세요.
        </div>
      )}
    </aside>
  )
}
