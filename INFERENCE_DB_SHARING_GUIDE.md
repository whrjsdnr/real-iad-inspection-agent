# Batch5 추론 → DB 적재 → 팀 공유

## 현재 상태와 정책

HVQ79ep : RT15ep EMA의 **30:70 + 품목별 기준TH**를 유지한다. 두 모델 모두 동일 제품의 C1–C5를 **batch5**로 입력한다. 제품별5장 max 이후 Val 백분위·가중합을 적용하는 정책이다. 다만 품목별 lookup/TH는 아직 복구되지 않았다. 따라서 현재 저장물은 **미보정 원시 점수/박스/맵**이고 정상·불량·보류 판정은 NULL이다. 팀원 보고의 F1 .9314는30품목 macro F1 참고치이며 현 환경 실측이 아니다.

신규코호트24,000제품/120,000장. 기존 학습3만장과 중복 여부 UNKNOWN. 원래 학습에 사용하지 않은12만장을 복구했다고 주장하지 않는다. 모델 학습이나 원본 이미지 변경은 하지 않는다.

## 1. 이미 실행 중인 배치 확인

서버 Ubuntu 터미널, 어느 폴더에서도 실행 가능하다. **현재 전량 추론이 실행 중이므로 두 번째 프로세스를 실행하지 않는다.**

```bash
cat ~/MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1/state.json
cat ~/MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1/pipeline_state.json
tail -f ~/MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1/full_batch.log
```

`completed`는 완료 제품 수, 이미지 수는 completed×5다. `failed`는 처리 실패 제품 수이며 실패를0점으로 치환하지 않는다. `Ctrl+C`로 tail만 종료해도 추론은 계속된다. PID는 `full_batch.pid`, 관리자는 `supervisor.pid`에 저장된다. state는25제품마다 갱신된다.

100제품/500장 파일럿: 실패0, 평균4.008초/제품, p95 3.759초, 피크1517.64MiB. 파일럿기반 잔여약26.6시간은 예측치이며 실제 ETA는 state를 따른다. 자동 판정 정확도나 보류율은 아직 미평가다.

## 2. 중단된 경우에만 추론 재개

`~/agent`에서 실행한다. 같은 manifest·모델·설정 해시만 재개된다. 이미 처리한 제품은 건너뛴다. 프로세스가 아직 실행 중이면 lock 오류로 거부한다. 새 실험을 하려면 새로운 output 경로와 출처를 사용한다.

```bash
cd ~/agent
~/MV/inference/.venv/bin/python -u score_batch.py \
  --manifest ~/MV/outputs/agent_integration_20261123_v1/inference_cohort_120000/manifest.csv \
  --data-root ~/MV/dataset \
  --mv-root ~/MV \
  --config ~/MV/outputs/agent_integration_20261123_v1/inference_config_batch5.json \
  --output ~/MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1 \
  --save-maps-products 100 \
  --resume
```

완료된 제품은 cache에 이미 있으므로 다시 모델을 실행하지 않는다. 실패 제품만 다시 시도하려면 원인을 확인한 뒤 `--retry-failed`를 추가한다. 이전 오류 기록과 log는 보존한다.

## 3. DB 준비 — 관리자 1회 작업

`.env`를 그대로 공유하지 않는다. `.env.example`에는 키/예시만 있다. 실제 `.env`는 기존 값을 보존하고 관리자에게 확인한다. `DATABASE_URL`은 명령별로 적절한 계정을 선택한다.

|환경변수|목적|
|---|---|
|DATABASE_URL|앱 기본 연결; 마이그레이션 때만 관리자 URL을 별도 환경파일로 제공|
|DATABASE_URL_READ|조회 로그인 계정(app_read 그룹)|
|DATABASE_URL_REVIEW|reviews 직접 쓰기 로그인 계정(app_review 그룹)|
|DATABASE_URL_WORKFLOW|검수 API 연관 트랜잭션 서비스 계정(app_workflow 그룹)|
|DATABASE_URL_BATCH|추론 결과 적재 서비스 계정(app_batch 그룹)|

운영 DB를 먼저 백업한다. 아래 `.env.admin`은 **사용자가 준비하는 별도의 관리자용 환경파일** 예시 이름이며 현재 자동 생성돼 있지 않다. 실제 자격증명을 코드·명령 이력·문서에 붙여 넣지 않는다. 기존 DB/볼륨 삭제는 하지 않는다.

