import type {StatusOverview} from '../types'
export function performanceStateLabel(state:StatusOverview['final_performance']['state']|undefined):string{
 if(state==='complete')return '완료'
 if(state==='report_pending')return '보고서 생성 대기'
 if(state==='computing')return '점수 반영·검증 중'
 return '대기 중'
}
