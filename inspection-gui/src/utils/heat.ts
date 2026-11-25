import { MIN_DENOMINATOR } from '../config'
import { cssVar,tokenRgb } from './tokens'

/** 분모 없음(데이터 없음) 표시색 — --faint 토큰. */
export const NULL_COLOR = cssVar('--faint')

type Rgb = [number, number, number]

/** 히트맵 앵커 — styles/tokens.css의 --heat-ok/--heat-warn/--heat-fail와 동일 값. */
export const HEAT_OK: Rgb = tokenRgb('--heat-ok')
export const HEAT_WARN: Rgb = tokenRgb('--heat-warn')
export const HEAT_FAIL: Rgb = tokenRgb('--heat-fail')
const BG: Rgb = tokenRgb('--bg')

function mix(a: Rgb, b: Rgb, t: number): Rgb {
  const k = Math.min(1, Math.max(0, t))
  return [
    a[0] + (b[0] - a[0]) * k,
    a[1] + (b[1] - a[1]) * k,
    a[2] + (b[2] - a[2]) * k,
  ]
}

/**
 * --ok → --warn → --fail 사다리에서 파생한 히트 스케일.
 * 낮음=차가움(--ok를 배경 쪽으로 어둡게), 높음=따뜻함(--warn→--fail).
 */
const STOPS: Array<[number, Rgb]> = [
  [0.0, mix(HEAT_OK, BG, 0.25)],
  [0.42, HEAT_OK],
  [0.72, HEAT_WARN],
  [1.0, HEAT_FAIL],
]

function clamp01(x: number): number {
  return Math.min(1, Math.max(0, x))
}

function toHex([r, g, b]: Rgb): string {
  const h = (v: number) => Math.round(v).toString(16).padStart(2, '0').toUpperCase()
  return `#${h(r)}${h(g)}${h(b)}`
}

/** rate(0~1)를 히트 색상으로. null이면 분모 없음 회색. */
export function rateToColor(rate: number | null | undefined): string {
  if (rate == null) return NULL_COLOR
  const t = clamp01(rate)
  for (let i = 1; i < STOPS.length; i++) {
    const [t1, c1] = STOPS[i]
    if (t <= t1) {
      const [t0, c0] = STOPS[i - 1]
      return toHex(mix(c0, c1, (t - t0) / (t1 - t0)))
    }
  }
  return toHex(STOPS[STOPS.length - 1][1])
}

export function formatRate(rate: number | null | undefined): string {
  if (rate == null) return '분모 없음'
  return `${(rate * 100).toFixed(1)}%`
}

export function formatNumDen(num: number, den: number): string {
  return `${num}/${den}`
}

/** 분모가 너무 작아 해석이 어려운 행인지 (0 초과 ~ 하한 미만). */
export function isInterpretationCaution(den: number | null | undefined): boolean {
  return den != null && den > 0 && den < MIN_DENOMINATOR
}

export const HEAT_GRADIENT_CSS = `linear-gradient(90deg, ${STOPS.map(
  ([t, c]) => `${toHex(c)} ${t * 100}%`,
).join(', ')})`
