/**
 * 도구 API 클라이언트. VITE_USE_FIXTURE=true면 fixture만 쓰고,
 * 아니면 FastAPI /tools/* 를 호출하며 실패 시 오류와 빈 결과를 반환한다.
 */
import { API_BASE, USE_FIXTURE } from '../config'
import fixtureReport from '../fixtures/final_performance.json'
import {
  fixtureComputeInspectionMetrics,
  fixtureGetCaseEvidence,
  fixtureQueryErrorStats,
  type EvidenceParams,
  type MetricsParams,
  type StatsParams,
} from '../fixtures/loader'
import type { CaseResponse, GuiInferenceResult, MetricsResponse, StatsResponse, StatusOverview } from '../types'

export type Source = 'api' | 'fixture' | 'fixture-fallback'

export interface ClientResult<T> {
  data: T
  source: Source
  /** 폭백 발생 시 원인 메시지 */
  error?: string
}

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

async function postApi<T>(tool: string, body: Record<string, unknown>): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}/tools/${tool}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(6000),
    })
  } catch (e) {
    throw new Error(`${API_BASE} 연결 실패: ${errorMessage(e)}`)
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 160)}`)
  }
  return (await res.json()) as T
}

export async function checkHealth(): Promise<boolean> {
  if (USE_FIXTURE) return true
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) })
    return res.ok
  } catch {
    return false
  }
}

export interface FusionRun {
  fusion_run_id: string
  status: string
  is_active: boolean
  deployment_eligible: boolean
  contract_version: string | null
  normalization: string | null
  hvq_score_variant: string | null
  report_model_version: string | null
  evaluation_products: number | null
  created_at: string | null
}

/** 기록된 퓨전 run 목록 — 활성 run이 첫 번째. 실패 시 빈 목록. */
export async function getFusionRuns(): Promise<ClientResult<{ runs: FusionRun[] }>> {
  if (USE_FIXTURE) return { data: { runs: [] }, source: 'fixture' }
  try {
    const res = await fetch(`${API_BASE}/fusion/runs`, { signal: AbortSignal.timeout(6000) })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return { data: (await res.json()) as { runs: FusionRun[] }, source: 'api' }
  } catch (e) {
    return { data: { runs: [] }, source: 'api', error: errorMessage(e) }
  }
}

export async function queryErrorStatsClient(
  params: StatsParams,
): Promise<ClientResult<StatsResponse>> {
  if (USE_FIXTURE) {
    return { data: fixtureQueryErrorStats(params), source: 'fixture' }
  }
  try {
    const data = await postApi<StatsResponse>('query_error_stats', {
      item: params.item,
      metric: params.metric,
      group_by: params.metric === 'capture_process_failure_rate' ? ['model_version'] : ['part_id'],
      date_from: `${params.dateFrom}T00:00:00`,
      date_to: `${params.dateTo}T23:59:59`,
      model_version: params.modelVersion,
      min_denominator: params.minDenominator ?? 1,
      order: 'desc',
      limit: 10,
    })
    return { data, source: 'api' }
  } catch (e) {
    return {
      data: { item: params.item, metric: params.metric, group_by: ["part_id"], rows: [], order: "desc", limit: 10, min_denominator: 1, model_version: params.modelVersion ?? null, mapping_version: null, definition_version: "unavailable" },
      source: 'api',
      error: errorMessage(e),
    }
  }
}

export async function computeInspectionMetricsClient(
  params: MetricsParams,
): Promise<ClientResult<MetricsResponse>> {
  if (USE_FIXTURE) {
    return { data: fixtureComputeInspectionMetrics(params), source: 'fixture' }
  }
  try {
    const data = await postApi<MetricsResponse>('compute_inspection_metrics', {
      item: params.item,
      part_id: params.partId,
      date_from: `${params.dateFrom}T00:00:00`,
      date_to: `${params.dateTo}T23:59:59`,
      model_version: params.modelVersion,
      review_state: params.reviewState,
    })
    return { data, source: 'api' }
  } catch (e) {
    return {
      data: { filters: {}, metrics: Object.fromEntries(["confirmed_defect_rate", "part_miss_rate", "part_false_alarm_rate", "capture_process_failure_rate"].map(m => [m, {num: 0, den: 0, rate: null, reason: "backend_unavailable"}])) as MetricsResponse["metrics"], model_version: null, mapping_version: null, definition_version: "unavailable" },
      source: 'api',
      error: errorMessage(e),
    }
  }
}

export async function getCaseEvidenceClient(
  params: EvidenceParams,
): Promise<ClientResult<CaseResponse>> {
  if (USE_FIXTURE) {
    return { data: fixtureGetCaseEvidence(params), source: 'fixture' }
  }
  try {
    const body: Record<string, unknown> = { limit: params.limit ?? 20 }
    if (params.statKey) body.stat_key = params.statKey
    if (params.productId) body.product_id = params.productId
    if (params.partId) body.part_id = params.partId
    if (params.cameraId) body.camera_id = params.cameraId
    const data = await postApi<CaseResponse>('get_case_evidence', body)
    return { data, source: 'api' }
  } catch (e) {
    return {
      data: { cases: [], count: 0, limit: params.limit ?? 20, filters: null, model_version: null, mapping_version: null, definition_version: "unavailable" },
      source: 'api',
      error: errorMessage(e),
    }
  }
}

// ---------------------------------------------------------------- 신규 엔드포인트

export async function getStatusOverview(): Promise<StatusOverview> {
  const res = await fetch(`${API_BASE}/status/overview`, { signal: AbortSignal.timeout(8000) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as StatusOverview
}

export async function getFinalPerformance(): Promise<StatusOverview['final_performance']> {
  const res = await fetch(`${API_BASE}/performance/final`, { signal: AbortSignal.timeout(8000) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const d = (await res.json()) as { summary: StatusOverview['final_performance'] }
  return d.summary
}

export async function listItems(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/items`, { signal: AbortSignal.timeout(8000) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const d = (await res.json()) as { items: string[] }
  return d.items
}

