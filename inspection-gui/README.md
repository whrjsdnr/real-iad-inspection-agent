# inspection-gui — 5시점 제조 외관검사 3D 오류 진단 GUI

데스크톱 우선의 다크 산업 대시보드. 중앙 3D 부위 지도에서 이상이 많은 부위를 히트맵으로 보고,
부위를 클릭하면 우측 패널에 2D 근거(사례 + C1~C5 뷰)를 연다.
백엔드 도구 API가 없으면 동일 스키마의 fixture로 동작하며, FastAPI `/tools/*`가 뜨면 그대로 교체한다.

## 실행

```bash
pnpm i
pnpm dev          # http://localhost:5173
```

기타 명령: `pnpm build` (tsc + vite 빌드), `pnpm lint` (eslint), `pnpm test` (vitest).

Node 20+ / pnpm 권장(개발은 Node 20.18, pnpm 9.15로 검증).

## 백엔드 연결

상위 프로젝트의 FastAPI 도구 API를 띄운 뒤 GUI를 연결한다.

```bash
# 저장소 루트에서
uv run python -m app.seed_mock
uv run uvicorn app.api:app --port 8080

# inspection-gui에서 (기본값 /api가 Vite 프록시로 연결)
pnpm dev
```

환경 변수(`.env` 또는 셸 export):

