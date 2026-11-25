# 다음 착수 작업 2-A — 고해상도 부위·3D 표면 공간 시각화

사용자의 최신 추가 지시를 인계용으로 정리했다. **현재 추가2-A는 착수 조사까지이며 공간 계산/GUI 고도화 구현 완료가 아니다.** 구현은 칫솔·지퍼에서 검증한 후 다른 품목으로 확장한다. 원문 대화의 세부 요구를 축소하는 근거로 이 요약을 사용하지 말 것.

## 고정 경계

모델 가중치, inference.py/inference_hvq.py/report_fusion_performance.py, 확정 퓨전 계약(v2로 지칭), 가중치·TH·margin, 기존 제품별 판정, 구max16자료, 공식평가 분할 변경 금지. 현재 실제 파일과 해시를 먼저 확인하고 계약 명칭을 이유로 내용을 다시 변경하지 않는다. 공간 점수는 시각화 전용이며 제품 판정/공식 성능에 반영하지 않는다. 추가 모델 추론은 별도 승인 없이 실행하지 않는다. 백필/DB동기화/배치 간섭 금지. 운영 재시작은 기존 승인 범위에서만 수행하고, 스키마 변경은 별도 승인 경계다.

## 조사 선행

/parts/heatmap 실제 명세, operational_findings source의 실제 테이블, ROI설정/derive, parts.ts와 메시/UV, region_id, RT박스좌표, HVQ NPY저장 여부, 원본 복원/정렬/가림/관측 영역, 색 적용을 읽는다. 현재 첫 조사 HEATMAP_DETAIL_ANALYSIS.md를 참고하되 실제 호스트 API/DB에서 재확인한다. 이전 검증 이후 공유 저장소 코드가 변경됐으므로 동시 변경을 보존한다.

## 계층·30품목 등록

- config에서 제품→주요부위→세부부위→부위내공간의4수준을 지원.
- 기존 region_id 유지. 칫솔은 현재 bristle/neck이며 handle은 사용자가 제거했다. head 예시 때문에 bristle을 개명하거나 handle을 복원하지 않는다.
- 각 노드: region_id,parent_region_id,display_name,category,supported_views,roi_polygon,mapping_version,mesh_part_id,mapping_status,검증 상태. 임의 신뢰도 수치 금지.
- 부모·자식 통계를 합산해 제품을 중복 계산하지 않는다.
- 30품목 각각 C1–C5의 실제 영상으로 주요/세부부위·관측·가림·미촬영·좌표·메시 연결·검증 상태를 기록. 동일 ROI 수 또는 균등 격자를 의미 있는 부위라고 강제하지 않는다.
- 칫솔/지퍼 ROI 오버레이를 먼저 생성하고 육안 검토. 이후 다른 품목을 확장. 현재69템플릿이 모든150시점을 검증했다는 뜻은 아니다.

## RT 공간 집계 비교

박스 중심 누적/면적 누적/confidence 가중/Gaussian 시각화/제품별 중복 제거 점유율을 비교. 박스 내부 전체를 불량 마스크로 해석하지 않는다. Gaussian은 위치 분포를 부드럽게 그리는 표현임을 표시. 검출 건수·제품수·점유율·평균confidence를 분리하고 제품×시점 중복으로 제품 분모를 늘리지 않는다.

## HVQ 공간 집계

실제 NPY 로드→모델 좌표 확인→원본 복원→ROI 점수→정렬/정규화→유효 관측 수→mean/max/percentile/신호빈도/유효관측대비비율 집계. 기존 heatmap_mean 제품 점수/판정 변경 금지. 실제 맵이 없으면 unsupported와 필요한 데이터 계약을 기록한다. 스칼라를 공간 패턴으로 바꾸거나 승인 없는 추가 추론 금지.

## 해상도와 시점

16/32/64/128²를 비교.64²는 검토 후보이며 기본 정답이 아님. 보존 정보·희소표본·작은 검출·계산시간·API크기·브라우저렌더·메모리를 실제 측정. 보간 결과와 원래 측정 해상도를 구분한다. C1–C5를 동일 grid에 단순 합산하지 않는다. 방향/자세/표면/ROI대응/가림/규모 정규화 근거가 없으면 시점별 공간 grid만 제공하고 제품 단위 부위 통계만 결합한다.

