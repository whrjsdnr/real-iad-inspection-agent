# 최신 상태 — 2026-11-25(정정): 데이터 분할 해석 정정 — 통합 추론 코호트는 두 모델 학습 미사용

이 절이 아래 모든 기록보다 우선한다. 성능 수치는 일절 변경 없이 해석만 정정했다.

## 정정 요지
- 기존 문서의 "전체 24,000 학습 중복 가능성(UNKNOWN)" 표현은 **근거가 없었다**. 사실 관계는:
  - 통합 추론 코호트 24,000제품·120,000장은 **RT-DETRv2·HVQ-Trans 모델 학습에 사용되지 않았다**(훈련 담당자 확인).
  - 유일한 주의점: 퓨전 규칙(가중치·품목별 min-max·TH·margin)은 이 코호트의 **Validation 3,610으로만 보정**했으므로 전체 지표에는 규칙 보정 데이터가 포함된다.
  - **Test 3,593은 모델 학습은 물론 규칙 보정에도 사용되지 않은 완전 홀드아웃 — 대표 지표**(F1 0.953210, Recall 95.3210%).
- 근거 상태: 추론 코호트 manifest(`~/MV/outputs/agent_integration_20261123_v1/inference_cohort_120000/manifest.csv`, seed 20261123 신규 표본)는 로컬에 있으나, 두 모델의 학습 ID manifest는 원격 학습 서버에 있어 로컬 직접 대조는 불가. `selection.json`의 `UNKNOWN_ORIGINAL_30000_ID_LIST_MISSING`은 당시 원본 퓨전 실험 학습 목록 미복구를 뜻한다. 정정은 훈련 담당자(사용자) 확인에 근거.
- 수정 범위: 양 저장소 README·docs·FINAL_FUSION_CONTRACT_REPORT·INFERENCE_DB_SHARING_GUIDE·TEAM_QUICKSTART·app/tools.py 설명·IntroPage 표시문구·team kit(FUSION_CONTRACT·DATA_AVAILABILITY, ZIP 재생성 649파일)·이력 보고서 5종 상단 정정 배너. 성능 수치·계약·판정·임계값 변경 없음.

---
이하 2026-11-25 배포 완료 기록

# 2026-11-25(최종): 배포·GitHub·Release 완료

이 절이 아래 모든 기록보다 우선한다. 사용자 승인(A→B→C→D)을 받아 실제 배포를 완료했다.

## A. Git 보안(완료)
- `git filter-branch`로 config/team-share.env의 실제 값(토큰 43자·DB 읽기 비밀번호 13자)을 전체 18개 커밋에서 `REMOVED_ROTATED_20261125`로 교체. 커밋 메시지·작성자·개수(18) 보존. 초기 3커밋 제외 해시 변경.
- refs/original·reflog 정리 + `gc --prune=now` → 전체 이력·객체 재검사 **히트 0, unreachable 0**. `scripts/scan_secrets.py --all-history` 통과. pre-commit 훅 유지.
- 인증정보 교체: DB 읽기 역할(app_read) 비밀번호 ALTER ROLE + TEAM_ACCESS_TOKEN 재발급(43자). .env·config/team-share.env 갱신. 신구 검증(신규 OK·구 거부). 18080 게이트웨이 새 자격증명으로 재기동 확인.
- 백업 ~/backups(700/600)에 구 이력·env 사본 보관. 노출 경로 없음 확인(로컬 전용이었음).

## B. 운영 배포(완료)
- :8000 구 프로세스(PID 35145) 정상 종료 → 신코드 기동(작업 PID 기록 /tmp/inspection-api-8000.pid, 로그 /tmp/inspection-api-8000.log). migrate() 가산·멱등, 스키마 변경 없음.
- 검증: 16개 엔드포인트 전부 200(/health·/docs·/openapi.json·/tools·/fusion/runs·/sharing/manifest·/catalog/parts·/roi/templates·/products·/products/findings·/parts/heatmap·/heatmaps 4종·/sharing/kit).
- 실데이터: 칫솔 마스크 64²(4096)·HVQ/RT 표면 32²(19종/5종 값)·지퍼 맵 지원 3제품·에이전트 도구 실호출(query_error_stats rows)·ZIP 다운로드(3.8MB·무결성 OK)·활성 run 계약 v2 유지 확인.

