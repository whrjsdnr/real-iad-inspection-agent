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

최신 추가2-A 상세검증: [HEATMAP_GUI_VALIDATION.md](HEATMAP_GUI_VALIDATION.md)

# GUI final validation report — 2026-11-24

**Overall: PARTIAL.** Code and isolated regression checks are completed below; latest host browser acceptance and operational deployment are not completed. No operational API restart, PostgreSQL transition, inference/backfill rerun, model change or recalculation of inspection results was performed.

## State and evidence

| Area | State | Evidence / limitation |
|---|---|---|
| Earlier redesign screenshots | VERIFIED | All4 original screenshots directly viewed, including final intro CTA; copies in reports/gui_validation/before |
| Thirty category templates | IMPLEMENTED; geometry VERIFIED | catalog.ts/parts.ts; real manifest and viewed C1 contact sheet;32 geometry tests |
| Canvas sizing/camera fit/filter width | IMPLEMENTED | explicit56vh parent, two-axis FOV fit, responsive filter rail; new live screenshots unavailable |
| Five-camera/eight-stage intro | IMPLEMENTED | IntroScene/IntroPage, conceptual labels, immediate CTA, reduced motion, demand rendering |
| Common coordinate transforms | VERIFIED in unit tests | app/coordinates.py; resize/crop/pad/inverse/normalized/map/boundary/missing metadata |
| Physical ROI mapping | PARTIAL |5 real images/96 boxes; original↔LUT registration is missing, no forced remapping |
| API/fixture separation | VERIFIED in unit tests | failed API→empty data/null rates; explicit fixture only; no fake normal/defect |
| Heatmap color visibility | IMPLEMENTED | brighter cyan→yellow→red tokens, stronger statistical material color, selected outlines, thicker legend and separate numeric heatmap; no live visual acceptance |
| Async development jobs | VERIFIED in unit/handler tests; runtime IMPLEMENTED | isolated durable SQLite, single-worker lease, idempotency, five states, disabled-by-default processor; no actual model run |
| Retry/resume | VERIFIED in unit tests; network IMPLEMENTED | bounded transient retries/Retry-After/same key/abort; opt-in UI monitor/localStorage |
| Agent tools/GUI commands | PARTIAL | isolated real tool stats→evidence test and local structured dispatcher; live Qwen and server-emitted GUI actions absent/unverified |
| API connection repair | IMPLEMENTED; proxy contract VERIFIED | /api Vite proxy, no CORS config change; separate read-only gateway/start script. Host runtime remains unverified |
| PostgreSQL sharing | VERIFIED preparation only | no schema/data/account/permission changes or transition |
| New browser screenshots/performance | BLOCKED | known sandbox Chromium shutdown syscall EPERM; no repeated launch/security weakening |

## Before/after

Before: tiny partial-height Canvas, generic boxes for28 categories, narrow truncated filters, low-contrast heatmap, direct localhost:8080 requests, automatic fixture fallback on API errors, synchronous long inference HTTP calls.

After: category-specific structural geometry/materials, centered fit and demand rendering; full-height Canvas; readable filter rail; saturated heatmap colors and explicit unknown status; same-origin /api proxy; API failures show errors/empty data; optional isolated durable jobs preserve the original API. Missing coordinate provenance is not hidden by coloring unknown regions.

## Test evidence

Current final checks are written by `scripts/validate_gui.sh` to:

- reports/gui_validation/final-pytest.log
- reports/gui_validation/final-vitest.log
- reports/gui_validation/final-eslint.log
- reports/gui_validation/final-build.log
- reports/gui_validation/integrity.json

Final current-code results (2026-11-24): **Python81 passed,4 skipped** (106.56s); **Vitest62 passed,10 files** (1.26s); **ESLint passed**; **TypeScript + production build passed** (11.56s). Protected inference/config hashes match and hardcoded HEX violations outside tokens.css are0. Four skips are unavailable original calibration integration checks. The build has a large-chunk warning, not a test failure. Commands/logs above are actual executions. No browser performance numbers or new screenshots were fabricated. Earlier baseline69 Python passes/4skips and46 frontend passes are historical, not substitutes for final results. Intermediate SQLite placeholder, CSS raw-token test processing and TypeScript errors were fixed and are not counted as final successes until rerun. Four integration skips depend on unavailable original fusion calibration artifacts; no threshold or model work was attempted.

Production build still reports a large JS chunk (~1.1MB uncompressed). No unmeasured loading/FPS/memory/API latency claim is made. Geometry triangle budgets are tested, not a substitute for browser GPU timing.

## ROI evidence

Full audit: ROI_COORDINATE_MAPPING_REPORT.md and reports/gui_validation/roi_audit.json. Original1024²→RT640² direct resize→original xyxy; HVQ224² direct resize. Legacy LUT640×480 has no physical registration. Old unknown87/96; conservative derived unknown/unverified96/96 (C3 alone9→10). This does **not** mean the ROI issue is solved. Other29 categories lack representative verified registration.

