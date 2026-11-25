# 퓨전 실험 복구 및 신규 실데이터 추론

> **정정(2026-11-25)**: 아래 기록 중 '학습 중복 UNKNOWN'은 당시 원격 학습 ID manifest 미확보로 인한 미확인 표기였다. 훈련 담당자 확인으로 통합 추론 120,000장(24,000제품)은 RT-DETRv2·HVQ-Trans 학습에 사용되지 않았으며, 유일한 주의점은 퓨전 규칙 보정(Val 3,610)이 전체 집계에 포함된다는 것이다. 성능 수치는 불변.
> 최신 상태: HVQ30:RT70 + 기준TH 정책 유지. Batch5 원시점수 전량 추론 진행 중이며 자동 판정은 미보정 상태입니다. 최신 테스트47통과/4skip, GUI14통과. 실행·DB 적재·공유 명령은 INFERENCE_DB_SHARING_GUIDE.md를 참고하세요.


작성: 2026-11-23T19:27:47.425833+09:00

## 판정

원 실험 **NOT_REPRODUCED**. CSV 부재로 전체 개발을 중단하지 않는다. 사용자 승인에 따라 신규 추론 코호트120,000장/24,000제품을 선정했다. **학습 원본30,000장과 비중복인 ‘나머지12만장’임을 입증한 목록은 아니다.** 동일 제품 C1–C5를 모델 입력 batch5로 고정한다. batch1 진단 결과는 별도 보존하며 최종 실행 조건에 섞지 않는다.

## 1. 팀원 전달 정보

HVQ79ep/RT15ep EMA, HVQ0.3:RT0.7, 모델별 제품5시점max 후 품목별Val백분위, 품목별Val F1 최고TH, 보류 margin이라는 설계는 사용자 확정이다. TestNG600/OK600, FN37/FP46, Recall93.8%/F1 .9314는 **팀원 전달 참고 성능**이며 현재 측정값이 아니다. 참고 기준선은 reference_baseline/UNVERIFIED로만 저장한다.

## 2. 원본 CSV 검색

~/agent와~/MV의 숨김·Git무시 파일을 포함해 지정4개 CSV를 찾지 못했다. 압축 내부·원격 전체를 전수 검색했다고 주장하지 않는다.

## 3. 발견한 과거 임의 추출 기록

- `real-iad-backup/offload/config.json`: 입력 코호트30,000장·6,000제품, Train21,045/Val4,400/Test4,555장. 원본`/workspace/real-iad/outputs/cohort_candidate_30000_20261117/cohort.csv`, SHA256`69bd3f26e8ee2613a341248843fef1a365416e623c1bb48f99bead5ba242ea79`.
- 동 설정의 파생`cohort.csv` SHA256`34a9bee06383d695edc2ba73813ca8f9223e8c3b46406782f484c1684838ad48`. 같은 원본/파생 파일이라고 해시를 혼용하지 않는다.
- Run seed42는 확인됐으나 표본 추출 seed라는 증거는 아니다. 원본 cohort 목록과 추출 코드 자체는 이번 검색에서 복구하지 못했다. 기록된 원격SSH 접속은 Connection refused로 실패했다.
- HVQ 체크포인트의 각 품목 Validation은 이미지40장(OK20/NG20)이며 ID/시점 목록이 없다. 이를 제품40개나 팀원 Test600+600과 동일하다고 해석하지 않는다.
- RT 체크포인트는 epoch15/EMA를 포함하나 학습/Val/Test 파일명 목록이 없다. HVQ는epoch79/30분기/품목별지표를 확인했다. 두 모델의 사용 이미지 동일성도 미확인이다.

## 4. 기존 분할과 신규 추론 목록

기존`outputs/filename_class_resolution_v1/image_metadata_with_split.csv`는151,050장/30,210선언제품이며 폴더를 포함한제품ID를 사용한다. 기존 파서의 품목+상태+serial 키로 서로 다른 결함 제품을 합치지 않는다. 새 코호트는각품목800제품,총24,000제품이며 기존Split 컬럼을 그대로 보존했다. 그룹마다5시점·품목·GT·Split 일치, 파일존재를 검사했다. 누락/중복/메타데이터불일치0개다. 새Val/Test는 생성하지 않았다.

선정 seed20261123, 품목 round-robin+seeded shuffle. 라벨·결함 위치는 추출 우선순위로 쓰지 않았다. 이미지GT 기준NG62,040장/OK57,960장이다. 데이터 중복·학습 누출은 **UNKNOWN**이며 독립성 보장 통계가 아니다.

Manifest SHA256: `c9b4788d9139b3a08c9a3bc3e2c3d7e5163bca536d2b2b68aeffcb6042557796`.

## 5. 점수 생성

`score_batch.py`가 원본 이미지를 읽고 기존CPU ONNX RT-FP32/HVQ-FP16IO를 사용한다. 원본추론자산은 수정하지 않았다. RT는기존postprocess(conf floor0.05, IoU0.5) 이후최대박스confidence이며 검출0개일때만 점수0이유효하다. 디코딩/추론실패는FAILED+NULL로저장한다. HVQ는`hvq_common.scores_from_pred`의이상맵평균이며 높을수록이상이다. 두 모델에같은제품C1–C5 5장을한배치로전달하고제품별max를별도저장한다.

산출물은SQLite점수캐시, 입력·모델·설정해시, 제품처리상태,뷰별GT/시점/원본XYXY박스/원시맵경로다. 초기100제품만 raw map을보존하고전량map전체누적은하지않는다. 현재확인완료100제품이며최신진행은 `../MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1/state.json`을참고한다. 이 문서값은동적으로갱신되지않는다.

