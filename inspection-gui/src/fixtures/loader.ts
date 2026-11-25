/**
 * Fixture 로더. VITE_USE_FIXTURE=true인 명시적 테스트 모드에서만 사용.
 * src/fixtures/*.json은 백엔드 응답의 "숫자/사례 뼈대"만 담고,
 * stat_key와 evidence URI(all_views)는 여기서 요청 파라미터에 맞게 조립해
 * 실제 API 응답 형태와 동일하게 만든다. 지표 숫자는 절대 재계산하지 않는다.
 */
import { DEFINITION_VERSION, MAPPING_VERSION, MODEL_VERSION } from '../config'
import type {
  Case,
  CaseResponse,
  Item,
  Metric,
  MetricsResponse,
  Rate,
  ReviewState,
  StatKeyFilters,
  StatsResponse,
  StatsRow,
  ViewId,
} from '../types'
import { VIEW_IDS } from '../types'
import toothbrushJson from './toothbrush.json'
import toyJson from './toy.json'

interface FixtureCaseSeed {
  product_id: string
  camera_id: string | null
  truth_label: 'defect' | 'normal' | null
  prediction: 'defect' | 'normal' | null
  box_ids: string[]
  attempt_status?: string
  missing_views?: ViewId[]
  blurred_views?: ViewId[]
}

interface FixtureItem {
  stats: Record<Metric, { rows: Array<Omit<StatsRow, 'stat_key'>> }>
  metrics: Record<string, Record<ReviewState, Record<Metric, Rate>>>
  evidence: Partial<Record<Metric, Record<string, FixtureCaseSeed[]>>>
}

const DATA: Record<string, FixtureItem> = {
  toothbrush: toothbrushJson as unknown as FixtureItem,
  toy: toyJson as unknown as FixtureItem,
}

/** 백엔드 _stat_key와 동일: 정렬된 키의 compact JSON. */
export function makeStatKey(filters: StatKeyFilters): string {
  const entries = Object.entries(filters).sort(([a], [b]) => (a < b ? -1 : 1))
  return JSON.stringify(Object.fromEntries(entries))
}

export function decodeStatKey(statKey: string): StatKeyFilters {
  const parsed = JSON.parse(statKey) as StatKeyFilters
  if (typeof parsed !== 'object' || parsed === null || !parsed.metric) {
    throw new Error(`유효하지 않은 stat_key: ${statKey.slice(0, 64)}`)
  }
  return parsed
}

export interface StatsParams {
  item: Item
  metric: Metric
  dateFrom: string
  dateTo: string
  modelVersion: string
  minDenominator?: number
}

export function fixtureQueryErrorStats(params: StatsParams): StatsResponse {
  const data = DATA[params.item as keyof typeof DATA]
  const isCapture = params.metric === 'capture_process_failure_rate'
  if (!data) {
    // fixture에 없는 품목(나머지 28개): 빈 집계로 폭백 (분모 없음 표시)
    return {
      item: params.item,
      metric: params.metric,
      group_by: isCapture ? ['model_version'] : ['part_id'],
      rows: [],
      order: 'desc',
      limit: 10,
      min_denominator: params.minDenominator ?? 1,
      model_version: params.modelVersion ?? null,
      mapping_version: MAPPING_VERSION,
      definition_version: DEFINITION_VERSION,
    }
  }
  const rows: StatsRow[] = data.stats[params.metric].rows.map((row) => {
    const partId = row.group.part_id ?? null
    const filters: StatKeyFilters = {
      def: DEFINITION_VERSION,
      metric: params.metric,
      item: params.item,
      part_id: partId,
      camera_id: isCapture ? null : partId ? cameraForPart(params.item, partId) : null,
      model_version: params.modelVersion ?? null,
      date_from: `${params.dateFrom}T00:00:00`,
      date_to: `${params.dateTo}T23:59:59`,
      review_state: 'confirmed',
      min_denominator: params.minDenominator ?? 1,
    }
    return { ...row, stat_key: makeStatKey(filters) }
  })
  return {
    item: params.item,
    metric: params.metric,
    group_by: isCapture ? ['model_version'] : ['part_id'],
    rows,
    order: 'desc',
    limit: 10,
    min_denominator: params.minDenominator ?? 1,
    model_version: params.modelVersion ?? null,
    mapping_version: MAPPING_VERSION,
    definition_version: DEFINITION_VERSION,
  }
}

/** 품목의 기본 검사 칼라(백엔드 ITEMS 정의와 동일). */
const PART_CAMERA: Record<string, Record<string, string>> = {
  toothbrush: { bristle: 'C1', neck: 'C2', handle: 'C3' },
  toy: { surface: 'C1', edge: 'C2', joint: 'C3' },
}

