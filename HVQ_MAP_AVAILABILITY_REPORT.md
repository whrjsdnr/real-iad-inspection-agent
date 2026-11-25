# HVQ 실제 이상 맵 가용성 및 표시 통일 — 2026-11-25

VERIFIED: 120,000개 저장 시점 중 실제 map_path 참조500개, 모두 파일 존재, 100제품/30품목, native224×224 float32. 모두 유한값이며 저장 views.hvq와 맵 평균 최대 차이1.1444091796875e-05. 근거: reports/gui_validation/spatial-urgent/hvq-map-availability.json.

원인1: 상대 map_path를 현재 작업 디렉터리 기준으로 검사해서 존재하는 맵이 누락됐다. scores.sqlite의 부모 디렉터리 기준으로 복원하고 허용 루트·NPY·원본 fingerprint/SHA를 검사하도록 수정했다.
원인2: 나머지 제품은 점수만 저장되고 실제 NPY 맵이 없다. 왜 당시100제품만 저장했는지는 이 조회 결과만으로 확정할 수 없다. 스칼라 점수로 맵을 생성하거나 추가 추론하지 않았다.

VERIFIED: 30품목×5시점에서 RT/HVQ가 같은 map-backed 대표 제품을 조회한다. GT150개와 RT/HVQ300개 실제 ASGI 응답의 배열을 검증·공유 패키지로 내보냈다. 대표 제품 ID와 split을 GUI에 표시해 전체 집계와 구분한다. C1–C5를 공간적으로 합치지 않는다.

조회: /products?maps_only=true&item=zipper → 실제 저장 참조 제품3개. /products/anomaly-map?product_id=zipper%2FNG%2FBX%2FS0050&view=C1&format=array → 실제 맵. S0002에는 맵이 없어 unsupported인 것이 정상이다. /heatmaps/surface?item=zipper&view=C1&source=hvq → S0050 실제32² ROI 표시 field. GT Train NG 집계와 모델 개별 대표 제품은 동일 표본이 아니다.

수정 코드: app/shared_data_api.py, app/surface_api.py, scripts/derive_spatial_heatmaps.py, inspection-gui/src/three/surfaceStore.ts, components/SurfaceControls.tsx 및 SurfaceHUD.tsx. 실제 배열은 surface_frames/에 제공한다. 공유 런타임은 team_integration_kit/three_surface/다.

3D는 사용자 승인에 따른 근사 표면 투영이며 실측 좌표 보정 검증은 false. 추가 모델 추론/판정 재계산/운영DB 스키마 변경/서버 재시작은 없다. 브라우저/TCP/LAN 검증은 sandbox 제한으로 미완료다.
