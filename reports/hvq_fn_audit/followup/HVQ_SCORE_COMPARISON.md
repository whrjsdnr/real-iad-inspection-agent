# HVQ_SCORE_COMPARISON — 저장 점수 집계 방식 비교

동일 제품 집단(24,000)의 저장 점수만 사용. 추론 없음. (상세 수치: score_comparison.csv, figures/)

## 저장 필드 확인
`max16_scores/hvq_max16.sqlite`: views(hvq_mean, hvq_max16, rtdetr_raw), products(hvq_mean_max, hvq_max16_max) — **percentile 계열·기타 원시 점수는 저장돼 있지 않음**(비교표에 미존재 사유 기록). 코드 정의: `hvq_common.scores_from_pred` = 히트맵 평균(EvalImageMean), max16 = 뷰 히트맵 상위 16 평균(저장 배치 산출).

## 제품 단위 비교(Validation / Test 각각)

| 변형 | 정의 | AUROC(Test) | best-F1 임계값(원척도 환산 위치) | FN@best | FP@best |
|---|---|---|---|---|---|
| mean_max | max(5시점 heatmap_mean) — 현행 퓨전 입력 | 0.669 | 36.4 | 204 | 2,754 |
| max16_max | max(5시점 hvq_max16) | **0.816** | 82.6 | 283 | 738 |
| combo_50_50 | 품목별 Val minmax 후 0.5·mean+0.5·max16 | — (CSV) | — | — | — |
| percentile 계열 | 저장 없음 | — | — | — | — |

## 해석
- **Max16이 제품 수준 판별력(AUROC 0.816)에서 Mean(0.669)보다 0.15 높다.** Mean은 결함 국소 신호를 전체 평균에서 희석(Phase 4 감사의 SCORE_AGGREGATION_LIMITATION 확인).
- 그러나 Max16의 FN@best(283)가 Mean(204)보다 많고 AUROC가 높은 것은 순위 능력 때문 — 임계값 운영 시 오탐-미탐 균형이 다르다.
- Mean+Max16 결합(50:50)은 단독 HVQ로서 Mean보다 약간 개선되나(어블레이션의 hvq_mean_max16_5050) 퓨전 수준에서는 현행을 넘지 못함(FUSION_ABLATION_REPORT.md).

## 결론
현행 퓨전 입력(heatmap_mean)은 "국소 신호 희석"이란 한계가 있으나, 퓨전 맥락에서는 RT 신뢰도와 결합해 이미 최적 후보다 우위 — 운영 교체 근거는 부족. Max16의 높은 AUROC는 향후 규칙 연구 후보로만 기록(운영 규칙 변경은 별도 승인).
