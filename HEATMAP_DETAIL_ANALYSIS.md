> 2026-11-25 최신: MV_HEATMAP_REUSE_REPORT.md / MV_MASK_API_404_FIX_REPORT.md / TEAM_DATA_SHARING_REPORT.md / FUSION_POLICY_COMPARISON.md 우선. 현재2D실데이터/공유API는구현·수치검증, 3D물리표면투영과호스트브라우저는미완료. 최신Python128/프런트131통과.

# 공간 히트맵 실제 구현 — 2026-11-24

상태: **IMPLEMENTED / 실제 저장 데이터 계산·오버레이 VERIFIED / 라이브 브라우저 BLOCKED**.

기존 부위 단색은 heatAppearance의 rate 하나를 Scene의 전체 부위 재질에 적용하는 구조였다. 기존 `/parts/heatmap` 계약과 fallback은 유지하고, 원시 좌표를 보존하는 별도 사전 계산 경로를 추가했다. 이미지를 보지 않고 스칼라로 공간 패턴을 생성하지 않는다.

## 확인한 실제 데이터

- 읽기 전용 소스: `/home/geonug/MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1/scores.sqlite`. products 24,000, views 120,000. views.boxes_json에 bbox와 confidence가 저장돼 있다. 원본은 `/home/geonug/MV/dataset`.
- RT-DETR 저장 박스는 batch_fusion.py postprocess의 orig_sizes 경로와 대조한 원본 픽셀 좌표다. 현재 표본 원본1024². 시각화 박스 선택은 기존 평가 설정의 RT0.4를 읽으며 정책을 변경하지 않는다.
- HVQ는 `gui_evidence/gui-a7b441dfce9a`의 칫솔 실제 224² NPY5장을 원본SHA 일치 시에만 재사용한다. 같은 이미지 재업로드는 추가 표본이 아니다. 지퍼와 다른 선정 표본의 저장 맵은 확인되지 않았다. scalar mean/max16은 공간 데이터가 아니다.
- operational_findings는 기존 source 명칭이며 SQL은 public.findings와 inspection_views를 사용한다. 새 공간 경로는 위 저장 캐시를 읽으며 운영 DB를 변경하지 않는다.
- 원본↔HVQ는 확인된 direct resize 변환을 사용하고 원시 map 픽셀 중심을 ROI로 옮긴다. legacy640×480 LUT를 일괄 확대하지 않는다. 메타데이터/원본 해시가 맞지 않으면 미지원이다.

## 구현 범위

`app/spatial_heatmap.py`, `scripts/derive_spatial_heatmaps.py`, `app/spatial_api.py`, `config/spatial_*.json`과 GUI SpatialHeatmapPanel을 추가했다. 30품목60제품(품목별 NG/OK 각1), 72품목-시점, 144제품-시점, 1,088공간 격자를 생성했다. 기존69시점에 지퍼 C3–C5 native ROI를 별도 공간 설정으로 추가했다. 나머지78품목-시점은 mapping_pending이며 표본 기준156개 상태 레코드로 기록했다. 전체24,000제품의 공간 집계를 완료했다는 의미가 아니다.

RT 중심점/박스면적/신뢰도 가중/가우시안/제품 점유/평균 신뢰도, HVQ mean/max/percentile을 지원한다. 정확히 같은 박스는 제거하며 분모는 관측 제품1이다. 부모/자식 지도를 더하지 않는다. 다른 카메라와 제품의 공간 정합은 미확인이므로 각각 분리한다.

원시 좌표 ROI 오버레이30품목×5시점 6장과 대표 비교 이미지를 직접 확인했다. 이는 개발용 실제 이미지 시각 검증이며 브라우저 렌더링 검증이 아니다. ROI 외곽은 근사 envelope이고 구멍/가림을 정밀 마스크로 복원한 것이 아니다.

기존 `/parts/heatmap`의 운영 artifact 분모24,001, 카메라/기간/모델 필터의 집계 일관성은 이번 공간 경로와 별개인 미해결 점검 사항이다. 새 개별 제품 모드에서 운영 집계로 혼용하지 않는다.
