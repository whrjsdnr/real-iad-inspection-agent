# 검사 데이터 공동 개발 패키지

실제 저장된 30품목/24,000제품/120,000시점을 팀 GUI·에이전트가 공통으로 읽기 위한 패키지다. DB 계정이나 DB 접속 없이 API만 사용한다. 검수 확정 통계, 원시 모델 신호, 보고서 전용 퓨전 결과는 서로 구분한다.

현재 검증: 실제 접속키 인증을 포함한 ASGI HTTP 라우팅·실데이터 조회 통과. 2026-11-25 기준 개발 읽기전용 게이트웨이(127.0.0.1:18080)에서 공유 API 전부 실응답 확인(새 코드 기동). 운영 중앙 서버(:8000)는 아직 구 코드라 /products·/fusion/runs·/heatmaps·/sharing/kit이 404다 — 배포 재시작은 담당자 승인 후 수행. 호스트 LAN IP는 172.24.157.10이며 18081 팀 공유 서비스 가동 시 해당 주소로 접근. samples는 실제 호출 응답이며 Mock이 아니다. 신규코드가 현재 운영 프로세스에 로드됐다고 보증하지 않는다.

## 호스트 담당자

기존 중앙 서버가 이번 소스를 배포했으면 기존 API 기본주소를 사용한다. 운영 재시작은 이번 작업에서 실행하지 않았다. 중앙 서버를 건드리지 않는 별도 공유 서비스도 준비돼 있다:

```bash
cd /home/geonug/agent
.venv/bin/python scripts/setup_team_share.py
TEAM_BIND_HOST=0.0.0.0 TEAM_SHARE_PORT=18081 nohup bash scripts/start_team_share.sh > reports/gui_validation/spatial-urgent/team-host.log 2>&1 &
```

팀원에게 실제 호스트 LAN/VPN 주소와 TEAM_ACCESS_TOKEN 값만 별도 전달한다. config/team-share.env 전체와 DB URL은 공유하지 않는다. 필요시 TEAM_ALLOWED_ORIGINS에 팀 GUI 출처를 쉼표로 지정한다. 기본값은 http://localhost:5173,http://127.0.0.1:5173 이다. 공용인터넷 주소를 새로 열거나 DB 포트를 공개하지 않았다.

## 팀원 4명

각자 로컬 GUI/에이전트에서 같은 기본주소를 사용한다. API 주소 예시는 `http://<호스트 LAN/VPN IP>:18081/api`이며 이 IP는 아직 실측·검증되지 않았다. 접속키는 Bearer 헤더로 전송한다. 공유키 방식이며 개인별 계정·검수쓰기 기능은 아니다.

```bash
export TEAM_API_URL='http://<실제 서버 IP>:18081/api'
# TEAM_ACCESS_TOKEN을 비공개 환경변수로 설정한 뒤 실행한다. 값은 커밋하지 않는다.
python examples/python_client.py
```

본 패키지에는 모델 가중치·전체 원본 이미지·전체 DB가 없다. 예제 응답, ROI/부위 정의, OpenAPI가 포함된다. 원본/NPY는 API로 읽는다. 실제 공간 배열을 3D 모델 표면에 표시하는 근사 투영 런타임을 포함한다. 물리 좌표의 실측 정합을 뜻하지 않는다.

기존 MV 마스크 기반150개 64×64 수치도 포함합니다. MV_HEATMAP_REUSE.md와 HEATMAP_CATALOG.json, heatmaps/*.json을 확인하세요. 마스크 API는 /heatmaps/catalog, /heatmaps/ground-truth, /heatmaps/metadata입니다.