## C. 팀 공유 서비스(서비스 완료, Windows 노출은 사용자 액션)
- :18081 0.0.0.0 가동(PID 1788050, 로그 reports/gui_validation/team-host-18081.log). 인증 200/미인증 401 확인, DB role=read.
- **Windows 관리자 PowerShell(사용자 실행 필요)**:
  `netsh interface portproxy add v4tov4 listenaddress=192.168.20.164 listenport=18081 connectaddress=172.24.157.10 connectport=18081`
  `New-NetFirewallRule -DisplayName "Inspection Share 18081 - Team" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 18081 -RemoteAddress 192.168.20.170,192.168.20.209,192.168.20.168 -Profile Any`
- 기존 정책: 8000번 방화벽이 팀원 IP 3개로 제한(portproxy 164:8000→WSL 이미 존재). 5432 비공개 유지.

## D. GitHub·Release(완료)
- MV: github.com/whrjsdnr/MV push 완료(8d01cc9..75966b0). 미푸시 10커밋 secret scan 클린.
- agent: **github.com/whrjsdnr/real-iad-inspection-agent(Private)** 생성·push. 최신 커밋 확인은 git log origin/main.
- Release **v1.0.0**: https://github.com/whrjsdnr/real-iad-inspection-agent/releases/tag/v1.0.0 — team_integration_kit.zip + .sha256 에셋, Release Notes(성능·범위·제한·데이터 권한 명시).
- README: 양 저장소 교차 링크 확정·push. GitHub 렌더링 확인(아키텍처·간트 mermaid 2블록, 이미지 6종 임베드·경로 무결).
- TEAM_QUICKSTART.md 작성·push(팀원 10개 작업 절차·오류표·토큰 별도 전달 원칙).

## 다음 에이전트가 할 일
1. 사용자가 Windows 관리자 명령 실행 후, 팀원 PC(또는 동일 네트워크 PC)에서 :18081 외부 접속 검증(TEAM_QUICKSTART 1~4절).
2. 공유 토큰을 3명 팀원에게 안전 경로로 전달(재발급된 최신 값 — config/team-share.env).
3. GUI 추론 v2 E2E(신코드 운영 기준), 팀원 피드백 수렴.
4. Private→Public 전환 검토 시 Real-IAD 라이선스·재배포 조건 별도 확인(Release Notes에 명시).

---
이하 이전 기록

# 2026-11-25(2차): 배포·공유 준비 완료(승인 4건 대기)

이 절이 아래 모든 기록보다 우선한다. 목표: 실제 팀 사용 가능 상태 + GitHub 안전 업로드 준비.

## Phase 1 Git 보안(완료 — 재작성은 승인 대기)
- 이력 검사: 실제 토큰(43자)+DB 읽기 비밀번호(13자)는 `config/team-share.env` 경로로 **6856e64~4fe4643 등 7개 커밋**에 존재. HEAD 트리·ZIP·MV 추적 파일은 깨끗(placeholder만).
- 백업: ~/backups/agent-git-history-20261125.tgz(31M)·agent-repo-20261125.bundle(29M)·team-share.env.local-backup.
- 재발 방지: config/team-share.env.example(placeholder)·scripts/scan_secrets.py(pre-commit 설치, HEAD 통과)·--all-history 모드로 7커밋 검출 확인.
- 외부 노출 경로 없음(원격 없음·미푸시·ZIP 무결). **승인 요청 A: filter-repo/filter-branch로 team-share.env 전 이력 제거 + 토큰/DB 비밀번호 교체.**

## Phase 2/3 운영 배포·팀 공유(준비 완료 — 기동 승인 대기)
- 운영 :8000(PID 35145, 11-24 10:07 기동, .env 로딩) 기록. migrate()는 가산·멱등. **승인 요청 B: 재시작.** 절차·검증 17엔드포인트·롤백은 docs/DEPLOYMENT.md.
- 18081 team_api 부트 자가테스트 통과(127.0.0.1:18099, 인증 200/미인증 401, 이후 종료). 사전조건(env·dist) 충족. **승인 요청 C: TEAM_BIND_HOST=0.0.0.0로 기동.**

