# 공간 히트맵 파이프라인

## 부위별 히트맵(app/part_heatmap.py)
- ROI는 원본 이미지 픽셀 좌표 폴리곤(`config/part_heatmap_regions.json`). 칫솔 손잡이는 미촬영으로 사용자 지시로 미등록.
- 저장된 RT 박스 중심이 하나의 ROI에만 속할 때만 배정. 경계·외부·해시 불일치는 보수 처리.
- HVQ 공간 집계는 운영에 원시 맵이 보존되지 않아 집계하지 않는다(실제 저장 맵 표본은 별도).
- 소표본(분모 MIN_DENOMINATOR 미만)은 수치 대신 사유 표시.
- 검증 산출물: `reports/part_heatmap/verify-multi-region.jpg` 등(육안 확인).

## 공간 격자(app/spatial_api.py)
- 저장 박스를 ROI 낶部 좌표로 정규화해 16/32/64/128 격자에 누적. method: center_count·box_area·confidence_area·gaussian·product_occupancy·mean_confidence.
- 서로 다른 칙첩 좌표를 합치지 않고, 같은 제품의 박스를 여러 제품으로 세지 않는다.
- 미검출 0 / 미관측 null / 표본부족 / 미지원을 구분한다.

## 마스크 기반 64²(app/ground_truth_api.py)
- ~/MV presence-v2 원본 560×64² 배열을 재사용(30품목×5시점=150개). Train NG 기반이며 정상/Test는 분모에서 제외.
- API: `/heatmaps/catalog`, `/heatmaps/ground-truth`, `/heatmaps/metadata`, `/heatmaps/evidence`.
- 실제 칫솔 C1 132장·지퍼 C1 98장을 원래 coarse 함수로 재검증해 일치 확인.

## 3D 표면 투영(app/surface_api.py + three_surface)
- 사용자 승인에 따른 **근사 표면 투영**(시각화용). 실측 물리 좌표 복원이 아니다.
- 부위 전체에 연속 투영 UV를 생성하고 DataTexture+ShaderMaterial을 적용, 원래 PBR 유지.
- 공유 런타임: `team_integration_kit/three_surface/`, 가이드는 `THREE_SURFACE_GUIDE.md`.
- 근거·한계: `HVQ_MAP_AVAILABILITY_REPORT.md`, `SURFACE_MAPPING_VALIDATION.md`, `HEATMAP_GUI_VALIDATION.md`, `SPATIAL_HEATMAP_CONTRACT.md`.
