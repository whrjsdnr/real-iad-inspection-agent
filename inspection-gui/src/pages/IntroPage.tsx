import { lazy, Suspense, useEffect, useState } from 'react'
import { getStatusOverview } from '../api/client'
import { useCountUp } from '../hooks/useCountUp'
import { navigate } from '../router'
import type { StatusOverview } from '../types'
import { IntroScene } from '../three/IntroScene'
import {performanceStateLabel} from '../utils/performanceState'
const PrecisionIntro=lazy(()=>import('../intro/PrecisionIntro').then(module=>({default:module.PrecisionIntro})))

const STEPS = [
  { no:'01',title:'제품 배치',desc:'동일 제품의 5시점 검사 준비' },
  { no:'02',title:'카메라 C1–C5',desc:'개념적 카메라 배치 · 실제 방향 미확정' },
  { no:'03',title:'5시점 촬영',desc:'시점별 이미지 수집' },
  { no:'04',title:'RT-DETRv2',desc:'검출 위치와 신뢰도 근거' },
  { no:'05',title:'HVQ-Trans',desc:'이상 맵과 이상 점수 근거' },
  { no:'06',title:'제품 결과 결합',desc:'기존 퓨전 정책으로 정상 / 불량 / 보류' },
  { no:'07',title:'3D 영역 표시',desc:'검증된 ROI 대응 부위에 근거 연결' },
  { no:'08',title:'AI 분석',desc:'도구 조회로 검사 결과 설명' },
] as const

function pct(v: number | null | undefined): string {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}

function ProgressBar({ value }: { value: number | null | undefined }) {
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-line/50">
      <div
        className="h-full rounded-full bg-signal/80 transition-all duration-500"
        style={{ width: `${Math.min(100, Math.max(0, (value ?? 0) * 100))}%` }}
      />
    </div>
  )
}

/** 모노 + tabular count-up 숫자. */
function Count({ value, digits = 0 }: { value: number | null | undefined; digits?: number }) {
  const v = useCountUp(value ?? null)
  return (
    <span className="font-mono tabular-nums text-tx">
      {v == null ? '—' : v.toLocaleString('ko-KR', { maximumFractionDigits: digits, minimumFractionDigits: digits })}
    </span>
  )
}

function TickerItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 whitespace-nowrap">
      <span className="font-mono text-[9px] uppercase tracking-label text-faint">{label}</span>
      <span className="font-mono text-[10px] text-muted">{children}</span>
    </div>
  )
}

