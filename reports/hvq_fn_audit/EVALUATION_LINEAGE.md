# HVQ 미탐(FN) 수치 평가 계보 — EVALUATION_LINEAGE

추적 일시 2026-11-25. 결론: 현재 표시되는 "HVQ 미탐 12,408건(FN 100%)"은 **평가 코드의 점수 척도 불일치 오류**에서 나온 값이며, HVQ 모델의 실제 미탐이 아니다.

## 수치 흐름(코드 → 저장 → API → GUI)

1. `scripts/report_minmax_fusion.py`(구 버전 59행): 단독모델 참고 판정으로
   `hvq_positive = hvq_mean >= base_config['hvq']['threshold_default']` — 임계값 **81.0**.
2. `config/fusion.json`의 `hvq.threshold_default=81.0`은 **max16 점수 척도**(뷰 히트맵 상위 16 평균, 범위 ~100±)용으로 보정된 값.
3. 계약 v2의 HVQ 입력은 **연속 heatmap_mean**(제품 최대값 범위 약 29.9~67.0) → 81.0보다 전수 낮아 `hvq_positive`가 모두 False.
4. → `reports/final_performance_minmax/performance.json`의 `single_model_hvq` = {tp:0, fn:12408(전체)/1838(Test), fp:0, tn:전수} → F1 0.0.
5. → `app/status.py` → `GET /performance/final` (`summary.metrics.single_model_hvq_f1`, `report.*.single_model_hvq`) → GUI 클라이언트(`client.ts`의 `single_model_hvq_f1`)와 에이전트 도구 설명이 소비.

## 검증한 수식·정의

- FN = 실제 불량을 정상으로 예측. FNR = FN/(TP+FN) = 1 − Recall. (구현 `app/cohort_performance.summarize`와 일치)
- 미탐 "건수"(12,408)와 "미탐률"(100%)을 구분 — 오류로 인해 둘 다 왜곡됐다.
- HOLD/UNKNOWN은 정상이나 미탐으로 집계되지 않는다(보류는 별도 카운트, 확정 혼동행렬에서 제외).
- HVQ 단독 지표와 퓨전 지표는 별도 블록 — 퓨전 FN(전체 306/Test 86)에는 영향 없음.

## 정정 후 계보

- `fit_single_model_reference()`: Validation 제품의 heatmap_mean min-max 정규화 → `threshold_and_margin`(F1 최대 구간 중점)으로 참고 임계값 적합(원척도 환산 36.0244).
- 재산출: performance.json·all_predictions.csv 갱신. `model_version` 해시와 퓨전 혼동행렬은 **동일**(전수 대조 확인).
- 교정값: HVQ 단독 참고 전체 FN **613**(Recall 95.06%), Test FN **82**(Recall 95.54%). 여전히 참고 지표일 뿐 운영 규칙은 불변.

## 근거 파일

- 오류 판정: `hvq_confusion_matrix.csv`(구/신 혼동행렬), `score_distributions.png`(81.0이 정상/불량 분포 오른쪽 끝 밖).
- 저장 점수: `max16_scores/hvq_max16.sqlite`(views.hvq_mean·hvq_max16 120,000행, products.hvq_mean_max·hvq_max16_max 24,000행).
