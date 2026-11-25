# 최신 상태 — 2026-11-25: 30품목 표면 표시 및 HVQ 저장 맵 복구

실행한 최종 회귀: Python133 passed/4 skipped(186.77초), 프런트135 passed/23파일(5.90초), ESLint 통과, TypeScript+Production Build 통과(1분58초), 보호 자산 해시 동일/하드코딩 색상 위반0. 번들500KB 경고는 남아 있다. source ASGI/Three 객체 검증이며 운영TCP·실브라우저 렌더링 완료 판정은 아니다.


이 절이 아래 이전 세션 상태보다 우선한다. 사용자가 **표시용 근사 표면 투영을 명시 승인**했다. 이전 ‘UV 검증 전 3D 적용 금지/2D만 구현’ 상태는 최신 표시 모드에는 해당하지 않는다.

- IMPLEMENTED: 실제 DataTexture+ShaderMaterial을 제품 하위 메시 표면에 적용. 전체 부위 공통 좌표, 칫솔모 측면 색상, 유효 관측만 보간, hotspot raycast, 원래 PBR 유지, 회전 상속, 리소스 해제. 재질/기존 부위 집계/3D 공간 모드 유지. 실패했던 메인2D 패널은 제거하고 실제 근거 뷰어는 유지.
- VERIFIED_ASGI: 30품목×5시점 GT150개 + 같은 대표 제품 RT/HVQ300개 배열 응답. 실제 맵500개/100제품/30품목 확인. 상대경로 로더 오류 수정으로 지퍼 등 누락된 맵 복구. 모든24,000제품에 맵이 있는 것은 아니다. 제품 ID/split 표시. HVQ_MAP_AVAILABILITY_REPORT.md 참조.
- VERIFIED_THREE_OBJECTS: 공유된 실제 ESM 런타임으로30품목/134overlay/118hotspot, 원래 재질 보존·회전·해제 확인. GPU 브라우저 검증과는 별개다.
- 공유: team_integration_kit.zip, THREE_SURFACE_GUIDE.md,450 surface_frames,150 원본GT field, 공통 렌더러·색상·투영설정·예제. /api/sharing/kit 다운로드 추가. 비밀정보 검사 통과.
- 제약: 브라우저/TCP/LAN 외부접속은 sandbox EPERM으로 미검증. 사용자의 현재 GUI 시각 피드백은 받았으나 에이전트 신규 스크린샷 촬영 완료로 주장하지 않는다. 캡처 스크립트는 최신3D UI에 맞춰 수정했다.
- 보호: 추론·백필·동기화·운영서버 재시작·추론 실행 없음. 기존 모델/퓨전/판정/운영DB 스키마 변경 없음. 기존보다 높은 현재 퓨전 결과 유지.


---
이하 이전 상태 기록

# 최우선 인계 — 2026-11-25 최종 상태

## 사용자 최신 결정

현재 지표가 이전보다 높으면 유지. 동일(product_id,category,split,truth)24,000개와Test3,593개를 저장CSV로정확대조했다. 현재전체F1 .968780 > 이전 .959035, Test F1 .953210 > .942795, Test Recall .953210 > .950490. **현재 minmax/heatmap_mean/RT0.4/RT70:HVQ30 유지 확정. 설정·임계값·판정·선택보고서를 변경하지 않았다.** FUSION_POLICY_COMPARISON.md 참조. 과거98.84%의모델평가원본은미확인이고 발견된98.8456 crop픽셀보존율과혼용하지않는다.

## 지금 실제 구현/검증

- 기존MV presence-v2 원본560×64²를재사용. Train NG54,805/제공마스크36,173/unknown18,632/30품목150시점. 원본분할·정상제외유지. source11파일해시보존.
- 칫솔CH/C1 132마스크+지퍼BX/C1 98마스크를원래coarse함수로재검증해원본count완전일치. 메타데이터선언제품+시점중복0. 전체마스크재디코딩은아님.
- adapter150집계+10대표제품시점,maskAPI/ROI필터,GUI A마스크/B RT/C HVQ/D부위/E동일제품비교. 개별지퍼C2마스크없음은unknown. source MV코드/데이터는변경없음.
- 기존RT공간32²도실재: 칫솔C1선택박스2/양의셀174/값19종/중심(17,7),(26,26). 스칼라복제가아님.
- 인증ASGI실제조회21건,공유SDK/ZIP/150수치JSON/예제준비. Python128 passed4skipped,frontend131 passed22파일,ESLint/TS/Build6.30초,보호해시동일/토큰위반0.

## 15173에서 관측된404와 수정

사용자URL http://127.0.0.1:15173/#/dashboard 에서 최초 /api/heatmaps/catalog가404. catalog데이터미존재는503이라라이터미도달계층오류다. 스크립트의기본프록시는18080,실제호스트PID/Network본문은미확인. 코드OpenAPI에는이미등록돼있었다.