## Phase 4 Windows LAN(확정)
- LAN IP **192.168.20.164**(이더넷), WSL 172.24.157.10. portproxy 164:8000→WSL:8000 이미 존재.
- 방화벽 기존 정책: 8000번 원격 {192.168.20.170, .209, .168}. 18081 추가용 PowerShell 명령은 docs/DEPLOYMENT.md(관리자 권한). 5432는 비공개 원칙 유지.

## Phase 5 GUI 스크린샷(완료)
- Chromium headless(샌드박스 유지) 캡처 18장 오류 0: 인트로·대시보드·5칩첩 시연·7개 품목 3D·개별제품·챗봇·모바일·연결실패.
- 대표 6종을 docs/images/에 등록·README 반영. 칫솔 3D 표면 히트맵은 실제 마스크 N=335·HR 핫스팟·범례 확인. 지퍼 3D·챗봇·C1~C5 근거 확인.
- 미커버: HVQ 맵 근거 패널·RT 분포 단독 화면·투명도 조절 장면(셀렉터 미매칭 — 스크립트는 최신 표면 제어 UI로 일부 수정함).

## Phase 6/7 GitHub·Release 준비
- gh 인증 확인(whrjsdnr, repo scope). MV는 origin 대비 9커밋 앞서 있음(미푸시). agent 원격 없음.
- README 교차 링크 완료. agent는 **Private**(real-iad-inspection-agent) 기본 제안. **승인 요청 D: MV push + agent Private 생성/push + tag v1.0.0 + ZIP Release(실데이터 재배포 권한 확인 후).**
- ZIP 최종 검증: 649파일·unzip -t OK·sha256 동봉·secret scan 통과·python_client 실실행(manifest 30/24000/120000, 32² 그리드 19종 값)·verify_surface_sdk(30품목/134 overlay/118 hotspot)·킷 OpenAPI 35경로 전부 라이브 게이트웨이와 일치.

## 커밋
- agent: 60627f9(총 16커밋), MV: README 교차링크 커밋 후 클린.

---
이하 2026-11-25 1차 기록

# 2026-11-25(1차): 통합·팀 공유·Git 정리 완료

이 절이 아래 모든 이전 기록보다 우선한다. 작업: 최종 인계·팀원 공유·Git 저장소 정리(신규 기능 개발 아님).

## Git(로컬 커밋 완료, push는 사용자 승인 대기)
- **~/agent 는 이번에 Git 저장소로 초기화**(기존에 .git 없음). main 브랜치, 커밋 12개: chore 기반설정 → feat(api/pipeline/config/gui/sdk) → test → docs → fix(security). remote 없음.
- **~/MV**: 기존 원격 github.com/whrjsdnr/MV(미푸시). 미커밋 130건을 8개 논리 커밋으로 정리. .gitignore에 /inference(2G)·/hvq_outputs(682M)·/rtdetr_outputs(570M)·/real-iad-backup(382G)·/environments(1.3G)·*Zone.Identifier 추가. 작업 트리 클린.
- **보안**: `config/team-share.env`(실제 TEAM_ACCESS_TOKEN·DATABASE_URL_READ)가 feat(config) 커밋에 포함됐다가 추적 제외됨(파일은 디스크 유지, .gitignore 등록). repo는 로컬 전용·미푸시이나 원격 공개 전 이력 재초기화/정리를 사용자 승인 하에 결정할 것. .env·*.pt·DB·node_modules·.venv 추적 0 확인.

## 검증(이번 세션 실행)
- 백엔드 pytest **133 passed/4 skipped**(116초), 프런트 vitest **135 passed/23파일**, ESLint 통과, tsc+production build 13.18s(500KB 청크 경고만).
- 보고 수치 재확인: 24,000제품/120,000시점/30품목, 계약 v2 Test F1 0.953210·Recall 95.3210%, 전체 참고 0.968780, all_predictions 24,001행, HVQ 실제 맵 500개/100제품, ZIP **649파일**/sha256 5005866e…/secret scan 통과/unzip -t OK.
- README(양 저장소) 재작성: 아키텍처·실날짜 간트(mermaid)·성능·문제-해결·실행법·한계. docs/ 9종 신규(ARCHITECTURE·DEVELOPMENT_HISTORY·FUSION_EVALUATION·HEATMAP_PIPELINE·AGENT_DESIGN·TEAM_INTEGRATION·TROUBLESHOOTING·REPRODUCIBILITY·LIMITATIONS). README 이미지 상대경로 7건 존재 확인.

