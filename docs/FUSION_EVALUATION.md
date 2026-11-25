# 퓨전 평가

## 계약 명세
- 설정: `config/fusion_evaluation.json`(버전 `weighted-minmax-heatmap-mean-rt40-v1`), 확정 가중치는 `config/fusion.json`과 일치.
- HVQ 점수: 연속 heatmap_mean. max16 임계값은 퓨전에 사용하지 않는다.
- RT 점수: 저장 최대 신뢰도, 0.4 미만이면 0.
- 정규화: Validation 3,610제품 품목별 min/max → `(x−min)/(max−min)`. 상수 범위 거부, Val 밖은 외삽.
- 제품 집계: C1~C5 최댓값.
- TH: 품목별 Validation F1 최대 구간 중 가장 높은 구간의 중점. margin: 정점 대비 F1 하락 0.005 이내 연결 구간.
- 보류: `abs(score−TH) ≤ margin`.

## 평가 결과(저장 점수 재사용, 재추론 없음)

| 범위 | 제품 | Recall | F1 | FP/FN | AUROC | 보류 |
|---|---:|---|---|---|---|---:|
| 전체 참고 | 24,000 | 12,102/12,408 = 97.5338% | 0.968780 | 474/306 | 0.992895 | 194 |
| Test | 3,593 | 1,752/1,838 = 95.3210% | 0.953210 | 86/86 | 0.986346 | 37 |

## 검증 근거
- `reports/gui_validation/part-heatmap/minmax-contract-audit.json`: 24,000제품 수식·TH·margin·판정 전수 대조 오차 0.
- 별도 인메모리 SQLite SQL 혼동행렬 일치.
- `scripts/activate_fusion_contract_v2.py` 실행 후 DB 활성 run과 보고서 예측 일치(identity 해시 `e917f9730ddb05d9c486b45d` 재현).
- 단위 테스트: `tests/test_minmax_fusion_contract.py`, v2 분기 테스트 5건.

## 구 계약 대비
- 구 max16/백분위/RT0.55: Test F1 0.942795, 전체 F1 0.959035. v2가 전 범위 상승 → 사용자 확정.
- 운영 DB는 구 max16 run을 보존한 채 v2 run을 활성(is_active)으로 등록, 조회는 `/fusion/runs`로 선택.

## 주의
- 평가 산출물(`reports/final_performance_minmax/performance.json`)의 `activation` 필드는 `report_only`로 기록돼 있다(평가 시점 기준). DB 활성화는 별도 배치로 이행됐다.
- 전체 24,000은 두 비전 모델의 학습에 사용되지 않은 데이터(훈련 담당자 확인). 단 Validation이 포함돼 있어, 퓨전 규칙(정규화·TH·margin) 보정에 사용된 데이터가 전체 지표에 섞여 있다 — Test 대비 다소 낙관적일 수 있다.
- 상세: `FINAL_FUSION_CONTRACT_REPORT.md`, `FUSION_POLICY_COMPARISON.md`, `FUSION_RECOVERY_REPORT.md`.
