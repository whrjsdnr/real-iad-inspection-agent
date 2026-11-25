#!/usr/bin/env bash
# Resource-limited checks; no network calls, no operational DB/worker changes.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
mkdir -p reports/gui_validation
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 DATABASE_URL=sqlite:////tmp/gui-validation-test-only.db AGENT_MOCK=1 nice -n 10 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/tmp/gui-validation-final-tests > reports/gui_validation/final-pytest.log 2>&1
npm --prefix inspection-gui test -- --pool=threads --poolOptions.threads.singleThread > reports/gui_validation/final-vitest.log 2>&1
npm --prefix inspection-gui run lint > reports/gui_validation/final-eslint.log 2>&1
npm --prefix inspection-gui run build > reports/gui_validation/final-build.log 2>&1
.venv/bin/python scripts/check_gui_integrity.py > reports/gui_validation/integrity.log
printf '%s\n' 'Checks passed. See reports/gui_validation/{final-*.log,integrity.json}.'