## 서버/공유 현황(중요)
- 운영 중앙 :8000(PID 35145) = **구 코드**. /products·/fusion/runs·/heatmaps/*·/sharing/kit 전부 404. 신코드 배포 재시작은 **사용자 승인 대기**.
- 개발 읽기전용 게이트웨이 :18080 = 신 코드로 **재기동 완료**(이번 세션, 기존 8000/15173/배치 무관). 공유 API 전부 실응답 확인: /sharing/manifest·/catalog/parts·/roi/templates·/products(views/findings/anomaly-map/fusion)·/heatmaps(catalog/ground-truth/metadata/evidence/surface/surface-layout)·/parts/heatmap·/fusion/runs·/sharing/kit.
- Vite :15173(127.0.0.1) 유지. 팀 공유 :18081 인증 서비스는 미기동(TEAM_SHARING_GUIDE.md 명령, 승인 후 실행). 호스트 LAN IP 172.24.157.10 — 192.168.20.164는 구 기록과 다름.
- **import_score_batch.py 배치 완료**(프로세스 종료 확인, 이번 세션 중). report_fusion_performance --wait 미기동.

## 다음 에이전트가 할 일
1. 운영 :8000 신코드 재배포 승인 요청 및 수행 후 /fusion/runs·/heatmaps 실주소 검증.
2. 18081 팀 공유 서비스 기동·팀원 PC 외부 접근 검증(verify_team_data.py, PowerShell/curl 예시는 킷 QUICKSTART).
3. GUI 추론 v2 계약 E2E 재검증(기존 기대값은 구 계약 기준), 실브라우저 스크린샷.
4. Git push/Release는 사용자 승인 후. MV 이력의 6.4MB PDF(기존)는 보고만 — 재작성 금지 원칙.

---
이하 2026-11-25 이전 기록(참고용)

# 2026-11-25: 30품목 표면 표시 및 HVQ 저장 맵 복구

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

# 추가2-A 최신 인계 — 2026-11-24 18시대 조사

**먼저 TASK_2A_SPATIAL_HEATMAP.md와 HEATMAP_DETAIL_ANALYSIS.md를 읽으세요.** 사용자의 마지막 큰 추가 지시는 고해상도 공간 히트맵이다. 앞서 사용량7%로 다음 에이전트 인계를 요청한 맥락에서 새 요구사항과 착수 조사를 저장했다. 공간 grid/texture/계층/챗봇 고도화를 구현 완료했다고 보고하지 말 것.

이 문서 아래17시대 인계 이후 공유 저장소에 추가 변경이 있었다. 현재 app/part_heatmap.py는 public.findings/inspection_views 읽기전용 운영 집계와 다중 폴리곤/ROI템플릿을 포함한다. config에는30품목69시점 템플릿이 있다. artifact의 운영 항목30개/부위50개/품목별 observed 합24001을 확인했다. 현재를 ‘GUI1표본만 있고 운영집계 미구현’이라고 설명하면 부정확하다. 그1표본은 여전히 실제HVQ 공간맵을 확인한 자료지만 운영RT집계는 별도다.

특히 camera 필터/부위별 관측 분모/model·date 적용/공식24000코호트 범위/GUI와운영 중복을 공간고도화 전에 검증할 것. 현재3D는부위당단색값이며 운영artifact에박스좌표분포가보존되지않는다. operational_findings는source명이고확인한실제SQL은public.findings다. 실테이블을추정하여새로만들지말것.

UV 속성과30품목등록선언을읽기전용으로조사했다: reports/part_heatmap/uv-inventory.json,roi_spatial_status.csv. UV 존재는 ROI와의 물리 정합 증거가 아니며 이 표는 새150장육안검증결과가 아니다. 이후 앱코드 변경에는이전103/116테스트통과로그를최신통과로대신사용하지말것. 코드 동시변경을 덮어쓰지 말고 현재상태부터 재검증한다.

추가2-A는 확정 퓨전계약(v2로 지칭)/모델/기존판정/구max16/공식분할을 변경하지 않는다. 현재평가설정의파일명버전은 weighted-minmax-heatmap-mean-rt40-v1이며 명칭때문에 내용을 다시변경하지 않는다. 손잡이는사용자가명시삭제했으므로예시계층을이유로복원하지않는다. 칫솔/지퍼부터 실제원본/맵/관측을검증하고다른품목은그뒤에확장한다.

---

# 다음 에이전트 인계 — 2026-11-24

## 먼저 알아야 할 최신 사용자 결정

- 기존 작업을 재개하며 새 모델 개발/재학습/양자화는 하지 않는다.
- 사용자는 부위별 히트맵 구현을 요구했다. ‘좌표 자료 없어서 불가’로 끝내면 안 된다.
- 실제 칫솔 C1–C5는 헤드 확대 촬영이다. 사용자가 **손잡이를 제거하라고 명시**했다. 현재 표시 ID는 `neck`, `bristle`; 손잡이를 복원하지 말 것.
- 최신 평가 계약을 사용자가 명시 선택했다: **min-max + 루트 설정(HVQ heatmap_mean, RT0.4), RT0.7/HVQ0.3**. Test 각 제품에 이 가중합을 적용한 뒤 지표를 계산하라고 재확인했다. 다시 max16/백분위로 돌아가지 말 것.
- 전체24,000제품 참고 집계를 포함하고 별도 Test3,593제품도 보존한다. Val3,610제품으로만 보정한다.
- 사용량7%라 현재 작업 마무리 후 인계를 요청했다. 아래 이미 완료한 추론/검사를 처음부터 반복하지 말 것.

## 운영 보호 / 환경

추론·max16 백필·DB 동기화 프로세스 중단/재실행 금지. 운영 PostgreSQL 데이터/스키마/권한 변경, 운영 서버 재시작, 기존 판정 덮어쓰기 금지. 모델/전처리/기존 root inference 자산 수정 금지. 새 평가는 별도 파생 파일로만 작성했다. 새 패키지 설치 없음.

이 샌드박스는 호스트 PID 목록을 볼 수 없고 localhost8080/PG 접속 및 Chromium sandbox 소켓이 제한된다. `ps`가 적게 보인다고 운영 프로세스가 없다고 주장하지 말 것. 같은 브라우저 실패를 반복하거나 보안 설정을 낮추지 말 것. 새 HTTP/브라우저 검증은 호스트에서 수행해야 한다. Git 메타데이터는 이전 조사상 사용 불가/대체 상태였다. 파일 해시 기준을 사용했다.

## 방금 완료한 평가 — VERIFIED

`FINAL_FUSION_CONTRACT_REPORT.md`가 최신 보고서 설명이다. 실제 산출물:

- `reports/final_performance_minmax/{performance.json,all_predictions.csv,latest.json}`
- `config/fusion_evaluation.json` 명시 계약. 기존 config/fusion.json은 변경하지 않았다.
- `scripts/report_minmax_fusion.py`: 읽기전용 max16 SQLite에 보존된 **hvq_mean**을 재사용한다. 이름이max16인 저장소라도 per-view mean 점수가 따로 있다. 모델 추론 재실행 없음.
- RT는0.4미만이면0, HVQ는 연속 mean을 사용하며 max16 임계값으로 자르지 않는다. Val 품목별 min-max, TH와 대칭 margin은 기존 검증된 threshold_and_margin 사용. min-max 범위 밖은 unclipped 외삽, 상수범위는 거부한다.
- 모든 Test 제품의 score=0.7×RT_norm+0.3×HVQ_norm. 모델 성능 지표를 가중 평균하지 않았다.
- 전체24,000: TP12102/FN306/FP474/TN11118, Recall12102/12408=97.5338%, F1=24204/24984=0.968780, AUROC0.992895, 보류194.
- Test3593: TP1752/FN86/FP86/TN1669, Recall1752/1838=95.3210%, F1=3504/3676=0.953210, AUROC0.986346, 보류37.
- 모델 ID `fusion-minmax-mean-rt40-w70-30:e917f9730ddb05d9c486b45d`.
- `reports/gui_validation/part-heatmap/minmax-contract-audit.json`:24,000제품 가중합 최대오차0,30품목 Val TH/margin 재확인, 별도SQLite 인메모리 SQL 혼동행렬 일치. 운영PG 독립검증은 아님.
- 이전0.9428(Test)/0.9590(전체)은 max16/백분위 기준의 **구 보고서**다. 최신 결과로 인용하지 말 것.

`app/status.py` 기본 로더는 새 보고서를 우선 선택한다(명시적 FINAL_PERFORMANCE_DIR는 우선권 유지). root/evaluation config SHA 일치 검사. old reports/cohort_performance는 새 보고서에 잘못 붙지 않는다. API/챗봇 summary에 fusion_policy/evaluation_scope/evaluation_products/source_model_version/database_run_activated 포함. GUI는 전체/Test 및 계약을 함께 표시. 로컬 파일 로더 실제 출력으로 확인했다. **운영 서버가 새 코드를 읽는지는 미확인**이다.

실제 운영 fusion_analysis.model_runs는 여전히 이전max16 run이다. 새 보고서는 별도 저장 점수 재평가이며 DB run을 활성화하지 않았다. 사용자에게 새 성능 수치와 기존 제품별 DB 판정이 동일 정책이라고 주장하지 말 것. check_final_sync.py는 report-only일 때 source_model_version을 활성 DB run과 비교한다.

## 방금 구현한 부위 히트맵 — IMPLEMENTED / 실제 표본 검사 VERIFIED

- `app/part_heatmap.py`: 원본 픽셀 좌표 다각형+이미지SHA를 이용해 기존 검출/맵을 별도 집계한다. 중심이 하나의 ROI에만 속하는 박스만 배정한다. 경계/외부/중복 ROI/해시 불일치는 보수적으로 처리.
- `config/part_heatmap_regions.json`: 기존 parts_roi.json과 별개. 현재 **칫솔1제품·5장 exact-image SHA**의 헤드 ROI만 등록. 실제 원본을 도구로 보고 폴리곤을 작성했고 겹침 이미지를 육안 확인했다. 운영 전체 보정 완료나 실제3D스캔이 아니다.
- 실제 소스: `gui_evidence/gui-a7b441dfce9a/result.json`, 제품 `toothbrush/NG/CH/S0001`. 동일 이미지 재업로드2건은 중복 제거.
- threshold_source=root_fusion_config로 RT0.4 적용. 헤드 검출6박스가 **제품1/관측제품1**에 연결된다. 6제품으로 중복 계산하지 않는다. HVQ ROI 평균72.59146은 원시값이며 확정 불량률이 아님.
- maps는224² 실제 배열을 읽고 확인된 direct-resize 변환을 공통 Transform으로 적용. polygon_mask는 픽셀 중심을 사용한다. 640×480 legacy LUT를1024²로 임의 확대한 것이 아님.
- `reports/part_heatmap/{latest.json,actual-summary.json,roi-native-overlay.html,native-roi-review.jpg}`. JPG는 실제 원본+ROI+검출 오버레이로 직접 확인했다. **라이브GUI 스크린샷은 아니다.**
- `app/part_api.py`: 읽기전용 GET `/parts/heatmap`, `/parts/evidence/{case_id}/{camera}`. 중앙 API와 별도 readonly gateway에 등록. 모델/기간/카메라/품목 필터, 원본 해시 확인, 등록된 이미지만 반환. DB 쓰기 없음.
- `scripts/derive_part_heatmap.py`: 기존 GUI 근거만 집계하며 추론하지 않는다.
- 프런트 `three/partHeatmapStore.ts`, `components/PartSignalPanel.tsx`, `CenterPanel.tsx`, `Scene.tsx`, `heatEvidence.ts`: ‘모델 검출 히트맵’ 기본 + ‘검수 확정 지표’ 선택 분리. 실제 데이터 외 fixture 대체 없음. 3D 부위 색/선택 → 원본 ROI/박스+C1–C5 근거. 표본수1을 명시한다. 손잡이 geometry/details/목록 제거, 기존 neck/bristle ID 유지.
- 모델 지표와 수동 reviews 지표를 섞지 않는다. 기존 unknown0/1은 별도 미분류 검수 그룹이다. 이를 손잡이나 다른 부위로 강제 배정하지 않았다.

### 히트맵 남은 일 — 우선순위 높음

1. **실제 호스트 브라우저 검증/승인된 배포.** 운영 서버를 임의 재시작하지 말 것. 새부위GET가404면 운영 코드가 이전 버전일 가능성부터 확인. 별도 개발 포트 사용.
2. 현재1제품·5장이라는 범위를 전체24,000으로 오해시키지 말 것. 다른 실제 품목·카메라별 ROI를 원본 위에서 등록/검증하고 근거를 확대해야 한다. neck도현재not_annotated다. 원본 크기와 물리 부위가 확인되지 않은 검출을 색칠하지 않는다.
3. ROI 등록용 개발 UI/도구는 아직 만들지 않았다. 현재 config를 직접 작성한 표본만 지원. 이를 만들어 다른 품목을 등록하면 확장 가능하다. 30품목 모델 region IDs는 parts.ts 참조.
4. derive_part_heatmap는 현재 gui_evidence만 읽는다. 전체 운영 findings를 읽기전용으로 수집·좌표출처 확인 후 파생 집계하는 경로가 필요하다. 운영DB 기존 part_id를 덮어쓰지 말 것.
5.23,900제품의 백필은 scalar mean/max16만 보존하며 공간 맵은 이 저장소에 없음. 원시 모델 맵이 없는 영역에 가상의 핫스팟을 만들지 말 것. 현재 헤드 원시맵은 GUI 근거5개에서 재사용했다. 추가 추론이 필요하면 운영 자원/사용자 제약을 확인.
6. 제품별 GUI의 기존 퓨전 판정은 이전 정책일 수 있다. 새 report 모델 ID에 해당하는 파생 CSV를 명확히 구분해서 조회하도록 연결해야 하며, 운영DB 판정과 몰래 섞으면 안 된다.

## 기존 렌더러/레이스 수정 — 유지

Scene은 카테고리별 CategoryScene 전체를 key로 재생성, 이전 detached renderer를 microtask에서 해제하고 연결된 StrictMode probe는 보호한다. 데이터 요청 세대무효화/이전 카테고리 통계 거부/namespace 불변 캐시가 구현됐다. SIM/칫솔 중첩은 실제 브라우저 해결 확인이 남아 있다. 이 코드를 삭제하거나 공용Canvas로 되돌리지 말 것.

## 최신 최종 검증

- Python **103 passed,4 skipped**,64.12초: `reports/gui_validation/part-heatmap/final-pytest-all.log`
- 프런트 Vitest **116 passed,18파일**: 같은 폴더 vitest.log
- ESLint 경고0,TypeScript+Production Build 통과(6.77초): eslint.log/build.log
- 보호된 inference/config 기준 해시 동일, 소스 토큰 외 HEX0: integrity.log. 새 평가/ROI 설정 파일만 추가.
- 실제 호스트 HTTP/PG/브라우저 검증은 환경 제약으로 미완료. 테스트는 별도SQLite/ASGI로 운영 startup을 실행하지 않았다. 전역 테스트 DB를 운영 URL로 설정하지 말 것.

## 이어서 쓸 명령

```bash
cd /home/geonug/agent
# 새 계약 보고서; 기존 MV report_fusion_performance.py는 구 max16용이다.
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/report_minmax_fusion.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/derive_part_heatmap.py
# 호스트에서만, 기존 서비스 중단 없이 미사용 포트에 읽기전용 개발 환경
bash scripts/start_gui_readonly.sh
# 다른 터미널: API 일치 및 실제 캡처/카테고리 전환 확인
.venv/bin/python scripts/check_final_sync.py --base-url http://127.0.0.1:18080
nice -n 15 node scripts/capture_gui_validation.mjs
nice -n 15 node scripts/check_category_overlap.mjs
```

start_gui_readonly는18080/15173이 이미 사용 중이면 중단하며 기존 서비스를 종료하지 않는다. `.env` 내용/비밀번호는 출력·공유하지 말 것. 운영 배포/재시작은 별도 승인 경계다. 사용자에게 미검증 화면을 완료했다고 보고하지 말 것.
