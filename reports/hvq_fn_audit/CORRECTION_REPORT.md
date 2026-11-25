# CORRECTION_REPORT — 수정 전후 기록

## 수정 항목(Phase 11.A: 평가·표시 오류 확정에 따른 정정)

### 코드
- `scripts/report_minmax_fusion.py`
  - `fit_single_model_reference()` 신규: Validation heatmap_mean min-max 정규화 → `threshold_and_margin`로 참고 임계값 적합(원척도 36.0244).
  - `hvq_positive`를 max16 임계값(81.0) 대신 적합 임계값으로 판정.
  - performance.json에 `single_model_reference` 계보 추가. `notes`의 구 분할 문구도 함께 정정(학습 미사용 명시).
  - **불변**: profile/parameters/퓨전 가중치·정규화·TH·margin·판정 로직 일절 변경 없음. `model_version` 해시 동일.

### 재산출(파생 통계 갱신)
- `reports/final_performance_minmax/performance.json`, `all_predictions.csv`(hvq_positive열), `latest.json` 재생성.
- 퓨전 혼동행렬 전수 동일(전체 TP12102/FN306/FP474/TN11118, Test 1752/86/86/1669 — 수정 전 백업과 대조).
- API `/performance/final`이 파일을 즉시 반영(서버 재시작 불필요) — `check_final_sync.py` **VERIFIED**.

### 수정 전후 수치

| 지표 | 수정 전(오류) | 수정 후(정정) |
|---|---|---|
| HVQ 단독 FN(전체) | 12,408 (FNR 100%) | 613 (FNR 4.94%) |
| HVQ 단독 Recall(전체) | 0.0 | 0.9506 |
| HVQ 단독 F1(전체) | 0.0 | 0.7063 |
| HVQ 단독 FN(Test) | 1,838 | 82 (Recall 0.9554) |
| 퓨전 전체 F1 | 0.968780 | 0.968780 (불변) |
| 퓨전 Test F1 | 0.953210 | 0.953210 (불변) |

### 회귀 테스트
- 신규 `test_single_model_hvq_reference_is_validation_fitted_not_max16_default`(적합 출처·scale 분리·참고 sanity).
- 기존 계약 테스트 4건 수정 없이 통과(에러 메시지 정렬 1건은 'minmax range' 문구 통일).

### 원시 데이터 보호
- 저장 점수 SQLite·원시 맵·운영 DB 판정·구 max16 예측 24,000행: **무수정**.
- 모델 가중치·추론 결과·퓨전 계약: 변경 없음.

## 변경하지 않은 것(한계·보류)
- 운영 퓨전 계약(max16 계열 변경 검토 등): 별도 사용자 승인 전까지 유지.
- 결함 면적 구간별 미탐률: Real-IAD Train NG 미주석 마스크(unknown 18,632)로 분모 불완전 — 미산출(가짜 데이터 생성 금지 원칙).
- 모델 재학습/추가 추론: 승인 없음 — 미실행.

## 정정 이력(2026-11-25 후속 검증)
- HVQ_FALSE_NEGATIVE_AUDIT.md Phase 8의 "정상 HVQ 단독 오탐 6,976건"은 RT 미동반 subset이며 총 FP는 9,195다.
  F1 0.7063은 FP 9,195 기준 binary F1로 수학적으로 정확(독립 재계산 일치). 문서 표기만 본 보고서와
  followup/METRIC_CONSISTENCY_REPORT.md에서 정정. 성능 수치·코드 추가 변경 없음.
