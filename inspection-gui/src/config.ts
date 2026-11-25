import type { Metric, ReviewState } from './types'

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api'
export const USE_FIXTURE: boolean = import.meta.env.VITE_USE_FIXTURE === 'true'

/** 해석 주의를 표시할 분모 하한 (UI 규칙). 지표 재계산과 무관하게 표시만 흐리게 한다. */
export const MIN_DENOMINATOR = 10

export const DEFAULT_DATE_FROM = '2026-11-01'
export const DEFAULT_DATE_TO = '2026-11-30'
export const DEFAULT_MODEL_VERSION = USE_FIXTURE ? 'mock-anomaly-v1' : ''

export const ITEM_LABELS: Record<string, string> = {
  toothbrush: '칫솔 toothbrush',
  toy: '장난감 toy',
}

/** 라벨이 없는 품목(나머지 28개 카테고리)은 원문 ID를 그대로 보여준다. */
export function itemLabel(item: string): string {
  return ITEM_LABELS[item] ?? item
}

export const METRIC_DEFS: Record<
  Metric,
  { label: string; definition: string; perAttempt?: boolean }
> = {
  confirmed_defect_rate: {
    label: '확정 불량률',
    definition: '불량 확인 제품 / 부위 검수 제품',
  },
  part_miss_rate: {
    label: '미탐률',
    definition: '놓친 불량 제품 / 부위 불량 확인 제품',
  },
  part_false_alarm_rate: {
    label: '오탐률',
    definition: '잘못 경보한 정상 제품 / 부위 정상 제품',
  },
  capture_process_failure_rate: {
    label: '캡처·처리 실패율',
    definition: '누락·흐림·추론 오류 / 시도 건수',
    perAttempt: true,
  },
}

export const REVIEW_STATE_OPTIONS: { value: ReviewState | 'all'; label: string }[] = [
  { value: 'confirmed', label: '검수 확정 confirmed' },
  { value: 'pending', label: '검수 전 pending' },
  { value: 'all', label: '전체 all' },
]

export const DEFINITION_VERSION = 'metrics-v1'
export const MAPPING_VERSION = 'roi-lut-v1'
export const MODEL_VERSION = 'mock-anomaly-v1'
