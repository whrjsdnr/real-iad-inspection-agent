# 팀원 읽기 전용 공유

**IMPLEMENTED / 자동 보안검사 VERIFIED / 호스트서비스 기동 BLOCKED**. 이 실행환경에서 socket생성이 EPERM으로 막혔다. 실제공유주소는 아직 열리지 않았다. 운영서버/DB스키마/계정/추론 프로세스는 변경하지 않았다.

기존 DATABASE_URL_READ를 이용하는 별도 FastAPI와 빌드된 GUI를 같은포트로 제공한다. DB포트를 팀원에게 공개하지 않는다. 접속키 로그인 후 서명된8시간 HttpOnly/SameSiteStrict cookie를 발급한다. 허용된읽기도구와 GET만 제공하며 검수쓰기·추론실행·임의LLM코드실행은 제공하지 않는다. GUI도 읽기전용을 표시한다.

config/team-share.env는 이미권한600으로 생성됐으며 gitignore 대상이다. **파일전체/DB URL을 공유하지 말고 TEAM_ACCESS_TOKEN 값만 신뢰할 팀원에게 별도전달한다.** 공통키 방식이며 개인별계정/감사/검수동시편집은 범위밖이다.

## Ubuntu 호스트에서 실행

```bash
cd /home/geonug/agent
# 이미 생성된키는 유지한다.
.venv/bin/python scripts/setup_team_share.py
# 같은 LAN/VPN의 호스트에서 새포트로 실행. 기존서비스는 중단하지 않는다.
TEAM_BIND_HOST=0.0.0.0 TEAM_SHARE_PORT=18081 nohup bash scripts/start_team_share.sh > reports/gui_validation/spatial/team-host.log 2>&1 &
```

팀원은 `http://<이 Ubuntu 서버의 LAN/VPN IP>:18081`에 접속해키를 입력한다. 방화벽은 필요한 LAN/VPN 범위만 운영자가허용해야 한다. 현재 실행환경에서 호스트주소/포트연결/실제DB조회는 확인하지 못했다. 공용인터넷에는 이HTTP주소를 직접노출하지 말고 기존HTTPS접근계층/VPN을 사용한다. HTTPS배포시 TEAM_COOKIE_SECURE=1을 설정한다. 인터넷공개/운영서버재시작은 수행하지 않았다.

로그: reports/gui_validation/spatial/team-host.log. 새포트가 이미사용중이면 스크립트가실패하고 기존프로세스를종료하지 않는다. 롤백은 이새서비스만 종료하고 기존운영서비스는 그대로둔다.

호스트 실제GUI 캡처:

```bash
GUI_VALIDATION_URL=http://127.0.0.1:18081 .venv/bin/python scripts/with_env.py --env-file config/team-share.env -- node scripts/capture_spatial_validation.mjs
```

Playwright sandbox를 유지한다. 결과스크린샷은 reports/gui_validation/spatial/screenshots/<시각> 아래에 생성되며 캡처후사람의육안검토가 필요하다. config파일이 아닌접속키만 전달해야 한다.