## 표면 표현과 GUI

- A: 검증된 세부메시 색, B: DataTexture/CanvasTexture UV, C: vertex color를 비용/표현/신뢰성/렌더 비용으로 비교.
- UV 존재는 보정 증거가 아니다. ROI 대응이 없는 메시에는 공간 투영하지 않고 기존 부위색 fallback 유지. 근사 시각화를 실제 물리좌표 투영이라고 주장하지 않는다.
- 모드: 주요/세부부위, 공간밀도, RT분포, HVQ분포, 두모델시각적중첩, 검수확정/FP/FN위치(근거있을때만), 관측/미매핑.
- 품목/제품/집계↔개별/부모↔자식/시점/모델/투명도/숨김/범례/회전/확대/Hover/클릭/핫스팟/순위/관련제품/점수분포/매핑·표본 상태 연결.
- 중첩은 공식 퓨전 판정이 아니다. 검수 근거 없는 FP/FN/확정불량 지도 금지.

## 공간 API·캐시

기존 /parts/heatmap 호환 유지, 공간 전용 읽기 API 추가 가능. 실제 저장 형식에 맞춰 item,product_id,region_id,parent_region_id,view_id,model_version,mapping_version,metric,grid_width/grid_height,values,valid_observation_counts,coverage_mask,numerator/denominator,aggregation_method,source,status/reason,updated_at를 확정한다.

요청마다 전체DB를 다시 읽어 계산하지 않는다. 읽기전용 export/별도 파생 캐시·사전집계를 사용한다. 운영 테이블에 새로운 컬럼을 무승인 추가하지 않는다. 캐시를 모델/매핑/원본 데이터 버전과 묶어 오래된 결과를 구분한다.

## 표본·챗봇

MIN_DENOMINATOR 유지. 유효측정/낮은신호/검출0/미관측/표본부족/준비중/실패/미지원 구분. 미관측을 정상색으로 칠하지 않고 결측/희소 영역을 주변 값으로 채우지 않는다. 보간은 유효범위 내부에서만, 상대/절대 색상 기준 구분.

조회 도구가 위치집중/좌우비교/HVQ만높음/RT집중/중첩/표본부족/관련제품을 실제 근거로 반환하도록 확장. LLM이 grid/좌표/SQL/JS를 생성해 실행하지 않는다. 등록된 구조화 GUI 명령만 사용하고 부위 통계와 공간 통계를 설명한다.

## 검증 및 진행 순서

조사→공간자료존재→칫솔·지퍼ROI→실제오버레이→모델별집계→해상도비교→표면검증→GUI→챗봇→대표E2E→다른품목→전체회귀→승인된배포.

테스트: 계층ID/기존ID호환, 좌표·박스·맵복원, grid분모/제품중복, 시점오결합금지, 미관측/희소/미등록, 운영근거조회, 신규API/기존API, 메시매핑, 모드/투명도, 챗봇GUI, 리소스해제. 백엔드·프런트 전체회귀/lint/TS/build.

실브라우저로 기존부위/세부/RT/HVQ/중첩/시점/확대/희소/미관측/준비중 화면을 캡처·육안 확인. 미지원/환경미검증을 통과로 보고하지 않는다. 성능은 측정값만 기록한다.

## 최종 산출물

- HEATMAP_DETAIL_ANALYSIS.md (현재 초기 조사 작성됨, 구현 후 갱신)
- HIERARCHICAL_ROI_CATALOG.md
- SPATIAL_HEATMAP_CONTRACT.md
- MODEL_HEATMAP_COMPARISON.md
- SURFACE_MAPPING_VALIDATION.md
- HEATMAP_GUI_VALIDATION.md
- 30품목 ROI/공간현황표(현재 설정 인벤토리는 reports/part_heatmap/roi_spatial_status.csv)
- 실제ROI오버레이, 전후 실GUI 스크린샷, 테스트/성능 측정 결과
- NEXT_AGENT_HANDOFF.md 갱신. IMPLEMENTED/VERIFIED/UNSUPPORTED/UNVERIFIED를 분리한다.