vite.config.ts에mvApiBridge.mjs를연결했다. 개발용MV GET와비교용findings만 scripts/mv_api_bridge.py로기존ASGI API에전달. 다른프록시유지,모델/DB startup없음,로컬reader최대2개·큐16. 중앙/18080/백필/동기화서버재시작없음. middleware+실제reader+JPEGstream검사에서양품목200/64²/칫솔known335unknown37/지퍼known367unknown0. /tmp cwd검사도통과.

브라우저새로고침 후 X-MV-Transport:vite-local-existing-asgi-routes를확인할것. 사용자가현재2D이미지가보인다고보고했다. 본에이전트의실브라우저/TCP검증은EPERM으로미완료. 오류시이제실제URL/method/body와route404/data404가분리표시된다.

## 남은핵심 — 3D는 완료 아님

사용자가 ‘3D적용아니고이미지만뜨는가’질문했고 **현재2D fallback,3D표면히트맵미완료**라고답했다. 현재UV는서로다른칫솔모최대392위치에반복되며물리ROI↔UV atlas/카메라보정부재. 임의로전체/다수모에같은맵을복제하지말것. 검증된대응을확보하기전까지표면투영은하지않는다. 칫솔모196필라멘트/28식모구멍/헤드외곽·뒷면/목을개선했고손잡이는미촬영참고형상체크박스로만추가. 기존neck/bristle ID유지.

## 산출물/다음검증

MV_MASK_API_404_FIX_REPORT.md, MV_HEATMAP_REUSE_REPORT.md, TEAM_DATA_SHARING_REPORT.md, FUSION_POLICY_COMPARISON.md, team_integration_kit.zip. 실제데이터비교jpg는reports/gui_validation/spatial-urgent/mv-mask-native-grid-model-comparison.jpg이며브라우저스크린샷아님.

호스트별도미리보기: bash scripts/start_spatial_preview.sh 후 http://127.0.0.1:18082/#/spatial. 브라우저캡처는node scripts/capture_toothbrush_spatial.mjs. 중앙team공유는TEAM_SHARING_GUIDE.md의18081인증서비스/기존중앙최신소스배포후검증. 실제외부IP/8000·8080 listen/운영uvicorn명령은미확인. 운영재시작승인범위가불명확하므로임의재시작하지말것.

모델·inference스크립트·퓨전·DB스키마·기존판정·백그라운드프로세스는유지. 새패키지설치없음. 조회요청마다전체마스크를재분석하지않는다. 이미완성된mask import/공간집계/SDK를다시설계하지말것.

---

# 최신 진행 — 2026-11-25 MV 마스크 재사용 / 공간 GUI / 팀 공유

원본 MV presence-v2 수치를 실제로 찾고 연결했다. 이전 NOT_STARTED 조사보다 이 절이 우선한다.

- VERIFIED: windows_preserved_20261111_v1의560×64×64 배열과 metadata,30품목150시점. Train NG54,805/제공마스크36,173/unknown18,632. 정상/Test를 분모로 혼용하지 않는다.
- VERIFIED: 원래 coarse_occupancy 함수로 칫솔 CH/C1 마스크132장+지퍼 BX/C1 98장을 재검증해 기존 수치와 정확일치. 선언제품ID/시점 중복0. 전체마스크 재디코딩은 아님.
- IMPLEMENTED: 기존배열 adapter,150집계+10대표제품시점 캐시, /heatmaps/catalog·ground-truth·metadata·evidence, ROI마스킹, GUI 마스크/모델 비교 분리. 3D UV는 미검증이며2D를 제공한다.
- VERIFIED: 접속키 인증 ASGI 조회21건,30품목24,000제품120,000시점 캐시와 원시박스/실제맵/ROI/공간/평가 조회. 실제 TCP/운영PG/팀원PC 접속 검증과는 다르다.
- BLOCKED: socket PermissionError EPERM. 실제8080/8000 listen,외부IP/브라우저스크린샷 미검증. 운영서버·백필·DB스키마·모델·퓨전·판정 변경없음.
- 최종회귀/ZIP 재빌드 진행 중. 최신로그 reports/gui_validation/spatial-urgent/. 이전 통과로그를 최신통과로 대신하지 않는다.

NEXT: 최종검사결과 확인,team_integration_kit.zip 배포검토, 호스트에서 별도18082 미리보기/18081 인증공유 접속 검증. 운영재시작은 하지 말 것.

---

# 최신 상태 — 추가2-A 실제구현 및 팀공유 (2026-11-24)

이 절이 아래 과거기록보다 우선한다. 공간기능 NOT_STARTED라는 이전조사는 현재상태가 아니다.

