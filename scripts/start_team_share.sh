#!/usr/bin/env bash
# Start a new read-only service only. Never stops existing services.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
TEAM_SHARE_PORT="${TEAM_SHARE_PORT:-18081}"
TEAM_BIND_HOST="${TEAM_BIND_HOST:-127.0.0.1}"
[[ -f config/team-share.env ]] || { echo '먼저 .venv/bin/python scripts/setup_team_share.py 실행'; exit 1; }
[[ -f inspection-gui/dist/index.html ]] || { echo '먼저 GUI production build 실행'; exit 1; }
.venv/bin/python - "$TEAM_BIND_HOST" "$TEAM_SHARE_PORT" <<'PY'
import socket,sys
try:
    with socket.socket() as probe:
        probe.bind((sys.argv[1],int(sys.argv[2])))
except OSError as error:
    raise SystemExit(f'공유 포트를 열 수 없습니다 ({error.strerror}). 기존 프로세스를 중단하지 않았습니다.')
PY
exec .venv/bin/python scripts/with_env.py --env-file config/team-share.env -- .venv/bin/python -m uvicorn app.team_api:app --host "$TEAM_BIND_HOST" --port "$TEAM_SHARE_PORT" --no-access-log
