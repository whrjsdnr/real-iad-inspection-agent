# 퓨전 재현 검증 상태

2026-11-23 / **BLOCKED_MISSING_ORIGINAL_FUSION_CSV**

## 미발견 산출물

- weighted_fusion_metrics.csv
- weighted_fusion_thresholds.csv
- validation_scores.csv
- test_predictions.csv

검색 범위는 `/home/geonug/agent`와 `/home/geonug/MV`다. 숨김·Git ignore 파일을 포함했고 패키지 설치 폴더 및 Git 메타데이터는 제외했다. 압축 내부와 원격 저장소는 미검색이다.

## 재현할 확정 알고리즘

각 모델 C1–C5의 원시 점수를 max로 제품 집계한 후 모델별·품목별 Val 경험적 백분위로 정규화한다. 동점 평균 순위, 관측값 사이 선형 보간, 범위 밖0/1을 적용한다. HVQ0.3+RT-DETR0.7 가중합, 품목별 Val F1 최고 기준 TH를 사용한다. 리콜 우선 TH는 원본에 존재할 때만 별도 모드로 저장한다.

margin은 Val F1 최고값−0.005 이상인 TH 집합 중 기준 TH를 포함하는 연속 구간을 분석한 뒤 산출 규칙을 명시해야 한다. 원본이 없어 구간/값을 아직 도출하지 않았다. 보류는 |score−TH|≤margin이며 이진 재현과 운영3단 평가를 분리한다.

## 목표와 실제 측정 구분

|지표|원본 목표의 분자/분모|산술 값|이번 CSV 재현|
|---|---|---|---|
|NG Recall|563/600|93.8333%|NOT_EXECUTED|
|NG 미검|37/600|6.1667%|NOT_EXECUTED|
|OK 오검/FPR|46/600|7.6667%|NOT_EXECUTED|
|Precision|563/609|92.4466%|NOT_EXECUTED|
|F1|1126/1209|0.931348|NOT_EXECUTED|

Test1200제품(NG600/OK600)은 사용자 확정 기준이다. 허용편차 Recall/F1 각각±0.02 검사는 미실행이다. 이 표의 목표를 metrics_snapshots에 새 측정값으로 등록하지 않았다.

## 차단 이유와 다음 입력

현재 설정은 min-max 및120제품 기준이 남아 있으며 최종 퓨전으로 사용할 수 없다. 원본4개CSV 경로를 제공받기 전 새 분할 생성·Test 기반 threshold 튜닝·실데이터 배치를 하지 않는다. 파일명 변경본이라면 각 원본과의 대응 관계 및 생성 근거를 함께 확인한다.