- IMPLEMENTED: 실제저장박스 기반공간밀도, 계층ROI, 4해상도, 모델/시점/투명도/hover/클릭근거/실제챗봇조회링크, 인증된팀읽기전용서비스.
- VERIFIED: 실제30품목60제품/72등록시점/1,088격자생성, 원본오버레이6장+대표비교직접검토, Python120통과4skip, Vitest121통과, lint/TS/build, 보호자산해시/토큰검사.
- PARTIAL: 나머지28품목은주요ROI공간계산가능; 의미적세부ROI/제품간자세정합미완료. 기존69+지퍼3시점등록, 미등록78조합.
- 미지원: 지퍼저장이상맵, 검증된3D물리UV투영. 현재시점별개별제품2D fallback이며전수제품공간집계가아니다.
- BLOCKED: socket EPERM으로실제공유서비스/브라우저검증. 운영서버/백필/DB동기화/스키마/모델/퓨전/판정은변경하지않았다.

실행·공유: TEAM_SHARING_GUIDE.md. 상세결과 HEATMAP_GUI_VALIDATION.md, HEATMAP_DETAIL_ANALYSIS.md, HIERARCHICAL_ROI_CATALOG.md, SPATIAL_HEATMAP_CONTRACT.md, MODEL_HEATMAP_COMPARISON.md, SURFACE_MAPPING_VALIDATION.md.

## 이어서 할 일

1. 호스트에서 TEAM_SHARING_GUIDE.md의 새읽기전용18081서비스를실행하고 접속키만팀원에게전달. env전체공유금지. 기존운영서비스재시작금지.
2. 호스트capture_spatial_validation.mjs 실행후 실제GUI스크린샷직접검토/수정. 브라우저스크린샷은현재없으며 software overlay와구분.
3. 물리UV/카메라정합근거를확보한경우에만3D국소표면투영활성화. 지금가짜투영금지.
4. 미등록78품목시점/하위ROI를원본근거로확장. 전수개별제품자료를추가하려면공간캐시대상선택을확장하되제품간공간합산금지.
5. 기존부위집계의24,001분모/카메라·모델·기간필터일관성을별도검증. 공식퓨전설정은고정.

캐시재생성(추론없음): `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/derive_spatial_heatmaps.py --all-registered`. config/spatial_* 또는공간계산코드가바뀌면캐시SHA검사409가발생하므로재생성한다. 최신로그 reports/gui_validation/spatial/.

---

> 최신 추가2-A: TASK_2A_SPATIAL_HEATMAP.md / HEATMAP_DETAIL_ANALYSIS.md / NEXT_AGENT_HANDOFF.md 우선 확인.

> 최신 인계: NEXT_AGENT_HANDOFF.md / FINAL_FUSION_CONTRACT_REPORT.md를 먼저 확인하세요. 아래에는 이전 계약의 역사 기록도 포함됩니다.

# 작업 상태 — 2026-11-23
> 최신 상태: HVQ30:RT70 + 기준TH 정책 유지. Batch5 원시점수 전량 추론 진행 중이며 자동 판정은 미보정 상태입니다. 최신 테스트47통과/4skip, GUI14통과. 실행·DB 적재·공유 명령은 INFERENCE_DB_SHARING_GUIDE.md를 참고하세요.


## 현재 결론

**Phase R 일부 복구·검증 완료, 중대한 제품 ID 설계 변경과 원본 Val 확인 대기. Phase R 전체/Phase 1–4 완료가 아니다.** 사용자 지시 “중대한 스키마/설계 변경이 필요하면 멈추고 먼저 질문”에 따라 배치·보정 실행을 중단했다. 요청한 파일럿·전량 배치는 시작하지 않았고 백그라운드 잡도 없다.

## 변경 전 확인한 실패

- pytest: 18 passed, 4 skipped, 5 errors. DB 전환 중 migrate() 인자와 호출부 불일치.
- API/에이전트는 app/inspection.db, 배치/지표는 루트 inspection.db를 사용. 도구 조회 `no such table: reviews`.
- 기존 DB에는 users와 reviews.reviewer_id/updated_at/version이 없었음.
- batch_fusion.py에 제거된 db_connect(), 잘못된 load_done()/migrate() 호출 잔존.
- config/fusion.json은 구형 두 모델 양성/음성 일치 규칙. TH/margin/정규화 통계/산출 근거 없음.
- derive_fusion.py는 확정값과 반대인 RT 0.3/HVQ 0.7을 사용하며 원본 Val 근거 없이 정렬 순 1,200제품을 선정함.

## 복구 내용

