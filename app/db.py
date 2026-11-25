"""DB 접근 추상화 — SQLAlchemy 엔진 중심, DATABASE_URL 주입, SQLite 폐백.

- 기본: 환경변수 DATABASE_URL (postgresql+psycopg2://...). 미설정 시 로컬 SQLite(개인 실험용).
- 용도별 계정: DATABASE_URL_READ (조회 전용), DATABASE_URL_REVIEW (검수 쓰기).
  미설정 시 DATABASE_URL로 폐백. 기동 로그에 백엔드와 사용 역할을 명시한다.
"""

from __future__ import annotations

import logging
import os
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger("inspection.db")
DEFAULT_SQLITE_URL = "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "inspection.db")

ROLES = ("admin", "review", "read", "workflow", "batch")
_ENV_FOR = {"admin": "DATABASE_URL", "review": "DATABASE_URL_REVIEW", "read": "DATABASE_URL_READ", "workflow": "DATABASE_URL_WORKFLOW", "batch": "DATABASE_URL_BATCH"}

_engines: dict[str, object] = {}
_engines_lock = threading.Lock()
SessionLocal: sessionmaker | None = None


def database_url(role: str = "admin") -> str:
    env = _ENV_FOR.get(role, "DATABASE_URL")
    return os.getenv(env) or os.getenv("DATABASE_URL") or DEFAULT_SQLITE_URL


def backend_name(url: str | None = None) -> str:
    u = url or database_url()
    return "postgresql" if u.startswith("postgresql") else "sqlite"


def get_engine(role: str = "admin"):
    """역할별 엔진(캐시). admin은 스키마 생성 권한이 있는 계정을 써야 한다."""
    with _engines_lock:
        url = database_url(role)
        key = (role, url)
        if key in _engines:
            return _engines[key]
        kwargs: dict = {}
        if url.startswith("sqlite"):
            kwargs = {"connect_args": {"check_same_thread": False, "timeout": 30}}
            if url in ("sqlite://", "sqlite:///:memory:"):
                kwargs["poolclass"] = StaticPool
        engine = create_engine(url, **kwargs)
        _engines[key] = engine
        if role == "admin":
            global SessionLocal
            SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
        logger.info("[db] backend=%s role=%s url=%s", backend_name(url), role,
                    url.split("@")[-1] if "@" in url else url.split("///")[-1])
        return engine


def configure(url: str | None = None):
    """하위 호환: app.db.configure() 호출 지점용. url 주입 시 admin 엔진 강제 재생성."""
    global _engines, SessionLocal
    if url:
        os.environ["DATABASE_URL"] = url
    with _engines_lock:
        _engines = {}
        SessionLocal = None
    return get_engine("admin")


def get_session(role: str = "admin"):
    """역할별 세션. 기본 admin(하위 호환)."""
    engine = get_engine(role)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


def init_db(engine) -> None:
    from .models import Base

    Base.metadata.create_all(engine)
