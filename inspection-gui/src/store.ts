import { create } from 'zustand'
import {
  checkHealth,
  computeInspectionMetricsClient,
  getCaseEvidenceClient,
  listItems,
  queryErrorStatsClient,
  type Source,
} from './api/client'
import {
  DEFAULT_DATE_FROM,
  DEFAULT_DATE_TO,
  DEFAULT_MODEL_VERSION,
  ITEM_LABELS,
  USE_FIXTURE,
} from './config'
import type {
  CaseResponse,
  Item,
  Metric,
  MetricsResponse,
  ReviewState,
  StatsResponse,
  ViewId,
  ViewMode,
} from './types'

export type ReviewFilter = ReviewState | 'all'

export interface Filters {
  item: Item
  metric: Metric
  modelVersion: string
  reviewState: ReviewFilter
  dateFrom: string
  dateTo: string
  /** 'all'이면 전체. 사례 리스트 표시 필터(요청과 무관). */
  productId: string
}

interface ViewerState {
  open: boolean
  index: number
  view: ViewId
  mode: ViewMode
}

interface StoreState {
  readOnly:boolean
  filters: Filters
  /** DB에 로드된 품목 목록 (백엔드 /items, 실패 시 fixture 2개). */
  items: string[]
  /** 대시보드 검수 모드 — 사례 원본에서 박스 지정·승인 가능. */
  reviewMode: boolean
  /** 근거 링크로 진입한 사례 포커스 (대시보드 1회 소비). */
  focusCase: { productId: string; cameraId?: string } | null
  source: Source | null
  connectionError: string | null
  stats: StatsResponse | null
  statsLoading: boolean
  statsError: string | null
  statsCache: Record<string, StatsResponse>
  cardsCache: Record<string, MetricsResponse>
  selectedPart: string | null
  hoveredPart: string | null
  metricCards: Partial<Record<ReviewState, MetricsResponse>> | null
  metricCardsLoading: boolean
  cases: CaseResponse | null
  casesLoading: boolean
  /** review_state='all'일 때 지표 카드에 표시할 상태(확정/검수 전 토글). 섞지 않기 위함. */
  cardReviewState: ReviewState
  viewer: ViewerState

  init: () => void
  setItems: (items: string[]) => void
  setReviewMode: (on: boolean) => void
  setFocusCase: (f: { productId: string; cameraId?: string } | null) => void
  setItem: (item: Item, loadMetrics?:boolean) => void
  setMetric: (metric: Metric) => void
  setModelVersion: (v: string) => void
  setReviewState: (s: ReviewFilter) => void
  setDateFrom: (d: string) => void
  setDateTo: (d: string) => void
  setProductId: (p: string) => void
  selectPart: (partId: string | null) => void
  hoverPart: (partId: string | null) => void
  setCardReviewState: (s: ReviewState) => void
  openCase: (index: number) => void
  closeViewer: () => void
  setViewerView: (v: ViewId) => void
  setViewerMode: (m: ViewMode) => void

  /** 낮은 수준 로더(컴포넌트에서 직접 호출하지 않음) */
  loadStats: (force?:boolean) => Promise<void>
  loadMetricCards: () => Promise<void>
  loadCases: (statKey: string) => Promise<void>
  reloadCases: () => Promise<void>
  loadCasesForSelectedPart: () => Promise<void>
}

const statsKey = (f: Filters) =>
  [f.item, f.metric, f.dateFrom, f.dateTo, f.modelVersion].join('|')
const cardsKey = (f: Filters, partId: string, state: ReviewState) =>
  [f.item, partId, state, f.dateFrom, f.dateTo, f.modelVersion].join('|')

/** 요청 경주 방지용 시퀀스(리소스별) */
let statsSeq = 0
let cardsSeq = 0
let casesSeq = 0

function mergeSource(
  error: string | undefined,
): string | null {
  return error ?? null
}

