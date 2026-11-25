# 전체 제품 집계 및 부위 표시 점검 — 2026-11-24

> **정정(2026-11-25)**: 아래 기록 중 '학습 중복 UNKNOWN'은 당시 원격 학습 ID manifest 미확보로 인한 미확인 표기였다. 훈련 담당자 확인으로 통합 추론 120,000장(24,000제품)은 RT-DETRv2·HVQ-Trans 학습에 사용되지 않았으며, 유일한 주의점은 퓨전 규칙 보정(Val 3,610)이 전체 집계에 포함된다는 것이다. 성능 수치는 불변.

## 전체 24,000제품 포함 요청

VERIFIED: 사용자가 학습 시 임의 추출했다는 설명과 함께 기존 분할 전체 포함을 요청했다. 저장된 `all_predictions.csv`와 원본 manifest를 읽어 제품 ID·카테고리·GT·split·C1–C5 무결성을 확인하고 별도 집계를 생성했다. 원본 Test 성능을 먼저 재현해 집계 구현의 수치 일치를 검사했다. 모델·점수·판정·임계값·운영DB·원본 Test 보고서는 수정하지 않았다.

생성 파일: `reports/cohort_performance/latest.json`. source 보고서/CSV/manifest SHA256 및 model version을 기록했다. 기존 보고서 경로·SHA256·model version·표본 수가 일치할 때만 API 로더가 별도 집계를 결합한다. 원본 보고서가 변경되면 과거 전체 집계는 사용하지 않고 Test 범위로 돌아간다. 재생성: `.venv/bin/python scripts/derive_cohort_performance.py`.

| 전체 24,000제품 이진판정 | 분자 / 분모 | 값 |
|---|---|---|
| Recall | 12,045 / 12,408 | 97.0745% |
| F1 micro | 24,090 / 25,119 | 0.959035 |
| FPR | 666 / 11,592 | 5.7453% |
| 미탐률 | 363 / 12,408 | 2.9255% |
| 보류율 | 205 / 24,000 | 0.8542% |

TP12,045/TN10,926/FP666/FN363. AUROC0.984276. 보류 제외:23,795제품, FP620/FN346. 보류를 정상 또는 정답으로 계산하지 않았다.

Test3,593제품 F1 0.942795/Recall0.950490/FP121/FN91은 `test_reference`에 보존. 전체 집계에는 Validation3,610제품이 포함되어 독립 Test 평가와 다르다. 원본 `train` 분할명만으로 실제 모델 학습 여부를 단정하지 않는다. 실제 학습목록은 없어 중복 UNKNOWN 유지. 98.84% 기존 실험의 재현 주장이나 새 운영 판정 정책 승인이 아니다. 전체 집계의 manifest/CSV 일치와 기존 Test 재현은 확인했지만 전체 집계에 대한 새 독립 SQL 검증은 수행하지 않았으므로 `verified=false`, `csv_consistency_verified=true`로 구분했다.

IMPLEMENTED: API 요약이 전체 참고 지표를 우선 제공하고 evaluation_products=24000, evaluation_scope=all_inferred_products_reference를 포함한다. test_products는 의미를 바꾸지 않고3593 유지. 화면에 전체 참고 집계와 별도 Test 집계를 함께 표시. 로컬 파일 로더로 실제 전체24,000집계 응답을 확인했다. 실제 운영 HTTP/브라우저 반영은 미검증이며 운영 재시작은 하지 않았다.

## unknown 0/1과 손잡이 메시지

VERIFIED(코드): query_error_stats는 confirmed reviews와 기존 findings를 집계한다. max16 신규 점수·제품 판정은 별도 fusion_analysis에 기록된다. 추론24,000제품이 완료되어도 부위 검수 표본이나 물리 ROI 등록이 자동으로 생기지 않는다. `unknown 0/1`의1은 선택 지표의 미분류 그룹 분모이며 전체 추론 제품 수가 아니다. 이 화면만으로 동기화 실패 또는 정상 손잡이로 판정할 수 없다. 현재 호스트 API/DB에는 접근할 수 없어 해당1건의 ID·출처는 미확인이다.

발견한 표시/조회 문제와 수정:

- unknown/모델에 없는 부위를 정상 부위처럼0.0% 컬러 카드로 표시하던 경로를 중립 ‘미분류 부위’ 근거 카드로 분리했다. 분자/분모는 유지하되 이를 손잡이 정상률로 해석하지 않는다.
- 3D 툴팁의 ‘부위 매핑 미확인 / 데이터 없음’ 혼합 문구를 API 실패/조회 중/미조회/미분류 기록만 있음/부위 검수 표본 없음/분모 없음/저장 통계 있으나 위치 미검증으로 나눴다. 저장된 유효 부위 통계는 위치 미확인과 구분하여 표시한다.
- statsError가 실제 API 응답 오류에서 설정되지 않던 누락 수정. 오류/로딩 중에는 이전 검증된 색상도 노출하지 않는다.
- statsCache가 동일 필터에서 서버 조회를 생략할 수 있음을 확인. ‘검수 통계 새로조회’ 버튼은 캐시를 우회해 해당 통계를 다시 읽는다. 제품 상세/다른 카드 전체를 자동 동기화하는 변경은 아니다.
- API에 source_scope(confirmed_reviews 또는 inspection_attempts)/mapping_verified=false를 명시. unknown과 비유한 분모는 검증 플래그가 있어도 3D에 투영하지 않는다.

PARTIAL/BLOCKED: 실제 손잡이·목·헤드와 원본 카메라별 ROI의 연결은 아직 해결되지 않았다. config의640×480 legacy LUT와1024×1024 실제 이미지 사이 등록 근거가 없고 현재 API도 검증된 부위 버전을 공급하지 않는다. 자세한 증거는 ROI_COORDINATE_MAPPING_REPORT.md. 이를 전체 제품의 GT/퓨전 점수로 대체하거나 모델 전처리 크기 비율만으로 손잡이에 강제 할당하지 않았다. 카테고리·카메라별 실제 원본 이미지에서 부위 ROI를 등록·검증하고 버전 및 증거를 제공해야 실제3D 히트맵을 완성할 수 있다.

## 검증 및 운영 경계

신규 테스트는20제품 전체 분할 집계의 기대 혼동행렬/F1/Recall/보류 분리, 동점 AUROC/AP, 중복 제품/카메라 거부, Test 재현 실패 거부, 원본 변경 후 오래된 전체 보고서 거부를 검증한다. 프런트는 unknown0/1의 손잡이 오할당 방지, 조회 상태 분리, 잘못된 분모, 캐시 우회 및 오류 상태를 검사한다.

현재 로그: `reports/gui_validation/cohort-mapping/`. 최신 프런트114테스트 통과, ESLint/TypeScript/Build통과(8.60초). 중간 IntroScene의 신규 props 누락으로 발생한 TypeScript 실패는 수정 후 재실행했다. Python 전체 회귀 결과는 실행 완료 후 진행 문서에 확정한다. 실제 브라우저 검증은 기존 환경 제약으로 미실행. 운영 프로세스 중단/서버 재시작/스키마 변경/실제 결과 덮어쓰기/새 패키지 설치 없음.


### 최신 마무리·인계 — 2026-11-24

사용자가 마지막으로 확정한 계약은 RT0.7/HVQ0.3 + RT0.4 + HVQ heatmap_mean + Val 품목별min-max다. 별도저장점수재평가를실행해 reports/final_performance_minmax/performance.json 생성. 전체24000:F1 0.968780/Recall97.5338%/FP474/FN306,Test3593:F1 0.953210/Recall95.3210%/FP86/FN86. Val3610만보정. 가중합24000전수오차0/THmargin30품목재확인/별도SQLite SQL혼동행렬일치. 운영DB새판정활성화없음. 최신보고서설명 FINAL_FUSION_CONTRACT_REPORT.md. 구max16보고서와혼동금지.

히트맵실구현: 손잡이는사용자요청으로3D와목록에서삭제. 새app/part_heatmap.py·part_api.py·모델신호/검수지표구분UI와C1–C5원본ROI·검출뷰어. 실제칫솔1제품5장nativeROI를원본해시로등록/오버레이직접검토,RT0.4검출6박스→제품1/관측1(중복업로드제외). 나머지부위·품목은ROI등록및운영findings읽기전용연결추가필요. 이것을전체24000제품부위평가완료로주장하지않음.

최종검증 Python103통과/4skip,Vitest116통과/18파일,ESLint경고0/TypeScript/Build통과6.77초. 보호추론/config해시동일/토큰외HEX0. 로그 reports/gui_validation/part-heatmap/. 모델추론재실행/운영서버재시작/DB수정/패키지설치없음. 실제호스트API/브라우저는환경제약으로미검증.

**다음에이전트는 NEXT_AGENT_HANDOFF.md부터읽을것.** 계약재질문/이미완료한추론재실행금지. 현재요청마무리후남은최우선은승인된운영반영또는별도개발서버실브라우저확인,다른ROI등록/운영findings의좌표출처확인및파생히트맵집계확대다.