Developer HTML: reports/gui_validation/roi_overlay.html. It shows actual original images+stored boxes and separate native LUT planes; a correctly registered combined overlay remains blocked by missing metadata. No operational DB rows changed.

## Real data / historical evaluation

Read-only background JSON files show advancing max16/insertion progress, not a completed production evaluation. The user-reported98.84% is historical, metric name/denominator unverified and shown separately from operational results. API_EXTENSION_REQUEST.md records absent product/disagreement/unmapped queries and central GUI-action schema. Current backend source was inspected; current live deployment OpenAPI is unavailable from the sandbox.

The `mapping_verified` optional statistics flag is required before coloring real statistics onto physical mesh regions. Current legacy tools do not supply it, so real3D mapping remains explicitly unverified. Numeric part statistics can still be shown independently as colored cards with numerator/denominator. Explicit fixture mode can demonstrate heatmap colors, with fixture labels; it is not real inspection evidence.

## API connection repair and host commands

The frontend default changed from absolute localhost:8080 to /api; Vite dev/preview forwards to GUI_API_TARGET(default127.0.0.1:8080). Logs contain both CORS OPTIONS400 and an API shutdown record. The proxy resolves browser-origin coupling but cannot revive a stopped backend. Operational config/web.json and server were not changed.

From host Ubuntu, start isolated read-only development services:

```bash
cd /home/geonug/agent
bash scripts/start_gui_readonly.sh
```

Open **http://127.0.0.1:15173/**. Ports18080/15173 must be unused. The script requires DATABASE_URL_READ in the existing.env, enforces read-only transactions, performs no migration, exposes no inference/review writes and stops only its own new gateway child on exit. Diagnostic log:/tmp/inspection-gui-readonly-api.log. It was syntax/unit checked, not started against production here.

In another host terminal capture new screenshots:

```bash
cd /home/geonug/agent
nice -n 15 node scripts/capture_gui_validation.mjs
```

Output: reports/gui_validation/screenshots/<timestamp>/. No new screenshots exist yet. The script does not run inference, chat or review writes. It captures intro/camera/dashboard/available representative categories/part selection/real product if available/chat/inference idle/mobile/API-error, logs overflow and optional heap measurements, and marks unavailable cases skipped. An actual inference-progress screenshot needs an existing isolated lightweight job; no artificial inspection results are injected. Browser JSON state CAPTURED_REQUIRES_HUMAN_REVIEW still requires a person to inspect images and correct issues.

For regression checks:

```bash
bash scripts/validate_gui.sh
```

## Backfill report command (user only)

Confirmed script and imports; environment has sqlalchemy/psycopg2/numpy. **This command was not executed.**

```bash
cd /home/geonug/MV
/home/geonug/agent/.venv/bin/python scripts/report_fusion_performance.py --env-file /home/geonug/agent/.env --wait
```

The script reads the versioned pipeline/score set and uses read-only DB access; it generates final performance report files when ready. Default pipeline:outputs/fusion_agent_validation_20261124_v1/background_pipeline. Default manifest:outputs/agent_integration_20261123_v1/inference_cohort_120000/manifest.csv. Default output:outputs/fusion_agent_validation_20261124_v1/final_performance. User runs it after/as backfill completes; the GUI developer did not wait for or restart backfill.

## Changed files

Authoritative scope hash inventory: reports/gui_validation/integrity.json. Main changes:

- frontend: catalog/parts/Scene/IntroScene/heatEvidence; Intro/Dashboard/Chat/Inference pages; CenterPanel/FilterPanel/GuiContextControls/bits/TopBar; client/retry/jobs/config/store/types/tokens/heat; apiProxy.ts/vite.config.ts and related tests.
- backend additions only: coordinates.py, jobs.py, job_api.py, readonly_api.py; no operational model/inference/fusion module changes.
- tools: audit_roi_coordinates.py, check_gui_integrity.py, capture_gui_validation.mjs, start_gui_readonly.sh, validate_gui.sh; isolated tests and requested reports.

Git metadata is unavailable; baseline hashes distinguish modified existing src/app/config from newly inventoried scripts/tests. Config files and protected inference/optimization source hashes remain unchanged. No new Python/npm package was installed.

## Remaining acceptance / approval boundaries

Host browser visual review, all-category camera/ROI registration, actual inference-progress UI, end-to-end async multipart/worker restart reconciliation, live LLM→GUI action schema, and central API extensions remain unverified or partial. No permission is needed to run the separate development checks already authorized. Operational deployment/restart, DB changes or a real model job during backfill need separate approval and were not performed. Rollback source changes from a verified Git checkout/baseline; do not restore production DB/backfill files as a GUI rollback.