- app.db와 dbconn의 엔진·기본 파일 경로 통일. 실제 API 백엔드 로그에 루트 DB 출력 확인. 파일 SQLite에서 하나의 StaticPool 연결을 다중 스레드가 공유하지 않도록 조정.
- 기존 DB를 reports/inspection_before_recovery.db에 SQLite backup API로 백업한 후 가산 마이그레이션. users 생성, reviews 컬럼/버전 보충. 기존 행 삭제 없음.
- API 시작 시 SQLite 마이그레이션 수행. ORM에 기존 width/height 컬럼 반영.
- 중단된 배치의 초기 DB 헬퍼 호출을 복구. 보정값 없을 때 구형 규칙으로 실행하지 않고 실패하도록 차단. 배치 전과정 복구 검증은 아직 아님.
- config/fusion.json에 확정 가중치 **RT-DETR 0.7/HVQ 0.3**, 목표·허용오차·필요 Val 크기를 저장. TH/margin/정규화 통계는 null, 상태는 pending_original_validation_manifest. 임의 값을 생성하지 않음.
- derive_fusion.py가 명시적 원본 Val CSV(product_id,item,truth,camera,image_path)를 요구하도록 변경. 제품/시점/GT/장수와 캐시 출처 검사 추가. 설정 출력은 config/fusion.json, 기준선 쓰기는 공통 DB 사용. 이 경로는 실데이터 실행 전이며 사용자 확인 후 추가 검증 필요.
- HVQ 점수는 최적화 보고서의 이미지 점수 정의인 heatmap mean을 따르도록 조정. 과거 max_avgpool16 실험과의 차이는 재현 시 확인 필요.
- 보류의 양 경계 포함(`|score−TH| ≤ margin`)과 부동소수점 경계 처리 복구.
- ROI 하드코딩을 config/parts_roi.json으로 이전. roi-lut-v1 목 좌표와 parts-roi-v1 실데이터 unknown 매핑을 구분해 원래 mapping_version 유지.
- 검수 expected_version API 입력, version 조건 원자적 UPDATE, 충돌 HTTP 409, 수동 박스 수정 시 PK 충돌 복구. GUI 연동과 신규 동시 생성 경합 검증은 잔여.

## 검증 결과와 범위

- `.venv/bin/pytest -q`: **30 passed, 4 skipped**. 로그 reports/pytest_recovery.txt. 4개는 원본 Val 보정 산출물 부재로 건너뛴 실제 재현 검사이며 성공으로 계산하지 않음.
- 추가 회귀 검사: 기본 DB 경로, 기존 행 보존/멱등 마이그레이션, 올바른 가중치, 보류 경계, Val 자동 표본 금지, 버전별 ROI, 두 검수자 동시 수정 충돌.
- `.venv/bin/python scripts/smoke_recovery.py`: API 핸들러 입력 검증/도구 조회 및 agent.run_tool 실제 DB 조회 통과. reports/recovery_smoke.json. **실제 LLM 호출이나 HTTP 전송 검증이 아님.**
- uvicorn은 앱 startup까지 통과했으나 포트 bind 실패. 별도 socket 생성에서 PermissionError `[Errno 1] Operation not permitted` 확인. Ollama 연결도 같은 소켓 제한. 해당 환경 밖에서 live 검증 필요.
- GUI `npm run build` 통과, vitest 12/12 통과. 번들 크기 경고만 있음. 실제 브라우저/실데이터 클릭 검증은 미수행.
- Docker Compose 2.40.3 설치 확인. Docker daemon socket 접근 permission denied로 PostgreSQL 서버 기동/마이그레이션 검증 불가. Phase 3 런타임 전환 스킵, SQLite 유지.
- 신규 Python 패키지 설치 없음. 루트 추론 자산 수정 없음.
- .git 디렉터리가 유효한 저장소 메타데이터를 제공하지 않아 git diff/status 사용 불가.

## 중대한 발견 / 질문

1. **제품 ID 충돌**: reports/data_identity_audit.json. annotation manifest 30,210제품이 현재 파서로 19,378제품이 됨. 충돌 ID 4,197개. 예: audiojack_defect_0001이 NG/BX, NG/HS, NG/QS, NG/ZW의 S0001을 합치고 setdefault()가 시점을 버림. manifest의 폴더 포함 ID로 전환할지 질문함. 승인 전 ID 변경·실데이터 기록 보류.
2. **Val/목표 분모 불일치**: 요청은 120제품×5=600장이나 FN37/600·FP46/600은 각 양성/음성 600제품을 암시함. 실제 목표의 원본 검증 목록과 분모 정의 요청함. TP563/FN37/FP46이면 Recall=563/600, F1=1126/1209로 요청 목표와 근접하지만 이것으로 검증 세트를 추정하지 않음.
3. 발견한 `/home/geonug/MV/outputs/filename_class_resolution_v1/image_metadata_with_split.csv`는 train 105,735장/21,147제품, validation 22,655장/4,531제품, test 22,660장/4,532제품. 요청의 학습 3만장/잔여12만장 분할과 다르므로 배치 제외할 실제 학습 목록도 확인 필요.

## 잔여 작업 / 재개 순서

