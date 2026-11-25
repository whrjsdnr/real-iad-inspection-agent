import { useEffect, useState } from 'react'
import { ScanLine,Layers3,MessageSquare,ArrowUpRight } from 'lucide-react'
import { navigate } from '../router'
import {
  fixtureFinalPerformance,
  getCaseEvidenceClient,
  getFinalPerformance,
} from '../api/client'
import { CenterPanel } from '../components/CenterPanel'
import { FilterPanel } from '../components/FilterPanel'
import { LeftPanel } from '../components/LeftPanel'
import { TopBar } from '../components/TopBar'
import { USE_FIXTURE } from '../config'
import { useCountUp } from '../hooks/useCountUp'
import { useStore } from '../store'
import type { StatusOverview, ViewId } from '../types'
import {performanceStateLabel} from '../utils/performanceState'

/** 기준선 v1 대비 비교 막대 — width 0.6s 전환. */
function CompareBar({ label, now, base, digits = 4 }: {
  label: string
  now: number | null | undefined
  base: number
  digits?: number
}) {
  const shown = useCountUp(now ?? null)
  const max = Math.max(base, now ?? 0) * 1.08 || 1
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-label text-faint">{label}</span>
        <span className="font-mono text-[11px] tabular-nums text-tx">
          {shown == null ? '—' : shown.toFixed(digits)}
        </span>
      </div>
      <div className="space-y-1">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-line/40">
          <div
            className="h-full rounded-full bg-signal transition-[width] duration-500 ease-out"
            style={{ width: `${((now ?? 0) / max) * 100}%` }}
          />
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-1 w-full overflow-hidden rounded-full bg-line/40">
            <div
              className="h-full rounded-full bg-faint/70 transition-[width] duration-500 ease-out"
              style={{ width: `${(base / max) * 100}%` }}
            />
          </div>
          <span className="shrink-0 font-mono text-[10px] uppercase tracking-label text-faint">
            v1 {base.toFixed(digits)}
          </span>
        </div>
      </div>
    </div>
  )
}

function BigNum({ label, value, sub }: { label: string; value: number | null | undefined; sub?: string }) {
  const shown = useCountUp(typeof value === 'number' ? value : null)
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-label text-faint">{label}</div>
      <div className="mt-0.5 font-mono text-xl font-semibold tabular-nums text-tx">
        {shown == null ? '—' : shown.toLocaleString('ko-KR', { maximumFractionDigits: 4 })}
      </div>
      {sub && <div className="mt-0.5 font-mono text-[10px] text-faint">{sub}</div>}
    </div>
  )
}

