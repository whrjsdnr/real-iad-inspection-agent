# 공통 데이터 정의

제품 = 동일 product_id의 C1–C5 묶음. 제품수와 박스수는 다르다. source=`saved_batch5_score_cache`는 기존 읽기전용 SQLite 결과 사본이며 현재 운영PG의 active run과 동일 정책이라고 가정하지 않는다. 제품 split/truth는 저장된 라벨이며 분할을 변경하지 않는다.

- bbox: 원본 픽셀 XYXY, width/height는 원본 해상도. confidence는 저장된 RT-DETR 신뢰도. /products/findings는 기본적으로 저장 박스를 모두 반환하며 min_confidence로 선택한다. RT 공간 시각화의 선택값은 기존 계약0.4다.
- views.hvq/제품 hvq_max: 저장 컬럼 원시값. 칫솔 GUI 일치표본에서 heatmap_mean과 일치함을 확인했으나 전 코호트 컬럼 출처를 별도 재추론해 검증하지 않았다. API가 이 provenance 한계를 표시한다. 정규화/공식 퓨전 입력과 임의 혼용하지 않는다.
- anomaly_map: 실제 저장224² NPY가 확인되고 원본 SHA가 일치할 때만 supported. 실제 저장500맵/100제품/30품목에서 지원한다. 상대경로는 점수캐시 디렉터리를 기준으로 복원한다. /products?maps_only=true로 지원 참조 제품을 찾고 개별 맵 API에서 검증한다. 스칼라로 대체하지 않는다.
- 좌표: RT 원본 복원은 inference.py postprocess(orig_sizes) 코드 경로를 확인했다. 입력코드의 direct Resize와 달리 모든 저장행에 crop/pad 행렬 메타데이터가 있는 것은 아니다. per_record_transform_metadata=null은 미저장 상태다. 실제 맵 표본은 확인된 full-frame direct resize를 사용한다. legacy640×480 LUT를 일괄 확대하지 않는다.
- region_id: 기존 메시 ID를 유지한다. ROI child ID는 parent_region_id로 연결된다. 지원 시점은 영상 ROI 정의를 뜻하며 보정된 표면 가시성 mask가 아니다. UV 정합과 카메라 extrinsics는 미확인이다.
- /products/fusion: 공식 저장 평가 CSV의 report_only 판정과 수치. database_run_activated=false. 운영 기존 verdict를 수정하지 않는다. 평가설정 version은 weighted-minmax-heatmap-mean-rt40-v1이며 사용자 지칭 퓨전 계약v2의 설정이다. RT0.7/HVQ0.3, 카테고리별 Val minmax, heatmap_mean·RT0.4, max_C1_C5, Val F1 최적 TH와 허용하락0.005 margin. 세부값은 응답과 기존 평가 보고서에 보존한다.
- 98.84%는 과거 사용자가 보고한 수치다. 지표 정의가 불명확한 상태에서 현재 저장 평가 결과로 덮어쓰거나 같은 평가라고 주장하지 않는다.

검수 전 신호는 의심 건수/검출 위치로 해석한다. 확정 불량률·FP·FN·미탐 위치는 검수/GT 위치 근거 없이 계산하지 않는다. 기존 부위 운영집계의 분모24,001과 공식 코호트24,000은 동일 범위로 검증된 값이 아니다. 현재 카메라/기간/모델 필터의 기존 artifact 적용 범위는 별도 점검 항목이며 공간 개별제품 API와 구분한다.
