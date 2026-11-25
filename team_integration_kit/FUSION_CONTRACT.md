# 퓨전 계약(확정 v2)

평가 설정 버전: `weighted-minmax-heatmap-mean-rt40-v1`. 저장된 120,000시점 점수 재사용(재추론 없음)으로 산출한 계약이다.

## 규칙

1. 제품 = 동일 product_id의 C1–C5 정확히 5개. 각 모델 제품 점수는 5시점 최댓값.
2. RT-DETR은 저장 최대 신뢰도가 0.4 미만이면 0. HVQ-Trans는 연속 heatmap_mean 점수를 사용하고 max16용 임계값은 쓰지 않는다.
3. 정규화: Validation 3,610제품에서 품목별·모델별 min/max 산출 후 `(점수−min)/(max−min)`. 상수 범위는 거부. Val 범위 밖은 수식대로 외삽(확률로 해석 금지).
4. 제품 fusion_score = 0.7×RT_norm + 0.3×HVQ_norm. 모델별 지표 가중 평균 금지.
5. 품목별 TH = Validation F1 최대 구간 중 가장 높은 구간의 중점. margin = 정점 대비 F1 하락 0.005 이내 연결 구간. `abs(score−TH) ≤ margin`이면 보류.
6. 모든 보정은 Validation에서만 산출하고 Test/운영에는 고정 적용.

## 결과(저장 점수 재평가)

| 범위 | 제품 | Recall | F1 | FP/FN | AUROC | 보류 |
|---|---:|---|---|---|---|---:|
| 전체 참고(Val 포함) | 24,000 | 12,102/12,408 = 97.5338% | 0.968780 | 474/306 | 0.992895 | 194 |
| Test(학습·검증 제외) | 3,593 | 1,752/1,838 = 95.3210% | 0.953210 | 86/86 | 0.986346 | 37 |

전체 집계는 Validation을 포함하고 원본 train 분할(16,797제품)의 실제 학습 목록과 중복 여부는 UNKNOWN이므로 참고 지표로만 쓴다. 대표 지표는 Test 값이다.

## 이전 계약과의 비교(동일 평가 범위)

| 규칙 | Test F1 | Test Recall | 전체 F1 |
|---|---:|---:|---:|
| 구 max16/백분위/RT0.55 | 0.942795 | 95.0490%(1,713/1,801 대상 정의 상이) | 0.959035 |
| 현재 v2(위 규칙) | 0.953210 | 95.3210% | 0.968780 |

과거에 보고된 98.84%는 평가 원본이 확인되지 않아 대표 성능으로 쓰지 않는다.

## 운영 반영 상태

- 평가 산출물(reports/final_performance_minmax/)은 `report_only` 계약이며 운영 DB의 기존 max16 판정을 덮어쓰지 않는다.
- DB fusion_analysis.model_runs에는 v2 run(`weighted-minmax-heatmap-mean-rt40-v1:e917f9730ddb05d9c486b45d`)이 활성(is_active)으로 등록됐고 구 max16 run은 보존·비활성이다. 조회 API /fusion/runs가 둘을 모두 보여준다.
- /products/fusion 은 저장 평가 CSV(report_only)의 판정을 반환한다. 운영 서버 프로세스가 구 코드면 /fusion/runs·/products 등 공유 API 자체가 404일 수 있다(배포 상태는 담당자 확인).