## Subsequent user-requested Precision redesign — 2026-11-24

The teammate V6 HTML is now the default isolated intro; the real dashboard uses its navy/cyan Precision Studio style. Existing8-stage intro is retained as an option. Source file preserved, example data is not operational data, and navigation targets the existing real dashboard. New final frontend checks: **66 Vitest passes, ESLint/TypeScript/build pass**; integrated inline script syntax parsed; source/protected hashes unchanged. Backend/Python unchanged in this design follow-up. Live browser acceptance remains BLOCKED, not claimed. See PRECISION_REDESIGN_REPORT.md and precision-*.log for current scope/evidence.

## Detailed 3D and heatmap follow-up

User requested more detailed dashboard meshes and stronger heatmaps, then reported occasional SIM/toothbrush mixing. Details and three display modes are implemented without changing inspection parameters. A confirmed cross-category stale-response path was fixed; GPU-specific overlap remains unreproduced. Current scope and latest final test/build logs: DETAILED_3D_HEATMAP_REPORT.md and reports/gui_validation/detail3d. Software geometry preview is separate from still-unverified live browser screenshots.


### 품목 전환 3D 중첩 재보고 후속 — 2026-11-24

IMPLEMENTED: 이전 수정 후에도 중첩된다는 재보고 반영. Scene.tsx의 Canvas를 품목별 CategoryScene 전체 key로 분리하여 카테고리 간 React Three Fiber root/renderer 재사용을 제거했다. 분리된 이전 캔버스는 microtask에서 animation loop/render lists/renderer/context를 해제한다. 연결 중인 StrictMode 캔버스는 파괴하지 않는다. 설치된 R3F 기본 unmount 해제는500ms 지연됨을 확인했으나 실제 화면 중첩의 확정 원인으로 주장하지 않는다.

VERIFIED: 현재 코드 Vitest109통과(16파일), ESLint통과, TypeScript+Production Build통과(11.16초), 보호된추론/config해시동일,토큰외HEX0. 신규4테스트: 분리키/해제1회/StrictMode보호/이전정리가새렌더러에영향없음. 로그 reports/gui_validation/category-overlap/{vitest,eslint,build,integrity}.log. 신규패키지없음, 운영프로세스·DB·모델·설정·서버재시작없음.

BLOCKED: 실제 브라우저 중첩 재현·시각적 해결확인은 기존 샌드박스 실행제약으로 미완료. 별도개발서버에서 `nice -n 15 node scripts/check_category_overlap.mjs` 실행 가능. 사용가능 품목 정방향/역방향 및 칫솔·SIM 재전환에서 단일Canvas/단일제품그룹/foreign category없음/renderer교체를 실제 장면그래프로 검사하고 스크린샷을 남긴다. 운영쓰기요청차단/보안샌드박스유지. 구문검사통과, 실제브라우저결과는미생성. 기존HMR화면은 새로고침후 확인필요.


### 최종 성능·조회 동기화 점검 — 2026-11-24

VERIFIED(파일): max16 16:33:59완료24,000제품/120,000시점/실패0, DB파이프라인16:34:51완료, 에이전트·독립SQL수치검증16:35:03완료. final_performance/latest.json은점검시없음. 기존코드가완료후에도computing을반환하는표시문제확인. 보고서명령은기존사용자직접실행지침유지/미실행.

IMPLEMENTED: report_pending상태와GUI표시, overview/API/tool상태일치,중복상태읽기제거. get_final_performance도구HTTP입력모델누락(404경로)등록수정. DB전체count(*)를유일제품수로오인하지않도록‘DB검사기록’표기. Test제품수/보고서시각표시. scripts/check_final_sync.py는등록된조회만호출하여세조회경로및활성모델일치검사. 보고서 FINAL_PERFORMANCE_SYNC_REPORT.md.

BLOCKED: 샌드박스호스트8080/PG접속불가, 실제서비스동기화/초과2시도·10시점출처/실브라우저미검증. 스냅샷에는fusion조회도구2종이있지만현재저장소와다름; 운영도구등록동일하다고주장하지않음. 기존모델/config/운영DB/추론/백필/서버변경없음,신규패키지없음. 현재최종테스트진행결과는reports/gui_validation/sync-final에기록.


최종 현재코드 검증 확정: Python 전체88통과/4skip(76.59초), 프런트110통과/17파일, ESLint/TypeScript/Production Build통과(14.02초), 보호된모델·추론/config해시동일/토큰외HEX0. 로그 reports/gui_validation/sync-final/{pytest-all,vitest,eslint,build,integrity}.log. 신규 점검스크립트 테스트의 urllib mock 메서드 접근 오류를 수정했고, 중간실패는pytest-all-first.log로구분보존했다. 실API/PG/브라우저검증은여전히BLOCKED, 운영미배포/재시작없음.


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
