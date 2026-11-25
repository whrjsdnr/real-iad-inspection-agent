# HVQ 미탐 정밀 감사 — HVQ_FALSE_NEGATIVE_AUDIT

일시 2026-11-25 / 범위: 저장된 24,000제품·120,000시점 점수(추론 재실행 없음)

## 1. 기존 표시 수치와 정확성

| 지표 | 기존 표기(오류) | 검증 결과 |
|---|---|---|
| HVQ 단독 FN(전체) | 12,408건(FNR 100%) | **평가 오류** — max16 임계값 81.0을 heatmap_mean에 적용 |
| HVQ 단독 FN(Test) | 1,838건(FNR 100%) | 동일 오류 |
| HVQ 단독 F1 | 0.0 | 동일 오류 |
| HVQ 단독 AUROC/AP | — | heatmap_mean 제품 최대 AUROC 0.67/Test 0.669(정상 산출) |
| 퓨전 FN(전체/Test) | 306 / 86 | **정확** — 이번 오류와 무관 |

## 2. Phase 2 — 평가 단위·라벨 검증(phase2_units.json)

- 제품 24,000 = 정확히 C1~C5 5시점(120,000행), (제품,시점) 중복 0, 칩첩 세트 전수 정상.
- 라벨: defect 12,408 / normal 11,592, 라벨 반전·무효값 0, 저장 manifest와 예측 CSV 제품 동일.
- 제품 단위 정답만 존재 → **시점 단위 미탐은 산출하지 않음**(시점별 결함 가시성 라벨 없음. "불량 제품의 모든 시점에 결함 가시" 가정은 하지 않음 — 시점 분석은 상한 분석으로만, hvq_view_metrics.csv).
- 비전 모델 학습 split과 퓨전 보정 split은 별개 — 추론 코호트는 두 모델 학습 미사용(담당자 확인), 퓨전 보정은 Validation 3,610만 사용.

## 3. Phase 3 — 추론 파이프라인 검토(추론 미실행, 코드 대조)

- `~/MV/inference_hvq.py` + `hvq_common.py`: PIL RGB → 224 direct-resize → ImageNet mean/std 정규화 → 체크포인트 분기 라벨 → 이상 점수 = 히트맵 평균(EvalImageMean), **높을수록 이상**(복원 오차 기반). 점수 방향성 정상.
- 학습 시 이미지 크기 224(`configs/training/hvq_trans.json` input_resolution 224)와 추론 224 일치. 학습 설정의 source_dir는 null(원격 학습)이라 원본 학습 목록 대조는 불가 — 보고서로만 기록.

## 4. Phase 4 — 점수 집계 비교(hvq_score_aggregation_comparison.csv)

제품 단위 HVQ 점수로 Val/Test 모두 산출(표는 Test 기준 일부):

| 집계 | AUROC(Test) | best-F1 임계값(원척도) | 특이 |
|---|---|---|---|
| 뷰 mean → 제품 mean | 0.671 | 32.5 | — |
| 뷰 mean → 제품 **max**(운영 v2 입력) | 0.669 | 36.4 | Recall 94.5% / FP 2,754 |
| 뷰 mean → top2/top3 | 0.679/0.675 | — | max와 유사 |
| 뷰 mean → median | 0.655 | 31.5 | 가장 약함 |
| **hvq_max16_max(저장)** | **0.816** | **82.6** | AUROC +0.15, FP 738 |

→ heatmap_mean의 전체 평균 집계는 국소 신호를 희석한다. 작은 결함 희석이 FN을 만들고, max16은 배경 노이즈 폭주를 함께 키운다(제한 사항).

## 5. Phase 5 — 임계값·정규화 검증(hvq_threshold_sweep.csv, figures/threshold_sweep.png)

- 오류 임계값 81.0은 정상·불량 분포 모두 오른쪽에 존재(분포도 참조) — min-max 정규화 후 1.37에 해당, 어떤 제품도 도달 불가.
- 정규화 파라미터·퓨전 TH는 Val 전용(보고서 확인). HVQ 참고 임계값도 Val 적합 36.0244로 교정.
- NaN/Inf/상수범위는 평가 스크립트가 거부(기존 테스트). Test 기반 임계값 조정은 수행하지 않음.

