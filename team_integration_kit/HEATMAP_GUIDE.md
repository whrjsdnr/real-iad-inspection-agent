# 공간 히트맵 계산과 표시

기존 부위별 API는 rate 한 값으로 전체 부위를 칠한다. 공간 API는 실제 saved Bounding Box를 ROI 내부 좌표로 정규화하여 32×32 격자에 누적한다. 예제 실제 칫솔 C1은 2박스,1,024셀 중174개 양의 신호,19종 값이다. 검출 중심은 (17,7),(26,26)셀에 연결된다.

values/observation_counts/coverage_mask는 row-major(y 아래 방향) 길이 width×height 배열이고 values_2d는 같은 배열의 행 표현이다. center_counts, box_occupancy_counts, detected_product_counts, confidence_weighted_area, mean_confidence를 따로 제공한다. 같은 박스의 정확중복을 제거하며 동일제품의 박스들을 여러제품으로 세지 않는다. 서로 다른 카메라의 좌표를 합치지 않는다. 부모/자식 지도를 합산하지 않는다.

RT method: center_count,box_area,confidence_area,gaussian,product_occupancy,mean_confidence. Gaussian은 박스중심 분포 시각화이며 실제 결함 마스크가 아니다. 박스 내부 전체를 실제 불량 영역으로 간주하지 않는다. HVQ mean/max/percentile은 실제 원시 맵 표본을 집계하고 비어 있는 고해상도 bin을 보간으로 채우지 않는다.

유효분모는 해당 제품·시점의 등록 ROI envelope 안 영상 관측1이며 카메라 보정으로 확인된3D 표면 관측수가 아니다. rate_supported=false이므로 발생률/확정 불량률로 표시하지 않는다. 표본1은 MIN_DENOMINATOR10 미만으로 별도 표기한다. 미검출0,미관측null,표본부족,미지원은 구분한다. 관측되지 않은 셀은 투명하게, 검출0은 낮은 신호로 표시하되 정상 판정이라고 쓰지 않는다.

현재 표시 방식은 사용자가 승인한 근사 표면 투영이다. 기존 primitive UV를 사용하지 않고 부위 전체에 연속적인 투영 UV를 새로 만든다. DataTexture/ShaderMaterial이 실제 메시 표면에 붙으며 칫솔모 측면도 위치별 히트맵 색을 따른다. 실제 수치는 유지하고 유효 관측 범위 안에서만 색을 부드럽게 보간한다. 물리 좌표 실측이 아니므로 physical_alignment_verified는 false다. 공유 런타임과 적용 예제는 THREE_SURFACE_GUIDE.md를 참고한다.

공간 캐시는 대표제품에 한정된다. 전수24,000개를 공간적으로 정합해 집계한 결과가 아니다. 동일품목/다른제품 자세 정합도 검증하지 않았다. 16/32/64/128은 표시·집계 해상도이며 원본 측정 정확도를 높이지 않는다. 상세 원본 근거와 공급 범위는 API 응답을 우선한다.

기존 MV 마스크 기반150개 64×64 수치도 포함합니다. MV_HEATMAP_REUSE.md와 HEATMAP_CATALOG.json, heatmaps/*.json을 확인하세요. 마스크 API는 /heatmaps/catalog, /heatmaps/ground-truth, /heatmaps/metadata입니다.