```bash
cd ~/agent
# 관리자 URL이 있는 파일 경로로 .env.admin을 바꾼다.
PG_CONTAINER=inspection-postgres .venv/bin/python scripts/with_env.py \
  --env-file .env.admin -- bash scripts/backup.sh ./backups

.venv/bin/python scripts/with_env.py --env-file .env.admin -- \
  .venv/bin/python -m alembic upgrade head

# 역할별 권한을 현재 DB에 적용한다. 원본 테이블은 삭제하지 않는다.
docker compose exec -T postgres sh -c \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < scripts/setup_roles.sql
```

마이그레이션 성공 시 Alembic head `d4e8c7a012bc`다. **새 진단DB**에서 스키마 생성·원본40/198/50/121행 이관·권한·낙관적잠금·별도DB 백업/복원은 검증했다. 운영DB에 같은 작업을 대신 실행한 것은 아니다. `sqlite_to_pg.py`는 대상이 비어 있을 때만 이관하며 기존 행이 있으면 중단한다. 두 DB가 이미 서로 다른 데이터를 가지고 있으면 임의 병합하지 않는다.

로그인 계정은 관리자가 PostgreSQL 대화형 셸에서 발급하고 `\password`로 비밀번호를 입력한다. 아래 이름은 예시다. 이미 존재하면 새로 만들거나 비밀번호를 임의 변경하지 않는다.

```sql
CREATE ROLE team_view LOGIN IN ROLE app_read;
\password team_view
CREATE ROLE inspection_batch LOGIN IN ROLE app_batch;
\password inspection_batch
CREATE ROLE inspection_workflow LOGIN IN ROLE app_workflow;
\password inspection_workflow
```

`app_review` 권한은 reviews INSERT/UPDATE로 유지한다. 사용자 생성·수동 finding·검사 상태 동시 갱신은 app_workflow 서비스로 처리한다. 배치 적재용 권한을 app_read/app_review에 추가하지 않는다. 마이그레이션 관리자로 API를 계속 운영하지 않는다.

## 4. 추론 결과를 DB에 넣기

모델 재추론 없이 **완료된 제품만** 읽어 적재한다. 진행 중에도 WAL 읽기로 이미 완료된 결과를 가져올 수 있다. 실패·미완료 제품은 제외한다. 같은 버전/제품은 skip하여 중복 적재하지 않는다.

먼저 `.env`의 DATABASE_URL_BATCH가 적재 대상 PostgreSQL의 batch 로그인 계정인지 확인한다. 환경파일은 사용자 소유의 신뢰하는 파일만 사용한다. 다음은 **운영 DB에 쓰는 명령이므로 대상 설정을 확인한 후 사용자가 실행**한다.

```bash
cd ~/agent
.venv/bin/python scripts/with_env.py --env-file .env -- \
  .venv/bin/python import_score_batch.py \
    --score-db ~/MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1/scores.sqlite \
    --data-root ~/MV/dataset \
    --limit-products 100
```

정상 출력 예: `added:100, skipped:0`. 다시 실행하면 `added:0, skipped:100`. 이 동작은 실제100제품으로 진단PG에서 검증했다. 전체 완료분을 넣으려면 `--limit-products 100`을 제거한다. 이후 같은 명령을 실행해 신규 완료분만 추가할 수 있다. **추론 프로세스는 DB 적재와 별도이며, 현재 점수 캐시에 쌓이는 결과가 운영DB에 자동 적재되는 것은 아니다.**

원시점수 버전은 `uncalibrated-scores:<binding hash>`로 기록된다. `verdict=NULL`, `review_status=pending`이다. NULL은 정상도 보류도 아니며 TH 미확정이다. NG를 정상 Negative로 바꾸지 않는다. 초기100제품에만 raw map을 보존했고 나머지는 점수·박스를 저장한다.

CSV가 필요하면 새 출력 파일명을 사용한다.

```bash
.venv/bin/python export_scores.py \
  --score-db ~/MV/outputs/agent_integration_20261123_v1/score_run_batch5_v1/scores.sqlite \
  --output ./reports/raw_scores_export_01.csv
```

## 5. 팀원이 같은 내용을 보는 방법 — 권장: API 공유

**DB 파일을 각자 복사하면 공동 DB가 아니다.** PostgreSQL 한 곳을 유지하고 팀원은 같은 API 주소를 보도록 한다. 이미지 원본은 서버에만 있어도 된다. `/evidence/{view_id}/image`가 서버의 원본을 전달하므로 클라이언트의 로컬 경로가 같을 필요는 없다. DB만 복사하면 이미지가 함께 전달되는 것은 아니다.

