# 검사 스키마와 기획 개념 매핑

2026-11-23 조사·복구. 기존 테이블명을 유지한다. 연결은 `app.db`를 공통 사용하며 `DATABASE_URL` 미설정 시 저장소 루트 `inspection.db`로 연결한다. `dbconn`은 같은 엔진을 재사용한다. 선택적인 READ/REVIEW URL은 DATABASE_URL로 폴백한다.

| 테이블 | 기획 개념 | 키·현재 역할 |
| --- | --- | --- |
| inspection_attempts | 제품 검사 시도 / products 판정 | attempt_id PK, product_id는 제품 논리 ID. 같은 제품에 모델별 검사 가능. status, verdict, truth_label, review_status, model_version, mapping_version |
| inspection_views | views / 제품 C1–C5 촬영 | view_id PK, attempt_id로 검사 연결. camera_id, 원본/맵 URI, width/height |
| findings | evidences / 모델·검수 근거 | finding_id PK, view_id 연결. source, kind, score, bbox, part_id, map_uri, meta_json. HVQ 스코어 존재 자체는 양성 경보가 아님 |
| reviews | 부위·시점 검수 | review_id PK, product_id/part_id/camera_id, pending/confirmed, truth_label/corrected_label, FP/FN, reviewer_id, updated_at, version |
| users | 검수자·운영자 | user_id PK, name unique, role. 현재 이름 기반 등록이며 인증/권한 통제 완료를 의미하지 않음 |
| metrics_snapshots | 지표·기준선 이력 | snapshot_id PK. metric, definition_version, numerator, denominator, value, reason, item/part/camera, date_from/to, model_version, mapping_version, computed_at |

`migrate.py`는 SQLite 기존 스키마에 누락 컬럼/테이블을 추가하고 reviews.version의 NULL을 1로 보충한다. 기존 데이터는 삭제하지 않는다. PostgreSQL은 기존 Alembic 경로를 사용하며 이번 실행에서는 Docker 소켓 접근 불가로 검증하지 못했다.

검수 수정은 SQLAlchemy `version_id_col`을 사용한다. 갱신 SQL에 이전 version을 조건으로 넣고, 경합 시 HTTP 409를 반환한다. submit_review API는 expected_version을 받는다. 기존 수동 박스 PK의 중복 INSERT는 merge로 수정했다. 신규 검수 동시 생성의 유일성, 부위별 수정 대상 선택, 사용자 인증은 아직 별도 해결이 필요하다.

## 지표 정의

| 지표 | 분자 | 분모 |
| --- | --- | --- |
| 제품 Recall | TP | TP+FN |
| 제품 FPR | FP | FP+TN |
| 제품 F1 | 2TP | 2TP+FP+FN |
| 부위 미탐률 | 놓친 불량 제품 | 해당 부위 불량 확인 제품 |
| 부위 오탐률 | 잘못 경보한 정상 제품 | 해당 부위 정상 확인 제품 |
| 확정 불량률 | 불량 확인 제품 | 검수 제품 |
| 촬영·처리 실패율 | 누락·흐림·추론 오류 검사 시도 | 전체 검사 시도 |

확정 지표는 GT/확정 검수 근거가 필요하고, 검수 전 데이터는 의심 건수만 표시해야 한다. 현재 metrics.py는 제품 지표에서 보류를 제외하므로 보류 건수/판정 커버리지를 함께 표시해야 한다. 제품 단위 중복 제거·검수 반영, 부위 지표의 모델 기준선 조인, pending 비율 표시 방지, AUPRO의 FPR 축 적분 등은 남아 있는 갭이다. 현 구현이 모든 정의를 충족한다고 간주하면 안 된다.

기준선 v1의 실제 Val 수치 등록은 원본 Val과 제품 ID 확인 후 수행한다. 요청 목표를 측정값으로 대체하지 않는다.

## 승인 대기 중인 제품 ID

기존 파일명 파서의 `품목_정상불량_일련`은 다른 결함 폴더의 제품을 합친다. 저장소 annotation manifest의 `품목/정상불량/결함/S번호`는 이를 구분한다. 조사상 30,210개 manifest 제품이 기존 파서로 19,378개가 되며 4,197개 ID가 충돌한다. 사용자 확인 전에는 ID를 변경하거나 실데이터를 기록하지 않는다. 목 데이터의 mock:// URI와 ID는 유지한다.


## 재구성 출처 컬럼과검수서비스역할

metrics_snapshots에source_scope,baseline_kind,split_reference,review_status를가산했다. reference_baseline은팀원전달수치이고measured_baseline은현재검증된실측이다. 기존열/테이블명은유지한다. PostgreSQL에는누락된뷰width/height도가산한다. SQLite이관은새빈대상에한트랜잭션으로수행하며기존행이있으면덮어쓰지않고중단한다. 원시점수의verdict=NULL은정상이나보류가아니라TH미확정이다. app_read=SELECT,app_review=SELECT+reviews INSERT/UPDATE,app_workflow는별도백엔드서비스의필수연관쓰기권한이다.
