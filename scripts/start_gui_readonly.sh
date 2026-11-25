#!/usr/bin/env bash
# Start only two NEW development children; never restart an existing server.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
if [[ ! -f .env ]]; then
  echo 'Missing .env with DATABASE_URL_READ. Existing operational configuration is not modified.' >&2
  exit 1
fi
if [[ -n "${VITE_API_BASE:-}" ]]; then
  echo 'Unset VITE_API_BASE to use the same-origin /api proxy.' >&2
  exit 1
fi
.venv/bin/python - <<'PY'
import socket
for port in (18080,15173):
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',port))
        except OSError:raise SystemExit(f'Development port {port} unavailable. No existing process was stopped.')
PY
.venv/bin/python scripts/with_env.py --env-file .env -- .venv/bin/python -m uvicorn app.readonly_api:app --host 127.0.0.1 --port 18080 > /tmp/inspection-gui-readonly-api.log 2>&1 &
GUI_READONLY_CHILD=$!
cleanup() {
  # This PID was created by this script and is the read-only gateway only.
  kill "$GUI_READONLY_CHILD" 2>/dev/null || true
  wait "$GUI_READONLY_CHILD" 2>/dev/null || true
}
trap cleanup EXIT
.venv/bin/python - <<'PY'
import time,urllib.request
for attempt in range(30):
    try:
        with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=2) as r:
            if r.status==200:break
    except OSError:time.sleep(.5)
else:raise SystemExit('Development API did not start. Check /tmp/inspection-gui-readonly-api.log; no operational process was restarted.')
PY
printf '%s\n' 'Open http://127.0.0.1:15173/ — read-only development; inference/review writes disabled.'
GUI_API_TARGET=http://127.0.0.1:18080 npm --prefix inspection-gui run dev -- --host 127.0.0.1 --port 15173 --strictPort
