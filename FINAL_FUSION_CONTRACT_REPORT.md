# 최종 퓨전 계약 평가 — 2026-11-24

사용자 최종 확정: **RT-DETR0.7 + HVQ0.3, HVQ heatmap_mean, RT0.4, Validation min-max**. 이전 max16/백분위 보고서와 구분한다. 모델 추론을 다시 실행하지 않고 저장된120,000시점 점수로 별도 평가했다. 운영 설정·DB 판정은 수정하지 않았다.

## 실제 적용 계약

`config/fusion_evaluation.json`에 명시하고 `config/fusion.json`의 가중치/RT 임계값/HVQ 점수 정의와 일치하는지 검사한다.

1. 제품은 동일 ID의 C1–C5 정확히5개. 각 모델의 제품 점수는5시점 최대값.
2. RT는 저장된 검출 최대 신뢰도가0.4미만이면0. HVQ는 연속적인 heatmap_mean 점수를 사용한다. max16용 HVQ 임계값은 사용하지 않는다. 기존 HVQ81은 부가 단일모델 참고값에만 사용하며 퓨전 점수를 잘라내지 않는다.
3. Validation3,610제품에서 품목별·모델별 min/max 산출. `(점수−Val최소)/(Val최대−Val최소)` 적용. 상수 범위는 오류로 거부하며 실제30품목에는 없음. Val 범위 밖은 수식 그대로 외삽하며 확률로 해석하지 않는다.
4. **각 제품의 fusion_score = 0.7×RT_normalized + 0.3×HVQ_normalized.** 모델별 F1/Recall을 가중 평균하지 않는다.
5. 품목별 Val F1 최대 구간 중 가장 높은 구간의 중점 TH. 정점 대비 F1 하락0.005 이내 연결 구간에서 대칭 margin 산출. `abs(score−TH)≤margin`이면 보류, 그 외 score≥TH이면 불량.
6. 모든 정규화/TH/margin은 Val에서만 산출하고 Test에는 고정 적용. 전체24,000제품 참고 집계와 Test 성능을 분리한다.

## 결과

| 범위 | 제품 | Recall | F1 micro | FP / FN | AUROC | 보류 |
|---|---:|---|---|---|---:|---|
| 전체 참고 |24,000|12,102/12,408 =97.5338%|24,204/24,984 =0.968780|474 /306|0.992895|194/24,000|
| Test |3,593|1,752/1,838 =95.3210%|3,504/3,676 =0.953210|86 /86|0.986346|37/3,593|

보류 제외 확정판정: 전체 FP432/FN291, Test FP82/FN81. 보류를 정답 또는 정상으로 간주하지 않았다. 전체 집계는 Validation을 포함한다. 원본 train 분할은16,797제품이나 실제 임의 추출 학습목록과의 중복은 UNKNOWN이다. 기존98.84%나 원본600건 평가 재현으로 주장하지 않는다.

## 파일 및 검증

- `reports/final_performance_minmax/performance.json`: 계약/30품목 min-max·TH·margin/Val IDs/전체·Test·품목별 결과.
- 같은 디렉터리 `all_predictions.csv`:24,000제품의 원시점수·정규화 점수·가중합·판정. `latest.json`: 포인터.
- 모델 ID: `fusion-minmax-mean-rt40-w70-30:e917f9730ddb05d9c486b45d`.
- `reports/gui_validation/part-heatmap/minmax-contract-audit.json`:24,000제품 수식·TH·margin·판정 전수 확인, 가중합 최대 오차0. 별도 인메모리 SQLite SQL로 전체/Test 혼동행렬 일치 확인. 운영PG의 새 판정 검증은 아니다.
- `tests/test_minmax_fusion_contract.py`:20제품 fixture에서 Test 가중합, Test 라벨/점수 변경이 Val 보정에 영향 없음, 잘못된 가중치/상수 범위 거부.

재생성: `/home/geonug/agent/.venv/bin/python /home/geonug/agent/scripts/report_minmax_fusion.py`. 기존 `start_final_performance_report.sh`도 이 새 명령으로 변경했다. 외부MV의 `report_fusion_performance.py --wait`는 이전max16보고서용이므로 새 계약 재생성에 사용하지 않는다.

현재 코드 `app.status`는 명시적 FINAL_PERFORMANCE_DIR가 없으면 이 새 보고서를 우선 선택하고 설정 해시를 검사한다. GUI/도구 로컬 로더에서 실제24,000제품 새 값을 확인했다. 운영DB의 활성 run은 여전히 이전max16이며 `source_model_version`/`database_run_activated=false`로 구분했다. 운영 서버 재시작·배포는 하지 않아 실제 호스트API/브라우저 자동 반영은 미검증이다.