export const useStore = create<StoreState>()((set, get) => ({
  readOnly:false,
  filters: {
    item: 'toothbrush',
    metric: 'part_miss_rate',
    modelVersion: DEFAULT_MODEL_VERSION,
    reviewState: 'confirmed',
    dateFrom: DEFAULT_DATE_FROM,
    dateTo: DEFAULT_DATE_TO,
    productId: 'all',
  },
  source: null,
  connectionError: null,
  items: Object.keys(ITEM_LABELS),
  reviewMode: false,
  focusCase: null,
  stats: null,
  statsLoading: false,
  statsError: null,
  statsCache: {},
  cardsCache: {},
  selectedPart: null,
  hoveredPart: null,
  metricCards: null,
  metricCardsLoading: false,
  cases: null,
  casesLoading: false,
  cardReviewState: 'confirmed',
  viewer: { open: false, index: 0, view: 'C1', mode: 'original' },

  init: () => {
    if (!USE_FIXTURE) {
      void checkHealth().then((ok) => {
        if (!ok) {
          set({
            connectionError:
              '도구 API 연결 실패. 검사 데이터는 표시하지 않습니다.',
          })
        }
      })
      void listItems()
        .then((items) => {
          if (items.length > 0) set({ items })
        })
        .catch(() => undefined)
    }
    void get().loadStats()
  },

  setItems: (items) => set({ items }),
  setReviewMode: (on) => set({ reviewMode: on&&!get().readOnly }),
  setFocusCase: (f) => set({ focusCase: f }),

  setItem: (item,loadMetrics=true) => {
    if (get().filters.item === item) return
    // Invalidate all old-category in-flight reads before clearing the screen.
    statsSeq++; cardsSeq++; casesSeq++
    set({
      filters: { ...get().filters, item, productId: 'all' },
      stats: null, statsLoading: false, statsError: null,
      metricCardsLoading: false, casesLoading: false, focusCase: null,
      selectedPart: null,
      hoveredPart: null,
      metricCards: null,
      cases: null,
      viewer: { ...get().viewer, open: false },
    })
    if(loadMetrics)void get().loadStats()
  },

  setMetric: (metric) => {
    if (get().filters.metric === metric) return
    set({ filters: { ...get().filters, metric }, cases: null })
    void get()
      .loadStats()
      .then(() => {
        if (get().selectedPart) void get().loadCasesForSelectedPart()
      })
  },

  setModelVersion: (v) => {
    if (get().filters.modelVersion === v) return
    set({ filters: { ...get().filters, modelVersion: v }, cases: null })
    void get()
      .loadStats()
      .then(() => {
        if (get().selectedPart) {
          void get().loadMetricCards()
          void get().loadCasesForSelectedPart()
        }
      })
  },

  setReviewState: (s) => {
    if (get().filters.reviewState === s) return
    set({
      filters: { ...get().filters, reviewState: s },
      cardReviewState: s === 'pending' ? 'pending' : 'confirmed',
    })
    if (get().selectedPart) void get().loadMetricCards()
  },

  setDateFrom: (d) => {
    set({ filters: { ...get().filters, dateFrom: d }, cases: null })
    void get()
      .loadStats()
      .then(() => {
        if (get().selectedPart) {
          void get().loadMetricCards()
          void get().loadCasesForSelectedPart()
        }
      })
  },

  setDateTo: (d) => {
    set({ filters: { ...get().filters, dateTo: d }, cases: null })
    void get()
      .loadStats()
      .then(() => {
        if (get().selectedPart) {
          void get().loadMetricCards()
          void get().loadCasesForSelectedPart()
        }
      })
  },

  setProductId: (p) => set({ filters: { ...get().filters, productId: p } }),

  selectPart: (partId) => {
    if (get().selectedPart === partId) return
    set({ selectedPart: partId, metricCards: null, cases: null })
    if (partId) {
      void get().loadMetricCards()
      void get().loadCasesForSelectedPart()
    }
  },

  hoverPart: (partId) => {
    if (get().hoveredPart !== partId) set({ hoveredPart: partId })
  },

  setCardReviewState: (s) => set({ cardReviewState: s }),

  openCase: (index) => {
    const c = get().cases?.cases[index]
    set({
      viewer: {
        open: true,
        index,
        view:
          c?.camera_id && (c.camera_id as ViewId) ? (c.camera_id as ViewId) : 'C1',
        mode: 'original',
      },
    })
  },

  closeViewer: () => set({ viewer: { ...get().viewer, open: false } }),
  setViewerView: (v) => set({ viewer: { ...get().viewer, view: v } }),
  setViewerMode: (m) => set({ viewer: { ...get().viewer, mode: m } }),

  loadStats: async (force=false) => {
    const mySeq = ++statsSeq
    const f = get().filters
    const key = statsKey(f)
    const cached = force?undefined:get().statsCache[key]
    if (cached) {
      set({ stats: cached, statsLoading: false, statsError: null })
      return
    }
    set({ statsLoading: true, statsError: null })
    const res = await queryErrorStatsClient({
      item: f.item,
      metric: f.metric,
      dateFrom: f.dateFrom,
      dateTo: f.dateTo,
      modelVersion: f.modelVersion,
    })
    if (mySeq !== statsSeq) return
    set((s) => ({
      stats: res.data,
      statsLoading: false,
      statsError: res.error ?? null,
      source: res.source,
      connectionError: mergeSource(res.error),
      statsCache: res.error ? s.statsCache : { ...s.statsCache, [key]: res.data },
    }))
    if (f.metric === 'capture_process_failure_rate') {
      const row0 = res.data.rows[0]
      if (row0) await get().loadCases(row0.stat_key)
      await get().loadMetricCards()
    }
  },

  loadMetricCards: async () => {
    const mySeq = ++cardsSeq
    const f = get().filters
    const isCapture = f.metric === 'capture_process_failure_rate'
    const part = get().selectedPart
    if (part === null && !isCapture) return
    const states: ReviewState[] =
      f.reviewState === 'all' ? ['confirmed', 'pending'] : [f.reviewState]
    set({ metricCardsLoading: true })
    const cards: Partial<Record<ReviewState, MetricsResponse>> = {}
    const newCache: Record<string, MetricsResponse> = {}
    await Promise.all(
      states.map(async (st) => {
        const key = cardsKey(f, part ?? '*', st)
        const cached = get().cardsCache[key]
        const res = cached
          ? { data: cached, source: get().source ?? 'fixture' }
          : await computeInspectionMetricsClient({
              item: f.item,
              partId: part,
              reviewState: st,
              dateFrom: f.dateFrom,
              dateTo: f.dateTo,
              modelVersion: f.modelVersion,
            })
        cards[st] = res.data
        newCache[key] = res.data
      }),
    )
    if (mySeq !== cardsSeq) return
    set((s) => ({
      metricCards: cards,
      metricCardsLoading: false,
      cardsCache: { ...s.cardsCache, ...newCache },
    }))
  },

  loadCases: async (statKey: string) => {
    const mySeq = ++casesSeq
    set({ casesLoading: true })
    const res = await getCaseEvidenceClient({ statKey })
    if (mySeq !== casesSeq) return
    set(() => ({
      cases: res.data,
      casesLoading: false,
      source: res.source,
      connectionError: mergeSource(res.error),
    }))
  },

  loadCasesForSelectedPart: async () => {
    const { stats, selectedPart } = get()
    if (!stats || !selectedPart) return
    const row = stats.rows.find((r) => r.group.part_id === selectedPart)
    if (!row) {
      set({ cases: null })
      return
    }
    await get().loadCases(row.stat_key)
  },

  reloadCases: async () => {
    await get().loadCasesForSelectedPart()
  },
}))