1. 제품 ID 규칙 승인, 목표 Val/학습 제외 목록 확인. 충돌·시점 중복을 오류로 처리하는 스캔과 manifest 기반 제외 구현.
2. 실제 Val 점수 생성(출처 일치 캐시 우선), mean/max 집계·TH/margin 재도출, ±2%p 재현 비교. 실제 값으로 snapshots 기준선 v1 4개 등록. 그 전에는 수치 미등록.
3. batch_fusion의 제품 트랜잭션, 실패 중복·잔여 버퍼, 재시작/모델·보정 fingerprint, 전체 처리 시간 측정 검증 후 파일럿100. 분포·보류>20% 경고·기준선 비교 보고. 통과 후 전량 nohup 실행 및 PID/로그 제공.
4. Phase 2: GT/검수 반영 및 제품 중복 방지, 의심 건수 분리, 부위 지표/필터/스냅샷 API·CLI 연결, 올바른 GT 시점 매칭과 AUPRO 계산. 기존 합성20제품 검사는 통과하지만 이 Phase 전체 충족을 의미하지 않음.
5. Phase 3: Docker 접근 가능 환경에서 기존 compose/Alembic 검증 후 sqlite_to_pg/roles/backup/restore/export 구현·검증.
6. Phase 4: 실제 이미지 안전 제공 경로, 실데이터 미검수 사례 조회, 기준선 선택·부위 모델 조인, 박스 렌더링·원본 좌표·C1–C5 검수 대상 수정, optimistic 충돌 UI, 캐시 무효화, 챗봇 근거 링크 이동. 현재 GUI 빌드/fixture 테스트만 검증됨.

## GUI 실제 검증 절차 (아직 미수행)

소켓 접근 가능한 환경에서 uvicorn과 Vite를 띄우고 실제 모델 기준선·품목·기간을 선택한다. 실제 제품 카드에서 원본 2D와 모델 박스/맵, C1–C5가 같은 제품인지 확인한다. 기간/지표/기준선 변경 시 요청 본문과 히트맵이 갱신되는지 확인한다. 서로 다른 두 검수 창에서 같은 version을 읽고 첫 저장 후 두 번째 저장이 409로 거절되는지 확인한다. 박스 수정 후 지표 재계산과 캐시 갱신, 채팅 근거 링크의 동일 제품/시점 이동까지 확인한다. 아직 이 절차의 성공을 주장하지 않는다.


---

## 인수 재점검 — 2026-11-23 (최신 통합 지시서 기준)

**Phase R 상태: BLOCKED — 원본 퓨전 CSV 4종 미발견. Phase R 완료가 아니며 Phase 1–4로 진행하지 않았다.** 앞선 기록의 mean/max 선택·Val 120제품·목표 분모 미확정 설명은 최신 명세로 대체된다. 최신 확정값은 모델별 C1–C5 max → 모델별·품목별 Val 백분위 → HVQ0.3+RT0.7 → 품목별 TH이며, 목표는 Test1,200제품(NG600/OK600)이다.

### 이번에 직접 확인한 실행 증거

