import { describe, expect, it } from 'vitest'
import {
  decodeStatKey,
  fixtureGetCaseEvidence,
  fixtureQueryErrorStats,
  type StatsParams,
} from './loader'
import { VIEW_IDS } from '../types'

const BASE: StatsParams = {
  item: 'toothbrush',
  metric: 'part_miss_rate',
  dateFrom: '2026-11-01',
  dateTo: '2026-11-30',
  modelVersion: 'mock-anomaly-v1',
}

describe('fixture query_error_stats', () => {
  it('bristle이 가장 뜨겁게 강조되는 num/den/rate를 반환', () => {
    const res = fixtureQueryErrorStats(BASE)
    expect(res.definition_version).toBe('metrics-v1')
    expect(res.mapping_version).toBe('roi-lut-v1')
    const bristle = res.rows.find((r) => r.group.part_id === 'bristle')
    expect(bristle).toBeDefined()
    expect(bristle!.num).toBe(6)
    expect(bristle!.den).toBe(40)
    expect(bristle!.rate).toBeCloseTo(0.15, 5)
    const rates = res.rows.map((r) => r.rate ?? -1)
    expect(Math.max(...rates)).toBe(bristle!.rate)
    // 모든 행에 stat_key가 있어야 LLM/GUI가 근거 조회로 이어갈 수 있다
    for (const row of res.rows) expect(row.stat_key.length).toBeGreaterThan(0)
  })

  it('분모 0 행은 rate=null, reason=denominator_zero (toy edge)', () => {
    const res = fixtureQueryErrorStats({ ...BASE, item: 'toy' })
    const edge = res.rows.find((r) => r.group.part_id === 'edge')
    expect(edge).toBeDefined()
    expect(edge!.den).toBe(0)
    expect(edge!.rate).toBeNull()
    expect(edge!.reason).toBe('denominator_zero')
  })
})

describe('stat_key로 사례 조회 fixture 연결', () => {
  it('part_miss_rate stat_key → bristle 불량 확인 사례와 C1~C5 근거', () => {
    const stats = fixtureQueryErrorStats(BASE)
    const bristle = stats.rows.find((r) => r.group.part_id === 'bristle')!

    const decoded = decodeStatKey(bristle.stat_key)
    expect(decoded.metric).toBe('part_miss_rate')
    expect(decoded.item).toBe('toothbrush')
    expect(decoded.part_id).toBe('bristle')

    const ev = fixtureGetCaseEvidence({ statKey: bristle.stat_key })
    expect(ev.count).toBeGreaterThanOrEqual(1)
    expect(ev.definition_version).toBe('metrics-v1')
    expect(ev.mapping_version).toBe('roi-lut-v1')
    for (const c of ev.cases) {
      expect(c.truth_label).toBe('defect')
      expect(c.model_version).toBe('mock-anomaly-v1')
      expect(c.mapping_version).toBe('roi-lut-v1')
      // C1~C5 탭용 근거가 모두 존재
      expect(Object.keys(c.evidence.all_views).sort()).toEqual([...VIEW_IDS].sort())
    }
    // 미탐 사례는 box_ids가 비어 있어야 한다
    const missed = ev.cases.filter((c) => c.prediction === 'normal')
    expect(missed.length).toBeGreaterThanOrEqual(1)
    for (const c of missed) expect(c.box_ids).toHaveLength(0)
  })

  it('capture stat_key → 오류 시도 사례 (part_id/truth 없음)', () => {
    const cap = fixtureQueryErrorStats({
      ...BASE,
      metric: 'capture_process_failure_rate',
    })
    expect(cap.group_by).toEqual(['model_version'])
    const ev = fixtureGetCaseEvidence({ statKey: cap.rows[0].stat_key })
    expect(ev.count).toBeGreaterThanOrEqual(1)
    for (const c of ev.cases) {
      expect(c.attempt_status).toBeTruthy()
      expect(c.truth_label).toBeNull()
      expect(c.part_id).toBeNull()
    }
  })

  it('stat_key는 요청 파라미터(날짜)를 그대로 담아 stable하게 유지된다', () => {
    const a = fixtureQueryErrorStats(BASE)
    const b = fixtureQueryErrorStats({ ...BASE, dateFrom: '2026-11-10' })
    expect(a.rows[0].stat_key).not.toBe(b.rows[0].stat_key)
    expect(decodeStatKey(b.rows[0].stat_key).date_from).toBe('2026-11-10T00:00:00')
  })

  it('품목 교체 시 해당 품목 fixture로 전체 갱신 (toy surface)', () => {
    const res = fixtureQueryErrorStats({ ...BASE, item: 'toy' })
    const ids = res.rows.map((r) => r.group.part_id).sort()
    expect(ids).toEqual(['edge', 'joint', 'surface'])
  })
})