- `VITE_API_BASE` — 도구 API 베이스. 기본 `/api` (Vite가 GUI_API_TARGET, 기본 http://127.0.0.1:8080으로 프록시).
- `VITE_USE_FIXTURE=true` — 네트워크 없이 `src/fixtures/*.json`만 사용. 상단에 FIXTURE 배지 표시.

동작 규칙:

- `VITE_USE_FIXTURE=true` → 항상 fixture, FIXTURE 배지.
- API 모드에서 호출 실패 → 자동으로 fixture로 폭백하고, 상단에 `FIXTURE 폭백` 배지와 amber 경고 배너(원인 포함)를 표시.
- 지표 숫자(num/den/rate)는 프론트에서 재계산하지 않고 API/fixture 응답을 그대로 표시한다.

## 화면 구성

- 상단 바: 제품(사례 기준 동적 목록), 품목(toothbrush/toy), 지표(4개), 기간, model_version, review_state(confirmed/pending/all), 소스 배지.
- 좌측: 지표 정의(분자/분모 문구), 키보드 탐색 가능한 부위 목록(Tab/Enter, 3D 클릭과 동일), 해석 주의 경고.
- 중앙: 3D 부위 지도.
  - 히트 색상 = 선택 지표의 rate(검수 확정 기준). 낮음=차가운 색 → 높음=amber/red.
  - 분모 0 → 회색 + wireframe overlay. 분모 < 10 → 흐리게 + “분모가 작아 해석 주의” 배지.
  - hover 시 part_id와 num/den/rate 툴팁, 클릭 시 선택 + 칩메라 부드럽게 이동(damping) + 우측 패널 갱신.
  - capture_process_failure_rate는 “시도 건수 기준”이라 부위 지도 미지원 → 안내 카드와 우측 카드/사례로만 확인.
- 우측: 선택 part의 지표 카드 4개(num/den/rate, rate=null이면 “분모 없음”), 사례 리스트(get_case_evidence).
  - review_state=pending/all이면 “검수 전 의심 포함” 경고. all일 때는 카드 헤더의 [확정|검수 전] 토글로 한 번에 하나의 상태만 표시(섞지 않음).
- 사례 클릭 → 근거 뷰어(모달): C1~C5 시점 탭, 원본/오차 맵/크롭 전환. 실제 이미지가 없으면 “근거 이미지 없음” 상태와 URI를 명확히 표시. Esc로 닫기.

## API 계약 (기존 도구 스키마 그대로)

- `POST /tools/query_error_stats` — `{item, metric, group_by:[part_id], date_from, date_to, model_version, ...}` → `rows[] {group, num, den, rate, reason, stat_key}`
- `POST /tools/compute_inspection_metrics` — `{item, part_id?, date_from, date_to, model_version, review_state}` → `metrics{4개 각 num/den/rate/reason}`
- `POST /tools/get_case_evidence` — `{stat_key}` 또는 `{product_id, part_id, camera_id}` → `cases[]`(all_views C1~C5, box_ids, model/mapping_version 등)
- `POST /tools/extract_abnormal_locations` — GUI는 현재 미사용(향후 위치 추출 화면용)

stat_key는 rows에서 사례 조회까지 그대로 이어지도록 유지한다(추후 LLM이 같은 API를 쓸 수 있게).

## 구조

```
src/
  config.ts            # 상수(지표 정의, MIN_DENOMINATOR, API_BASE, USE_FIXTURE)
  types.ts             # 백엔드 응답 스키마 동치 타입
  api/client.ts        # fetch 래퍼 + fixture 폭백
  fixtures/*.json      # 품목별 숫자/사례 뼈대 (toothbrush: bristle이 최악 6/40=15%)
  fixtures/loader.ts   # stat_key 조립, all_views 확장, fixture 응답 생성
  store.ts             # zustand: 필터/통계 캐시/선택/사례/뷰어 상태
  three/parts.ts       # PartDef + 파라메트릭 placeholder (GLB 교체 포인트)
  three/Scene.tsx      # R3F 씬(조명, ContactShadows, OrbitControls, tooltip, CameraRig)
  utils/heat.ts        # rate→색상, 분모 0/해석 주의 포맷
  components/          # TopBar, LeftPanel, CenterPanel, RightPanel, CaseViewer, bits
```

### GLB로 교체하기

`src/three/parts.ts`의 `PartDef.makeGeometry`를 GLB 로드 결과로 바꾸면 된다.
part_id/label/position 계약만 유지하면 히트맵·선택·근거 연동은 그대로 동작한다.

## 테스트

```bash
pnpm test   # vitest: heat 색상 매핑, 분모 0 처리, stat_key→사례 fixture 연결
```

## 수동 체크리스트 (Playwright 미사용 시)

1. 초기 화면(toothbrush · part_miss_rate · confirmed): bristle이 가장 뜨겁게(amber 쪽) 표시되고 상단에 FIXTURE 또는 API 배지가 보인다.
2. 품목을 toy로 변경: 3D가 surface/edge/joint로 바뀌고, edge는 분모 0으로 회색+wireframe, “분모 없음”이 표시된다.
3. 부위 클릭(bristle): 칩메라가 이동하고 우측에 미탐 6/40 · 15.0% 카드와 사례 리스트가 뜬다.
4. 사례 카드 클릭: C1~C5 탭과 원본/오차 맵/크롭 전환이 동작하고, 이미지가 없으면 “근거 이미지 없음” 상태가 보인다.
5. 지표를 capture로 변경: 3D가 “부위 지도 미지원” 안내로 바뀌고 “시도 건수 기준” 배지가 붙는다.
6. review_state를 pending/all로 변경: “검수 전 의심 포함” 경고가 뜨고, all이면 카드 [확정|검수 전] 토글이 동작한다.
7. 백엔드를 끈 상태(API 모드): 상단에 FIXTURE 폭백 배지와 경고 배너가 표시되고 화면은 fixture로 동작한다.
8. 기간/모델 버전 변경: 히트맵이 재조회되고(캐시 히트 시 즉시) stat_key가 그에 맞게 바뀐다.
9. 1280px 미만 축소: 우측 패널이 아래로 날아가고 3D 뷰가 55vh 이상 유지된다.
10. 키보드: Tab으로 부위 목록/칩 이동, Enter로 선택(3D 클릭과 동일), Esc로 뷰어 닫기.

## 개발 API 연결 (운영 서버 설정 변경 없음)

`npm run dev` / `npm run preview`는 `/api/*`를 기존 API로 전달합니다. `GUI_API_TARGET=http://127.0.0.1:8080`이 기본이며 필요하면 시작할 때 지정합니다. 브라우저는 같은 origin으로 요청하므로 CORS preflight가 필요하지 않습니다. `VITE_API_BASE`를 직접 URL로 설정하면 프록시를 우회하므로 기존 CORS 제한이 적용됩니다. 정적 배포에는 같은 `/api` reverse proxy가 별도로 필요합니다. 이 변경은 운영 API를 시작하거나 재시작하지 않습니다. 백엔드 자체가 중지된 경우 프록시만으로 복구되지 않습니다.
