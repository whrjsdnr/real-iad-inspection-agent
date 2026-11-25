> 2026-11-25 최신: MV_HEATMAP_REUSE_REPORT.md / MV_MASK_API_404_FIX_REPORT.md / TEAM_DATA_SHARING_REPORT.md / FUSION_POLICY_COMPARISON.md 우선. 현재2D실데이터/공유API는구현·수치검증, 3D물리표면투영과호스트브라우저는미완료. 최신Python128/프런트131통과.

# 공간 히트맵 데이터 계약 v1

기존 `/parts/heatmap`은 유지한다. 신규 GET:

- `/parts/spatial/index?item=toothbrush`: 등록된 사전 계산 grid 목록, 원본 식별자, 제품/카메라/부위/부모/해상도, 모델 지원 여부, 추천 해상도, 매핑 상태. 사설 원본 경로 목록은 제외한다.
- `/parts/spatial/grid/{grid_id}?model=rt&method=gaussian`: grid_id는 목록의24자리 hex. RT method: center_count, box_area, confidence_area, gaussian, product_occupancy, mean_confidence. HVQ: mean,max,percentile. 잘못된 method400, 미등록ID404, 설정/계산코드 해시 불일치409.
- `/parts/spatial/image/{image_id}`: 목록에 등록된 원본만, SHA 검사. 임의 경로 입력 불가.

응답은 item/product_id/camera/region_id/parent_region_id, mapping_version, image/ROI bounds, resolution, coverage_mask, model, aggregation_method, values, valid_observation_counts, native_sample_counts/map_size, stats, region_value, status/reason, image_url을 포함한다. 실제 필드명/형상은 app/spatial_api.py 및 handler-real-data-validation.json을 기준으로 한다. 단일 제품·시점·부위 단위다. 카메라간 좌표 또는 제품간 좌표의 합산 API가 아니다.

coverage 외부/원시 HVQ 샘플 없는 bin은 null 및 관측0. RT 관측은 있으나 검출 없는 bin의 밀도0은 유효값이다. mean_confidence는 검출 없으면 null. MIN_DENOMINATOR10 미만은 표본 부족을 표시한다. 미관측을 정상으로 보간하지 않는다.

캐시 경로 reports/spatial_heatmap, gzip 레코드. derive 시 미리 계산하며 HTTP 요청마다 운영 전체 DB를 읽지 않는다. 설정/알고리즘 SHA를 저장해 낡은 결과를 거부한다. 원본/지도 파일이 바뀌면 재생성이 필요하다. 기존 제품 판정/공식 퓨전 결과에는 쓰지 않는다.

추가 요구: 전수 제품별 맵, 카메라 보정/자세/가림 mask, 검증된 ROI↔UV atlas가 없으므로 전수 HVQ/다시점3D/FP·FN 위치는 현재 미지원이다. 별도 추론이나 운영스키마 변경 없이 구현한 범위다.
