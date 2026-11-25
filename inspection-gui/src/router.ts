/**
 * 최소 해시 라우터 — 신규 의존성 없이 인트로 → 3개 메뉴 전환과
 * 근거 링크(대시보드 사례 포커스) 딥링크를 지원한다.
 *
 * 경로: #/ (인트로) · #/chat · #/inference · #/dashboard?item=..&focus=..
 */
import { useEffect, useState } from 'react'

export type RoutePath = 'intro' | 'chat' | 'inference' | 'dashboard' | 'spatial'

export interface Route {
  path: RoutePath
  params: URLSearchParams
}

const VALID: RoutePath[] = ['intro', 'chat', 'inference', 'dashboard', 'spatial']

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#/, '') || '/'
  const [pathPart, query = ''] = raw.split('?')
  const name = (pathPart.replace(/^\//, '').split('/')[0] || '') as RoutePath
  const path = (VALID as string[]).includes(name) ? name : 'intro'
  return { path, params: new URLSearchParams(query) }
}

export function navigate(to: string) {
  const target = to.startsWith('#') ? to : `#${to}`
  if (window.location.hash === target) return
  window.location.hash = target
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash))
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

/** 대시보드 사례 포커스 딥링크 생성. */
export function dashboardFocusLink(productId: string, cameraId?: string): string {
  const q = new URLSearchParams({ focus: productId })
  if (cameraId) q.set('camera', cameraId)
  return `#/dashboard?${q.toString()}`
}
