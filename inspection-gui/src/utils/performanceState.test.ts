import {it,expect} from 'vitest'
import {performanceStateLabel} from './performanceState'
it('distinguishes completed processing awaiting a report from work still in progress',()=>{
 expect(performanceStateLabel('report_pending')).toBe('보고서 생성 대기')
 expect(performanceStateLabel('computing')).toBe('점수 반영·검증 중')
 expect(performanceStateLabel('waiting')).toBe('대기 중')
 expect(performanceStateLabel('complete')).toBe('완료')
 expect(performanceStateLabel(undefined)).toBe('대기 중')
})
