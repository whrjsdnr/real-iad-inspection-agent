# 보존된 MV 마스크 히트맵 재사용

이번 데이터는 모델 추론 결과가 아니라 실제 제공 마스크를 집계한 기존 분석 결과다. Train/Test를 새로 나누거나 GAN 학습·추가 추론을 하지 않았다. 원래 MV 산출물을 수정하지 않는다.

## 실제 발견한 코드와 배열

- 생성 코드: `/home/geonug/MV/mv_analysis/presence_heatmaps.py`
- 원래 pooling 함수: `/home/geonug/MV/legacy/windows_snapshot/RealIAD_OpenCV_Analysis_Assignment_v2/RealIAD_OpenCV/coursework.py`의 coarse_occupancy
- 노트북: `/home/geonug/MV/notebooks/03_defect_heatmap.ipynb`
- 수치 경로: `/home/geonug/MV/outputs/windows_preserved_20261111_v1/`
- presence_count.npy, observation_count.npy, occupancy_known.npy, occupancy_positive.npy, area_fraction_sum.npy: 각각 (560,64,64)
- 그룹·분모: heatmap_groups.json, heatmap_summary.csv
- 출처·분할: run.json, image_metadata_with_split.csv, mask_policy.json, heatmap_schema.json, heatmap_validation.json

선정본은 presence-v2다. 별도 scripts/render_heatmaps.py의 positive/known 재나눗셈은 다른 배열 의미를 전제로 하므로 이번 presence-v2에 재사용하지 않았다. 이미 빈도인 배열을 다시 나눠 수치를 왜곡하지 않는다. PNG 색을 역변환하지 않는다.

## 검증한 범위

기존 Windows seed42 split을 보존한 Train NG54,805장 중 제공 마스크36,173장. source validation 오류0, unknown18,632장. 560개 품목/불량유형/시점 그룹을 재사용한다. NG product_id+view 중복0과 원본1024×1024를 메타데이터 전체에서 확인했다. 이 product_id는 선언된 제품 단위이며 물리적으로 동일 제품인지 별도 입증한 것은 아니다.

칫솔 CH/C1의132개, 지퍼 BX/C1의98개 실제 마스크를 원래 함수로 다시 읽어 해당 그룹 presence_count가 완전히 일치함을 확인했다. 전체36,173개 마스크를 이번에 전부 다시 디코딩한 것은 아니다. 560그룹 전체의 count/n_known, count/n_positive와 기존 빈도배열의 수치 일치도 확인했다.

API/패키지는150개 품목-카메라 집계와 칫솔·지퍼 대표2제품×5시점의 개별 마스크 캐시를 제공한다. 지퍼 대표제품C2는 마스크가 없으므로 unknown이다. 기타 제품별 마스크는 전체 데이터셋에 존재하더라도 현재 API의 개별 캐시 대상으로 가져오지 않았을 수 있다.

## 조회

- GET /heatmaps/catalog?item=toothbrush
- GET /heatmaps/ground-truth?item=toothbrush&view=C1&split=train
- GET /heatmaps/ground-truth?item=toothbrush&view=C1&split=train&product_id=toothbrush/NG/CH/S0001
- GET /heatmaps/ground-truth?item=toothbrush&view=C1&split=train&region_id=bristle
- GET /heatmaps/metadata?item=toothbrush
- 모델지도는 기존 /parts/spatial-heatmap을 사용한다. 별도 /heatmaps/model 중복 API를 만들지 않았다.

수치는 row-major/y-down의64×64다. positive_count는 셀에 원본 양성 픽셀이 하나라도 있었던 마스크 수, known_count는 제공 마스크 수(빈 마스크 포함), unknown_count는 미제공/오류 수, defect_rate는 positive_count/known_count다. 이 값은 **Train NG 제공 마스크에 조건부인 위치 빈도**이며 전체 제품의 불량률이 아니다. occupancy_positive는 비어 있지 않은 마스크만 분모로 쓴다.

mask_coverage는 원본 마스크의 셀 면적 비율 합/known_count다. annotation_coverage=known_products/product_count와 다르다. coverage_mask는 알려진 마스크 관측을 뜻하며 실제3D 물체 표면 가시성 mask가 아니다. 분모0은 null, MIN_DENOMINATOR10 미만은 표본 부족이다.

ROI 요청은 기존 원본좌표 폴리곤에64격자 셀중심을 대조해 외부 셀을 투명하게 한다. 원시16픽셀 셀 안의 경계 정밀도를 새로 복원한 것은 아니다. 카메라간 공간 정합과 3D UV 정합은 여전히 미검증이다.

## GUI와 비교

`#/spatial` 또는 대시보드의 ‘실제 마스크 위치 분포’는 A, ‘RT 공간 밀도’는 B, HVQ 실제 맵은 C, 기존 부위 집계는 D다. ‘마스크·검출 비교’는 같은 제품·시점·train·원본SHA 확인을 통과한 대표 표본에서만 제공한다. 집계 Train 분포와 다른 제품의 모델 결과를 같은 위치의 근거인 것처럼 겹치지 않는다.

패키지 heatmaps/*.json에150개 실제 공간 배열, HEATMAP_CATALOG.json에 지원 목록, samples/gt_*.json에 실제 인증된 ASGI 응답이 있다. 실 TCP/외부 PC/브라우저 화면 검증은 sandbox socket EPERM으로 미완료다. 미배포 서버가 이 API를 이미 제공한다고 가정하지 않는다.
