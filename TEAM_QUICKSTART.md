# TEAM_QUICKSTART — 팀원 10분 시작 가이드

이 프로젝트의 기존 구조를 몰라도 아래 절차대로 따라하면 중앙 데이터와 SDK를 바로 쓸 수 있습니다.
전제: 담당자로부터 **공유 토큰**을 별도로 전달받았습니다. 토큰은 커밋·메신저·코드에 넣지 마세요.

## 1. 중앙 서버 접속 확인
```bash
curl -m 8 -o /dev/null -w "%{http_code}\n" http://192.168.20.164:8000/health        # 200 기대
```
Windows PowerShell: `Invoke-RestMethod http://192.168.20.164:8000/health`
접근 허용 IP: 192.168.20.170 / .209 / .168(방화벽 정책). 다른 IP면 담당자에게 요청.

## 2. 인증 설정(팀 공유 API 전용)
```bash
export TEAM_API_URL='http://192.168.20.164:18081/api'
export TEAM_ACCESS_TOKEN='<담당자가 전달한 토큰>'
```
중앙 :8000은 팀 낮에서는 인증 없이 조회 가능(읽기 위주). :18081은 반드시 Bearer 인증.

## 3. API 명세 확인
- Swagger: http://192.168.20.164:8000/docs (신코드 전체 경로)
- 공유 서비스 스키마: `TEAM_API_URL/openapi.json` (Bearer 인증)
- 킷의 `openapi.json`·`API_GUIDE.md`도 동일 계약입니다.

## 4. 실제 검사 데이터 조회
```bash
curl -s -H "Authorization: Bearer $TEAM_ACCESS_TOKEN" "$TEAM_API_URL/sharing/manifest"        # 30품목/24,000제품/120,000시점
curl -s -H "Authorization: Bearer $TEAM_ACCESS_TOKEN" "$TEAM_API_URL/products?item=toothbrush&limit=2"
curl -s -H "Authorization: Bearer $TEAM_ACCESS_TOKEN" "$TEAM_API_URL/products/findings?product_id=toothbrush%2FNG%2FCH%2FS0001&view=C1&min_confidence=0.4"
```
제품 ID에 `/`가 있으므로 반드시 query parameter + URL 인코딩을 쓰세요.

## 5. 공유 ZIP 다운로드
- Release: https://github.com/whrjsdnr/real-iad-inspection-agent/releases/tag/v1.0.0 (Private — 멤버 초대 필요)
- 또는 서버: `curl -O http://192.168.20.164:8000/sharing/kit` → `unzip -t`와 `.sha256`으로 무결성 확인

## 6. Python 클라이언트 실행
```bash
cd team_integration_kit
python examples/python_client.py    # manifest → 제품 목록 → 실제 32² 공간 배열까지 자동 확인
```

## 7. Three.js SDK 적용
- `three_surface/` 모듈을 프로젝트에 복사(의존성: three).
- `THREE_SURFACE_GUIDE.md`대로 DataTexture+ShaderMaterial로 제품 표면에 수치 배열을 입힙니다.
- `surface_frames/`의 실제 32² 배열로 먼저 동작 확인.

## 8. 3D 히트맵 생성(직접 계산 경로)
```bash
curl -s -H "Authorization: Bearer $TEAM_ACCESS_TOKEN" \
  "$TEAM_API_URL/parts/spatial-heatmap?item=toothbrush&product_id=toothbrush%2FNG%2FCH%2FS0001&view=C1&region_id=bristle&model=rt&resolution=32&method=confidence_area"
```
`values`(1024개=32×32), `observation_counts`, `coverage_mask`를 받아 row-major로 그리드에 표시.

## 9. AI 에이전트 도구 연동
```bash
curl -s -X POST http://192.168.20.164:8000/tools/query_error_stats \
  -H 'Content-Type: application/json' \
  -d '{"item":"toothbrush","metric":"part_miss_rate","group_by":["part_id"]}'
```
도구 목록·스키마: `GET /tools`. GUI 챗봇 라우트: `/#/chat`.

## 10. 연결 오류 해결
| 증상 | 확인 |
|---|---|
| 000/timeout | 허용 IP 여부(1), 서버 가동 여부를 담당자에게 확인 |
| 401 | 토큰 누락·오타(2). 토큰은 새로 발급됐으니 최신 것인지 확인 |
| 404 | 경로 오타 또는 구 서버(담당자 확인). `/docs`에서 실제 경로 확인 |
| 422 | 파라미터 누락. OpenAPI 스키마 대조 |
| 503 | 저장 캐시 없음 — 담당자에게 캐시 재생성 요청 |

## 데이터 한계(중요)
- HVQ 원시 Anomaly Map은 **100제품·500시점만** 저장. 나머지는 스칼라 점수만 → `unsupported` 응답은 정상.
- 마스크 64² 150개는 **Train NG 기반** 집계(정상/Test 미포함).
- 3D 표면 투영은 **시각화용 근사**이며 물리 좌표 실측이 아님.
- 전체 24,000은 두 모델 학습 미사용 데이터(훈련 담당자 확인)이나 퓨전 규칙 보정(Val 3,610)이 포함된 집계 — 대표 지표는 규칙 보정에도 쓰이지 않은 Test 3,593(F1 0.9532).
상세: 킷의 `DATA_DICTIONARY.md`, `FUSION_CONTRACT.md`, `DATA_AVAILABILITY.md`.
