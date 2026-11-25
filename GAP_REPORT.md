# Phase 0 갭 리포트 — ~/agent 점검 + 기획 스펙 대조

작성: 2026-11-23 / 대상: `~/agent` (제조 외관검사 조회·집계·근거 도구 + inspection-gui)

## 1. 현재 구조 정리

```
~/agent
├── app/                    # FastAPI 백엔드 (도구 API)
│   ├── db.py               # SQLAlchemy SQLite 접근 (DATABASE_URL 환경변수, 지연 초기화)
│   ├── models.py           # 테이블 4개: inspection_attempts / inspection_views / findings / reviews
│   ├── tools.py            # 도구 4개 + Ollama tool-calling 스키마 (682행)
│   ├── rois.py             # ROI LUT (코드 내 하드코딩, mapping_version=roi-lut-v1, 이미지 640x480 가정)
│   ├── providers/base.py   # AnomalyProvider / DefectProvider Protocol
│   ├── providers/mock.py   # deterministic mock (seed 고정, 오차맵=노이즈+가우시안 blob)
│   ├── seed_mock.py        # mock 시딩 (toothbrush 24 + toy 16 제품, 검수 시나리오)
│   └── api.py              # FastAPI: GET /health /tools, POST /tools/{tool_name}
├── agent.py                # Ollama Qwen 에이전트 (OpenAI 호환 API, 도구 호출 루프, 최대 5회)
├── Modelfile               # FROM qwen2.5:3b (qwen25-cpu)
├── inspection.db           # SQLite (mock 데이터: attempts 40, views 198, findings 49, reviews 120)
├── tests/                  # pytest (test_heatmap_extract 등)
├── pyproject.toml          # fastapi/uvicorn/sqlalchemy/pydantic/numpy/opencv/openai/pytest
└── inspection-gui/         # Vite + React 18 + TypeScript + R3F/three + zustand + tailwind
    └── src/
        ├── three/Scene.tsx # 3D 캔버스: 절차형 부위 메시, 히트 컬러링, OrbitControls, 클릭 선택
        ├── three/parts.ts  # PartDef (toothbrush: handle/neck/bristle, toy …) — GLB 교체 포인트
        ├── components/     # TopBar(필터) / LeftPanel(3D) / CenterPanel / RightPanel(사례) / CaseViewer
        ├── fixtures/       # 백엔드 없을 때 동일 스키마 fixture (toothbrush/toy)
        ├── api/client.ts   # /tools/* 클라이언트 (fixture 폐백)
        └── store.ts        # zustand 상태 (필터/선택/카드)
```

**사용 스택**: Python 3.12(FastAPI+SQLAlchemy+SQLite) / Ollama(qwen25-cpu, OpenAI 호환 로컬) /
Node 20 + pnpm + Vite + React + react-three-fiber + three + zustand + tailwind(+vitest/eslint).

