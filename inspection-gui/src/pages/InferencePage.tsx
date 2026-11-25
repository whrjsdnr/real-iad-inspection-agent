import { useEffect, useMemo, useRef, useState } from 'react'
import {
  getCaseEvidenceClient,
  listSampleProducts,
  runInferenceExisting,
  runInferenceUpload,
} from '../api/client'
import { API_BASE, itemLabel } from '../config'
import { ASYNC_JOBS, rememberedJob, resumeJob, submitJob, monitorJob, type Job } from '../api/jobs'
import { useStore } from '../store'
import { cssVar } from '../utils/tokens'
import type { CaseResponse, GuiInferenceResult, ViewId } from '../types'
import { VIEW_IDS } from '../types'

const VERDICT_STYLE: Record<string, { label: string; cls: string; ring: string }> = {
  defect: { label: '불량', cls: 'border-fail/60 bg-fail/10 text-fail', ring: 'var(--fail)' },
  normal: { label: '정상', cls: 'border-ok/60 bg-ok/10 text-ok', ring: 'var(--ok)' },
  hold: { label: '보류', cls: 'border-warn/60 bg-warn/10 text-warn', ring: 'var(--warn)' },
}

/** 판정 다이얼 — 가중합 점수 게이지 + TH 마커 + 보류 마진 구간. */
function VerdictDial({ score, th, margin }: {
  score: number | null
  th: number | null
  margin: number | null
}) {
  const R = 52
  const C = 2 * Math.PI * R
  const frac = score == null ? 0 : Math.min(1, Math.max(0, score))
  const thFrac = th == null ? null : Math.min(1, Math.max(0, th))
  const band = th != null && margin != null
    ? [Math.max(0, th - margin), Math.min(1, th + margin)]
    : null
  const arc = (from: number, to: number) => ({
    dasharray: `${(to - from) * C} ${C}`,
    dashoffset: -from * C,
  })
  return (
    <div className="relative mx-auto h-40 w-40" role="img" aria-label={`퓨전 점수 ${score ?? '미계산'}`}>
      <svg viewBox="0 0 128 128" className="h-full w-full -rotate-90">
        <circle cx="64" cy="64" r={R} fill="none" stroke="var(--line)" strokeWidth="7" opacity="0.6" />
        {band && (
          <circle
            cx="64" cy="64" r={R} fill="none"
            stroke="var(--warn)" strokeWidth="7" opacity="0.35"
            {...arc(band[0], band[1])}
          />
        )}
        <circle
          cx="64" cy="64" r={R} fill="none"
          stroke="var(--signal)" strokeWidth="7" strokeLinecap="round"
          {...arc(0, frac)}
        />
        {thFrac != null && (
          <line
            x1={64 + (R - 8) * Math.cos(2 * Math.PI * thFrac)}
            y1={64 + (R - 8) * Math.sin(2 * Math.PI * thFrac)}
            x2={64 + (R + 8) * Math.cos(2 * Math.PI * thFrac)}
            y2={64 + (R + 8) * Math.sin(2 * Math.PI * thFrac)}
            stroke="var(--text)" strokeWidth="2"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-2xl font-semibold tabular-nums text-tx">
          {score?.toFixed(3) ?? '—'}
        </span>
        <span className="font-mono text-[8px] uppercase tracking-label text-faint">
          {th != null ? `TH ${th.toFixed(3)}${margin != null ? ` ±${margin.toFixed(3)}` : ''}` : '미확정'}
        </span>
      </div>
    </div>
  )
}

/** 원본 + RT-DETR 박스 캔버스 오버레이. */
function BoxCanvas({ src, result, cam }: {
  src: string
  result: GuiInferenceResult
  cam: ViewId
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  const view = result.views[cam]

  useEffect(() => {
    const canvas = ref.current
    if (!canvas || !view) return
    const img = new Image()
    img.onload = () => {
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.drawImage(img, 0, 0)
      for (const d of view.detections) {
        const [x1, y1, x2, y2] = d.bbox
        ctx.strokeStyle = d.score >= 0.55 ? cssVar('--fail') : cssVar('--warn')
        ctx.lineWidth = Math.max(2, img.naturalWidth / 400)
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
        ctx.fillStyle = ctx.strokeStyle
        ctx.font = `${Math.max(12, img.naturalWidth / 55)}px monospace`
        ctx.fillText(`${d.class_name} ${d.score.toFixed(2)}`, x1 + 4, Math.max(14, y1 - 4))
      }
    }
    img.src = src
  }, [src, view])

  if (!view) return null
  return (
    <canvas
      ref={ref}
      className="max-h-80 w-full rounded-md bg-black/40 object-contain"
      aria-label={`${cam} 원본 + RT-DETR 검출 박스`}
    />
  )
}

const RUN_STEPS = ['업로드', 'RT-DETR', 'HVQ', '퓨전'] as const

/** 진행 중 단계 표시 + 경과 타이머. */
function RunProgress({ elapsedMs }: { elapsedMs: number }) {
  const secs = Math.floor(elapsedMs / 1000)
  return (
    <div className="glass flex items-center gap-4 px-4 py-3">
      <div className="flex items-center gap-2">
        {RUN_STEPS.map((s, i) => (
          <span key={s} className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                i === 0 ? 'animate-pulse-soft bg-signal' : 'bg-line'
              }`}
            />
            <span className={`font-mono text-[9px] uppercase tracking-label ${i === 0 ? 'text-signal' : 'text-faint'}`}>
              {s}
            </span>
            {i < RUN_STEPS.length - 1 && <span className="text-faint/50">→</span>}
          </span>
        ))}
      </div>
      <span className="ml-auto font-mono text-[11px] tabular-nums text-muted">
        {String(Math.floor(secs / 60)).padStart(2, '0')}:{String(secs % 60).padStart(2, '0')}
      </span>
    </div>
  )
}

/** 5시점 모델 추론 메뉴 — 판정 다이얼 + 단계 진행 + 칼라별 근거 그리드. */
export function InferencePage() {
  const items = useStore((s) => s.items)
  const [item, setItem] = useState<string>('toothbrush')
  const [mode, setMode] = useState<'upload' | 'existing'>('existing')
  const [files, setFiles] = useState<Record<string, File | null>>({})
  const [samples, setSamples] = useState<string[]>([])
  const [productId, setProductId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GuiInferenceResult | null>(null)
  const [evidence, setEvidence] = useState<CaseResponse | null>(null)
  const [cam, setCam] = useState<ViewId>('C1')
  const [showMap, setShowMap] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [job,setJob]=useState<Job|null>(null)
  const [canResume,setCanResume]=useState(()=>ASYNC_JOBS&&rememberedJob()!==null)
  const requestAbort=useRef<AbortController|null>(null)
  useEffect(()=>()=>requestAbort.current?.abort(),[])
  const resume=async()=>{
    requestAbort.current?.abort();const controller=new AbortController();requestAbort.current=controller
    setBusy(true);setError(null)
    try{const saved=await resumeJob(controller.signal);if(saved)setResult(await monitorJob(saved,setJob,controller.signal))}
    catch(e){if(!controller.signal.aborted)setError(String(e))}finally{if(!controller.signal.aborted)setBusy(false)}
  }

  useEffect(() => {
    if (mode !== 'existing') return
    let alive = true
    listSampleProducts(item)
      .then((p) => {
        if (!alive) return
        setSamples(p)
        setProductId((prev) => (prev && p.includes(prev) ? prev : (p[0] ?? '')))
      })
      .catch(() => alive && setSamples([]))
    return () => {
      alive = false
    }
  }, [mode, item])

  useEffect(() => {
    if (!busy) return
    const t0 = performance.now()
    const t = setInterval(() => setElapsed(performance.now() - t0), 500)
    return () => clearInterval(t)
  }, [busy])

  const canRun = useMemo(() => {
    if (mode === 'existing') return !!productId
    return VIEW_IDS.every((v) => files[v])
  }, [mode, productId, files])

  const run = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    setEvidence(null)
    setShowMap(false)
    setElapsed(0)
    try {
      let r: GuiInferenceResult
      if(ASYNC_JOBS){
        const form=new FormData();form.set('item',item);form.set('mode',mode)
        if(mode==='existing')form.set('product_id',productId)
        else for(const view of VIEW_IDS)if(files[view])form.set(view,files[view]!)
        const controller=new AbortController();requestAbort.current=controller
        const next=await submitJob(form,crypto.randomUUID(),controller.signal);setJob(next);setCanResume(true)
        r=await monitorJob(next,setJob,controller.signal)
      }else r =
        mode === 'existing' 
          ? await runInferenceExisting({ item, productId })
          : await runInferenceUpload({
              item,
              files: Object.fromEntries(
                VIEW_IDS.filter((v) => files[v]).map((v) => [v, files[v] as File]),
              ),
            })
      setResult(r)
      setCam('C1')
      if (r.db_record?.recorded && r.product_id) {
        const ev = await getCaseEvidenceClient({ productId: r.product_id })
        setEvidence(ev.data)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const v = result?.views[cam]
  const verdict = result?.product.verdict
  const vStyle = verdict ? VERDICT_STYLE[verdict] : null
  const evView = evidence?.cases[0]?.evidence.all_views?.[cam]
  const imageSrc = evView?.image_uri
    ? evView.image_uri.startsWith('/evidence/')
      ? `${API_BASE}${evView.image_uri}`
      : evView.image_uri
    : ''
  const mapSrc = evView?.error_map_uri
    ? evView.error_map_uri.startsWith('/evidence/')
      ? `${API_BASE}${evView.error_map_uri}`
      : evView.error_map_uri
    : ''

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 py-2">
      <div className="motion-rise flex flex-wrap items-center gap-x-4 gap-y-2" style={{ ['--i' as string]: 0 }}>
        <h1 className="font-mono text-[11px] font-semibold uppercase tracking-wide2 text-tx">
          5시점 모델 추론
        </h1>
        <label className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-label text-faint">
          품목
          <select className="control" value={item} onChange={(e) => setItem(e.target.value)}>
            {items.map((i) => (
              <option key={i} value={i}>
                {itemLabel(i)}
              </option>
            ))}
          </select>
        </label>
        <div className="flex gap-1" role="group" aria-label="입력 방식">
          {(['existing', 'upload'] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={`btn px-2.5 py-1 text-[9px] uppercase tracking-label ${mode === m ? 'btn-active' : ''}`}
              onClick={() => setMode(m)}
            >
              {m === 'existing' ? '기존 제품' : '업로드'}
            </button>
          ))}
        </div>
      </div>

      <div className="motion-rise glass flex flex-wrap items-end gap-3 p-3" style={{ ['--i' as string]: 1 }}>
        {mode === 'existing' ? (
          <label className="block">
            <span className="label">제품 (5시점 보유)</span>
            <select
              className="control min-w-72"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
            >
              {samples.length === 0 && <option value="">(불러오는 중/없음)</option>}
              {samples.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <div className="flex flex-wrap gap-2">
            {VIEW_IDS.map((vid) => (
              <label key={vid} className="block">
                <span className="label">{vid}</span>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png"
                  className="control w-36 text-[9px]"
                  onChange={(e) =>
                    setFiles((f) => ({ ...f, [vid]: e.target.files?.[0] ?? null }))
                  }
                />
              </label>
            ))}
          </div>
        )}
        <button
          type="button"
          className="cta-glow inline-flex items-center gap-1.5 rounded-md px-5 py-1.5 font-mono text-xs font-semibold"
          disabled={!canRun || busy}
          onClick={run}
        >
          {busy ? '추론 중…' : '추론 실행'}
        </button>
        {error && <span className="font-mono text-[10px] text-fail">{error}</span>}
      </div>

      {ASYNC_JOBS&&<div className="glass flex flex-wrap items-center gap-3 p-3 text-xs text-muted"><span>{job?`${job.state} · ${job.stage} · 갱신 ${job.updated_at}`:'백그라운드 작업 · 측정되지 않은 진행률은 표시하지 않습니다.'}</span>{canResume&&<button className="btn" disabled={busy} onClick={resume}>기존 작업 상태 재확인</button>}{job&&<span className="break-all font-mono">Job {job.id}</span>}</div>}
      {busy && <RunProgress elapsedMs={elapsed} />}

      {result && (
        <div className="motion-rise grid gap-3 lg:grid-cols-[minmax(0,1fr)_300px]" style={{ ['--i' as string]: 2 }}>
          <section className="glass p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <div className="flex gap-1" role="tablist" aria-label="시점 선택">
                {VIEW_IDS.map((vid) => (
                  <button
                    key={vid}
                    type="button"
                    role="tab"
                    aria-selected={cam === vid}
                    className={`btn px-2.5 py-1 font-mono text-[10px] ${cam === vid ? 'btn-active' : ''}`}
                    onClick={() => setCam(vid)}
                  >
                    {vid}
                  </button>
                ))}
              </div>
              <div className="ml-auto flex gap-1" role="group" aria-label="근거 모드">
                <button
                  type="button"
                  className={`btn px-2 py-0.5 text-[9px] uppercase tracking-label ${!showMap ? 'btn-active' : ''}`}
                  onClick={() => setShowMap(false)}
                >
                  원본+박스
                </button>
                <button
                  type="button"
                  className={`btn px-2 py-0.5 text-[9px] uppercase tracking-label ${showMap ? 'btn-active' : ''}`}
                  onClick={() => setShowMap(true)}
                >
                  오차 맵
                </button>
              </div>
            </div>
            {showMap ? (
              mapSrc ? (
                <img
                  src={mapSrc}
                  alt={`${cam} HVQ 오차 맵 오버레이`}
                  className="max-h-80 w-full rounded-md bg-black/40 object-contain"
                />
              ) : (
                <div className="empty-dashed flex h-64 items-center justify-center font-mono text-[11px] text-faint">
                  오차 맵 근거 없음
                </div>
              )
            ) : imageSrc ? (
              <BoxCanvas src={imageSrc} result={result} cam={cam} />
            ) : (
              <div className="empty-dashed flex h-64 items-center justify-center font-mono text-[11px] text-faint">
                근거 이미지 없음
              </div>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line/70 pt-2 font-mono text-[9px] uppercase tracking-label text-faint">
              <span>{cam}</span>
              {v && (
                <>
                  <span>rt {v.rtdetr_raw.toFixed(4)}</span>
                  <span>hvq_mean {v.hvq_mean.toFixed(2)}</span>
                  <span>hvq_max16 {v.hvq_max16.toFixed(2)}</span>
                  <span>검출 {v.detections.length}</span>
                </>
              )}
            </div>
            {v && v.detections.length > 0 && (
              <ul className="mt-1 max-h-20 space-y-0.5 overflow-y-auto font-mono text-[9px] text-muted">
                {v.detections.slice(0, 10).map((d, i) => (
                  <li key={i}>
                    {d.class_name} · {d.score.toFixed(3)} · [{d.bbox.map((x) => Math.round(x)).join(', ')}]
                  </li>
                ))}
              </ul>
            )}
          </section>

          <aside className="glass flex flex-col gap-3 p-3">
            <div className={`rounded-md border px-4 py-3 text-center ${vStyle?.cls ?? 'border-line bg-panel-raised/60'}`}>
              <div className="font-mono text-[9px] uppercase tracking-wide2 opacity-80">판정</div>
              <div className="mt-0.5 text-xl font-semibold">{vStyle?.label ?? '—'}</div>
            </div>

            <VerdictDial
              score={result.product.fusion_score}
              th={result.product.threshold}
              margin={result.product.margin}
            />

            <div className="border-t border-line/70 pt-2">
              <div className="mb-1 font-mono text-[9px] uppercase tracking-wide2 text-faint">
                제품 점수 (C1~C5 최대)
              </div>
              <div className="grid grid-cols-2 gap-1.5 font-mono text-[10px]">
                {[
                  ['RT-DETR raw', result.product.rtdetr_raw.toFixed(4)],
                  ['HVQ max16', result.product.hvq_max16.toFixed(2)],
                  ['RT 임계', String(result.product.rtdetr_conf_threshold)],
                  ['HVQ 임계', result.product.hvq_threshold.toFixed(2)],
                ].map(([k, val]) => (
                  <div key={k} className="rounded bg-panel-raised/70 px-2 py-1.5">
                    <div className="font-mono text-[8px] uppercase tracking-label text-faint">{k}</div>
                    <div className="tabular-nums text-tx">{val}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-line/70 pt-2">
              <div className="mb-1 font-mono text-[9px] uppercase tracking-wide2 text-faint">판정 근거</div>
              <ol className="list-decimal space-y-1 pl-4 font-mono text-[10px] leading-relaxed text-muted">
                {result.rationale.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ol>
            </div>

            <div className="border-t border-line/70 pt-2 font-mono text-[9px] text-faint">
              <div>{result.models.hvq}</div>
              <div>+ {result.models.rtdetr}</div>
              <div>config {result.config_version} · {result.elapsed_ms?.toFixed(0) ?? '—'}ms</div>
              {result.db_record?.recorded ? (
                <div className="mt-1 text-signal">
                  DB 기록 — attempt {result.db_record.attempt_id}
                </div>
              ) : (
                <div className="mt-1">DB 미기록</div>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
