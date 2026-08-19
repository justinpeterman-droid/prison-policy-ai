"""Fictional cookie-session helpers for browser API integration tests."""
from contextlib import contextmanager

from backend.identity.browser_sessions import BrowserActor
from backend.webapp.web_api import middleware as web_middleware
from backend.webapp.web_api.middleware import ACCESS_COOKIE, CSRF_COOKIE


CSRF_VALUE = "fictional-csrf-token-000000000000"


def authenticate_browser(
    monkeypatch,
    client,
    db_session_factory,
    account,
) -> BrowserActor:
    actor = BrowserActor(
        account_id=account.id,
        staff_member_id=account.staff_member_id,
        session_id=account.id,
        role=account.role,
        auth_version=account.auth_version,
        must_change_pin=account.must_change_pin,
    )

    @contextmanager
    def request_scope():
        session = db_session_factory()
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(web_middleware, "session_scope", request_scope)
    monkeypatch.setattr(
        web_middleware,
        "resolve_browser_actor",
        lambda *args, **kwargs: actor,
    )
    monkeypatch.setattr(
        web_middleware,
        "validate_browser_csrf",
        lambda *args, **kwargs: None,
    )
    client.set_cookie(ACCESS_COOKIE, "fictional-browser-access")
    client.set_cookie(CSRF_COOKIE, CSRF_VALUE)
    return actor


def browser_headers(
    request_id: str,
    *,
    idempotency_key: str | None = None,
    if_match: int | None = None,
) -> dict[str, str]:
    headers = {
        "Host": "localhost",
        "Origin": "http://localhost",
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Token": CSRF_VALUE,
        "X-Client-Version": "1.0.0",
        "X-Request-ID": request_id,
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    if if_match is not None:
        headers["If-Match"] = f'"{if_match}"'
    return headers
