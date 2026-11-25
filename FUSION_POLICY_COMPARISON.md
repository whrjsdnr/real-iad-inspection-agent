# 퓨전 정책 비교 및 유지 결정 — 2026-11-25

사용자 지시: 이전이 더 좋으면 그때 규칙을 표시하되, 현재 지표가 더 높다면 현재를 유지한다. **현재 규칙 유지**로 확정했다. 기존 저장 CSV의 (product_id,category,split,truth)24,000개가 정확히 일치하며 Test3,593개도 동일하다. 보고서 점수를 비교했으며 모델을 실행하거나 임계값을 다시 맞추지 않았다.

| 범위/지표 | 이전 max16·RT0.55·Val percentile | 현재 mean·RT0.4·Val minmax |
|---|---:|---:|
| 전체 F1 |0.959035|0.968780|
| 전체 Recall |0.970745|0.975338|
| 전체 FP/FN |666/363|474/306|
| Test F1 |0.942795|0.953210|
| Test Recall |0.950490|0.953210|
| Test FP/FN |121/91|86/86|

둘 다 RT0.7/HVQ0.3이나 HVQ스칼라·RT선택·정규화 방식이 다른 고정된 정책이다. 현재 설정·보고서 선택·운영 DB 기존 판정은 변경하지 않았다. 선택모델: fusion-minmax-mean-rt40-w70-30:e917f9730ddb05d9c486b45d.

전체수치는 Validation을 포함한 참고집계이고 실제 모델학습표본과의 중복은 미확인이다. 정책 비교로 Test를 재튜닝하지 않았다. 과거98.84%의 정확한 모델평가 원본은 이번 비교에서 특정하지 못했다. 별도로 발견된 COMBINED_CROP_RESULT_REPORT.md의98.8456%는 crop픽셀보존율이며 분류F1로 사용하지 않았다.

기계판독 검증: reports/gui_validation/spatial-urgent/fusion-policy-comparison.json.