/** 하단 실시간 상태 위젯 + 티커 — 60초 평백, 실패 시 목 모드 배지. */
function StatusWidget() {
  const [data, setData] = useState<StatusOverview | null>(null)
  const [mock, setMock] = useState(false)
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const d = await getStatusOverview()
        if (!alive) return
        setData(d)
        setMock(false)
        setUpdatedAt(new Date().toLocaleTimeString('ko-KR', { hour12: false }))
      } catch {
        if (!alive) return
        setMock(true)
      }
    }
    void tick()
    const t = setInterval(tick, 60000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const fp = data?.final_performance

  return (
    <section className="glass w-full max-w-3xl" aria-label="실시간 상태">
      <div className="flex items-center justify-between border-b border-line/70 px-4 py-2">
        <h2 className="flex items-center gap-2 font-mono text-[10px] font-semibold uppercase tracking-wide2 text-faint">
          <span className={`live-dot ${mock ? 'live-dot--warn' : ''}`} />
          실시간 상태
        </h2>
        <div className="flex items-center gap-2">
          {mock && (
            <span className="chip border-dashed border-warn/60 bg-warn/5 text-warn">
              서버 연결 실패
            </span>
          )}
          <span className="font-mono text-[9px] text-faint">
            60s{updatedAt ? ` · ${updatedAt}` : ''}
          </span>
        </div>
      </div>

      {mock ? (
        <p className="px-4 py-3 font-mono text-[11px] text-faint">
          백엔드에 연결하지 못했습니다. API 기동 후 자동으로 실제 카운트를 표시합니다.
        </p>
      ) : !data ? (
        <p className="px-4 py-3 font-mono text-[11px] text-faint">불러오는 중…</p>
      ) : (
        <div className="grid gap-x-8 gap-y-2 px-4 py-3 md:grid-cols-2">
          <div className="space-y-2">
            <div>
              <div className="mb-1 flex items-baseline justify-between">
                <span className="font-mono text-[9px] uppercase tracking-label text-faint" title="전체 검사 시도 건수입니다. 중복 제품이나 목표 코호트 밖의 기록이 포함될 수 있습니다.">DB 검사 기록</span>
                <span className="font-mono text-[10px] text-faint">
                  <Count value={data.loaded.products} />
                  <span className="text-faint/70"> / {data.loaded.target_products.toLocaleString()}</span>
                </span>
              </div>
              <ProgressBar value={data.loaded.product_progress} />
            </div>
            <div>
              <div className="mb-1 flex items-baseline justify-between">
                <span className="font-mono text-[9px] uppercase tracking-label text-faint">시점 적재</span>
                <span className="font-mono text-[10px] text-faint">
                  <Count value={data.loaded.views} />
                  <span className="text-faint/70"> / {data.loaded.target_views.toLocaleString()}</span>
                </span>
              </div>
              <ProgressBar value={data.loaded.view_progress} />
            </div>
            <div>
              <div className="mb-1 flex items-baseline justify-between">
                <span className="font-mono text-[9px] uppercase tracking-label text-faint">점수 반영 max_avgpool16</span>
                <span className="font-mono text-[10px] text-faint">
                  {data.score_backfill.completed_products != null ? (
                    <>
                      <Count value={data.score_backfill.completed_products} />
                      <span className="text-faint/70"> / {data.score_backfill.expected_products.toLocaleString()} ({pct(data.score_backfill.progress)})</span>
                    </>
                  ) : '—'}
                </span>
              </div>
              <ProgressBar value={data.score_backfill.progress} />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-[9px] uppercase tracking-label text-faint">최종 성능 산출</span>
              <span className="font-mono text-[10px]">
                {fp?.state === 'complete' && fp.metrics ? (
                  <span className="text-signal">완료</span>
                ) : fp?.state === 'computing' ? (
                  <span className="animate-pulse-soft text-warn">{performanceStateLabel(fp.state)}</span>
                ) : (
                  <span className="text-faint">{performanceStateLabel(fp?.state)}</span>
                )}
                {fp?.is_fixture && (
                  <span className="ml-1.5 rounded border border-dashed border-line px-1 text-[8px] text-faint">fixture</span>
                )}
              </span>
            </div>
            {fp?.state === 'complete' && fp.metrics ? (
              <>
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-[9px] uppercase tracking-label text-faint">F1 (micro) · {fp.metrics.evaluation_scope==='all_inferred_products_reference'?'전체':'Test'}</span>
                  <span className="font-mono text-[11px] tabular-nums text-tx">
                    {fp.metrics.f1_micro?.toFixed(4)}
                    <span className="ml-1.5 text-[9px] text-faint">v1 {fp.baseline_v1.f1}</span>
                  </span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-[9px] uppercase tracking-label text-faint">AUROC</span>
                  <span className="font-mono text-[11px] tabular-nums text-tx">
                    {fp.metrics.auroc?.toFixed(4) ?? '—'}
                  </span>
                </div>
                <p className="text-[9px] leading-relaxed text-faint">{(fp.metrics.evaluation_products??fp.metrics.test_products)?.toLocaleString()} 제품 집계{fp.metrics.evaluation_scope==='all_inferred_products_reference'?' · Validation 포함 참고 성능 · 학습 중복 미확인':''}</p>
              </>
            ) : (
              <p className="font-mono text-[9px] leading-relaxed text-faint">
                {fp?.state === 'report_pending' ? '점수 반영 완료. 최종 성능 보고서 생성 후 자동 표시됩니다.' : '전체 추론·DB 반영·에이전트 검증 완료 후 산출됩니다.'}
              </p>
            )}
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-[9px] uppercase tracking-label text-faint">모델</span>
              <span className="font-mono text-[10px] text-muted">HVQ 79ep · RT-DETR 15ep EMA</span>
            </div>
          </div>
        </div>
      )}

      {!mock && data && (
        <div className="flex gap-6 overflow-hidden border-t border-line/70 px-4 py-1.5">
          <TickerItem label="DB 검사 기록">
            <Count value={data.loaded.products} /> / {data.loaded.target_products.toLocaleString()}
          </TickerItem>
          <TickerItem label="시점">
            <Count value={data.loaded.views} /> / {data.loaded.target_views.toLocaleString()}
          </TickerItem>
          <TickerItem label="점수 반영">
            {data.score_backfill.completed_products != null
              ? `${data.score_backfill.completed_products.toLocaleString()} (${pct(data.score_backfill.progress)})`
              : '—'}
          </TickerItem>
          <TickerItem label="최종 성능">
            {fp?.state === 'complete' ? `F1 ${fp.metrics?.f1_micro?.toFixed(4) ?? '—'}` : performanceStateLabel(fp?.state)}
          </TickerItem>
        </div>
      )}
    </section>
  )
}

