# MV 마스크 API 404 수정 결과 — 2026-11-25

상태: **연결 코드/실데이터 transport 검사 VERIFIED, 현재 브라우저/운영 TCP 미검증**.

## 원인 구분

사용자 화면은 http://127.0.0.1:15173/#/dashboard 이고 오류는 `MV 마스크 API 404`였다. 이 문자열은 GroundTruthHeatmapPanel의 최초 GET /api/heatmaps/catalog?item=... 실패에서 발생한다. 숫자 배열용 /heatmaps/ground-truth의 데이터 조회 오류와는 다른 단계다. 현재 catalog handler는 미지원 품목에 빈 목록200, 캐시 없으면503, 버전 불일치409를 반환하므로 목록404는 핸들러에 도달하지 못한 라우팅 계층 오류다.

apiProxy는/api만 제거하며 남은경로는 그대로 전달한다. start_gui_readonly.sh의15173 기본대상은18080이다. 실행중인 readonly API가 새 라우터를 읽지 않은 상태 또는 실제 프록시 대상 불일치가 남은 원인 후보다. 실제 Network 본문·운영PID·uvicorn 명령·8000/8080 listen은 샌드박스에서 보이지 않아 어느 프로세스가 낡았는지는 확정하지 않았다. 현재 소스의 app.api,app.readonly_api,app.spatial_preview OpenAPI에는 신규4개 heatmaps 경로가 실제 등록됨을 확인했다.

## 실제 수정

- inspection-gui/mvApiBridge.mjs, .d.mts와 vite.config.ts: 해당15173 개발 화면에서 MV GET만 기존 Python API handler로 전달. 나머지 프록시는 유지. model·DB startup 없음. reader 최대2개, 요청 취소시 해당reader만 종료.
- scripts/mv_api_bridge.py: 등록된 읽기 경로만 실행하는 transport. 수치계산은 기존 ground_truth_api를 사용. 파일근거는 기존 id/루트/SHA 검증을 통과한 경우만 반환.
- src/api/mvRead.ts, GroundTruthHeatmapPanel: HTTP method·실제URL·status·본문을 표시. 경로 미등록404와 데이터범위404를 구분. Mock fallback 없음.
- SpatialInspectionPage/store: 대표 품목 전환시 불필요한 중앙 검수통계 요청을 생략하고 이전 품목 요청을 무효화한다.

기존 중앙 API,18080,8000/8080,추론,백필,동기화 프로세스를 중단/재시작하지 않았다. 데이터·스키마·판정·퓨전·모델 설정을 수정하지 않았다. Vite 개발설정의 자동 재적용은 가능하나 사용자 호스트의 재적용 여부는 직접 확인하지 못했다.

## 실데이터 결과

middleware→실제Python API→실제캐시 연결검사:

| item/view/split | status | 배열 | 제공 마스크 분모 | unknown | 서로다른 셀값 |
|---|---:|---|---:|---:|---:|
| toothbrush/C1/train |200|64×64=4096|335|37|35|
| zipper/C1/train |200|64×64=4096|367|0|112|

원본JPEG도348,330/562,978 bytes를 stream으로 확인. /tmp 작업경로에서의 reader도200/catalog10항목으로 성공. 단순빈배열/단일수치복제가 아니다. 증거: reports/gui_validation/spatial-urgent/vite-mv-bridge-validation.json, mv-loader-cwd-check.json. 이는 TCP 없는 실제 middleware/reader 통합검사이며 운영HTTP 검증과 구분한다.

## 데이터 경로

원본: /home/geonug/MV/outputs/windows_preserved_20261111_v1/{presence_count,occupancy_known,occupancy_positive,observation_count,area_fraction_sum}.npy. 원본560그룹64². adapter 캐시: /home/geonug/agent/reports/ground_truth_heatmaps. 원래 생성코드: /home/geonug/MV/mv_analysis/presence_heatmaps.py. 원래coarse_occupancy 재사용. Train NG조건부 분포이며 Test/운영전체불량률이 아니다.

## 화면 확인

http://127.0.0.1:15173/#/dashboard 를 Ctrl+Shift+R로 새로고침하고 Network의 /api/heatmaps/catalog 응답과 X-MV-Transport: vite-local-existing-asgi-routes를 확인한다. 칫솔/지퍼·C1–C5·개별/집계 모드, 지퍼 개별C2 unknown을 확인한다. 중앙 팀원용 API는 최신소스 배포가 별도로 필요할 수 있다. 중앙재시작 승인은 불명확하고 환경검증도 남아 있어 재시작하지 않았다.

브라우저 소켓 EPERM으로 신규 GUI 스크린샷은 촬영하지 못했다. 개발용 실제 마스크/배열/RT 위치 비교이미지는 reports/gui_validation/spatial-urgent/mv-mask-native-grid-model-comparison.jpg이며 직접 검토했다. 브라우저스크린샷이나3D표면구현완료증거로 사용하지 않는다.

## 회귀

Python전체128 passed/4 skipped. 프런트131 passed/22파일, ESLint·TS·Build 통과(6.30s). Token HEX위반0, 보호된추론/config 해시동일. 기타 chunk500kB경고는 남아 있다. 신규패키지 설치 없음.

## 남은 문제

사용자 호스트의 실제 새로고침 결과·브라우저 Network·8000/8080프로세스·외부팀원주소는 미검증. 현재3D UV는 칫솔모에서 동일좌표가최대392위치에 반복되므로 물리표면 Texture는 활성화하지 않았다. 2D 실데이터지도와 기존부위집계모드를 구분한다. 운영반영전 호스트검증과 정확한 프로세스 식별/재시작 승인범위를 확인해야 한다.
