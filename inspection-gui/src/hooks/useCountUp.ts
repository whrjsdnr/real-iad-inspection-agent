import { useEffect, useRef, useState } from 'react'

const reducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** 숫자 변경 시 count-up (모션 감소 시 즉시 반영). 지표 숫자 표시용. */
export function useCountUp(target: number | null, durationMs = 600): number | null {
  const [display, setDisplay] = useState<number | null>(target)
  const fromRef = useRef<number | null>(target)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    if (target == null) {
      setDisplay(null)
      fromRef.current = null
      return
    }
    const from = fromRef.current ?? target
    fromRef.current = target
    if (from === target || reducedMotion()) {
      setDisplay(target)
      return
    }
    const t0 = performance.now()
    const tick = (now: number) => {
      const k = Math.min(1, (now - t0) / durationMs)
      const eased = 1 - Math.pow(1 - k, 3)
      setDisplay(from + (target - from) * eased)
      if (k < 1) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, durationMs])

  return display
}

/** 상단바 라이브 시계 (콘텐츠 갱신 — 모션과 무관). */
export function useLiveClock(intervalMs = 1000): string {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), intervalMs)
    return () => clearInterval(t)
  }, [intervalMs])
  return now.toLocaleTimeString('ko-KR', { hour12: false })
}
