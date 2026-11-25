"""DB 마이그레이션 — 백엔드 인식.

- SQLite(폐백): 기존 테이블에 가가적 컬럼(ALTER) + metrics_snapshots 생성.
- PostgreSQL: alembic이 스키마를 관리하므로 여기서는 no-op(기동 순서상 alembic upgrade 선행).
"""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import text, create_engine

import dbconn

NEW_COLUMNS = {
    "metrics_snapshots": [("source_scope", "TEXT"), ("baseline_kind", "TEXT"),
                          ("split_reference", "TEXT"), ("review_status", "TEXT")],
    "inspection_attempts": [
        ("verdict", "TEXT"), ("review_status", "TEXT"),
        ("truth_label", "TEXT"), ("processed_at", "TEXT"),
    ],
    "inspection_views": [("width", "INTEGER"), ("height", "INTEGER")],
    "findings": [("kind", "TEXT"), ("map_uri", "TEXT"), ("meta_json", "TEXT")],
    "reviews": [("fp_fn", "TEXT"), ("corrected_label", "TEXT"),
                ("reviewer_id", "TEXT"), ("updated_at", "TEXT"), ("version", "INTEGER")],
}

METRICS_SNAPSHOTS_DDL = """
CREATE TABLE IF NOT EXISTS metrics_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    numerator INTEGER,
    denominator INTEGER,
    value REAL,
    reason TEXT,
    item TEXT,
    part_id TEXT,
    camera_id TEXT,
    date_from TEXT,
    date_to TEXT,
    model_version TEXT,
    mapping_version TEXT,
    computed_at TEXT
)
"""


def migrate(db_path: Path | None = None) -> list[str]:
    if db_path is None and dbconn.backend_name() == "postgresql":
        return ["postgresql: alembic이 스키마 관리 — no-op"]
    engine = create_engine("sqlite:///" + str(db_path)) if db_path else dbconn.get_engine()
    from app.models import Base
    Base.metadata.create_all(engine)
    applied: list[str] = []
    with engine.begin() as con:
        tables = {r[0] for r in con.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table'"))}
        for table, cols in NEW_COLUMNS.items():
            if table not in tables:
                applied.append(f"{table} (없음, 스킵)")
                continue
            existing = {r[1] for r in con.execute(text(f"PRAGMA table_info({table})"))}
            for name, ddl in cols:
                if name not in existing:
                    con.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    applied.append(f"{table}.{name}")
        con.execute(text("UPDATE reviews SET version=1 WHERE version IS NULL"))
        con.execute(text(METRICS_SNAPSHOTS_DDL))
        applied.append("metrics_snapshots")
        con.execute(text("CREATE INDEX IF NOT EXISTS ix_attempts_verdict "
                         "ON inspection_attempts(verdict)"))
        con.execute(text("CREATE INDEX IF NOT EXISTS ix_findings_kind ON findings(kind)"))
    return applied


if __name__ == "__main__":
    changes = migrate()
    print(f"[migrate] backend={dbconn.backend_name()}: {len(changes)}개 항목")
    for c in changes:
        print(" -", c)
