# 제조 외관검사 조회·집계·근거 도구

5시점(C1~C5) RGB 제조 외관검사 GUI/LLM 에이전트가 공통으로 쓰는 도구 세트.
하부 이상탐지/불량탐지 모델 대신 교체 가능한 provider 인터페이스 + deterministic mock을 사용한다.
LLM은 Ollama 로컬 Qwen만 사용하고, SQL을 직접 만들지 않으며 검증된 도구 4개만 호출한다.

## 구성

```
app/
  db.py              # SQLite 접근 (DATABASE_URL 변경 가능)
  models.py          # inspection_attempts / inspection_views / findings / reviews
  rois.py            # ROI LUT (camera_id + 픽셀 bbox -> part_id), mapping_version=roi-lut-v1
  providers/base.py  # AnomalyProvider, DefectProvider Protocol
  providers/mock.py  # deterministic mock (seed 고정)
  tools.py           # 도구 4개 + Ollama/Qwen tool calling JSON schema (TOOL_SCHEMAS)
  seed_mock.py       # mock 데이터 시딩 (python -m app.seed_mock)
  api.py             # FastAPI (POST /tools/{tool_name}, GET /health, GET /tools)
tests/               # test_metrics / test_stats_chain / test_heatmap_extract
agent.py             # Ollama Qwen 에이전트 (도구 4개만 호출)
```

## 지표 정의 (definition_version=metrics-v1)

| 지표 | 정의 | 분자 / 분모 |
|---|---|---|
| confirmed_defect_rate | 불량 확인 제품 / 부위 검수 제품 | 검수 확정 중 truth=defect / 검수 확정 전체 |
| part_miss_rate | 놓친 불량 제품 / 부위 불량 확인 제품 | 불량 확인 중 finding 없음(모델 미검출) / 불량 확인 |
| part_false_alarm_rate | 잘못 경보한 정상 제품 / 부위 정상 제품 | 정상 확인 중 finding 있음 / 정상 확인 |
| capture_process_failure_rate | 누락·흐림·추론 오류 / 시도 건수 | status가 capture_missing·capture_blurred·inference_error / 시도 전체 |

- 집계 최소 단위: product_id × item × part_id × camera_id × model_version × mapping_version
- 분모 0이면 `rate=null`, `reason="denominator_zero"`
- pending과 confirmed를 섞지 않는다 (`review_state`로 구분)

## 설치·실행

```bash
uv init --bare
uv python pin 3.12
uv add fastapi uvicorn sqlalchemy pydantic numpy opencv-python pytest

uv run python -m app.seed_mock                       # mock 데이터 시딩 (inspection.db)
uv run uvicorn app.api:app --reload --port 8080      # 도구 API
OLLAMA_MODEL=qwen25-cpu uv run python agent.py       # LLM 에이전트 (대화형)
uv run pytest                                        # 테스트
```

Ollama 모델은 `Modelfile`(`qwen2.5:3b`)로 만든 `qwen25-cpu`를 기본으로 한다.
`OLLAMA_BASE_URL`(기본 `http://localhost:11434/v1`), `OLLAMA_MODEL`로 변경 가능.

## 도구 4개 (app/tools.py)

GUI와 LLM이 모두 `POST /tools/{tool_name}`으로 호출한다.

- `extract_abnormal_locations(product_id, camera_id, source, threshold_mode="p99", min_area_px=24)`
  - mock 오차 맵에서 threshold(p95/p99/fixed) → morphology → connected components → min_area_px 필터로 영역 추출
  - ROI LUT으로 part_id 매핑 후 findings에 저장
  - 반환: regions[] (region_id, part_id, bbox, centroid, area_px, score, evidence.image_uri/error_map_uri, model_version, mapping_version)
- `compute_inspection_metrics(item, part_id=None, camera_id=None, date_from, date_to, model_version, review_state="confirmed")`
  - 4개 지표 각각 num/den/rate/reason + filters, definition_version="metrics-v1"
- `query_error_stats(item, metric, group_by, date_from=None, date_to=None, model_version=None, min_denominator=1, order="desc", limit=10)`
  - rows[]: group key, num/den/rate, stat_key(필터를 모두 포함한 stable JSON string)
- `get_case_evidence(stat_key=None, product_id=None, part_id=None, camera_id=None, limit=20)`
  - 검수 기반 지표는 분모 집합(불량 확인/정상 확인 제품), capture 지표는 오류 시도 집합을 연다
  - cases[]: product_id, item, part_id, camera_id, truth_label, prediction, model_version, mapping_version, box_ids, evidence(original_uri/error_map_uri/crop_uri/all_views C1~C5), review(state/reviewer/reason)

Ollama/Qwen tool calling용 스키마는 `app.tools.TOOL_SCHEMAS`에서 export한다.

## API

- `GET /health` — 상태 확인
- `GET /tools` — 도구 목록 + 스키마
- `POST /tools/{tool_name}` — 도구 호출 (본문은 각 도구의 인자 JSON)

에러 응답(내부 스택은 서버 로그에만 남음):

```json
{"error": {"tool": "...", "input_summary": "...", "message": "사용자에게 보여줄 안전한 메시지"}}
```

## provider 교체

`app/providers/base.py`의 `AnomalyProvider`/`DefectProvider` Protocol을 구현한 클래스를 만들고,
`app/providers/mock.py:get_provider()`가 해당 클래스를 반환하도록 바꾼다.
출력에는 반드시 `model_version`, `mapping_version`을 포함해야 한다.

## 주의사항

- mock 이미지/오차맵/크롭은 실제 파일이 아닌 `mock://` URI다 (mock provider 표기).
- 검수 라벨 변경, 모델 교체, 재학습 실행은 범위 외다. 조회와 mock 위치 추출만 제공.
- 민감한 shell 실행 기능은 없다.


## 2026-11-23 재구성 작업 안내

현재현황은 [FUSION_RECOVERY_REPORT.md](FUSION_RECOVERY_REPORT.md)와[STATUS.md](STATUS.md)를확인하세요. 원본퓨전CSV는미확보이며참고성능과실측을분리합니다. `score_batch.py`는 **같은제품C1–C5 batch5** 고정원시점수추론입니다. 미보정품목의자동정상/불량/보류판정은하지않습니다. `reconstruct_fusion.py --help`는검증된Val분할보정CLI입니다. 학습겹침검증없이현재신규추론코호트를보정용으로사용할수없습니다.

환경설정은`.env.example`의키만참고하고실제비밀번호를공유하지마세요. PostgreSQL검증은별도DB에서완료했으며운영DB전환과역할별로그인계정은별도구성해야합니다. `DATABASE_URL_WORKFLOW`는검수API서비스의최소쓰기역할이며`app_review`의권한을확대하지않습니다. 기존8080 API프로세스는임의로종료하지않았으므로변경적용을위한재기동은관리자가진행하세요. 다른PC에서는설정한API호스트/포트만방화벽으로허용하고DB포트를외부에개방하기보다API를공유하세요. 인증·HTTPS가없으면신뢰할수있는팀내망에서만운영합니다.


추론 실행·DB 적재·팀 공유 명령어는 [INFERENCE_DB_SHARING_GUIDE.md](INFERENCE_DB_SHARING_GUIDE.md)를 확인하세요.
