import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from tests.integration.identity_fixtures import (
    bearer_headers,
    issue_fictional_tokens,
    seed_fictional_account,
)
from tests.support.reporting import (
    FictionalStaff,
    make_incident,
    make_report,
    seed_fictional_staff_and_accounts,
)
from backend.webapp.api_v1.middleware import Actor

from datetime import UTC, datetime


ROOT = Path(__file__).resolve().parents[2]
DATABASE_FIXTURES = frozenset({"db_engine", "db_session_factory", "db_session"})


def _truncate_application_tables(engine):
    with engine.begin() as connection:
        table_names = [
            table_name
            for table_name in inspect(connection).get_table_names()
            if table_name != "alembic_version"
        ]
        if not table_names:
            return
        quote = connection.dialect.identifier_preparer.quote
        tables = ", ".join(quote(table_name) for table_name in table_names)
        connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


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


@pytest.fixture(autouse=True)
def isolate_postgres_test(request):
    if DATABASE_FIXTURES.isdisjoint(request.fixturenames):
        yield
        return

    engine = request.getfixturevalue("db_engine")
    _truncate_application_tables(engine)
    yield
    _truncate_application_tables(engine)


@pytest.fixture
def db_session(db_session_factory):
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def api_client(monkeypatch):
    import backend.webapp.app as app_module

    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://integration.example.invalid")
    monkeypatch.setattr(
        app_module,
        "ACCESS_CODE",
        "fictional-local-integration-access-code",
    )
    app = app_module.create_app()
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def identity_fixed_now():
    return datetime(2026, 8, 12, 15, 0, tzinfo=UTC)


@pytest.fixture
def fictional_user_account(db_session, identity_fixed_now):
    return seed_fictional_account(
        db_session,
        employee_number="TEST-1001",
        role="user",
        pin="Z9Y8X7",
        now=identity_fixed_now,
    )


@pytest.fixture
def fictional_admin_account(db_session, identity_fixed_now):
    return seed_fictional_account(
        db_session,
        employee_number="TEST-9001",
        role="admin",
        pin="Q7W9E2",
        now=identity_fixed_now,
    )


@pytest.fixture
def fictional_user_tokens(db_session, fictional_user_account, identity_fixed_now):
    return issue_fictional_tokens(
        db_session,
        account=fictional_user_account,
        device_id="device-fictional-user-0001",
        now=identity_fixed_now,
    )


@pytest.fixture
def fictional_admin_tokens(db_session, fictional_admin_account, identity_fixed_now):
    return issue_fictional_tokens(
        db_session,
        account=fictional_admin_account,
        device_id="device-fictional-admin-0001",
        now=identity_fixed_now,
    )


@pytest.fixture
def user_bearer_headers(fictional_user_tokens):
    return bearer_headers(fictional_user_tokens)


@pytest.fixture
def admin_bearer_headers(fictional_admin_tokens):
    return bearer_headers(fictional_admin_tokens)


@pytest.fixture
def fictional_staff_and_accounts(db_session, identity_fixed_now):
    return seed_fictional_staff_and_accounts(db_session, identity_fixed_now)


@pytest.fixture
def fictional_staff(fictional_staff_and_accounts):
    return FictionalStaff(
        fictional_staff_and_accounts.user.staff_member,
        fictional_staff_and_accounts.preparer.staff_member,
    )


@pytest.fixture
def fictional_incident(db_session, fictional_staff_and_accounts, identity_fixed_now):
    return make_incident(
        db_session,
        fictional_staff_and_accounts.preparer,
        identity_fixed_now,
    )


@pytest.fixture
def fictional_report(
    db_session,
    fictional_incident,
    fictional_staff_and_accounts,
    identity_fixed_now,
):
    return make_report(
        db_session,
        incident=fictional_incident,
        owner=fictional_staff_and_accounts.user,
        preparer=fictional_staff_and_accounts.preparer,
        now=identity_fixed_now,
    )


@pytest.fixture
def shared_report(fictional_report):
    return fictional_report


@pytest.fixture
def incident_id(fictional_incident):
    return fictional_incident.id


@pytest.fixture
def report_id(fictional_report):
    return fictional_report.id


@pytest.fixture
def user_actor(fictional_staff_and_accounts, fictional_owner_tokens):
    account = fictional_staff_and_accounts.user
    return Actor(
        account.id,
        account.staff_member_id,
        fictional_owner_tokens.session_id,
        "user",
        account.auth_version,
        account.must_change_pin,
    )


@pytest.fixture
def fictional_owner_tokens(
    db_session, fictional_staff_and_accounts, identity_fixed_now
):
    return issue_fictional_tokens(
        db_session,
        account=fictional_staff_and_accounts.user,
        device_id="device-fictional-owner-0001",
        now=identity_fixed_now,
    )


@pytest.fixture
def fictional_preparer_tokens(
    db_session, fictional_staff_and_accounts, identity_fixed_now
):
    return issue_fictional_tokens(
        db_session,
        account=fictional_staff_and_accounts.preparer,
        device_id="device-fictional-preparer-0001",
        now=identity_fixed_now,
    )


@pytest.fixture
def fictional_unrelated_tokens(
    db_session, fictional_staff_and_accounts, identity_fixed_now
):
    return issue_fictional_tokens(
        db_session,
        account=fictional_staff_and_accounts.unrelated,
        device_id="device-fictional-unrelated-0001",
        now=identity_fixed_now,
    )


@pytest.fixture
def owner_bearer_headers(fictional_owner_tokens):
    return bearer_headers(fictional_owner_tokens)


@pytest.fixture
def preparer_bearer_headers(fictional_preparer_tokens):
    return bearer_headers(fictional_preparer_tokens)


@pytest.fixture
def unrelated_bearer_headers(fictional_unrelated_tokens):
    return bearer_headers(fictional_unrelated_tokens)


@pytest.fixture
def old_client_bearer_headers(fictional_owner_tokens):
    return bearer_headers(fictional_owner_tokens, client_version="0.1.0")
