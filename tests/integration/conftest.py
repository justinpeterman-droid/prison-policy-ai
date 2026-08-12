import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.integration.identity_fixtures import (
    bearer_headers,
    issue_fictional_tokens,
    seed_fictional_account,
)

from datetime import UTC, datetime


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


@pytest.fixture
def identity_fixed_now():
    return datetime(2026, 8, 12, 15, 0, tzinfo=UTC)


@pytest.fixture
def fictional_user_account(db_session, identity_fixed_now):
    return seed_fictional_account(
        db_session, employee_number="TEST-1001", role="user",
        pin="Z9Y8X7", now=identity_fixed_now,
    )


@pytest.fixture
def fictional_admin_account(db_session, identity_fixed_now):
    return seed_fictional_account(
        db_session, employee_number="TEST-9001", role="admin",
        pin="Q7W9E2", now=identity_fixed_now,
    )


@pytest.fixture
def fictional_user_tokens(db_session, fictional_user_account, identity_fixed_now):
    return issue_fictional_tokens(
        db_session, account=fictional_user_account,
        device_id="device-fictional-user-0001", now=identity_fixed_now,
    )


@pytest.fixture
def fictional_admin_tokens(db_session, fictional_admin_account, identity_fixed_now):
    return issue_fictional_tokens(
        db_session, account=fictional_admin_account,
        device_id="device-fictional-admin-0001", now=identity_fixed_now,
    )


@pytest.fixture
def user_bearer_headers(fictional_user_tokens):
    return bearer_headers(fictional_user_tokens)


@pytest.fixture
def admin_bearer_headers(fictional_admin_tokens):
    return bearer_headers(fictional_admin_tokens)