서버의 `~/agent`에서, 기존8080 서버가 있는지 먼저 확인한다. 기존 서버는 이번 작업에서 임의로 종료하지 않았다. 이미 사용 중인 포트에 두 번째 서버를 띄우지 않는다. 아래는 관리자가 재기동할 때의 명령이다.

```bash
cd ~/agent
.venv/bin/python scripts/with_env.py --env-file .env -- \
  .venv/bin/python -m uvicorn app.api:app --host 0.0.0.0 --port 8080
```

서버 LAN/WSL 주소는 `hostname -I`로 확인한다. 팀원 GUI의 `inspection-gui/.env.local`에 서버 주소를 지정하고 Vite를 재시작한다. `<서버-IP>`는 실제 접근 가능한 주소로 바꾼다.

```text
VITE_API_BASE=http://<서버-IP>:8080
VITE_USE_FIXTURE=false
```

서버 `config/web.json`의 allowed_origins에는 **팀원 브라우저가 여는 GUI의 origin**도 추가한다. 예를 들어 팀원이 자신의 PC `http://localhost:5173`에서 GUI를 열면 localhost origin이고, 서버의 Vite 주소로 열면 `http://<서버-IP>:5173`다. CORS 설정과 방화벽은 서로 다르다. Windows+WSL에서는 localhost forwarding이 LAN 공유까지 보장하지 않으므로 Windows 방화벽/WSL 네트워크 모드·포트 전달도 확인한다. PostgreSQL5432를 인터넷에 노출할 필요는 없다.

접속 확인: 팀원 PC 브라우저에서 `http://<서버-IP>:8080/health` → GUI에서 fixture가 아닌 `api` 출처 확인 → 실제 제품 ID로 사례 조회 → C1–C5 전환. 실제5개 원본의 HTTP200/JPEG 바이트는 진단API에서 검증했고, 실제 브라우저 E2E는 미검증이다.

현재 API의 본격적인 사용자 인증·TLS는 완료되지 않았다. 신뢰하는 팀 내부망에서 사용하고, 외부 공개 전 인증/권한 검증을 추가한다. 검수자 이름 입력과 PostgreSQL 역할은 웹 로그인 인증을 대신하지 않는다.

## 6. DB 직접 접속이 꼭 필요한 경우

같은 DB 호스트/포트/DB명을 사용하고 조회만 하는 팀원에게는 app_read 소속 로그인 계정만 발급한다. 예시 연결 문자열은 `postgresql://team_view:<password>@<서버-IP>:5432/inspection`이며 실제 비밀번호를 문서/채팅에 저장하지 않는다. PostgreSQL 포트 바인딩·pg_hba.conf·호스트 방화벽에서 팀원 IP만 허용해야 한다. 일반 GUI 사용자는 직접DB 접속 대신 API를 쓰는 편이 단순하다.

팀원에게 전달할 것: Git/코드, API 주소, GUI 환경설정 예시, 필요시 조회 계정. 전달하지 않을 것: 관리자 `.env`, DB관리자 비밀번호, 원본 승인 Ledger, 가중치/데이터 전체. 별도 허가된 파일 배포는 이와 구분한다.

## 7. 아직 하지 않는 것

품목별Val lookup/TH가 없으므로 실제자동퓨전 판정은 하지 않는다. 기존30:70 기준 정책은 유지되지만 **TH 숫자가 복원됐다는 뜻은 아니다.** 참고macroF1 .9314를 새 운영 성능으로 표시하지 않는다. 검수 전 FP/FN은 의심 건수이며 확정 지표가 아니다. `FUSION_RECOVERY_REPORT.md`, `STATUS.md`와 실행state.json을 함께 확인한다.


## 실제 제품 조회 확인 예시

API 재기동·DB 적재 후 아래처럼 조회할 수 있습니다. 예시 제품은 이번 진단100제품에 포함돼 있습니다.

```bash
curl -s http://127.0.0.1:8080/tools/get_case_evidence \
  -H 'Content-Type: application/json' \
  -d '{"product_id":"audiojack/NG/QS/S0006","camera_id":"C1"}'
```

`cases`에C1–C5의image_uri/error_map_uri가반환됩니다. raw map이저장된초기100제품은맵API도조회가능합니다. 그밖의제품은저장된원시점수/박스만있을수있습니다.
