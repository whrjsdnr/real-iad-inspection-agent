# AI 에이전트 설계

## 구조
- LLM: Ollama `qwen25-cpu:latest`(로컬). 래퍼: 루트 `agent.py`, API 진입: `app/api.py`의 `/tools`·챗봇 경로.
- 도구 레지스트리: `app/tools.py`의 `TOOL_FUNCS` + `TOOL_SCHEMAS`(OpenAI 함수호출 형식).
- 시스템 지시: 수치는 분자/분모와 출처를 함께 제시하고, 도구 근거 없는 수치 생성 금지.

## 도구 목록(읽기 중심)
- `query_error_stats` — 오류 통계(부위·품목·기간 필터)
- `compute_inspection_metrics` — 확정/의심 지표 재계산
- `get_case_evidence` — 사례 근거 이미지·박스
- `get_training_status` — 적재/동기화 상태
- `get_final_performance` — 최종 성능 JSON(파일 로더)
- `query_spatial_evidence` — 공간 근거 조회

읽기전용 개발 게이트웨이(`app/readonly_api.py`)는 위 도구 중 읽기만 허용하고 나머지는 403으로 거절한다.

## 실행 흐름
1. 사용자 질문 수신 → Ollama에 스키마와 함께 전송.
2. 모델이 도구 선택 → 서버가 `TOOL_FUNCS` 실행 → 결과를 대화에 주입.
3. 답변에 근거 링크 포함 시 GUI 대시보드 라우팅.

## 오류 처리
- 도구 실행 실패는 사용자에게 숨기지 않고 실패 사유를 명시.
- 검수 저장은 expected_version 낙관적 잠금 — 충돌 시 HTTP 409.
- Ollama 미기동 시 목 모드 폭백 + "목 모드" 배지.

## 검증 상태
- 직접 도구 조회·ASGI 호출은 통과. 실제 Qwen 대화 루프·장시간 안정성은 미검증(과거 APITimeout 기록).
- 관련 보고: `AGENT_GUI_INTEGRATION_REPORT.md`, `E2E_VALIDATION.md`(절차), `DASHBOARD_DATA_CONTRACT.md`.
