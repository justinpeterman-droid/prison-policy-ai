import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def db_engine():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    alembic_config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c timezone=utc"},
    )
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(alembic_config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    return sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
def db_session(db_session_factory):
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def api_client():
    from backend.webapp.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()
