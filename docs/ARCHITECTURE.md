# 시스템 아키텍처

## 구성 요소와 책임

| 계층 | 모듈 | 역할 |
|---|---|---|
| 중앙 API | `app/api.py` | 운영 FastAPI. 도구 호출·검수·추론 job·마이그레이션·recompute 워커 |
| 개발 게이트웨이 | `app/readonly_api.py` | DATABASE_URL_READ 전용, 트랜잭션 READ ONLY. 기존 서비스와 무관하게 신코드 검증 |
| 공유 API | `app/shared_data_api.py` | 제품/박스/실제 이상맵/ROI/부위 카탈로그 |
| 부위 히트맵 | `app/part_heatmap.py`, `app/part_api.py` | 원본 픽셀 폴리곤 ROI에 저장 근거를 배정해 부위별 num/den 집계 |
| 공간·표면 | `app/spatial_api.py`, `app/ground_truth_api.py`, `app/surface_api.py` | 저장 박스→ROI 좌표 32² 격자, 마스크 64², 3D 표면용 배열 |
| 팀 공유 | `app/team_api.py` | Bearer 토큰 인증 공유 서비스(18081), shared_openapi()로 킷 OpenAPI 생성 |
| 퓨전 | `app/gui_fusion.py`, `app/gui_inference.py` | 계약 v2 분기(정규화·TH·margin·판정 근거) |
| 상태·성능 | `app/status.py` | final_performance 로더(신보고서 우선·해시 검사) |
| 에이전트 | `agent.py`, `app/tools.py` | Ollama qwen25-cpu 도구 호출 루프, TOOL_SCHEMAS 레지스트리 |
| 작업 큐 | `app/jobs.py`, `app/job_api.py` | 영속 JobStore, Idempotency-Key, CAS 전이, 단일 워커 |
| GUI | `inspection-gui/src` | zustand 스토어·R3F Scene·tokens.css 디자인 토큰 |

## 데이터 흐름

1. `~/MV` 추론 산출 `scores.sqlite` → `import_score_batch.py`가 PostgreSQL `inspection` DB에 적재(현재도 배치 실행 중일 수 있음).
2. `scripts/activate_fusion_contract_v2.py`가 저장 점수로 24,000제품을 계약 v2로 재판정해 `fusion_analysis.model_runs`에 새 run 등록(구 run 보존).
3. API/챗봇/GUI는 읽기 전용으로 DB·파생 캐시를 조회한다.
4. `scripts/build_team_integration_kit.py`가 공유 API에서 카탈로그·OpenAPI·샘플을 추출해 ZIP을 만들고 secret scan을 수행한다.

## 배포 상태(2026-11-25)

- 운영 `:8000`(uvicorn app.api): **구 코드** — 공유 API 경로 404. 신코드 배포 재시작은 사용자 승인 대기.
- 개발 게이트웨이 `:18080`: 신코드 기동 중, 공유 API 전부 실응답 확인.
- Vite `:15173`(127.0.0.1): GUI 개발 서버, mv_api_bridge 연결.
- 팀 공유 `:18081`: 인증 서비스, 기동 명령은 TEAM_SHARING_GUIDE.md(승인 후 실행).

자세한 스키마는 `SCHEMA.md`, DB 이관은 `POSTGRESQL_PHASE3_PREPARATION.md` 참조.
