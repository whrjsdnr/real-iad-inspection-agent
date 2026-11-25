# ROOT_CAUSE_REPORT — HVQ 미탐 12,408건 표기 오류

## 현상
GUI/API/평가 보고서의 HVQ 단독 지표가 FN=12,408(전체 불량 100%), F1=0.0으로 표시됨.

## 근본 원인(확정)
`scripts/report_minmax_fusion.py`의 단독모델 참고 판정이 `config/fusion.json`의 `hvq.threshold_default`(81.0)를 그대로 사용.
- 81.0은 **max16 점수 척도**(뷰 히트맵 상위 16개 평균, 실제 불량 분포 상위 ~80~110)에서 유효.
- 계약 v2의 HVQ 입력은 **연속 heatmap_mean**(제품 최대값 범위 29.92~66.96) — 81.0보다 모든 제품이 낮음.
- 결과: `hvq_positive`가 24,000제품 전수 False → FN=전수 불량, FP=0, F1=0.

## 기여 요인
1. 점수 정의를 max16에서 heatmap_mean으로 전환(계약 v2)하면서 단독모델 참고 판정의 임계값 척도를 따라 전환하지 않음.
2. 참고 블록이 "퓨전과 무관"한 supplemental로 취급돼 검증이 생략됨(GUI/API 노출 경로는 살아 있었음).
3. `threshold_default`의 score_variant 속성이 주석에만 존재해 코드가 scale을 구분할 수 없었음.

## 증거
- `hvq_confusion_matrix.csv`: 81.0 적용 시 tp=0/fn=12,408 — 정상·불량 무관하게 전수 미달.
- `figures/score_distributions.png`: 81.0 위치가 양 분포 우측 경계 밖.
- 정상화 실험: 동일 점수에 Val 적합 임계값 36.0244를 쓰면 FN 613(Recall 95.06%) — 모델이 정상 작동함을 확인.
- 저장소에 max16 점수(`hvq_max16_max`)가 그대로 존재하고 81.0 근처에서 AUROC 0.816으로 분리됨 → 81.0 자체는 max16에 유효했음.

## 영향 범위
- HVQ 단독 참고 지표(FN/FNR/F1/Precision) 전부 — 사용자 노출 수치 오류.
- 퓨전 지표(전체/Test F1·FP/FN·AUROC·보류), DB 판정, GUI 대시보드 카드: **영향 없음**(전수 대조로 확인).

## 재발 방지
- 참고 임계값은 `fit_single_model_reference()`로 Validation에서만 적합(원척도 환산값을 보고서에 기록).
- 회귀 테스트 `test_single_model_hvq_reference_is_validation_fitted_not_max16_default` 추가.
- performance.json에 `single_model_reference` 계보(정규화 범위·적합 출처·원척도 임계값) 기록.
