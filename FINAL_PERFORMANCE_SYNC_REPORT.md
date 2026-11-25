# 최종 성능·조회 동기화 점검 — 2026-11-24

> **정정(2026-11-25)**: 아래 기록 중 '학습 중복 UNKNOWN'은 당시 원격 학습 ID manifest 미확보로 인한 미확인 표기였다. 훈련 담당자 확인으로 통합 추론 120,000장(24,000제품)은 RT-DETRv2·HVQ-Trans 학습에 사용되지 않았으며, 유일한 주의점은 퓨전 규칙 보정(Val 3,610)이 전체 집계에 포함된다는 것이다. 성능 수치는 불변.

상태: **PARTIAL**. 파일 기반 완료 증거와 로컬 코드 수정은 확인했다. 운영 API/DB 연결, 배포 반영 및 실제 브라우저 표시는 검증하지 못했다.

## 확인된 상태

- `max16_scores/state.json`: 16:33:59 완료, 24,000/24,000제품, 120,000시점, 실패0.
- `background_pipeline/pipeline_state.json`: 16:34:51 COMPLETE, 별도 `fusion_analysis` 반영 완료, 기존 결과 미수정.
- `supervisor_state.json`: 16:35:03 COMPLETED_AND_AGENT_VERIFIED.
- `FINAL_VALIDATION.json`: 제품24,000/시점120,000, 에이전트 도구 수치와 독립 SQL 일치. 운영 반영 자격은 false.
- `final_performance/latest.json` 및 해당 디렉터리는 점검 시 없음. 따라서 최종 보고서는 아직 GUI에 공급되지 않는다.

파일 증거 사본: `reports/gui_validation/sync-final/artifact-status.json`. 실행 중 프로세스에는 관여하지 않았다.

## 현재 검증 산출물의 성능 (최종 보고서와 구분)

`background_pipeline/metrics.json` 및 `agent_numeric_validation.json`의 Test3,593제품(불량1,838/정상1,755), 제품 C1–C5 단위:

| 지표 | 분자 / 분모 | 값 |
|---|---|---|
| Recall, 보류 분리 전 이진판정 | 1,747 / 1,838 | 95.049% |
| F1, 이진판정 | 3,494 / 3,706 | 0.942795 |
| FPR | 121 / 1,755 | 6.8946% |
| 미탐률 | 91 / 1,838 | 4.9510% |
| 보류율 | 31 / 3,593 | 0.8628% |

이진판정 FP121/FN91. 보류를 제외한 확정판정 FP112/FN90, 커버리지3,562/3,593. 보류를 정답으로 간주하지 않는다. 학습 표본 중복은 UNKNOWN이며 기존 98.84% 평가의 재현 결과로 주장하지 않는다. 이 점검에서 모델 추론·성능 재산출은 실행하지 않았다.

## 발견·수정

1. 완료된 model run도 보고서 파일이 없으면 무조건 computing으로 표시했다. `report_pending`을 추가하고 ‘보고서 생성 대기’로 구분했다. 점수만 끝나고 퓨전 검증이 남으면 computing을 유지한다.
2. `/performance/final`은 기다림, `/status/overview`와 도구는 계산 중으로 서로 다르게 응답할 수 있었다. 동일한 상태 판정 함수를 사용하고 overview에서 보고서/백필/파이프라인을 중복 조회하지 않도록 수정했다. 여러 HTTP 요청 사이의 DB 트랜잭션 일관성까지 보장하는 변경은 아니다.
3. `get_final_performance`는 도구/LLM 목록에 있었으나 HTTP 입력 모델에 빠져404가 발생하는 경로가 있었다. 입력 모델 등록 및 중앙/읽기전용 ASGI 요청 테스트 추가.
4. 제품 적재 수치는 distinct product가 아닌 `inspection_attempts` 전체 행 수였다. ‘DB 검사 기록’으로 명확히 표시하고 집계 범위 메타데이터를 추가했다. 24,002/120,010과 목표 코호트24,000/120,000은 직접 동일시하지 않는다. 초과2시도/10시점의 ID·출처는 실제DB 접근 불가로 미확인이다. 값을 잘라 맞추거나 데이터를 지우지 않았다.
5. 성능 카드에 Test 제품 수와 보고서 시각을 표시하고 ‘전체 실데이터 성능’이라는 부정확한 표기를 Test 기준으로 수정했다.