function cameraForPart(item: Item, partId: string): string | null {
  return PART_CAMERA[item]?.[partId] ?? null
}

export interface MetricsParams {
  item: Item
  partId: string | null
  reviewState: ReviewState
  dateFrom: string
  dateTo: string
  modelVersion: string
}

export function fixtureComputeInspectionMetrics(params: MetricsParams): MetricsResponse {
  const data = DATA[params.item as keyof typeof DATA]
  const key = params.partId ?? '*'
  const metrics = data?.metrics[key]?.[params.reviewState]
  const allNull = Object.fromEntries(
    (['confirmed_defect_rate', 'part_miss_rate', 'part_false_alarm_rate',
      'capture_process_failure_rate'] as Metric[]).map((m) => [
      m,
      { num: 0, den: 0, rate: null, reason: 'fixture_item_missing' },
    ]),
  ) as MetricsResponse['metrics']
  return {
    filters: {
      item: params.item,
      part_id: params.partId,
      date_from: `${params.dateFrom}T00:00:00`,
      date_to: `${params.dateTo}T23:59:59`,
      model_version: params.modelVersion,
      review_state: params.reviewState,
    },
    metrics: metrics ?? allNull,
    model_version: params.modelVersion,
    mapping_version: null,
    definition_version: DEFINITION_VERSION,
  }
}

export interface EvidenceParams {
  statKey?: string
  productId?: string | null
  partId?: string | null
  cameraId?: string | null
  limit?: number
}

function buildCase(seed: FixtureCaseSeed, item: Item): Case {
  const cam = seed.camera_id
  const views = Object.fromEntries(
    VIEW_IDS.map((vid): [ViewId, Case['evidence']['all_views'][ViewId]] => {
      if (seed.missing_views?.includes(vid)) return [vid, null]
      const status = seed.blurred_views?.includes(vid) ? 'blurred' : 'ok'
      return [
        vid,
        {
          view_id: `V-${seed.product_id}-${vid}`,
          image_uri: `mock://images/${item}/${seed.product_id}/${vid}.png`,
          error_map_uri: `mock://errmaps/${item}/${seed.product_id}/${vid}.png`,
          status,
        },
      ]
    }),
  ) as Case['evidence']['all_views']
  const primary = cam ? views[cam as ViewId] : null
  return {
    product_id: seed.product_id,
    item,
    part_id: seed.attempt_status ? null : inferPart(item, cam),
    camera_id: cam,
    truth_label: seed.truth_label,
    prediction: seed.prediction,
    model_version: MODEL_VERSION,
    mapping_version: MAPPING_VERSION,
    box_ids: seed.box_ids,
    attempt_status: seed.attempt_status ?? null,
    evidence: {
      original_uri: primary?.image_uri ?? null,
      error_map_uri: primary?.error_map_uri ?? null,
      crop_uri:
        primary && seed.box_ids.length > 0
          ? `mock://crops/${seed.product_id}/${cam}/${seed.box_ids[0]}.png`
          : null,
      all_views: views,
    },
    review: seed.attempt_status
      ? null
      : { state: 'confirmed', reviewer: 'qa-1', reason: null },
  }
}

function inferPart(item: Item, cameraId: string | null): string | null {
  if (!cameraId) return null
  const entry = Object.entries(PART_CAMERA[item] ?? {}).find(([, cam]) => cam === cameraId)
  return entry ? entry[0] : null
}

export function fixtureGetCaseEvidence(params: EvidenceParams): CaseResponse {
  const limit = params.limit ?? 20
  let filters: StatKeyFilters | null = null
  let item: Item | null = null
  let metric: Metric | null = null
  let partId: string | null = params.partId ?? null

  if (params.statKey) {
    filters = decodeStatKey(params.statKey)
    item = filters.item
    metric = filters.metric
    partId = filters.part_id ?? partId
  }

  let seeds: FixtureCaseSeed[] = []
  if (item && metric) {
    const key = metric === 'capture_process_failure_rate' ? '*' : (partId ?? '*')
    seeds = DATA[item as keyof typeof DATA]?.evidence[metric]?.[key] ?? []
  }
  let cases = seeds.map((seed) => buildCase(seed, item ?? 'toothbrush'))
  if (params.productId) {
    cases = cases.filter((c) => c.product_id === params.productId)
  }
  cases = cases.slice(0, limit)

  return {
    cases,
    count: cases.length,
    limit,
    filters: filters as Record<string, unknown> | null,
    model_version: filters?.model_version ?? null,
    mapping_version: MAPPING_VERSION,
    definition_version: DEFINITION_VERSION,
  }
}
