import { originalPoint } from '../reviewGeometry'
import { getCaseEvidenceClient } from '../api/client'
import { useEffect, useState } from 'react'
import { API_BASE } from '../config'
import { useStore } from '../store'
import { VIEW_IDS, type Case, type ViewId, type ViewMode } from '../types'

const MODE_LABELS: Record<ViewMode, string> = {
  original: '원본',
  error_map: '오차 맵',
  crop: '크롭',
}

/** 실제 이미지가 없으면(mock/fixture) 명확한 빈 상태를 표시한다. */
function EvidenceImage({ uri, onImageClick, onNatural }: {
  uri: string | null
  onImageClick?: (e: React.MouseEvent<HTMLImageElement>) => void
  onNatural?: (w: number, h: number) => void
}) {
  const [err, setErr] = useState(false)
  useEffect(() => setErr(false), [uri])
  if (!uri || err) {
    return (
      <div className="empty-dashed flex h-64 flex-col items-center justify-center gap-2 bg-panel-raised/40 px-4 text-center">
        <div className="font-mono text-[11px] text-muted">근거 이미지 없음</div>
        <div className="max-w-full truncate font-mono text-[9px] text-faint">
          {uri ?? '(URI 없음)'}
        </div>
        <div className="font-mono text-[9px] text-faint">
          mock/fixture 데이터라 실제 이미지 파일이 없습니다.
        </div>
      </div>
    )
  }
  return (
    <img
      src={uri.startsWith("/evidence/") ? `${API_BASE}${uri}` : uri}
      alt="근거 이미지"
      onError={() => setErr(true)}
      onClick={onImageClick}
      onLoad={(e) => onNatural?.(e.currentTarget.naturalWidth, e.currentTarget.naturalHeight)}
      className={`h-64 w-full rounded-md bg-black/40 object-contain ${onImageClick ? 'cursor-crosshair' : ''}`}
    />
  )
}

