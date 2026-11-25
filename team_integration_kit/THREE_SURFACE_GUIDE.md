# 실제 공간 배열의 근사 3D 표면 표시

2026-11-25: 사용자가 표시 목적의 근사 표면 투영을 승인했다. 물리적 카메라 보정이나 실측 CAD 투영을 주장하지 않는다. 이전 문서의 ‘검증된 UV만 사용’ 제한은 이 표시 모드에 적용하지 않는다.

## 공통 데이터와 런타임

- `GET /heatmaps/surface-layout?item=toothbrush`: 실제 지원 데이터 종류/시점.
- `GET /heatmaps/surface?item=toothbrush&view=C1&source=ground_truth|rt|hvq`: 실제 공간 배열, region_id, 원본 ROI 범위, 관측 수, 투영 설정.
- `surface_frames/`: 30품목 × C1–C5 × 3종 = 450개 실제 조회 스냅샷. GT는 Train NG 집계, RT/HVQ는 같은 대표 제품이다. GT와 모델 자료를 동일 제품의 평가 결과로 혼용하지 않는다.
- `three_surface/surface-runtime.mjs`: 현재 GUI와 같은 DataTexture/ShaderMaterial 커널. Three.js는 외부 의존성이므로 팀 프로젝트에 설치된 하나의 Three 인스턴스로 import한다.
- `three_surface/surface-runtime.d.mts`: 타입, `projection-presets.json`: 표시 설정, `surface-tokens.css`: 공통 색상.

기존 메시/부모 그룹에 `userData.region_id`를 지정한다. 상세 메시의 `userData.detail_id='bristle-filaments'`는 칫솔모 측면까지 색상을 적용한다. `__whole_template__`는 전 외형 공통 범위다. 부위마다 전체 지도를 반복하지 않는다. 원래 PBR 재질은 유지하고 새 overlay만 추가한다.

`examples/three_texture.ts`의 attachApproximateSurface를 호출하고, 카테고리 변경/컴포넌트 해제 때 반환된 dispose()를 호출한다. 원본 geometry/material을 폐기하지 않으며 overlay 자원만 해제한다. root를 회전하면 overlay가 함께 회전한다. opacity는 setOpacity(0..1)로 변경한다. hotspots는 실제 격자값에 연결된 raycast 위치이며 가상의 이상 좌표를 만들지 않는다.

## HVQ 저장 범위 정정

120,000개 저장 시점 중 실제 NPY 맵은 **500개/100개 제품/30품목**이다. 모두 224×224, 유한값, 맵 평균과 저장 점수 최대 차이 0.0000114441. 상대경로는 scores.sqlite가 있는 디렉터리 기준이며 cwd 기준이 아니다. 이전 GUI/문서에서 지퍼 등 맵이 없다고 한 것은 이 로더 오류와 이전 캐시 선정 범위 때문이었다.

30품목 모두에서 맵이 있는 대표 제품을 선택하여 RT/HVQ를 같은 제품·시점으로 제공한다. 임의 제품에 맵이 있다고 가정하지 않는다. `GET /products?maps_only=true`로 저장 참조가 있는 제품을 찾고 `/products/anomaly-map?product_id=...&view=C1&format=array`로 실제 파일/원본 정합 검증 후 조회한다. 없는 제품은 unsupported다. 추가 추론은 실행하지 않았다.

## 표시 의미

카메라별 독립 2D field를 근사 외형 축에 연결한다. 3D 물리 위치의 검증은 false다. 실제값을 바꾸지 않고 유효 관측 범위 내 색상만 보간한다. 미관측은 원래 재질, 작은 표본은 별도 hatch/경고로 표시한다. 상대 강도 범례는 부위 내 분포 확인용이며 공식 퓨전 또는 전체 불량률이 아니다.

## 공유

현재 개발 GUI: `http://127.0.0.1:15173/api/sharing/kit` 다운로드. 127.0.0.1은 팀원 PC 주소가 아니다. LAN 서비스는 README의 별도 18081 읽기 전용 서버 실행 후 `http://<실제 서버 IP>:18081/api`와 비공개 Bearer 키를 사용한다. 호스트 TCP/LAN 연결과 GPU 화면 검증은 sandbox 제한으로 미검증이며 배포 완료를 뜻하지 않는다. DB 계정, .env, 비밀번호는 패키지에 없다.
