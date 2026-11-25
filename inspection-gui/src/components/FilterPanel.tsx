import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { METRIC_DEFS, MODEL_VERSION, REVIEW_STATE_OPTIONS, itemLabel } from '../config'
import { getFusionRuns, type FusionRun } from '../api/client'
import { useStore, type ReviewFilter } from '../store'
import type { Item, Metric } from '../types'

const METRIC_OPTIONS = Object.keys(METRIC_DEFS) as Metric[]

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
    </label>
  )
}

/** 좌측 필터 레일 — 품목/지표/기간/기준선/검수 상태 (기존 store 세터 재사용). */
export function FilterPanel() {
  const filters = useStore((s) => s.filters)
  const cases = useStore((s) => s.cases)
  const items = useStore((s) => s.items)
  const setItem = useStore((s) => s.setItem)
  const setMetric = useStore((s) => s.setMetric)
  const setModelVersion = useStore((s) => s.setModelVersion)
  const setReviewState = useStore((s) => s.setReviewState)
  const setDateFrom = useStore((s) => s.setDateFrom)
  const setDateTo = useStore((s) => s.setDateTo)
  const setProductId = useStore((s) => s.setProductId)

  const productIds = cases ? [...new Set(cases.cases.map((c) => c.product_id))] : []
  const [runs, setRuns] = useState<FusionRun[]>([])
  useEffect(() => {
    let cancelled = false
    void getFusionRuns().then((result) => {
      if (!cancelled) setRuns(result.data.runs)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const runLabel = (run: FusionRun) => {
    const name = run.contract_version ?? run.fusion_run_id
    const short = run.fusion_run_id.split(':')[1]?.slice(0, 8) ?? ''
    return `${name}${short ? ` (${short})` : ''}${run.is_active ? ' — 활성' : ''}`
  }

  return (
    <section className="glass p-3">
      <h2 className="mb-4 font-mono text-[11px] font-semibold uppercase tracking-wide2 text-signal">
        검사 조건
      </h2>
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
        <Field label="품목">
          <select
            className="control w-full"
            value={filters.item}
            onChange={(e) => setItem(e.target.value as Item)}
          >
            {items.map((value) => (
              <option key={value} value={value}>
                {itemLabel(value)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="지표">
          <select
            className="control w-full"
            value={filters.metric}
            onChange={(e) => setMetric(e.target.value as Metric)}
          >
            {METRIC_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {METRIC_DEFS[m].label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="기간 시작">
          <input
            type="date"
            className="control w-full"
            value={filters.dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </Field>
        <Field label="기간 종료">
          <input
            type="date"
            className="control w-full"
            value={filters.dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </Field>
        <Field label="모델 기준선">
          <select
            className="control w-full"
            value={filters.modelVersion}
            onChange={(e) => setModelVersion(e.target.value)}
          >
            <option value="">전체 (활성 run 근거)</option>
            {runs.length === 0 && <option value={MODEL_VERSION}>{MODEL_VERSION}</option>}
            {runs.map((run) => (
              <option key={run.fusion_run_id} value={run.fusion_run_id}>
                {runLabel(run)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="검수 상태">
          <select
            className="control w-full"
            value={filters.reviewState}
            onChange={(e) => setReviewState(e.target.value as ReviewFilter)}
          >
            {REVIEW_STATE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="mt-2.5">
        <Field label="제품">
          <select
            className="control w-full"
            value={filters.productId}
            onChange={(e) => setProductId(e.target.value)}
          >
            <option value="all">전체</option>
            {productIds.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </section>
  )
}
