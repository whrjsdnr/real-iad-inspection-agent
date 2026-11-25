# 팀 통합 가이드

## 패키지
- `team_integration_kit/` — 팀 공용 SDK·문서·실제 샘플. `team_integration_kit.zip`으로 배포(649파일, secret scan 통과, `.sha256` 체크섬).
- 생성: `PYTHONPATH=/home/geonug/agent .venv/bin/python scripts/build_team_integration_kit.py`
- 구성: README·QUICKSTART·API_GUIDE·DATA_DICTIONARY·FUSION_CONTRACT·DATA_AVAILABILITY·HEATMAP_GUIDE·THREE_SURFACE_GUIDE, catalogs/, roi/, surface_frames/, three_surface/, examples/(Python·TS 클라이언트), samples/(실제 호출 응답), openapi.json.

## 공유 API(신코드 기준, :18080에서 검증)
- `/sharing/manifest`·`/catalog/parts`·`/roi/templates`·`/products`·`/products/views`·`/products/findings`·`/products/anomaly-map`·`/products/fusion`
- `/heatmaps/catalog`·`/heatmaps/ground-truth`·`/heatmaps/metadata`·`/heatmaps/evidence`·`/heatmaps/surface`·`/heatmaps/surface-layout`
- `/parts/heatmap`·`/parts/evidence/{case}/{cam}`·`/parts/spatial-heatmap`
- `/fusion/runs`·`/performance/final`·`/tools`(읽기 전용)

## 팀원 유형별 진입
- API 팀원: QUICKSTART.md → examples/python_client.py
- 3D SDK 팀원: THREE_SURFACE_GUIDE.md → three_surface/ 런타임(의존성 three)
- GUI/에이전트 팀원: openapi.json 스키마, `/tools` 응답

## 원격 접근 경로
1. **운영 중앙 서버 재배포**(권장): 신코드로 재시작하면 0.0.0.0:8000으로 팀원 접근 가능. 재시작은 사용자 승인 필요.
2. **18081 인증 공유 서비스**: `scripts/setup_team_share.py` + `TEAM_BIND_HOST=0.0.0.0 TEAM_SHARE_PORT=18081 bash scripts/start_team_share.sh`. 토큰만 팀원에게 전달.
3. 개발 게이트웨이(127.0.0.1:18080)는 로컬 전용.

## 주의
- 3D 표면 투영은 승인된 근사 시각화이지 물리 좌표 복원이 아니다(FUSION_CONTRACT·HEATMAP_GUIDE 명시).
- HVQ 원시 맵은 100제품·500시점뿐. 없으면 unsupported로 응답 — 값을 만들지 않는다.
- 비밀정보 검사: ZIP 빌드 시 postgresql URL·개인키·실제 토큰 대조 통과. `config/team-share.env`는 Git 추적 제외.
- 팀 검증 스크립트: `scripts/verify_team_data.py`(ASGI, 토큰 필요).
- 상세: `TEAM_SHARING_GUIDE.md`, `TEAM_DATA_SHARING_REPORT.md`, `INFERENCE_DB_SHARING_GUIDE.md`.
