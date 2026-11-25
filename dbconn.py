"""Batch and metrics share the API engine and DATABASE_URL (SQLite fallback)."""
from sqlalchemy import text
from app.db import get_engine, backend_name


def execute(sql, params=None):
    engine = get_engine()
    with engine.begin() as con:
        con.execute(text(sql), params if params is not None else {})
    return engine


def query(sql, params=None):
    with get_engine().connect() as con:
        return [dict(r) for r in con.execute(text(sql), params or {}).mappings()]
