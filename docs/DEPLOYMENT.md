# 배포·팀 공유 절차 (승인 후 실행)

작성일 2026-11-25. 각 절차는 사용자 승인 후 수행한다.

## 1. 운영 중앙 서버(:8000) 최신 코드 재배포

### 현황(2026-11-25 기록)
- 프로세스: PID 35145, 시작 2026-11-24 10:07:58, cmd `.venv/bin/python -m uvicorn app.api:app --host 0.0.0.0 --port 8000`, cwd ~/agent
- 환경: 부모 셸에서 .env 로딩(DATABASE_URL·DATABASE_URL_READ·DATABASE_URL_REVIEW·POSTGRES_*)
- 게이트웨이/개발: 18080(신코드 readonly, PID 1466463), Vite 15173 유지
- lifespan은 `migrate()`(가산·멱등) + recompute 워커 시작. 스키마 변경은 없음.

### 절차
```bash
cd ~/agent
kill 35145 && sleep 3
set -a && source .env && set +a
nohup .venv/bin/python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 > /tmp/inspection-api-8000.log 2>&1 &
echo $! > /tmp/inspection-api-8000.pid
```

### 검증(운영 포트)
```bash
for p in /health /docs /openapi.json /tools /fusion/runs /sharing/manifest /catalog/parts "/roi/templates?item=toothbrush" "/products?item=zipper&limit=1" "/products/findings?product_id=zipper%2FNG%2FBX%2FS0050&view=C1" "/parts/heatmap?item=toothbrush" /heatmaps/catalog "/heatmaps/ground-truth?item=toothbrush&view=C1" "/heatmaps/surface?item=toothbrush&view=C1&source=hvq" "/heatmaps/surface-layout?item=toothbrush&view=C1" /sharing/kit; do
  printf "%-75s " "$p"; curl -s -m 10 -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000$p"
done
```
- 칫솔·지퍼 실데이터 응답 확인: 제품 ID·split·64²/32² 배열 길이.
- GUI(15173) 새로고침 → 대시보드·3D·챗봇 정상.

### 롤백
- 신코드 기동 실패 시 로그(/tmp/inspection-api-8000.log) 확인 후 동일 명령 재시도.
- 구동은 이전 커밋 체크아웃 불가(구 실행 코드는 메모리 내). 데이터·스키마는 무손실이므로
  최신 커밋에서 수정 후 재기동이 원칙. 백업: ~/backups/agent-git-history-20261125.tgz.

## 2. 팀 공유 서비스(:18081) 기동

```bash
cd ~/agent
TEAM_BIND_HOST=0.0.0.0 TEAM_SHARE_PORT=18081 nohup bash scripts/start_team_share.sh > reports/gui_validation/team-host-18081.log 2>&1 &
```
- 사전 조건: config/team-share.env(권한 600, 실제 토큰)·inspection-gui/dist 빌드 완료 — 둘 다 충족(2026-11-25 확인).
- 읽기 전용(DATABASE_URL_READ), 임의 SQL 실행·DB 직접 접속 정보 미제공. 로컬 부트 자가테스트 통과(인증 성공/미인증 401).
- 팀원 전달: 주소 `http://192.168.20.164:18081/api`, Bearer 토큰만 별도 전달.

## 3. Windows LAN 공개(관리자 PowerShell)

기존 정책 유지: 8000번은 팀원 IP {192.168.20.170, .209, .168}만 허용하는 규칙이 이미 존재(portproxy 164:8000→WSL).

18081 추가 시(관리자 권한):
```powershell
netsh interface portproxy add v4tov4 listenaddress=192.168.20.164 listenport=18081 connectaddress=172.24.157.10 connectport=18081
New-NetFirewallRule -DisplayName "Inspection Share 18081 - Team" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 18081 -RemoteAddress 192.168.20.170,192.168.20.209,192.168.20.168
```
PostgreSQL 5432는 절대 공개하지 않는다. 인터넷 전체 공개 금지.

### 팀원 PC 검증 명령
```powershell
# PowerShell
Invoke-RestMethod -Uri http://192.168.20.164:18081/api/health -Headers @{Authorization="Bearer <TOKEN>"}
Invoke-RestMethod -Uri "http://192.168.20.164:8000/health"
```
```bash
# Ubuntu
curl -m 8 -H "Authorization: Bearer <TOKEN>" http://192.168.20.164:18081/api/sharing/manifest | head -c 200
curl -m 8 -o /dev/null -w "%{http_code}\n" http://192.168.20.164:8000/health
```

## 4. GitHub 업로드(비밀정보 정리·승인 후)
1. 이력 재작성: config/team-share.env를 전체 이력에서 제거(git filter-repo/filter-branch), `scan_secrets.py --all-history` 재검사.
2. 인증정보 교체: TEAM_ACCESS_TOKEN 재발급, DB 읽기 계정 비밀번호 변경(setup_team_share.py 재실행 후 18081 env 갱신).
3. MV: `git push origin main`(9커밋 앞서 있음). agent: Private 저장소 `real-iad-inspection-agent` 생성 후 push.
4. Release: tag v1.0.0 + team_integration_kit.zip 에셋(sha256 동봉).

## 5. 공유 데이터 권한
- ZIP에 실제 검사 데이터(ROI·배열·샘플 응답) 포함. Real-IAD 원본 데이터셋 재배포 조건과 팀 내 공유 범위를
  사용자가 확인·승인한 뒤 배포. 그 전까지 ZIP은 위에서 지정한 팀원 IP 대상으로만 제공.
