# 데이터 가용성 — 무엇이 어디에 있는가

| 데이터 | 범위 | 제공 방식 | 비고 |
|---|---|---|---|
| 제품/시점 코호트 | 24,000제품·120,000시점(C1–C5) | API /products·/sharing/manifest | split train 16,797/val 3,610/test 3,593. 학습 중복 UNKNOWN |
| RT-DETR 박스·신뢰도 | 전체 저장 시점 | API /products/findings | 원본 픽셀 XYXY |
| HVQ 이상 점수 | 전체 저장 시점(스칼라) | API /products/views | heatmap_mean 출처 일치는 칫솔 표본에서 확인, 전 코호트는 미재검증 |
| HVQ 원시 Anomaly Map | 500개 시점·100제품·30품목뿐 | API /products/anomaly-map | 224×224 NPY. 전체 제품에 맵이 있는 것은 아님. 없으면 unsupported |
| 불량 마스크 64×64 수치 배열 | 30품목×5시점 = 150개 | API /heatmaps/*, heatmaps/*.json | Train NG 기반 집계. 정상/Test는 분모에서 제외 |
| RT/HVQ 공간 대표 배열 | 같은 대표 제품 300개 응답 | API /heatmaps/surface, surface_frames/ | 개별 제품·단일 칩첩; 전수 공간 집계 아님 |
| ROI/부위 정의 | 기존 69 템플릿+계층 ROI | /roi/templates, ROI_CATALOG.json | 원본 픽셀 좌표 폴리곤. UV/칙첩 보정 미검증 |
| 부위별 관측 분모/양성 | 기존 계약 집계 | /parts/heatmap | 분모 24,001은 공식 코호트 24,000과 동일 범위로 검증된 값 아님 |
| 퓨전 평가 결과 | 위 FUSION_CONTRACT.md 표 | /products/fusion, /performance/final | report_only 저장 평가 |
| ZIP에 없는 것 | 모델 가중치, 전체 원본 이미지, 전체 DB, 전수 원시 맵 | — | 필요시 담당자 승인 하에 별도 제공 |

데이터가 없는 경우의 처리: API는 없는 맵/캐시를 지원한다고 거짓 응답하지 않는다. unsupported/404/503을 받으면 스칼라로 대체하거나 가상 핫스팟을 만들지 말고 "데이터 없음"으로 표시한다. 소표본(분모 MIN_DENOMINATOR 미만)은 수치 대신 사유를 표시한다.