수정 파일: `app/status.py`, `app/api.py`, `app/tools.py`, `inspection-gui/src/types.ts`, 두 pages(IntroPage/DashboardPage), `utils/performanceState.ts`와 테스트, `tests/test_gui_status.py`, `scripts/check_final_sync.py`, `tests/test_final_sync_check.py`.

## 동기화 검증 범위

이 샌드박스의 localhost:8080 HTTP 및 PostgreSQL read-only 접속은 실패했다. 실제 운영 서버 다운이라고 단정하지 않는다. HTTP 점검 결과는 `reports/gui_validation/sync-final/live-api-check.json`에 BLOCKED로 기록했다. 운영 서버 재시작/설정변경/DB 쓰기는 수행하지 않았다.

주의: 백그라운드 검증 코드 스냅샷에는 `compute_fusion_metrics`와 `get_fusion_case_evidence`가 있지만 현재 GUI 작업 저장소에는 등록되어 있지 않다. 두 코드가 자동으로 같아지는 구조가 아니며, 스냅샷의 검증 성공이 현재 서버·챗봇의 동일 도구 지원을 보장하지 않는다. 실제 `/tools` 목록 확인이 필요하다. 기존 부위 검수 통계와 별도 `fusion_analysis`의 퓨전 성능은 서로 다른 지표이며 기존 판정을 덮어쓰지 않았다.

## 사용자가 실행할 명령

기존 지침에 따라 최종 보고서 생성은 사용자가 수행한다. 아래 스크립트는 기존 점수와 DB를 읽고 보고서 파일을 생성하며 모델 추론을 다시 실행하지 않는다.

```bash
cd /home/geonug/MV
/home/geonug/agent/.venv/bin/python scripts/report_fusion_performance.py --env-file /home/geonug/agent/.env --wait
```

보고서 생성 후 기존 파일 조회 코드는 다음 polling(60초) 때 읽는다. 실행 서버가 다른 경로/환경을 사용하면 자동 반영을 보장할 수 없다. 새 코드의 `report_pending` 표시와 HTTP 입력 모델 수정은 승인된 배포가 필요하며 운영 재시작은 수행하지 않았다.

호스트에서 실제 API의 overview/성능/도구 응답 및 활성 model run 일치를 검사:

```bash
cd /home/geonug/agent
.venv/bin/python scripts/check_final_sync.py --base-url http://127.0.0.1:8080
```

읽기전용 개발 게이트웨이는 `--base-url http://127.0.0.1:18080`. 해당 서버가 기존 `scripts/start_gui_readonly.sh`로 기동돼 있을 때만 사용한다. 이 검사 스크립트는 이미 등록된 성능 조회 도구만 호출하며 추론/검수/보고서 생성/서버 재시작 요청을 보내지 않는다. 결과 VERIFIED는 API 간 일치 확인이며 DB 전체 및 시각적 E2E 검증을 의미하지 않는다.

확인할 화면: 인트로 상태 위젯, 대시보드 최종 성능 카드, 챗봇의 최종 성능 조회. 모델 ID·Test 표본 수·FP/FN·F1·보고서 시각이 같은지 비교한다. 검사기록 초과분과 ROI 부위 통계는 별도 검증이 남는다.


최종 현재코드 검증 확정: Python 전체88통과/4skip(76.59초), 프런트110통과/17파일, ESLint/TypeScript/Production Build통과(14.02초), 보호된모델·추론/config해시동일/토큰외HEX0. 로그 reports/gui_validation/sync-final/{pytest-all,vitest,eslint,build,integrity}.log. 신규 점검스크립트 테스트의 urllib mock 메서드 접근 오류를 수정했고, 중간실패는pytest-all-first.log로구분보존했다. 실API/PG/브라우저검증은여전히BLOCKED, 운영미배포/재시작없음.


### 보고서 실행 요청 — 2026-11-24

사용자가 최종보고서 직접실행을 새로 승인했다. 기존명령을 실행했으나 즉시exit1, 로그는 {"status":"REPORT_FAILED","type":"OperationalError"}. reports/gui_validation/sync-final/report-generation.log. latest.json미생성. 이샌드박스의ps에는샌드박스자체프로세스만보이므로 호스트의기존프로세스가없다고확정하지않는다. DB접속실패의구체원인은스크립트가예외상세를숨겨미확인(이전접속검사도차단됨). 실행중인보고서생존확인/성공주장없음. 운영프로세스/DB수정없음. 호스트용 scripts/start_final_performance_report.sh 제공: pgrep중복확인+flock+nohup,전용로그/PID기록. bash구문검사통과, 호스트실행은미완료.