- 실제 경로: 앱 `/home/geonug/agent`, 모델 저장소 `/home/geonug/MV`. agent의 `git status`는 유효한 Git 저장소가 아니라고 반환했고 MV의 기존 미커밋 변경은 보존했다.
- 기존 테스트를 다시 실행: **30 passed / 0 failed / 4 skipped,66.35초**. 실행 명령: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/tmp/agent_recovery_20261123_tests`. 4개 skip은 실제 보정 산출물 부재에 따른 퓨전 재현 검사이며 통과가 아니다.
- 원본 SQLite를 읽기 전용으로 열고 임시 복사본을 사용하여 FastAPI를 `127.0.0.1` 임시 포트에 실제 기동했다. `/health` **HTTP200** 확인 후 해당 테스트 서버만 종료했다. 샌드박스 소켓 제한은 승인된 재실행으로 구분했다.
- `agent.run_tool('get_training_status',{})`의 DB 조회 성공. `AGENT_MOCK=1`인 직접 도구 검사다. Ollama `/api/tags`에서 `qwen25-cpu:latest` 확인. **실제 Qwen 대화·도구 선택 루프는 미검증**이다.
- 운영 DB 읽기 전용 집계: `inspection_attempts40`, `inspection_views198`, `findings50`, `reviews121`, `metrics_snapshots0`, `users0`. 기존 보고의49/120과 차이가 있으므로 현재 관측값을 우선한다. 원인이나 실데이터 반영으로 추측하지 않았다.
- `hvq_best.pt`, `epoch_0015.pt`, RT640 ONNX 및 HVQ FP16IO ONNX 파일 존재 확인. 추론 자산4개 파일의 조사 전후 SHA256 동일. **이번 점검에서 실제 모델 추론·파일럿·전량 배치는 실행하지 않았다.**
- GUI package.json과 설치된 tsc/vite 실행 파일 확인. **이번 재점검에서 GUI 빌드·브라우저 E2E는 실행하지 않았다.** 이전 문서의 GUI 성공 기록과 구분한다.

### 원본 산출물 검색과 설정 차이

`~/agent`, `~/MV` 전체 파일명 검색에 숨김·Git ignore 파일을 포함했으며 .venv/node_modules/.git은 제외했다. 아래4종을 찾지 못했다. 압축파일 내부·다른 디스크·원격 서버까지 검색한 것은 아니다.

- `weighted_fusion_metrics.csv`
- `weighted_fusion_thresholds.csv`
- `validation_scores.csv`
- `test_predictions.csv`

현재 `config/fusion.json`은 가중치만 일치한다. `score_definition.normalize=validation_view_minmax`, `product_agg=null`, `calibration.expected_products=120`, `expected_views=600`, TH/lookup/margin 미도출 상태이며 확정 알고리즘과 호환되지 않는다. 기존 `test_derived_fusion.py`도 min-max 기반 검사가 포함돼 있어 테스트 통과만으로 최신 퓨전 명세 충족을 주장할 수 없다. **CSV 없이 임의 정규화·TH·margin을 만들거나 Test로 보정하지 않았다.**

`fusion.py` 파일명 파서는 결함 종류를 product_id에 포함하지 않아 서로 다른 결함 폴더의 같은 일련번호가 합쳐질 위험이 코드에서 확인된다. 기존 `reports/data_identity_audit.json`의4,197충돌 기록은 이전 분석 자료이며 이번 재점검에서 전수 재산출하지 않았다. 원본 CSV의 제품 키·학습 제외 목록과 대조하기 전 전량 배치를 실행하면 안 된다.

### 다음 재개 조건

원본4개 CSV의 실제 경로 또는 원본 압축파일을 받아 동일 Val/Test를 사용해 재현한다. Recall=563/600, FPR=46/600, Precision=563/609, F1=1126/1209는 **제공된 목표의 산술 확인**이며 이번 측정값이 아니다. 원본 CSV 확보 후 정규화 lookup·품목 TH·margin 도출과 재현 테스트를 먼저 완료한다.

실행 증거: `/home/geonug/MV/outputs/agent_recovery_20261123/{smoke.json,initial_inventory.json,phase_r_validation.json}`. 이번 변경은 이 상태 추기와 차단 사유 문서뿐이며 설정·운영 DB·모델·승인 기록·기존 코드는 변경하지 않았다. 신규 패키지 설치 없음.


---
## 최신 추가 지시 반영 — 퓨전 재구성·Batch5 신규 추론

CSV 부재로 전체 개발을 중단하는 이전 조건은 해제됐다. 원 실험은NOT_REPRODUCED, 품목TH는UNCONFIGURED다. 학습표본코호트경로·해시기록을찾았으나원본목록은미복구다. 사용자승인에따라신규24,000제품/120,000장추론목록을만들었으며학습중복UNKNOWN을명시했다. 모델입력도제품C1–C5 batch5로고정한다.

백분위/max/TH/margin재구성엔진·출처분리지표·Postgres가산마이그레이션/이관/권한/백업복원·검수UI버전/좌표처리를구현·검증했다. 현재100제품점수파일럿중이며전량점수추론과자동정상불량판정은구분한다. 세부현황과미검증은 FUSION_RECOVERY_REPORT.md 및실행state.json을본다. 실제모델학습이나원본추론자산수정은없다.


## 최신 실행·적재·공유 확인

사용자는 기존HVQ30:RT70+기준TH를 유지하기로 확정했다. `config/teammate_fusion_reference.json`은 원문 표의 주요 참고값과 macro 평균 정의를 보존하며 현재 측정값이 아니다.

Batch5 전량 원시 점수 추론 실행 중: worker PID2459734, supervisor PID2459730. 마지막 state 관측 완료375제품/1875장, 실패0제품. 진행률은 계속 변하며 전체완료가 아니다. 운영 자동판정은 비활성이다.

별도 진단PG에서 실제100제품 첫 적재100/재적재0+skip100, C1–C5 실제JPEG HTTP200, raw map5개 표시PNG HTTP200, stale 검수409를 확인했다. 테스트 DB의 진단 검수는 사람이 승인한 운영 GT가 아니다. 기존운영DB와8080서버는변경/재기동하지않았다. 로컬Qwen 실제호출루프는45초 APITimeoutError로 실패했고도구호출0회였다. 직접도구조회는통과했으나실제LLM루프는미검증으로남긴다.

명령어와DB공유절차: [INFERENCE_DB_SHARING_GUIDE.md](INFERENCE_DB_SHARING_GUIDE.md). 추천은중앙PostgreSQL을백엔드API로공유하는방식이다. .env/관리자비밀번호는공유하지않는다.

잔여: 품목별Val lookup/TH/margin, 학습중복검증, 실제브라우저E2E, 운영계정발급/DB전환, 부위지표의5시점제품중복제거와부위GT정의세부검증. 따라서시스템전체Phase완료를주장하지않는다.

## GUI 안정화 재개 — 2026-11-24

기존 GUI 리디자인/30품목 메시/8단계 인트로 및 좌표 변환 코드 존재 확인. 이전 최종 로그는 Python69통과+4skip, Vitest46통과, lint/build통과. 이 값은 이번 재개 후 최종 검증값과 구분한다. 운영 모델·config·DB·프로세스 변경 금지 유지.

ROI 실제 저장5시점/96박스 감사: 기존 규칙 unknown87/96, 근거 없는 LUT 등록을 거부한 파생 결과96/96 unknown(unverified). 이 결과는 ROI 해결/성능향상이 아니다. C3의9→10은96박스 중10박스 하위집합이며 파일 reports/gui_validation/roi_audit.json에 카메라별 내역 보존. 원본1024²→RT640² 직방향 resize 및 RT원본좌표복원, HVQ224² direct resize를 코드에서 확인. 원본↔640×480 LUT 등록 근거는 없음. 운영 결과 수정 없이 별도 HTML검증도구 생성됨.

독립 개발용 영속 JobStore와 API factory 구현: 별도 .sqlite, 단일워커, Idempotency-Key/입력fingerprint, CAS 상태전이, QUEUED만 취소, RUNNING은중단하지않음. processor미주입 시503으로추론비활성. 기존운영/inference/run미변경. 새테스트작성중이며최종로그는추후갱신.

### GUI 연결 및 히트맵 후속 요청 반영

`Failed to fetch`: 과거로그에서 CORS OPTIONS400 및API프로세스 종료기록확인. frontend 기본주소를 /api+Vite dev/preview프록시로수정, config/web.json변경없음. 별도읽기전용게이트웨이app/readonly_api.py와scripts/start_gui_readonly.sh제공. 운영API재시작없음; 호스트런타임확인은샌드박스소켓제약으로미완료.

히트맵팔레트를청록→밝은노랑→선명한빨강으로강화하고재질조명이통계색을흐리지않도록조정. 선택부위윤곽선과범례두께확대. 물리ROI등록미확인인경우3D임의착색차단; 별도수치히트맵에실제API의부위별분자/분모를보여주는구조. 데이터가없으면여전히값을만들지않음. 신규mapping_verified메타데이터는현재중앙API에없으므로실제3D투영은미확인상태유지.

Job/GUI/MockReal/Backoff/readonly/proxy테스트추가. 코드수정중발견한SQLiteINSERT자리수와토큰raw import테스트설정,TypeScript타입검사문제를수정했으며중간실패로그를최종통과로간주하지않는다. 최종통합검사는scripts/validate_gui.sh로다시실행한다.

### GUI 최종 검증 확정 — 2026-11-24

전체완료가아닌 PARTIAL 상태로인계. 현재코드 Python81통과/4skip, Vitest62통과(10파일), ESLint통과, TypeScript+Build통과. 보호된추론소스/config해시동일, 토큰외HEX0건. 중간실패수정후실행한최종로그: reports/gui_validation/final-*.log. 최신통합보고서 FINAL_GUI_VALIDATION_REPORT.md. 신규실제브라우저검증과스크린샷은샌드박스제약으로BLOCKED이며호스트검증스크립트제공. ROI등록근거부재로3D실제부위매핑은PARTIAL/unverified 유지. 기존운영서버·모델·백필·DB동기화변경/중단/재시작없음.

연결복구용별도읽기전용개발: bash scripts/start_gui_readonly.sh → http://127.0.0.1:15173/. 브라우저검증: nice -n 15 node scripts/capture_gui_validation.mjs. 회귀검증: bash scripts/validate_gui.sh. 이명령은샌드박스밖호스트에서실행; 운영API재시작명령아님.

### V6 Precision 인트로·대시보드 디자인 요청 반영 — 2026-11-24

원본inspect_ai_v6_precision.html보존(해시확인). 기본인트로를V6플랜지/5카메라시연으로연결하고이전8단계개념인트로도선택가능하게유지. 예시대시보드는노출하지않고검증된iframe메시지로실제대시보드라우팅. 시연네트워크차단/격리,모션최소화/비활성탭렌더중지/24fps상한/자원해제구현. 큰소스는lazychunk분리.

실제대시보드도같은네이비·시안·둥근패널·INSPECT AI테마로재구성. 필터/3D/근거/검수/챗봇기능과실제데이터계약유지. 예시수치미이식. 토큰집중화,66Vitest통과+ESLint/TypeScript/Build통과,원본HTML및보호된추론/config해시동일. 실제브라우저신규육안검증은여전히BLOCKED. 상세PRECISION_REDESIGN_REPORT.md. 운영프로세스/DB/모델변경·재시작없음.

### 상세3D·히트맵 및 SIM 혼합 보고 후속 — 2026-11-24

30품목에103개상세표면추가. 개별칫솔모/고무그립/실제구멍소켓/접점/PCB배선·실장부품/나사홈/배터리실링/지퍼슬라이더등을기존부위ID아래생성. 외부HDR없는스튜디오반사/재질/스테이지,상세포함bounds와초기보기각도. 재질/겹쳐보기/히트맵+강도조절,조명과분리한unlit히트레이어와밝은범례구현. 미확인ROI/데이터없음은중립유지.

SIM/칫솔혼합보고: 품목변경시이전stats잔류와늦은cases/cards응답유입경로확인·수정. 세요청세대무효화,이전선택/통계/사례초기화,item일치검증추가. 메시category소유권/namespace/불변캐시와프레임버퍼초기화보강. SIM몸체를원형구멍이아닌얇은사각트레이로개선. 실제브라우저GPU중첩원인은미재현이며실화면해결확정으로주장하지않음. 빠른전환/지연응답/메시소유권테스트추가.

메시소프트웨어투영미리보기를직접검토했으며라이브GUI스크린샷과구분. DETAILED_3D_HEATMAP_REPORT.md와reports/gui_validation/detail3d참고. 운영프로세스/DB/모델/config미변경. 최종수정본테스트·빌드실행중결과는로그/보고서에확정후기록.

상세3D최종검증확정: Vitest105통과(15파일),ESLint/TypeScript/Build통과(최종13.48초),보호된추론/config해시동일,토큰외HEX0. 최대삼각형23,892/품목. 이전빌드SIGTERM후자원제한재실행으로통과. 실제GUI브라우저검증은여전히미완료. SIM사각트레이와칫솔소프트웨어투영을재검토했으며실제검사값/공간ROI자료는생성하지않음.


### 품목 전환 3D 중첩 재보고 후속 — 2026-11-24

IMPLEMENTED: 이전 수정 후에도 중첩된다는 재보고 반영. Scene.tsx의 Canvas를 품목별 CategoryScene 전체 key로 분리하여 카테고리 간 React Three Fiber root/renderer 재사용을 제거했다. 분리된 이전 캔버스는 microtask에서 animation loop/render lists/renderer/context를 해제한다. 연결 중인 StrictMode 캔버스는 파괴하지 않는다. 설치된 R3F 기본 unmount 해제는500ms 지연됨을 확인했으나 실제 화면 중첩의 확정 원인으로 주장하지 않는다.

VERIFIED: 현재 코드 Vitest109통과(16파일), ESLint통과, TypeScript+Production Build통과(11.16초), 보호된추론/config해시동일,토큰외HEX0. 신규4테스트: 분리키/해제1회/StrictMode보호/이전정리가새렌더러에영향없음. 로그 reports/gui_validation/category-overlap/{vitest,eslint,build,integrity}.log. 신규패키지없음, 운영프로세스·DB·모델·설정·서버재시작없음.

BLOCKED: 실제 브라우저 중첩 재현·시각적 해결확인은 기존 샌드박스 실행제약으로 미완료. 별도개발서버에서 `nice -n 15 node scripts/check_category_overlap.mjs` 실행 가능. 사용가능 품목 정방향/역방향 및 칫솔·SIM 재전환에서 단일Canvas/단일제품그룹/foreign category없음/renderer교체를 실제 장면그래프로 검사하고 스크린샷을 남긴다. 운영쓰기요청차단/보안샌드박스유지. 구문검사통과, 실제브라우저결과는미생성. 기존HMR화면은 새로고침후 확인필요.


### 최종 성능·조회 동기화 점검 — 2026-11-24

VERIFIED(파일): max16 16:33:59완료24,000제품/120,000시점/실패0, DB파이프라인16:34:51완료, 에이전트·독립SQL수치검증16:35:03완료. final_performance/latest.json은점검시없음. 기존코드가완료후에도computing을반환하는표시문제확인. 보고서명령은기존사용자직접실행지침유지/미실행.

IMPLEMENTED: report_pending상태와GUI표시, overview/API/tool상태일치,중복상태읽기제거. get_final_performance도구HTTP입력모델누락(404경로)등록수정. DB전체count(*)를유일제품수로오인하지않도록‘DB검사기록’표기. Test제품수/보고서시각표시. scripts/check_final_sync.py는등록된조회만호출하여세조회경로및활성모델일치검사. 보고서 FINAL_PERFORMANCE_SYNC_REPORT.md.

BLOCKED: 샌드박스호스트8080/PG접속불가, 실제서비스동기화/초과2시도·10시점출처/실브라우저미검증. 스냅샷에는fusion조회도구2종이있지만현재저장소와다름; 운영도구등록동일하다고주장하지않음. 기존모델/config/운영DB/추론/백필/서버변경없음,신규패키지없음. 현재최종테스트진행결과는reports/gui_validation/sync-final에기록.


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


### 추가2-A 인계와 현재 저장소 재조사 — 2026-11-24 18시대

사용량7%인계요청맥락에서 고해상도공간히트맵 추가지시를 TASK_2A_SPATIAL_HEATMAP.md에정리하고 NEXT_AGENT_HANDOFF.md맨위에최신상태보정. HEATMAP_DETAIL_ANALYSIS.md에코드상원인/소스/선행검증기록. 실제현재는30품목69시점템플릿+public.findings운영집계가추가되어있다. 운영artifact관측합24001은공식코호트24000과동일범위라고검증되지않음. 현재메시는부위당단색/운영집계는좌표를버림. 공간grid/계층/UVtexture/고해상도GUI는NOT_STARTED. 읽기전용UV인벤토리와ROI현황CSV를생성하며실API/브라우저150장검증으로주장하지않음. 이전103/116통과로그이후앱코드변경있어새코드전체통과주장없음. 앱/평가/운영설정변경없이문서와인벤토리만추가.
