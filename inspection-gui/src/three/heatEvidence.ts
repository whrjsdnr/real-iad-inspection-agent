import type {StatsResponse,StatsRow} from '../types'
type RegionStats=Pick<StatsResponse,'rows'|'mapping_verified'|'mapping_version'> & {reason?:string|null;source_scope?:string;coverage?:Record<string,string>}
/** A rate alone is insufficient evidence for projecting a statistic onto a mesh. */
export function mappedHeatRow(stats:RegionStats|null|undefined,regionId:string,fixture=false):StatsRow|undefined {
 if(!regionId||regionId==='unknown'||regionId==='unmapped')return undefined
 if(!stats||(!fixture&&(!stats.mapping_verified||!stats.mapping_version)))return undefined
 const row=stats.rows.find(r=>r.group.part_id===regionId)
 if(!row||!Number.isFinite(row.den)||row.den<=0||row.rate===null||!Number.isFinite(row.rate)||row.rate<0||row.rate>1)return undefined
 return row
}

export function regionEvidence(stats:RegionStats|null|undefined,regionId:string,options:{loading?:boolean;error?:string|null;fixture?:boolean}={}){
 const row=stats?.rows.find(entry=>entry.group.part_id===regionId)
 const mappedRow=mappedHeatRow(stats,regionId,options.fixture)
 const result=(status:string,message:string,detail:string)=>({status,message,detail,row,mappedRow:status==='mapped'?mappedRow:undefined})
 if(options.error)return result('api_error','검사 통계 조회 실패','서버 연결을 확인하세요. 검사 결과는 미확인입니다.')
 if(options.loading)return result('loading','부위 통계 조회 중','현재 필터 조건으로 조회하고 있습니다.')
 if(!stats)return result('not_loaded','부위 통계 미조회','조회가 완료되면 표본 상태를 확인할 수 있습니다.')
 if(!row&&stats.coverage?.[regionId]==='not_annotated')return result('not_annotated','이 부위의 ROI 미등록','관측이 확인된 원본 영역을 등록하면 검출 신호를 연결할 수 있습니다.')
 if(!row&&stats.source_scope==='stored_gui_evidence_exact_image_samples')return result('no_registered_evidence','현재 조건의 등록 부위 근거 없음','이 품목·카메라·모델·기간과 일치하는 원본 ROI가 필요합니다.')
 if(stats.reason==='fusion_thresholds_unconfigured')return result('unconfigured','선택 모델의 퓨전 판정 기준 미설정','현재 모델 기준선에서는 FP/FN을 계산할 수 없습니다.')
 if(!row&&stats.rows.some(entry=>!entry.group.part_id||entry.group.part_id==='unknown'||entry.group.part_id==='unmapped'))return result('unmapped','미분류 부위 기록만 있음','unknown 그룹은 이 부위의 통계가 아닙니다. 원본 이미지와 부위 좌표 등록이 필요합니다.')
 if(!row)return result('no_samples','선택 조건의 부위 검수 표본 없음','전체 제품 추론 완료와 부위별 검수 표본은 별도입니다.')
 if(!Number.isFinite(row.den)||row.den<=0||row.rate===null||!Number.isFinite(row.rate)||row.rate<0||row.rate>1)return result('no_denominator','유효한 지표 표본 없음','확정 검수와 현재 지표의 분모 조건을 확인하세요.')
 if(!mappedRow)return result('unverified','저장된 부위 통계 · 3D 연결 미확인','검수 집계는 있으나 이미지 좌표와 3D 부위의 연결은 검증되지 않았습니다.')
 return result('mapped','부위 통계 확인',stats.source_scope==='stored_gui_evidence_exact_image_samples'?'등록된 원본 표본의 모델 검출 빈도입니다. 확정 불량률이 아닙니다.':'검증된 부위 연결 기준으로 표시합니다.')
}