/** 상단 성능 요약 카드 — final_performance JSON 자동 반영(60s 폴리). */
function PerformanceCards() {
  const [fp, setFp] = useState<StatusOverview['final_performance'] | null>(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    let alive = true
    const tick = () =>
      getFinalPerformance()
        .then((d) => alive && (setFp(d), setErr(false)))
        .catch(() => {
          if (!alive) return
          if (USE_FIXTURE) {
            setFp(fixtureFinalPerformance())
            setErr(false)
          } else {
            setErr(true)
          }
        })
    void tick()
    const t = setInterval(tick, 60000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  if (err || !fp) {
    return (
      <div className="glass col-span-full px-4 py-3">
        <span className="font-mono text-[10px] uppercase tracking-label text-faint">
          성능 보고서 — {err ? '백엔드 연결 실패' : '불러오는 중…'}
        </span>
      </div>
    )
  }
  if (!fp.available || !fp.metrics) {
    return (
      <div className="glass col-span-full flex flex-wrap items-baseline gap-x-6 gap-y-1 px-4 py-3">
        <span className="font-mono text-[10px] uppercase tracking-label text-faint">
          성능 보고서 — 산출 대기 중
        </span>
        <span className="font-mono text-[10px] text-muted">
          상태: {performanceStateLabel(fp.state)} ·
          final_performance 산출 후 자동 표시
        </span>
        <span className="font-mono text-[10px] text-faint">
          기준선 v1: F1 {fp.baseline_v1.f1} · Recall {fp.baseline_v1.recall} ({fp.baseline_v1.label})
        </span>
      </div>
    )
  }
  const m = fp.metrics
  const allProducts=m.evaluation_scope==='all_inferred_products_reference'
  const aggregateChecked=m.verified||m.csv_consistency_verified

  return (
    <>
      <div className="glass col-span-full space-y-1 px-4 py-3 text-xs text-muted">
        <strong className="text-tx">{allProducts?'전체 추론 제품 참고 성능':'Test 평가 성능'} · {(m.evaluation_products??m.test_products)?.toLocaleString()} 제품</strong>
        {m.fusion_policy?.weights&&<p>퓨전 RT {m.fusion_policy.weights.rtdetr} + HVQ {m.fusion_policy.weights.hvq} · {m.fusion_policy.hvq_score_variant} · RT {m.fusion_policy.rtdetr_conf_threshold} · {m.fusion_policy.normalization}</p>}
        {m.database_run_activated===false&&<p>저장 점수 재평가 보고서 · 운영 DB 판정 변경 없음</p>}
        {allProducts&&<><p>기존 분할 전체 포함 · 임계값 산출용 Validation 포함 · 실제 모델 학습 표본과의 중복 미확인</p><p>별도 Test {m.test_products?.toLocaleString()} 제품 · F1 {m.test_f1_micro?.toFixed(4)??'—'} · Recall {m.test_recall==null?'—':`${(m.test_recall*100).toFixed(2)}%`}</p></>}
      </div>
      <div className="glass px-4 py-3">
        <CompareBar label="F1 (micro)" now={m.f1_micro} base={fp.baseline_v1.f1} />
      </div>
      <div className="glass px-4 py-3">
        <CompareBar label="Recall" now={m.recall} base={fp.baseline_v1.recall} />
      </div>
      <div className="glass px-4 py-3">
        <BigNum label="AUROC" value={m.auroc} sub={`macro ${m.auroc_category_macro?.toFixed(4) ?? '—'}`} />
      </div>
      <div className="glass px-4 py-3">
        <BigNum label="FP / FN" value={m.fp == null || m.fn == null ? null : m.fp + m.fn} sub={`FP ${m.fp ?? '—'} · FN ${m.fn ?? '—'} · v1 미검 ${fp.baseline_v1.miss} 오검 ${fp.baseline_v1.false_alarm}`} />
      </div>
      <div className="glass px-4 py-3">
        <BigNum
          label="보류"
          value={m.hold_products}
          sub={`${m.hold_rate != null ? `${(m.hold_rate * 100).toFixed(2)}%` : '—'} · 확정 커버리지 ${m.coverage != null ? `${(m.coverage * 100).toFixed(1)}%` : '—'}`}
        />
      </div>
      <div className="glass flex flex-col justify-center px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className={`live-dot ${aggregateChecked ? '' : 'live-dot--warn'}`} style={aggregateChecked ? undefined : { animation: 'none' }} />
          <span className={`font-mono text-[10px] ${aggregateChecked ? 'text-ok' : 'text-warn'}`}>
            {m.verified ? '교차검증 완료' : m.csv_consistency_verified?'저장 결과·manifest 일치 확인':'검증 미완'}
          </span>
        </div>
        <span className="mt-1 break-all font-mono text-[10px] text-faint">
          {fp.model_version}{fp.is_fixture ? ' · fixture' : ''}
        </span>
        <span className="mt-1 font-mono text-[10px] text-faint">{allProducts?'전체':'Test'} {(m.evaluation_products??m.test_products)?.toLocaleString() ?? '—'} 제품 · 보고서 {m.timestamp ?? '갱신 시각 없음'}</span>
      </div>
    </>
  )
}

/** 대시보드 메뉴 — 미션 헤더 + 필터 레일 + 3D 부위 지도 + 사례 패널 + 검수 모드. */
export function DashboardPage() {
  const readOnly=useStore(state=>state.readOnly)
  const reviewMode = useStore((s) => s.reviewMode)
  const setReviewMode = useStore((s) => s.setReviewMode)
  const focusCase = useStore((s) => s.focusCase)
  const setFocusCase = useStore((s) => s.setFocusCase)

  // 근거 링크로 진입한 사례를 연다 (라우트 파라미터 → 1회 소비).
  useEffect(() => {
    if (!focusCase) return
    const { productId, cameraId } = focusCase
    let alive = true
    getCaseEvidenceClient({ productId })
      .then((r) => {
        if (!alive) return
        if (r.data.count === 0) { setFocusCase(null); return }
        useStore.setState({ cases: r.data, casesLoading: false })
        useStore.getState().openCase(0)
        if (cameraId) {
          useStore.getState().setViewerView(cameraId as ViewId)
        }
        setFocusCase(null)
      })
      .catch(() => undefined)
    return () => {
      alive = false
    }
  }, [focusCase, setFocusCase])

  return (
    <div className="precision-dashboard flex flex-col gap-4">
      <header className="precision-hero flex flex-wrap items-start justify-between gap-5 rounded-xl border border-line px-5 py-5 md:px-6">
        <div><p className="mb-2 flex items-center gap-2 font-mono text-[10px] font-semibold tracking-wide2 text-signal"><ScanLine size={14} aria-hidden/> REAL-IAD / FIVE-VIEW INSPECTION</p><h1 className="text-2xl font-semibold tracking-tight text-tx md:text-3xl">종합 검사 대시보드</h1><p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">제품별 5시점 근거를 연결하고, 검사 부위와 검수 결과를 한곳에서 확인합니다.</p></div>
        <div className="flex flex-wrap gap-2"><button className="btn" onClick={()=>navigate('#/chat')}><MessageSquare size={14} aria-hidden/> AI 에이전트</button><button className="btn btn-active" onClick={()=>navigate('#/inference')}><ScanLine size={14} aria-hidden/> 5시점 검사 <ArrowUpRight size={14} aria-hidden/></button></div>
      </header>
      <TopBar />
      <section aria-label="평가 성능 요약" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1"><h2 className="flex items-center gap-2 text-sm font-semibold text-tx"><Layers3 size={16} aria-hidden/> 검사 성능과 기준선</h2><span className="text-xs text-muted">기존 평가와 현재 운영 집계를 구분합니다</span></div>
      <div className="motion-rise grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6" style={{ ['--i' as string]: 1 }}>
        <PerformanceCards />
      </div>
      <p className="precision-historical text-xs leading-relaxed text-muted">참고 · 기존 보고값 98.84%는 지표명·평가 분모 미확인입니다. 위 운영 평가의 현재 정확도로 해석하지 않습니다.</p>
      </section>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-panel px-4 py-3">
        <label className="flex cursor-pointer items-center gap-2 font-mono text-[11px] text-muted">
          <input
            type="checkbox"
            className="h-3.5 w-3.5"
            style={{ accentColor: 'var(--signal)' }}
            checked={reviewMode}
            disabled={readOnly}
            onChange={(e) => setReviewMode(e.target.checked)}
          />
          {readOnly?'팀 공유 · 읽기 전용':'검수 모드'}
        </label>
        {reviewMode && (
          <span className="font-mono text-[10px] text-warn">
            사례를 열어 원본에서 클릭 2회로 박스 지정 → FP/FN 확정 시 reviews 반영 + 지표 재계산
          </span>
        )}
      </div>
      <main className="motion-rise grid flex-1 grid-cols-1 items-start gap-3 xl:grid-cols-[248px_minmax(0,1fr)]" style={{ ['--i' as string]: 3 }}>
        <div className="flex flex-col gap-3">
          <FilterPanel />
          <LeftPanel />
        </div>
        <CenterPanel />
      </main>
    </div>
  )
}