**챗봇 구현 방식**: 이미 "실제 도구 호출" 단계다. agent.py가 Ollama Qwen에게 TOOL_SCHEMAS를 주고
도구 호출 루프를 돌린다(최대 5회). 목데이터는 providers/mock.py + fixtures/*.json(프론트 폐백)이며,
`mock://` URI로 표기된다. 응답 생성은 LLM(도구 결과 JSON 기반), 추측 답변 금지 프롬프트는 부분 적용.

**GUI 유무**: 있다(inspection-gui). 다크 대시보드 톤, 3D 부위 지도 + 히트 컬러링 + 부위 클릭 →
우측 사례 카드 + C1~C5 뷰어까지 구현됨.

**환경**: Ollama 설치+실행 중(`qwen25-cpu:latest` 1.9GB 보유). node/pnpm/npm 사용 가능.

## 2. 기획 스펙 대조 갭 리스트

### 2-1. 이미 있는 것 (재사용)
| 스펙 요구 | 현재 자산 |
|---|---|
| 도구 기반 LLM 에이전트(Ollama Qwen, 로컬) | agent.py + tools.py (TOOL_SCHEMAS) |
| 도구 4개 중 2개: 오류 통계 조회 / 사례 근거 조회 | query_error_stats / get_case_evidence (분자/분모 반환) |
| DB (SQLite) + 검사 기록 연결 | attempts/views/findings/reviews 4테이블 + mock 시딩 |
| 부위 매핑(ROI→part_id) | rois.py map_bbox_to_part (LUT 방식) |
| 3D 부위 지도 + 히트 컬러링 + 클릭 → 2D 근거/C1–C5 | Scene.tsx + parts.ts + RightPanel/CaseViewer |
| 상단 필터(품목/지표/기간/모델 기준선) | TopBar (품목/지표/기간/모델버전/검수상태) |
| 분자/분모 지표 4종(확정 불량률·부위 미탐·부위 오탐·촬영처리실패율) | tools.py metrics-v1 (confirmed만 집계) |
| 단위 테스트 | tests/ (pytest + vitest) |

### 2-2. 스펙과 다른 것 (수정 필요 — 기존 동작 유지 전제)
1. **도구 4개 구성이 다르다.** 스펙: 오류통계조회 / 사례근거조회 / **검수 요청(대기 기록)** / **학습 상태 조회**.
   현재: extract_abnormal_locations / compute_inspection_metrics / query_error_stats / get_case_evidence.
   → 기존 4개는 유지(GUI가 씀)하고 `request_review`(pending 등록), `get_training_status`(승인 표본 수·후보 비교·작업 상태)를 **추가**한다.
2. **테이블 명세 차이.** 스펙: products(판정/검수상태), views, evidences(종류 rtdetr_box/hvq_score/hvq_map, 맵 경로), reviews(수정 라벨/FP·FN 확정), **metrics_snapshots**.
   현재: attempts(판정·검수상태 컬럼 없음), views(≡), findings(kind/map_uri 없음), reviews(FP/FN 확정·수정 라벨 없음), snapshots 없음.
   → **가가적 마이그레이션**: attempts += verdict/review_status, findings += kind/map_uri, reviews += fp_fn/corrected_label, **metrics_snapshots 신규 생성**. 기존 컬럼·mock 데이터는 그대로.
3. **판정 규칙·임계값·ROI가 코드에 하드코딩.** 스펙: 전부 설정 파일.
   → `~/agent/config/fusion.json`(퓨전 규칙·RT conf·HVQ 임계값 소스), `~/agent/config/parts_roi.json`(품목·카AMERA별 ROI) 신규. rois.py는 LUT 파일을 읽도록 유지(기본값=기존 LUT). ROI 정의 없는 품목은 "unknown" 집계 후 리포트 명시(스펙 동일).
4. **지표 추가.** 스펙: 제품 단위 Recall/FPR/F1(분모 명시), AUPRO(GT 마스크 시), 5시점 처리 비용(p95·피크 메모리, 기존 벤치마크 재사용), 의심 건수 vs 확정 구분, **snapshots 영속화**.
   → tools.py compute_inspection_metrics 확장(Recall/FPR/F1 + 스냅샷 저장), metrics.py 신규(계산+CLI/API), AUPRO는 GT 마스크 있는 사례만.
5. **LLM 폐백.** 스펙: Ollama 미실행 시 목 모드 + 상단 "목 모드" 표시. 현재 agent.py는 Ollama 다운 시 예외로 죽음.
   → agent.py에 연결 확인 후 mock 응답 경로 추가(기존 대화형 유지), GUI config에 mock_mode 노출.
6. **GUI에 챗봇 패널·검수 모드(박스 추가/수정/승인) 없음.** TopBar/RightPanel는 조회만.
   → RightPanel에 챗봇 패널(백엔드 /chat 프록시 또는 agent 라이브러리 호출), CaseViewer에 검수 편집(박스 CRUD → reviews 반영 → 지표 재계산 트리거) 추가.

### 2-3. 없는 것 (신규 구축)
1. **퓨전 배치 러너**: 12만 장(Real-IAD dataset/, 현재 151,050장 jpg · 51,329장 GT 마스크 png)을
   제품 ID 단위(C1–C5 묶음)로 두 모델 추론. → `~/agent/batch_fusion.py` + `~/agent/fusion.py`.
   - 제품 ID 규칙: `dataset/<품목>/<OK|NG>/<결함>/<S####>/<품목>_<일련>_..._C<n>_<타임스탬프>.jpg`
     → product_id = `<품목>_<일련>` (예: toothbrush_0080, C1–C5 공유).
   - 모델: RT-DETR FP32 ONNX(graph ALL, rtdetr_outputs/epoch_0015_640.onnx) + HVQ FP16 ONNX
     (hvq_outputs/hvq_best.fp16io.onnx) — 둘 다 검증된 최적 구성.
   - HVQ 임계값: hvq_best.pt 내 validation.threshold(카테고리별, 학습 검증 근거) 사용 — 별도 튜닝 불필요, 근거 기록.
   - 실행 venv: inference/.venv(모델 의존). DB 쓰기는 표준 sqlite3(agent venv와 호환).
   - 재시작 가능(완료 제품 스킵), 진행률·ETA·처리량, 실패 사유 기록, Ctrl+C 후 이어서 동작.
2. **제품 판정 규칙(정상/불량/보류)**: 둘 다 양성→불량, 둘 다 음성→정상, 엇갈림→보류 (설정 파일).
3. **Recall/FPR/F1 + AUPRO 계산** 및 합성 20개 제품 단위 테스트(tests/test_metrics_fusion.py).
4. **챗봇 목 모드** 자동 폐백 + "목 모드" 표기.
5. **검수 요청/학습 상태 조회 도구** + 백엔드 /chat 엔드포인트(GUI 챗봇 패널용).

## 3. 데이터 확인 사항
- Real-IAD `dataset/`: 151,050장 jpg / 51,329장 png(GT 마스크) / 30개 품목.
  품목별 예: toothbrush 5,005장(≈1,001 제품×5시점). 파일명에 C1–C5 시점 표기 확인.
- 품목=칫솔(toothbrush) GUI 기본 필터와 호환. ROI는 미정의 → "unknown" 집계로 시작(스펙 동일).
- GT 마스크: NG 결함 이미지에 한해 존재 → AUPRO는 이들 사례로만 계산.

## 4. 리스크·주의
- **처리 비용**: RT-DETR ~0.3s + HVQ ~0.07s/장 → 전량 약 13시간(CPU 단일 프로세스 기준, 배치·스레드 튜닝 시 단축).
  파일럿 100개 제품(500장)으로 실측 후 ETA 보고 → 전량은 재개 가능한 백그라운드 잡으로 지속.
- ~/agent 기존 파일은 **추가·호환 변경만**(삭제/대체 금지). rois.py/tools.py/agent.py는 기존 함수 시그니처 유지.
- 기존 mock 파이프라인(seed_mock→API→GUI fixture)은 실데이터 퓨전과 **병행** 동작하도록
  model_version으로 구분(mock-anomaly-v1 vs 실모델 버전).
- "기존 코드 삭제/대체" 결정 불요 — 전부 추가 설계로 진행 가능. 사용자 확인 없이 Phase 1~4 진행.