### 호스트 최종보고서 생성 확인 — 2026-11-24 16:53

VERIFIED(파일/로컬로더): 사용자가 호스트명령실행후 report-host.log와 final_performance/latest.json 생성확인. 보고서20261124_165313_094234/performance.json. app.status 실제로더 state=complete/available=true/is_fixture=false,Test3593제품,FP121/FN91,Recall0.9504896627,F1micro0.9427954668,AUROC0.9730806432,보류31,coverage0.9913721124,SQL/agent검증true. 생성실행은성공완료이며 계속살아있어야하는서버가아님. 실서비스HTTP/브라우저자동갱신은미검증.


### 전체24,000제품 포함 및 unknown/손잡이 후속 — 2026-11-24

VERIFIED: 사용자요청에따라 train/validation/test 표기전체를저장CSV에서집계. manifest24,000제품×C1–C5,GT/분할/ID일치와원본Test성능재현확인. reports/cohort_performance/latest.json생성. 전체FP666/FN363,Recall12045/12408=97.0745%,F1=24090/25119=0.959035,AUROC0.984276,보류205/24000. Test3593성능별도보존. Validation포함참고집계이며학습중복UNKNOWN,운영판정정책/원본보고서/DB/추론변경없음. app.status실제파일로더에서전체evaluation_products24000확인. 운영HTTP/브라우저는미검증/서버재시작없음.

IMPLEMENTED: unknown0/1을정상0%색상카드가아닌중립미분류근거카드로분리. 손잡이툴팁은API실패/조회중/표본없음/미분류기록/좌표미검증을구분. statsError연결과캐시우회‘검수통계새로조회’추가. API는검수테이블출처와mapping_verified=false명시. 전체제품성능과부위검수통계를혼동하지않음.

PARTIAL/BLOCKED: 물리적손잡이ROI매핑자체는해결되지않음. 640×480LUT↔원본1024²등록자료부재,실DBunknown1건정체미확인. 실제좌표자료경로를사용자에게질문함. 임의로정상/불량색강제할당없음.

최종검증: Python94통과/4skip(66.01초),Vitest114통과/17파일,ESLint/TypeScript/Build통과(8.60초),보호추론/config해시동일/토큰외HEX0. 로그reports/gui_validation/cohort-mapping. 신규패키지없음. COHORT_AND_PART_MAPPING_REPORT.md상세참조.


### 최신 마무리·인계 — 2026-11-24

사용자가 마지막으로 확정한 계약은 RT0.7/HVQ0.3 + RT0.4 + HVQ heatmap_mean + Val 품목별min-max다. 별도저장점수재평가를실행해 reports/final_performance_minmax/performance.json 생성. 전체24000:F1 0.968780/Recall97.5338%/FP474/FN306,Test3593:F1 0.953210/Recall95.3210%/FP86/FN86. Val3610만보정. 가중합24000전수오차0/THmargin30품목재확인/별도SQLite SQL혼동행렬일치. 운영DB새판정활성화없음. 최신보고서설명 FINAL_FUSION_CONTRACT_REPORT.md. 구max16보고서와혼동금지.

히트맵실구현: 손잡이는사용자요청으로3D와목록에서삭제. 새app/part_heatmap.py·part_api.py·모델신호/검수지표구분UI와C1–C5원본ROI·검출뷰어. 실제칫솔1제품5장nativeROI를원본해시로등록/오버레이직접검토,RT0.4검출6박스→제품1/관측1(중복업로드제외). 나머지부위·품목은ROI등록및운영findings읽기전용연결추가필요. 이것을전체24000제품부위평가완료로주장하지않음.

최종검증 Python103통과/4skip,Vitest116통과/18파일,ESLint경고0/TypeScript/Build통과6.77초. 보호추론/config해시동일/토큰외HEX0. 로그 reports/gui_validation/part-heatmap/. 모델추론재실행/운영서버재시작/DB수정/패키지설치없음. 실제호스트API/브라우저는환경제약으로미검증.

**다음에이전트는 NEXT_AGENT_HANDOFF.md부터읽을것.** 계약재질문/이미완료한추론재실행금지. 현재요청마무리후남은최우선은승인된운영반영또는별도개발서버실브라우저확인,다른ROI등록/운영findings의좌표출처확인및파생히트맵집계확대다.
