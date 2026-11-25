# 문제 해결(Troubleshooting)

| 증상 | 원인 | 조치 |
|---|---|---|
| 공유 API 404(운영:8000) | 운영 프로세스가 구 코드 | 개발 게이트웨이(:18080)로 확인, 운영 재배포는 승인 후 |
| GUI "연결 실패" | API 프로세스 다운/CORS | readonly 게이트웨이 기동 확인, backoff 재시도 후 목 모드 배지 |
| 추론 중 API 무응답 | 단일 워커 동기 대기 | 비동기 JobStore 패턴 사용(POST job → GET 폼), /health는 경량 유지 |
| 409 Conflict | 검수 낙관적 잠금 충돌 | 최신 version으로 재조회 후 재시도 |
| 503 | 저장 캐시 없음 | `scripts/derive_spatial_heatmaps.py --all-registered`(추론 없음) |
| 422 | 파라미터 오류 | OpenAPI 스키마 확인(product_id는 query, URL 인코딩) |
| HVQ 맵이 안 나옴 | 해당 제품 맵 미저장(100제품 한정) | `/products?maps_only=true`로 지원 제품 조회. 스칼라로 대체 금지 |
| Ollama 응답 없음 | 서비스 미기동 | `ollama serve`·모델 pull 확인. 목 모드로 폭백 |
| ROI 오버레이 어긋남 | 이미지 해시 불일치/좌표계 혼용 | 원본 픽셀 좌표 기준 재등록, reports/part_heatmap 오버레이로 육안 확인 |
| pytest DB 오염 | 전역 DATABASE_URL을 운영으로 설정 | 테스트는 별도 SQLite 사용(conftest 강제) |

로그 위치: 개발 게이트웨이 `/tmp/inspection-gui-readonly-api.log`, GUI 검증 로그 `reports/gui_validation/*/`.
상세 이력: `MV_MASK_API_404_FIX_REPORT.md`, `API_CONNECTION_FIX.md`, `FINAL_PERFORMANCE_SYNC_REPORT.md`, `POSTGRES_VALIDATION.md`.
