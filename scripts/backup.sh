#!/usr/bin/env bash
# DATABASE_URL은 환경변수로만 전달한다. 원본 DB/기존 백업은 덮어쓰지 않는다.
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL required}"
backup_dir="${1:?backup directory required}"
mkdir -p "$backup_dir"
backup_file="$backup_dir/inspection_$(date -u +%Y%m%dT%H%M%S)_$$.dump"
pg_url="${DATABASE_URL/postgresql+psycopg2:/postgresql:}"
if command -v pg_dump >/dev/null 2>&1; then
  pg_dump --dbname="$pg_url" --format=custom --file="$backup_file.tmp"
else
  : "${PG_CONTAINER:?Install postgresql-client or set PG_CONTAINER}"
  docker exec "$PG_CONTAINER" pg_dump --dbname="$pg_url" --format=custom > "$backup_file.tmp"
fi
mv "$backup_file.tmp" "$backup_file"
# 이 스크립트가 생성한 백업만 최근7개 유지한다. 원본·다른 파일은 대상이 아니다.
python3 - "$backup_dir" <<'PYROTATE'
from pathlib import Path
import sys
for p in sorted(Path(sys.argv[1]).glob('inspection_*.dump'),key=lambda p:p.stat().st_mtime,reverse=True)[7:]:p.unlink()
PYROTATE
printf '%s\n' "$backup_file"
