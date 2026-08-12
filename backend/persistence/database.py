from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.identity.config import IdentitySettings


class DatabaseUnavailable(RuntimeError):
    """The Access identity database has not been initialized or is unavailable."""


_engine = None
_session_factory = None


def init_database(settings: IdentitySettings) -> None:
    global _engine, _session_factory
    if not settings.enabled:
        _engine = None
        _session_factory = None
        return
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is required when Access API is enabled")
    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"options": "-c timezone=utc"},
    )
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    if _session_factory is None:
        raise DatabaseUnavailable("identity database is not initialized")
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def database_ready() -> bool:
    if _engine is None:
        return False
    try:
        with _engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
