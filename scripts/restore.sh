#!/usr/bin/env bash
set -euo pipefail
: "${RESTORE_DATABASE_URL:?Use a NEW EMPTY test database URL}"
: "${CONFIRM_EMPTY_RESTORE:?Set CONFIRM_EMPTY_RESTORE=YES for a new empty database}"
[[ "$CONFIRM_EMPTY_RESTORE" == YES ]] || exit 2
pg_url="${RESTORE_DATABASE_URL/postgresql+psycopg2:/postgresql:}"
if command -v pg_restore >/dev/null 2>&1; then
  pg_restore --exit-on-error --single-transaction --no-owner --no-privileges --dbname="$pg_url" "${1:?dump file required}"
else
  : "${PG_CONTAINER:?Install postgresql-client or set PG_CONTAINER}"
  docker exec -i "$PG_CONTAINER" pg_restore --exit-on-error --single-transaction --no-owner --no-privileges --dbname="$pg_url" < "${1:?dump file required}"
fi
