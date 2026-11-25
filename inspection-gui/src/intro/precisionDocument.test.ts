import {describe,it,expect} from 'vitest'
import original from '../../../inspect_ai_v6_precision.html?raw'
import {buildPrecisionDocument,isPrecisionNavigation,PRECISION_NAVIGATION} from './precisionDocument'

describe('team Precision intro integration',()=>{
 it('preserves the source design and geometry while isolating the demo',()=>{
  const html=buildPrecisionDocument()
  expect(original).toContain('const flangeData=')
  expect(html).toContain('const flangeData=')
  expect(html).toContain('HVQ-Trans');expect(html).toContain('RT-DETRv2')
  expect(html).toContain("connect-src 'none'")
  expect(html).toContain('#dashboard{display:none!important}')
  expect(html).not.toContain("q('dashboard').style.display='grid'")
  expect(html).not.toContain('fetch(')
  expect(html).toContain('precisionColor(')
  expect(html).toContain('var(--precision-color-')
  expect(html).toContain('가상의 결함')
 })
 it('routes only via the parent protocol and never auto-replaces the real dashboard',()=>{
  const html=buildPrecisionDocument()
  expect(html).toContain(`type:'${PRECISION_NAVIGATION}'`)
  expect(html).toContain("destination:'dashboard'")
  expect(html).toContain('실제 대시보드로 이동')
 })
 it('supports reduced motion, paused/hidden rendering, capped frames and cleanup',()=>{
  const html=buildPrecisionDocument()
  for(const text of ['prefers-reduced-motion: reduce','document.hidden','1000/24','precisionDispose','WEBGL_lose_context','cancelAnimationFrame','pagehide'])expect(html).toContain(text)
  expect(html).not.toContain('render(0);requestAnimationFrame(tick);')
  expect(html).toContain('CPU 모드 · 단계 선택')
 })
 it('accepts only the current iframe and exact destination message',()=>{
  const frame={} as Window,other={} as Window
  const data={type:PRECISION_NAVIGATION,destination:'dashboard'}
  expect(isPrecisionNavigation({source:frame,data},frame)).toBe(true)
  expect(isPrecisionNavigation({source:other,data},frame)).toBe(false)
  expect(isPrecisionNavigation({source:frame,data},null)).toBe(false)
  expect(isPrecisionNavigation({source:frame,data:{...data,destination:'javascript:alert(1)'}},frame)).toBe(false)
  expect(isPrecisionNavigation({source:frame,data:{...data,code:'evil'}},frame)).toBe(false)
  expect(isPrecisionNavigation({source:frame,data:null},frame)).toBe(false)
 })
})