/** 검수 패널: 클릭 2회 박스 → FP/FN 확정 → submit_review → 지표 스냅샷 재계산. */
type Pt = [number, number]
function ReviewPanel({ productId, cameraId, clicks, setClicks, onDone, enabled, expectedVersion }: {
  enabled: boolean
  expectedVersion?: number
  productId: string
  cameraId: string
  clicks: Pt[]
  setClicks: (fn: (c: Pt[]) => Pt[]) => void
  onDone: () => void
}) {
  const [status, setStatus] = useState('')
  const [reviewer, setReviewer] = useState('')

  const box = (() => {
    if (clicks.length < 2) return null
    const [a, b] = clicks
    return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])]
  })()

  const submit = async (truthLabel: 'defect' | 'normal', fpFn: 'FP' | 'FN') => {
    if (!enabled || !reviewer.trim() || !box) {
      setStatus('이미지 위를 클릭 2회로 박스를 지정하세요')
      return
    }
    setStatus('검수 기록 중…')
    try {
      const res = await fetch(`${API_BASE}/tools/submit_review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId, camera_id: cameraId, bbox: box,
          truth_label: truthLabel, fp_fn: fpFn, reviewer: reviewer.trim(), expected_version: expectedVersion,
          reason: `GUI 검수 ${fpFn}`,
        }),
      })
      const d = await res.json()
      if (res.status === 409) { setStatus('이미 다른 사용자가 검수함 — 최신 사례를 다시 조회하세요'); return }
      if (!res.ok) { setStatus(d.error?.message ?? `저장 실패 HTTP ${res.status}`); return }
      if (d.review_id) {
        setStatus(`저장 ${d.review_id} · 재계산 상태 ${d.snapshot}`)
        setClicks(() => [])
        onDone()
      } else {
        setStatus(`오류: ${d.error?.message ?? '알 수 없음'}`)
      }
    } catch (err) {
      setStatus(`전송 실패: ${String(err)}`)
    }
  }

  return (
    <div className="mt-2 rounded-md border border-line bg-panel-raised/70 p-2">
      <label className="flex items-center gap-2 font-mono text-[10px] text-muted">
        검수자
        <input aria-label="검수자" value={reviewer} onChange={e=>setReviewer(e.target.value)} className="control flex-1 px-1.5 py-0.5" />
      </label>
      {!enabled && <p className="mt-1 font-mono text-[9px] text-warn">실제 원본 이미지·최신 검수 버전을 조회한 뒤 승인할 수 있습니다.</p>}
      <div className="mb-1 mt-2 flex items-center justify-between">
        <span className="font-mono text-[9px] font-semibold uppercase tracking-label text-faint">
          검수 모드 — 클릭 2회로 박스 지정 ({clicks.length}/2)
        </span>
        <div className="flex gap-1">
          <button type="button" className="btn px-2 py-0.5 text-[9px]" disabled={!enabled || !reviewer.trim() || !box} onClick={() => submit('defect', 'FN')}>
            불량 확정(FN)
          </button>
          <button type="button" className="btn px-2 py-0.5 text-[9px]" disabled={!enabled || !reviewer.trim() || !box} onClick={() => submit('normal', 'FP')}>
            정상 확정(FP)
          </button>
          <button type="button" className="btn px-2 py-0.5 text-[9px]" onClick={() => setClicks(() => [])}>
            초기화
          </button>
        </div>
      </div>
      {box && (
        <div className="font-mono text-[9px] text-faint">bbox [{box.join(', ')}]</div>
      )}
      {status && <div className="mt-0.5 font-mono text-[9px] text-muted">{status}</div>}
    </div>
  )
}

function MetaRow({ k, v }: { k: string; v: string | null | undefined }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1">
      <span className="shrink-0 font-mono text-[9px] uppercase tracking-label text-faint">{k}</span>
      <span className="break-all text-right font-mono text-[10px] text-muted">
        {v ?? '—'}
      </span>
    </div>
  )
}

function CaseMeta({ c }: { c: Case }) {
  return (
    <div className="glass divide-y divide-line/60 p-3">
      <MetaRow k="truth" v={c.truth_label} />
      <MetaRow k="prediction" v={c.prediction} />
      <MetaRow k="part" v={c.part_id} />
      <MetaRow k="camera" v={c.camera_id} />
      {c.attempt_status && <MetaRow k="status" v={c.attempt_status} />}
      <MetaRow k="model" v={c.model_version} />
      <MetaRow k="mapping" v={c.mapping_version} />
      <MetaRow
        k="boxes"
        v={c.box_ids.length > 0 ? `${c.box_ids.length}개` : '(없음)'}
      />
      <MetaRow
        k="review"
        v={
          c.review
            ? `${c.review.state} · ${c.review.reviewer ?? '—'}${c.review.reason ? ` · ${c.review.reason}` : ''}`
            : '(검수 없음)'
        }
      />
    </div>
  )
}

/** 사례 클릭 시 여는 C1~C5 근거 뷰어(모달). */
export function CaseViewer() {
  const viewer = useStore((s) => s.viewer)
  const cases = useStore((s) => s.cases)
  const closeViewer = useStore((s) => s.closeViewer)
  const setViewerView = useStore((s) => s.setViewerView)
  const setViewerMode = useStore((s) => s.setViewerMode)
  const reviewMode = useStore((s) => s.reviewMode)

  const [reviewClicks, setReviewClicks] = useState<Pt[]>([])
  const [imageReady,setImageReady]=useState(false)
  const [reviewReady,setReviewReady]=useState(false)
  const [reviewVersion,setReviewVersion]=useState<number | undefined>()
  const activeId=cases?.cases[viewer.index]?.product_id
  useEffect(()=>{
    setReviewClicks([]);setImageReady(false);setReviewReady(false);setReviewVersion(undefined)
    let canceled=false
    if (viewer.open && activeId) getCaseEvidenceClient({productId:activeId,cameraId:viewer.view}).then(r=>{
      if (canceled || r.source!=='api') return
      const review=r.data.cases[0]?.review
      setReviewVersion(review && 'version' in review ? (review as {version?:number}).version : undefined)
      setReviewReady(true)
    })
    return ()=>{canceled=true}
  },[viewer.open,viewer.view,viewer.index,viewer.mode,activeId])

  const open = viewer.open
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeViewer()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, closeViewer])

  if (!open) return null
  const c = cases?.cases[viewer.index]
  if (!c) return null

  const view = c.evidence.all_views[viewer.view]
  const uri =
    viewer.mode === 'original'
      ? (view?.image_uri ?? c.evidence.original_uri)
      : viewer.mode === 'error_map'
        ? (view?.error_map_uri ?? c.evidence.error_map_uri)
        : c.evidence.crop_uri

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/70 p-4 backdrop-blur-md"
      onClick={closeViewer}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`사례 근거 뷰어 ${c.product_id}`}
        className="glass max-h-[90vh] w-full max-w-3xl overflow-y-auto border-line bg-panel p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-tx">
              {c.product_id}
            </span>
            <span className="font-mono text-[10px] text-faint">
              {c.truth_label ?? '—'} → {c.prediction ?? '—'}
            </span>
          </div>
          <button type="button" className="btn" onClick={closeViewer}>
            닫기 (Esc)
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_230px]">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-1.5">
              <div className="flex gap-1" role="tablist" aria-label="시점 선택">
                {VIEW_IDS.map((vid: ViewId) => {
                  const v = c.evidence.all_views[vid]
                  return (
                    <button
                      key={vid}
                      type="button"
                      role="tab"
                      aria-selected={viewer.view === vid}
                      disabled={!v}
                      title={v ? undefined : '이 시점 뷰가 없습니다'}
                      className={`btn px-2.5 py-1 font-mono text-[11px] ${
                        viewer.view === vid ? 'btn-active' : ''
                      }`}
                      onClick={() => setViewerView(vid)}
                    >
                      {vid}
                    </button>
                  )
                })}
              </div>
              <div className="ml-auto flex gap-1" role="group" aria-label="근거 모드">
                {(Object.keys(MODE_LABELS) as ViewMode[]).map((m) => (
                  <button
                    key={m}
                    type="button"
                    className={`btn px-2 py-1 text-[11px] ${
                      viewer.mode === m ? 'btn-active' : ''
                    }`}
                    onClick={() => setViewerMode(m)}
                  >
                    {MODE_LABELS[m]}
                  </button>
                ))}
              </div>
            </div>

            <EvidenceImage
              uri={uri}
              onNatural={()=>setImageReady(true)}
              onImageClick={(e) => {
                if (!reviewMode || viewer.mode!=='original' || !imageReady) return
                const point=originalPoint(e.clientX,e.clientY,e.currentTarget.getBoundingClientRect(),e.currentTarget.naturalWidth,e.currentTarget.naturalHeight)
                if (!point) return
                setReviewClicks(c=>c.length>=2?[point]:[...c,point])
              }}
            />

            <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-slate-500">
              <span>
                {viewer.view} · {MODE_LABELS[viewer.mode]}
                {view ? ` · view ${view.view_id}` : ' · (뷰 없음)'}
                {view && view.status !== 'ok' ? ` · status ${view.status}` : ''}
              </span>
              {viewer.mode === 'crop' && c.box_ids.length === 0 && (
                <span className="text-accent-amber">검출 박스 없음 — 크롭 불가</span>
              )}
            </div>
          </div>

          <div>
            <CaseMeta c={c} />
            {reviewMode && (
              <ReviewPanel
                productId={c.product_id}
                cameraId={viewer.view}
                enabled={imageReady && reviewReady && viewer.mode === "original" && !!view}
                expectedVersion={reviewVersion}
                clicks={reviewClicks}
                setClicks={setReviewClicks}
                onDone={() => {setReviewClicks([]);setReviewReady(false);useStore.setState({statsCache:{},cardsCache:{}});void useStore.getState().loadStats();void useStore.getState().reloadCases()}}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
