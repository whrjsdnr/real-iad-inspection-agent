#!/usr/bin/env bash
# Run on the host. Starts only the read-only report generator, never inference/services.
set -euo pipefail
REPORT_AGENT_ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
REPORT_LOG="$REPORT_AGENT_ROOT/reports/gui_validation/sync-final/report-host.log"
REPORT_LOCK="$REPORT_AGENT_ROOT/reports/gui_validation/sync-final/report-host.lock"
REPORT_PID="$REPORT_AGENT_ROOT/reports/gui_validation/sync-final/report-host.pid"
REPORT_PATTERN='(^|/)(python[0-9.]*|uv)[[:space:]].*report_(fusion_performance|minmax_fusion)[.]py([[:space:]]|$)'
if pgrep -af "$REPORT_PATTERN"; then
  printf '%s\n' 'Report generator already running; no duplicate started.'
  exit 0
fi
command -v flock >/dev/null
mkdir -p -- "$(dirname -- "$REPORT_LOG")"
cd -- "$REPORT_AGENT_ROOT"
nohup flock -n "$REPORT_LOCK" env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  "$REPORT_AGENT_ROOT/.venv/bin/python" scripts/report_minmax_fusion.py \
  > "$REPORT_LOG" 2>&1 < /dev/null &
REPORT_CHILD=$!
printf '%s\n' "$REPORT_CHILD" > "$REPORT_PID"
sleep 1
if kill -0 "$REPORT_CHILD" 2>/dev/null; then
  printf 'Started report launcher PID %s\nLog: %s\n' "$REPORT_CHILD" "$REPORT_LOG"
else
  if wait "$REPORT_CHILD"; then
    printf 'Report command finished successfully. Log: %s\n' "$REPORT_LOG"
  else
    printf 'Report command exited unsuccessfully. Log: %s\n' "$REPORT_LOG" >&2
    exit 1
  fi
fi
