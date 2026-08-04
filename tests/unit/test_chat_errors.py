"""Unit tests for /api/chat error classification (no GCP calls)."""
import socket
import urllib.error

import pytest
from backend.webapp.app import create_app
from backend.webapp.errors import classify_error, ERROR_MESSAGES


def _raise(exc):
    """Return a callable that raises *exc* when invoked."""

    def _fn(*args, **kwargs):
        raise exc

    return _fn


@pytest.fixture
def client(monkeypatch):
    """Flask test client with auth gate disabled."""
    monkeypatch.setattr("backend.webapp.app.ACCESS_CODE", "")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


class TestChatErrors:
    """Error classification and response shape for POST /api/chat."""

    def test_success_passthrough(self, client, monkeypatch):
        """The success path and response shape are unchanged."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            lambda q, **kw: {"answer": "ok", "citations": [], "sources": []},
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["answer"] == "ok"

    def test_missing_question(self, client):
        """Empty payload returns 400 without hitting the pipeline."""
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 400
        assert "No question provided" in resp.get_json()["error"]

    # ── Credentials / ADC ──

    def test_credentials_by_message(self, client, monkeypatch):
        """A RuntimeError mentioning 'default credentials were not found' → 503."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(RuntimeError("default credentials were not found")),
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 503
        data = resp.get_json()
        assert "request_id" in data
        assert len(data["request_id"]) == 8
        assert "configured" in data["error"]

    def test_credentials_by_class(self, client, monkeypatch):
        """DefaultCredentialsError → 503 (when google.auth is importable)."""
        try:
            from google.auth.exceptions import DefaultCredentialsError  # noqa: F811
        except ImportError:
            pytest.skip("google.auth not installed")
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(DefaultCredentialsError("test")),
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 503
        data = resp.get_json()
        assert "request_id" in data

    # ── Search / upstream ──

    def test_search_api_error(self, client, monkeypatch):
        """RuntimeError with 'Search API error' → 500 + upstream message."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(RuntimeError("Search API error 500")),
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 500
        data = resp.get_json()
        assert "request_id" in data
        assert "search" in data["error"].lower()

    # ── Timeout ──

    def test_timeout_socket(self, client, monkeypatch):
        """socket.timeout → 500 + timeout message."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(socket.timeout("timed out")),
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 500
        data = resp.get_json()
        assert "request_id" in data
        assert "too long" in data["error"]

    def test_timeout_builtin(self, client, monkeypatch):
        """TimeoutError → 500 + timeout message."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(TimeoutError("operation timed out")),
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 500
        data = resp.get_json()
        assert "request_id" in data

    def test_timeout_by_message(self, client, monkeypatch):
        """Any exception whose message contains 'timed out' → 500 + timeout message."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(Exception("connection timed out")),
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 500
        data = resp.get_json()
        assert "request_id" in data
        assert "too long" in data["error"]

    # ── Generic / fallback ──

    def test_generic_error(self, client, monkeypatch):
        """Unrecognised exceptions → 500 + generic message."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(ValueError("something weird happened")),
        )
        resp = client.post("/api/chat", json={"question": "test"})
        assert resp.status_code == 500
        data = resp.get_json()
        assert "request_id" in data
        assert "unexpected" in data["error"]

    # ── Request id uniqueness ──

    def test_request_ids_vary(self, client, monkeypatch):
        """Every error response carries a distinct request id."""
        monkeypatch.setattr(
            "backend.webapp.routes.chat.answer_question",
            _raise(ValueError("boom")),
        )
        ids = set()
        for _ in range(5):
            resp = client.post("/api/chat", json={"question": "test"})
            ids.add(resp.get_json()["request_id"])
        assert len(ids) == 5


# ── Search failures must classify as search failures ────────────────────────

class TestSearchFailureClassification:
    """Found while smoke-testing production: the chat 500'd with "An unexpected
    error occurred" on every work question. That message is the `internal`
    catch-all — so the one thing the officer and the person debugging both
    needed to know (policy SEARCH is what failed) was the one thing neither was
    told. A non-HTTPError in the search path re-raised bare and matched none of
    classify_error's patterns."""

    def test_a_transport_failure_is_reported_as_a_search_outage(self):
        """A connection/DNS/TLS failure is a search outage, and the officer
        should be told that rather than 'something unexpected happened'."""
        exc = RuntimeError(
            "Search API error (transport) URLError: <urlopen error [Errno -2]>")
        category, status = classify_error(exc)
        assert category == "upstream"
        assert "policy search" in ERROR_MESSAGES[category].lower()
        assert status == 500

    def test_an_http_search_error_still_classifies_the_same_way(self):
        """The existing HTTPError path must be unaffected by the new wrapper."""
        assert classify_error(RuntimeError("Search API error 404"))[0] == "upstream"

    def test_a_bare_transport_error_would_have_been_miscategorised(self):
        """The regression this guards: unwrapped, it reads as 'internal'."""
        assert classify_error(urllib.error.URLError("connection reset"))[0] == "internal"

    def test_credential_errors_keep_their_more_specific_category(self):
        """Token acquisition re-raises unwrapped precisely so this stays true —
        'not configured' is more actionable than 'search is down'."""
        assert classify_error(
            Exception("default credentials were not found"))[0] == "credentials"

    def test_the_wrapper_names_the_exception_class(self):
        """`%s` of a URLError is just '<urlopen error ...>'; the class is what
        identifies the fault."""
        exc = RuntimeError("Search API error (transport) SSLCertVerificationError: bad cert")
        assert "SSLCertVerificationError" in str(exc)
        assert classify_error(exc)[0] == "upstream"
