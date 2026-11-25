# API 사용법

공유 게이트웨이 기본주소는 `http://<HOST-IP>:18081/api`. 모든 요청에 `Authorization: Bearer <TEAM_ACCESS_TOKEN>`을 넣는다. URL이나 소스 코드에 실제 키를 넣지 않는다. 기존 중앙 API의 root 주소에는 `/api` 프리픽스가 없을 수 있으므로 운영자 설정을 따른다. GUI는 상대 `/api`를 사용한다. 현재15173 개발 서버의 MV/표면 조회는 읽기 전용 bridge이며 나머지 기존 프록시는18080이다. 운영8000/8080 실제 listen 상태와 외부 연결은 이번 환경에서 확인하지 못했다.

| 조회 | 경로 | 범위/주의 |
|---|---|---|
| 데이터·계약·30품목 목록 | GET /sharing/manifest | 실제 저장 cohort 캐시. 기존 GET /items는 운영DB 품목 목록이며 네트워크 미검증 |
| 부위 ID | GET /catalog/parts?item=toothbrush | 메시 ID와 계층형 ROI ID, 관측 시점, UV 미검증 |
| ROI | GET /roi/templates?item=toothbrush&view=C1 | 기존69 native 템플릿, offset/limit≤100 |
| ROI 품목별 | GET /roi/templates/toothbrush | 같은 API의 품목별 별칭 |
| 세부 ROI | GET /roi/hierarchy?item=toothbrush | spatial_regions의 별도 버전 |
| 제품 목록 | GET /products?item=toothbrush&limit=50&offset=0 | 최대100, product_id/status 필터 |
| C1–C5/점수/좌표 | GET /products/views?product_id=...&view=C1 | 제품 ID에 /가 있으므로 query parameter 사용 |
| 저장박스 | GET /products/findings?product_id=...&view=C1&model=rt&min_confidence=0.4 | bbox XYXY, confidence, class, ROI; offset/limit≤500 |
| 실제 원본 | GET /products/image?product_id=...&view=C1 | 허용 dataset root 안의 저장 파일만 |
| 표시용 3D 공간 배열 | GET /heatmaps/surface?item=toothbrush&view=C1&source=hvq | 같은 대표 제품 RT/HVQ; 실제 배열/투영 설정 |
| 지원 표면 모드 | GET /heatmaps/surface-layout?item=toothbrush | 3종 데이터/시점/지원 여부 |
| 실제 이상 맵 | GET /products/anomaly-map?product_id=...&view=C1&format=metadata | format=array 또는 npy; 없으면 unsupported |
| 기존 부위 통계 | GET /parts/heatmap?item=toothbrush | 기존 계약 유지; 검출 의심 신호와 확정 검수 지표 구분 |
| 실제 공간 배열 | GET /parts/spatial-heatmap?item=toothbrush&product_id=toothbrush/NG/CH/S0001&view=C1&region_id=bristle&model=rt&resolution=32&method=confidence_area | 원시박스 좌표 집계; 개별 제품/단일카메라 |
| 공간 캐시 목록 | GET /parts/spatial/index?item=toothbrush | 실제 지원 제품/시점/부위만 선택 |
| 퓨전 보고서 판정 | GET /products/fusion?product_id=... | report_only, 운영 판정을 대체하지 않음 |
| 기존 평가 보고 | GET /performance/final | 기존 평가 API 재사용 |
| 도구 | GET /tools, POST /tools/{tool_name} | 읽기 허용목록만; query_spatial_evidence 포함 |
| 명세 | GET /openapi.json | 실제 공유 서비스 스키마, Bearer 인증 |

RT/HVQ 공간 모드는 실제 저장 자료만 조회한다. model_version별 전수 공간 집계/카메라 보정/검수 위치 FP·FN은 미지원이다. API는 지원하지 않는 모델 타입과 해상도를 거부한다. ZIP의 OpenAPI는 현재 소스의 준비된 API이며 배포 완료 증거가 아니다.

예제 URL의 product_id는 반드시 URLSearchParams/urlencode로 인코딩한다. 데이터 양이 크면 페이지네이션을 사용한다. NPY 원시 맵은 numpy.load(...,allow_pickle=False)로 읽는다. 401=키/로그인,404=없는 제품/캐시,409=원본·설정 불일치,422=입력 오류,503=저장 캐시 없음이다.

기존 MV 마스크 기반150개 64×64 수치도 포함합니다. MV_HEATMAP_REUSE.md와 HEATMAP_CATALOG.json, heatmaps/*.json을 확인하세요. 마스크 API는 /heatmaps/catalog, /heatmaps/ground-truth, /heatmaps/metadata입니다.