## 6. Phase 6 — 5시점 집계 검증

- 현행 운영 규칙(C1~C5 최대값)은 변경 없음. 비교 집계(mean/top2/median)는 모두 max보다 AUROC가 낮아(0.655~0.679) 현행 max가 합리적.
- "하나 이상의 시점 불량이면 제품 불량"은 max와 동일. 다수결은 미검출을 키울 수 있어 채택하지 않음(분석 근거).

## 7. Phase 7 — 품목·결함 유형별(hvq_category_metrics.csv, hvq_defect_type_metrics.csv, figures/category_fnr.png)

- 교정 참고 기준 품목별 FN: 결함 12,408 중 613(FNR 4.94%). 품목별 FNR 범위는 category_fnr.png(일부 품목에서 10% 안팎).
- 결함 유형 8종(ZW/QS/HS/AK/CH/BX/PS/기타) 전수 집계 완료 — ZW FN 117, QS 160, HS 140 등.
- **결함 면적 구간별 미탐률은 미산출**: 원본 마스크 PNG 경로(`inference_cohort_120000/manifest.csv` mask_path) 대조 필요하나 Real-IAD Train NG 미주석 마스크(unknown 18,632)로 유효 면적 분모가 불완전해 신뢰 구간을 만들 수 없음. 대신 맵 보유 51개 결함 표본으로 대체 분석(Phase 9).

## 8. Phase 8 — RT-DETRv2와 상호 보완성(model_complementarity.csv)

불량 12,408제품 기준(교정 참고 양성 사용):
- A(둘 다 검출) 11,720(94.5%) / B(RT만) 607(4.9%) / **C(HVQ만) 75(0.6%)** / D(둘 다 미탐) 6(0.05%).
- 정상 11,592: HVQ 총 FP 9,195건(N_both_fp 2,219 + N_hvq_fp_only 6,976 — 6,976은 RT 미동반 subset. 초기 본문이 이를 총 FP처럼 표기한 오류는 followup/METRIC_CONSISTENCY_REPORT.md에서 정정) — HVQ는 단독 게이트로 부적합(퓨전에서 RT가 오탐을 억제).
- 결론: HVQ 단독 Recall은 높으나 정밀도가 낮고, RT가 놓친 결함을 HVQ가 크게 보완하지는 못한다(75건). 퓨전 개선(구 0.9428→신 0.9532)은 주로 HVQ 연속 점수의 순위 보정 기여.

## 9. Phase 9 — 실제 미탐 사례(fn_mapped_analysis.json, figures/fn_cases_grid.png)

- 저장 원시 맵 보유 결함 제품 51개 중 FN **3개**(소표본 — 전체 613 FN의 표본이 아님).
- 3건 모두 맵에 이상 반응은 존재하나 map_max 83~103으로 TP 평균(119.8)보다 약하고, 제품 점수는 TH(36.0) 바로 아래(34.1~34.9) → 원인 분류: **신호 존재 + 집계/임계값 경계**(전체 평균 희석 + 품목 분포 경계), 순수 미검출(모델 한계)은 부분적.
- 원시 맵 없는 제품에는 가상 맵을 만들지 않았다. 원본 이미지·마스크 대조는 GUI 근거 뷰어로 가능(제품 ID 목록: hvq_false_negative_cases.csv).

## 10. Phase 10 — DB·API·GUI 정합성(database_consistency.json)

- SQLite 원본 120,000/24,000 = PostgreSQL 예측 48,000(v2 24,000 활성 + 구 max16 24,000 보존) — 일치, 이전 run/점수 혼용 없음.
- API `/performance/final`이 파일 기준으로 정정된 단독 지표를 서빙(0.7063). GUI는 API 필드 소비 — 코드 변경 불필요. NULL→0 처리·축 반전·분모 오류 발견 없음.

## 판정

**EVALUATION_ERROR(확정·수정 완료)**, SCORE_AGGREGATION_LIMITATION(heatmap_mean 전체 평균 희석), MODEL_LIMITATION(보조 — 맵 소표본의 약한 신호), INSUFFICIENT_EVIDENCE(결함 면적 구간 미탐률 — 마스크 분모 불완전).
