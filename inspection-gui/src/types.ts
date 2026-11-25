/** 백엔드 도구 API와 동일한 스키마 (app/tools.py 기준). */

/** 품목은 DB에 로드된 30개 카테고리 전부 — 문자열로 받는다. */
export type Item = string

export type Metric =
  | 'confirmed_defect_rate'
  | 'part_miss_rate'
  | 'part_false_alarm_rate'
  | 'capture_process_failure_rate'

export type ReviewState = 'pending' | 'confirmed'

export type Rate = {
  num: number
  den: number
  rate: number | null
  reason: string | null
}

export interface StatsRow {
  group: Record<string, string | null>
  num: number
  den: number
  rate: number | null
  reason: string | null
  stat_key: string
}

export interface StatsResponse {
  reason?: string
  source_scope?: string
  /** Only a provenance-validated backend may enable physical region projection. */
  mapping_verified?: boolean
  item: Item
  metric: Metric
  group_by: string[]
  rows: StatsRow[]
  order: string
  limit: number
  min_denominator: number
  model_version: string | null
  mapping_version: string | null
  definition_version: string
}

export interface MetricsResponse {
  filters: Record<string, unknown>
  metrics: Record<Metric, Rate>
  model_version: string | null
  mapping_version: string | null
  definition_version: string
}

export type ViewId = 'C1' | 'C2' | 'C3' | 'C4' | 'C5'
export const VIEW_IDS: ViewId[] = ['C1', 'C2', 'C3', 'C4', 'C5']

export type ViewMode = 'original' | 'error_map' | 'crop'

export interface CaseView {
  view_id: string
  image_uri: string
  error_map_uri: string
  status: string
}

export interface Case {
  product_id: string
  item: Item
  part_id: string | null
  camera_id: string | null
  truth_label: 'defect' | 'normal' | null
  prediction: 'defect' | 'normal' | null
  model_version: string | null
  mapping_version: string | null
  box_ids: string[]
  attempt_status?: string | null
  evidence: {
    original_uri: string | null
    error_map_uri: string | null
    crop_uri: string | null
    all_views: Record<ViewId, CaseView | null>
  }
  review: { state: string; reviewer: string | null; reason: string | null } | null
}

export interface CaseResponse {
  cases: Case[]
  count: number
  limit: number
  filters: Record<string, unknown> | null
  model_version: string | null
  mapping_version: string | null
  definition_version: string
}

/** stat_key에 담기는 필터 형태 (백엔드 query_error_stats와 동일 구조). */
export interface StatKeyFilters {
  def: string
  metric: Metric
  item: Item
  part_id: string | null
  camera_id: string | null
  model_version: string | null
  date_from: string | null
  date_to: string | null
  review_state: string
  min_denominator: number
}

// ---------------------------------------------------------------- 신규: 상태/성능/추론

export interface LoadedStatus {
  products: number | null
  views: number | null
  target_products: number
  target_views: number
  product_progress: number | null
  view_progress: number | null
}

export interface ScoreBackfillStatus {
  status: string | null
  expected_products: number
  completed_products: number | null
  completed_views: number | null
  score_variant: string | null
  progress: number | null
}

export interface FinalPerformanceMetrics {
  database_run_activated?:boolean
  fusion_policy?:{weights?:{rtdetr:number;hvq:number};hvq_score_variant?:string;rtdetr_conf_threshold?:number;normalization?:string}
  evaluation_products?: number | null
  evaluation_scope?: 'test' | 'all_inferred_products_reference'
  contains_calibration_products?: boolean
  training_overlap?: string | null
  csv_consistency_verified?: boolean
  test_reference?: Record<string, unknown> | null
  test_f1_micro?: number | null
  test_recall?: number | null
  cohort_products: number | null
  test_products: number | null
  fp: number | null
  fn: number | null
  recall: number | null
  f1_micro: number | null
  auroc: number | null
  ap: number | null
  f1_category_macro: number | null
  auroc_category_macro: number | null
  hold_products: number | null
  hold_rate: number | null
  coverage: number | null
  final_fp: number | null
  final_fn: number | null
  decided_f1: number | null
  single_model_hvq_f1: number | null
  single_model_rtdetr_f1: number | null
  verified: boolean
  timestamp: string | null
}

export interface StatusOverview {
  loaded: LoadedStatus
  score_backfill: ScoreBackfillStatus
  pipeline: { model_run: string | null; model_run_status: string | null }
  final_performance: {
    available: boolean
    is_fixture: boolean
    state: 'waiting' | 'computing' | 'report_pending' | 'complete'
    report_path: string | null
    model_version: string | null
    baseline_v1: {
      label: string
      recall: number
      f1: number
      miss: number
      false_alarm: number
      source: string
    }
    metrics: FinalPerformanceMetrics | null
  }
  models: {
    hvq: string
    rtdetr: string
    hvq_epochs: number
    rtdetr_epochs: string
    weights: { hvq: number; rtdetr: number }
    config_version: string
  }
}

export interface Detection {
  bbox: [number, number, number, number]
  class_id: number
  class_name: string
  score: number
}

export interface GuiInferenceView {
  camera_id: ViewId
  width: number
  height: number
  image_path: string
  rtdetr_raw: number
  hvq_mean: number
  hvq_max16: number
  detections: Detection[]
  heatmap_png: string
  map_npy: string
}

export interface GuiInferenceProduct {
  item: string
  status: 'CONFIGURED' | 'UNCONFIGURED'
  rtdetr_raw: number
  hvq_max16: number
  rtdetr_conf_threshold: number
  hvq_threshold: number
  rtdetr_positive: boolean
  hvq_positive: boolean
  rt: number
  hvq: number
  weights: { rtdetr: number; hvq: number }
  fusion_score: number | null
  threshold: number | null
  margin: number | null
  rt_percentile: number | null
  hvq_percentile: number | null
  binary_verdict: 'defect' | 'normal' | null
  verdict: 'defect' | 'normal' | 'hold' | null
}

export interface GuiInferenceResult {
  ok: boolean
  item: string
  product_id: string | null
  views: Record<string, GuiInferenceView>
  product: GuiInferenceProduct
  models: Record<string, string>
  config_version: string | null
  elapsed_ms: number | null
  rationale: string[]
  db_record: { attempt_id?: string; product_id?: string; model_version?: string; recorded: boolean }
}