export async function listSampleProducts(item: string, limit = 8): Promise<string[]> {
  const res = await fetch(
    `${API_BASE}/inference/sample_products?item=${encodeURIComponent(item)}&limit=${limit}`,
    { signal: AbortSignal.timeout(8000) },
  )
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const d = (await res.json()) as { products: string[] }
  return d.products
}

export async function runInferenceUpload(args: {
  item: string
  files: Record<string, File>
}): Promise<GuiInferenceResult> {
  const form = new FormData()
  form.set('item', args.item)
  form.set('mode', 'upload')
  for (const [cam, f] of Object.entries(args.files)) form.set(cam, f)
  const res = await fetch(`${API_BASE}/inference/run`, { method: 'POST', body: form })
  const d = await res.json()
  if (!res.ok) throw new Error(d?.error?.message ?? `HTTP ${res.status}`)
  return d as GuiInferenceResult
}

export async function runInferenceExisting(args: {
  item: string
  productId: string
}): Promise<GuiInferenceResult> {
  const form = new FormData()
  form.set('item', args.item)
  form.set('mode', 'existing')
  form.set('product_id', args.productId)
  const res = await fetch(`${API_BASE}/inference/run`, { method: 'POST', body: form })
  const d = await res.json()
  if (!res.ok) throw new Error(d?.error?.message ?? `HTTP ${res.status}`)
  return d as GuiInferenceResult
}

// ---------------------------------------------------------------- fixture 폭백

const BASELINE_V1 = {
  label: '기준선 v1 (Test NG600+OK600)',
  recall: 0.938,
  f1: 0.9314,
  miss: 37,
  false_alarm: 46,
  source: 'config/teammate_fusion_reference.json',
}

/** 백엔드에 final_performance가 없을 때 렌더링 검증용 fixture 요약. */
export function fixtureFinalPerformance(): StatusOverview['final_performance'] {
  const r = (fixtureReport as { test?: Record<string, unknown> }).test ?? {}
  const binary = (r.binary_threshold ?? {}) as Record<string, unknown>
  const hold = (r.final_with_hold ?? {}) as Record<string, unknown>
  const decided = (hold.decided_only_metrics ?? {}) as Record<string, unknown>
  const macro = (fixtureReport as { category_macro?: Record<string, unknown> }).category_macro ?? {}
  const rate = (d: unknown): number | null =>
    d && typeof d === 'object' ? ((d as { rate?: number }).rate ?? null) : null
  return {
    available: true,
    is_fixture: true,
    state: 'complete',
    report_path: 'fixture://final_performance.json',
    model_version:
      (fixtureReport as { model_version?: string }).model_version ?? null,
    baseline_v1: BASELINE_V1,
    metrics: {
      cohort_products:
        (fixtureReport as { cohort_products?: number }).cohort_products ?? null,
      test_products: (r.products as number) ?? null,
      fp: (binary.fp as number) ?? null,
      fn: (binary.fn as number) ?? null,
      recall: rate(binary.recall),
      f1_micro: rate(binary.f1),
      auroc: (binary.auroc as number) ?? null,
      ap: (binary.average_precision as number) ?? null,
      f1_category_macro: (macro.f1 as number) ?? null,
      auroc_category_macro: (macro.auroc as number) ?? null,
      hold_products: (hold.hold_products as number) ?? null,
      hold_rate: (hold.hold_rate as number) ?? null,
      coverage: (hold.coverage as number) ?? null,
      final_fp: (decided.fp as number) ?? null,
      final_fn: (decided.fn as number) ?? null,
      decided_f1: rate(decided.f1),
      single_model_hvq_f1: rate(
        ((r.single_model_hvq ?? {}) as Record<string, unknown>).f1,
      ),
      single_model_rtdetr_f1: rate(
        ((r.single_model_rtdetr ?? {}) as Record<string, unknown>).f1,
      ),
      verified: true,
      timestamp:
        (fixtureReport as { timestamp?: string }).timestamp ?? null,
    },
  }
}
