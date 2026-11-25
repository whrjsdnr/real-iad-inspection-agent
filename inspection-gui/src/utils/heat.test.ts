import { describe, expect, it } from 'vitest'
import {
  HEAT_FAIL,
  HEAT_OK,
  HEAT_WARN,
  NULL_COLOR,
  formatRate,
  isInterpretationCaution,
  rateToColor,
} from './heat'

function redChannel(hex: string): number {
  return parseInt(hex.slice(1, 3), 16)
}

function rgbHex([r, g, b]: readonly number[]): string {
  const h = (v: number) => Math.round(v).toString(16).padStart(2, '0').toUpperCase()
  return `#${h(r)}${h(g)}${h(b)}`
}

describe('rateToColor 히트 색상 매핑', () => {
  it('분모 0(null/undefined)은 무조건 회색(--faint)', () => {
    expect(rateToColor(null)).toBe(NULL_COLOR)
    expect(rateToColor(undefined)).toBe(NULL_COLOR)
  })

  it('rate 0은 차가운 색, rate 1은 --heat-fail', () => {
    const cold = rateToColor(0)
    const hot = rateToColor(1)
    expect(redChannel(cold)).toBeLessThan(redChannel(hot))
    expect(hot).toBe(rgbHex(HEAT_FAIL))
  })

  it('rate가 오를수록 R 채널이 단조 증가한다 (ok→warn 구간)', () => {
    let prev = -1
    for (let i = 0; i <= 14; i++) {
      const r = redChannel(rateToColor((i / 14) * 0.7))
      expect(r).toBeGreaterThanOrEqual(prev)
      prev = r
    }
  })

  it('경계값: 0.42는 --heat-ok, 0.72는 --heat-warn', () => {
    expect(rateToColor(0.42)).toBe(rgbHex(HEAT_OK))
    expect(rateToColor(0.72)).toBe(rgbHex(HEAT_WARN))
  })
})

describe('분모 0 처리', () => {
  it('formatRate(null)은 "분모 없음"', () => {
    expect(formatRate(null)).toBe('분모 없음')
    expect(formatRate(0.15)).toBe('15.0%')
  })

  it('해석 주의는 분모가 0보다 크고 하한 미만일 때만', () => {
    expect(isInterpretationCaution(0)).toBe(false)
    expect(isInterpretationCaution(null)).toBe(false)
    expect(isInterpretationCaution(5)).toBe(true)
    expect(isInterpretationCaution(10)).toBe(false)
    expect(isInterpretationCaution(40)).toBe(false)
  })
})
