#!/usr/bin/env bash
# Local-only development preview; no operational process is stopped or restarted.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
[[ -f inspection-gui/dist/index.html ]] || { echo 'GUI production build가 필요합니다.'; exit 1; }
[[ -f reports/spatial_heatmap/index.json ]] || { echo '저장 공간 캐시가 없습니다.'; exit 1; }
exec .venv/bin/python -m uvicorn app.spatial_preview:app --host 127.0.0.1 --port "${SPATIAL_PREVIEW_PORT:-18082}" --workers 1 --no-access-log