## 6. 정규화/TH/margin 구현

`fusion_calibration.py`에 검증된Val전용경험적백분위 `(평균순위−0.5)/n`(1-based순위), 동점평균순위, 선형보간, 관측범위밖0/1을구현했다. 모델별max를먼저취한다. TH는ValF1최고구간중높은구간의중점으로tie를고정했다. TH를포함한 F1최고−0.005이상의연속구간에서대칭margin을도출하며 비대칭절삭폭을기록한다.

이는신규재구성규칙이지원실험동일순위공식복구가아니다. Val지지표본하한은config에명시된잠정guard(20제품,클래스별5)다. 실제품목별TH/lookup/margin은아직없고`UNCONFIGURED`다. `reconstruct_fusion.py`는점수해시·분할검증·학습비중복audit가없으면보정을거부한다. Test로TH를맞추지않는다. 기존min-max보정CLI는오용을막기위해명시적으로거부한다.

## 7. 실제 결과/비교

현재실측은원시점수추론만이다. 품목별TH·margin·운영정상/불량/보류·F1·Recall은 **NOT_MEASURED**. 원참고성능과동일조건재현을주장하지않는다. 보류를임의정상/불량으로치환하지않는다.

## 8. 독립 개발 결과

- 신규백분위/TH/margin/지표/manifest검사포함Python42 passed/4 skipped.4skip은실제원퓨전재현검사다.
- 합성제품20개TP/TN/FP/FN,중복제품,목데이터제외,GT없는경우제외,precision/coverage/분모0검사. AUPRO는명시적raw map/GT쌍만허용하고과거잘못된PNG·타시점추정평가는N/A처리.
- PostgreSQL신규진단DB에서이관행수일치:40시도/198뷰/50근거/121검수. 읽기역할쓰기거부·검수역할UPDATE·동시수정충돌확인. 기존DB는덮어쓰지않았다.
- pg_dump/새DB복원행수모두일치: `True`. 기존SQLite·기존Postgres운영DB는이번진단으로변경하지않았다.
- GUI TypeScript/production build통과(큰번들경고),Vitest14통과. 원본좌표변환·검수자필수·버전전달·409처리·시점변경좌표초기화를구현했다. 실제브라우저E2E는미검증이다.
- LLM도구4종으로제한했고GUI승인API는별도유지했다. 기존모델다운로드/학습/유료API/Commit/Push없음.

## 9. 남은 과제

100제품파일럿검증후12만장점수추론만자동재개한다. 정책TH가없는상태에서12만장자동판정은시작하지않는다. 학습cohort목록/추출코드를확보하거나 별도보정실험의검증가능분할을준비해학습겹침을해소해야한다. 실제ROI를제공받기전에는unknown매핑을부위GT로취급하지않는다. 역할별로그인계정발급·운영DB전환·기존API재기동·실제브라우저E2E는별도확인이필요하다.


## 팀원 원문 보고서 추가 확인 및 사용자 정책 선택

2026-11-23 원문 표를 제공받았다. F1·AUROC는30품목 단순평균이다. 기존F1목표0.9314를전체혼동행렬F1과동일시하지않는다. Val선택기준형10:90(제품Recall92.3%,FN46/600,FP23/600,macroF1 .9401), 리콜우선형30:70(Recall97.5%,FN15/600,FP136/600,macroF1 .8953)과사용자고정정책을구분한다. **사용자는기존고정HVQ30:RT70+품목별기준TH유지를재확정했다.** 따라서원시점수배치·가중치·모델입력은바꾸지않았다.

Val이미지1200/제품1200,Test이미지2400/제품1200은서로다른평가단위의표본이다. 전체5시점이미지를모두포함한동일목록으로간주하면장수가맞지않으므로, 원본ID목록미제공상태에서는동일모집단이라고주장하지않는다. 원보고서도RT학습/Test중복미확인이라고명시했다.


## 최신 실행·적재·공유 확인

사용자는 기존HVQ30:RT70+기준TH를 유지하기로 확정했다. `config/teammate_fusion_reference.json`은 원문 표의 주요 참고값과 macro 평균 정의를 보존하며 현재 측정값이 아니다.

Batch5 전량 원시 점수 추론 실행 중: worker PID2459734, supervisor PID2459730. 마지막 state 관측 완료375제품/1875장, 실패0제품. 진행률은 계속 변하며 전체완료가 아니다. 운영 자동판정은 비활성이다.

별도 진단PG에서 실제100제품 첫 적재100/재적재0+skip100, C1–C5 실제JPEG HTTP200, raw map5개 표시PNG HTTP200, stale 검수409를 확인했다. 테스트 DB의 진단 검수는 사람이 승인한 운영 GT가 아니다. 기존운영DB와8080서버는변경/재기동하지않았다. 로컬Qwen 실제호출루프는45초 APITimeoutError로 실패했고도구호출0회였다. 직접도구조회는통과했으나실제LLM루프는미검증으로남긴다.

명령어와DB공유절차: [INFERENCE_DB_SHARING_GUIDE.md](INFERENCE_DB_SHARING_GUIDE.md). 추천은중앙PostgreSQL을백엔드API로공유하는방식이다. .env/관리자비밀번호는공유하지않는다.

잔여: 품목별Val lookup/TH/margin, 학습중복검증, 실제브라우저E2E, 운영계정발급/DB전환, 부위지표의5시점제품중복제거와부위GT정의세부검증. 따라서시스템전체Phase완료를주장하지않는다.