/** 인트로 — 관제실 연출: 그리드 패닝 배경, 플로우 스태거 리빌, 티커, CTA 글로우. */
function ConceptIntroPage() {
  const [phase,setPhase]=useState(0)
  const [paused,setPaused]=useState(false)
  const [reduced,setReduced]=useState(()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(()=>{const media=window.matchMedia('(prefers-reduced-motion: reduce)');const update=()=>setReduced(media.matches);media.addEventListener('change',update);return ()=>media.removeEventListener('change',update)},[])
  useEffect(()=>{if(reduced||paused||phase>=7)return;const t=setTimeout(()=>setPhase(p=>p+1),1800);return ()=>clearTimeout(t)},[phase,reduced,paused])
  const shown=reduced?7:phase
  return <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 py-5">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="mb-2 font-mono text-[10px] uppercase tracking-wide2 text-ok">5-View · Industrial Vision</p><h1 className="text-3xl font-semibold tracking-tight text-tx">검사 근거를 하나의 제품으로.</h1><p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">5시점 촬영부터 두 비전 모델의 결과 결합, 3D 부위 조회와 AI 분석까지.</p></div>
      <button className="btn btn-active px-5 py-3" onClick={()=>navigate('#/dashboard')}>대시보드 시작하기 →</button>
    </header>
    <section className="glass overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line p-3"><span className="text-xs text-warn">시연용 개념 장면 · 실제 실시간 검사 결과가 아닙니다</span><button className="btn" onClick={()=>setPaused(p=>!p)} disabled={reduced}>{reduced?'모션 최소화 적용':paused?'시연 재생':'시연 일시정지'}</button></div>
      <div className="grid lg:grid-cols-[minmax(0,1fr)_310px]">
        <div className="h-[360px] w-full min-w-0 md:h-[440px]"><IntroScene phase={shown}/></div>
        <ol className="grid grid-cols-2 gap-2 border-t border-line p-4 lg:grid-cols-1 lg:border-l lg:border-t-0" aria-label="시스템 흐름">{STEPS.map((s,i)=><li key={s.no}><button className={`flex w-full gap-3 rounded-md p-2 text-left ${shown===i?'bg-signal/10 text-tx':'text-muted'}`} onClick={()=>{setPhase(i);setPaused(true)}} aria-current={shown===i?'step':undefined}><span className="font-mono text-xs text-signal">{s.no}</span><span><strong className="block text-xs">{s.title}</strong><span className="mt-1 block text-[11px] leading-relaxed text-faint">{s.desc}</span></span></button></li>)}</ol>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line p-3"><p className="text-xs text-muted">카메라 방향·거리와 이상 위치는 설명을 위한 연출입니다. 제품은 제품군 근사 템플릿입니다.</p><button className="btn btn-active" onClick={()=>navigate('#/dashboard')}>검사 대시보드 열기</button></div>
    </section>
    <StatusWidget/>
  </div>
}

/** Team V6 precision design is the default; retain the previous concept view. */
export function IntroPage(){
 const [concept,setConcept]=useState(false)
 if(concept)return <><div className="my-2"><button className="btn" onClick={()=>setConcept(false)}>← Precision 인트로</button></div><ConceptIntroPage/></>
 return <div className="mx-auto flex w-full max-w-[1500px] flex-col gap-4 py-2"><Suspense fallback={<div className="glass flex flex-wrap items-center justify-between gap-3 p-5"><p className="text-muted">Precision 시연 준비 중…</p><button className="btn btn-active" onClick={()=>navigate('#/dashboard')}>대시보드 시작하기 →</button></div>}><PrecisionIntro onFallback={()=>setConcept(true)}/></Suspense><StatusWidget/></div>
}
