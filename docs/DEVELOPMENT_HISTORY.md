# 개발 이력

날짜는 산출물 디렉터리명·보고서 타임스탬프·Git 커밋 기록 기준이다.

## 2026-11-06 ~ 11-12 — 데이터 분석(~/MV)
- 30품목 메타데이터·밝기 분포·해상도 정보 손실 분석(`outputs/full_20261111_*`, `content_audit_20261111_v7`).
- 제품 ID 충돌 4,197개 발견 → 결함 폴드 포함 ID로 전환(`filename_class_resolution_v1`).
- 마스크 정합성·이진화 점검(`mask_integrity_20261111_v6`).

## 2026-11-12 ~ 11-17 — 전처리(~/MV)
- 객체 중심 Crop 비교·수동 재검수(`bbox_review_fix_20261112_v1`, `adaptive_crop_*_20261117_v1`).
- 정책 확정: 이상탐지는 승인 Crop, 객체탐지는 원본 전체 이미지.

## 2026-11-16 ~ 11-20 — 모델 연구(~/MV)
- 12종 모델 학습/평가 인프라와 공통 러너.
- PatchCore·EfficientAD-S·INP-Former 등 성능 보고(`PERFORMANCE_*_20261119.md`).
- HVQ-Trans native 평가(`HVQ_TRANS_EVAL_NATIVE_20261119.md`), 최종 선정(`FINAL_12MODEL_TRAINING_REPORT_20261120.md`).
- ONNX 최적화 비교(`optimize_compare*.py`).

## 2026-11-23 — 추론·적재·DB 구축(~/agent)
- batch5(C1~C5) 추론 목록 작성, 24,000제품·120,000시점 추론 시작(`agent_integration_20261123_v1`).
- DB 복구(테스트 30→47 통과), SQLite→PostgreSQL 이관 준비, 읽기전용 역할 설계.
- 이 단계 이전: pytest 18 passed/5 errors → 복구 완료.

## 2026-11-24 — 퓨전 평가·확정
- 120,000시점 추론 완료(실패 0). max16 기준선 보고서(`fusion_agent_validation_20261124_v1`).
- 계약 v2 별도 평가: `report_minmax_fusion.py` → `reports/final_performance_minmax/`. Test F1 0.953210.
- 부위 히트맵 구현(`app/part_heatmap.py`), 칫솔 1표본 native ROI 등록·육안 검증.
- GUI: V6 테마 재구성, 3D 상세 메시(103개 표면), 카테고리 중첩 수정, 비동기 추론 JobStore.

## 2026-11-24(계속) — 계약 v2 운영 활성화
- `activate_fusion_contract_v2.py`로 저장 점수 재판정 24,000제품 → PostgreSQL 활성 run 등록(구 run 보존).
- 보고서와 DB 판정 전수 대조 오차 0. metrics_snapshots에 기준선 v2 20행.

## 2026-11-25 — 공간 히트맵·3D 표면·공유
- ROI 템플릿 30품목 전수 등록(실제 이미지 육안 확인), derive 전 품목 실행.
- HVQ 저장 맵 상대경로 누락 복구(실제 500맵/100제품 확인).
- 사용자 승인 하에 근사 3D 표면 투영(DataTexture+ShaderMaterial) 구현.
- 공유 패키지 재생성(649파일), 개발 게이트웨이 신코드 기동 검증.
- 백엔드 133 passed/4 skipped, 프런트 135 passed/23 파일 확정.

## 잔여
- 운영 :8000 신코드 배포(승인 대기), GUI 추론 v2 E2E 재검증, 물리 UV 정합,
  HVQ 맵 100제품→확장, 실브라우저 스크린샷.
