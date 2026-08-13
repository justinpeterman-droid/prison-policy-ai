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
        exc = RuntimeError("Search API error (transport) URLError: <urlopen error [Errno -2]>")
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
        assert classify_error(Exception("default credentials were not found"))[0] == "credentials"

    def test_the_wrapper_names_the_exception_class(self):
        """`%s` of a URLError is just '<urlopen error ...>'; the class is what
        identifies the fault."""
        exc = RuntimeError("Search API error (transport) SSLCertVerificationError: bad cert")
        assert "SSLCertVerificationError" in str(exc)
        assert classify_error(exc)[0] == "upstream"


class TestSnippetsFallbackClassification:
    """The snippets-only fallback needs the same wrapper as the primary path.

    It runs whenever the data store rejects the extractive-content spec with a
    400 (see the fix that introduced it), so it is a live path rather than a
    corner. It handled HTTPError but re-raised everything else bare, which put
    a transport failure there straight back into the `internal` catch-all this
    change exists to eliminate.
    """

    def test_the_fallback_wraps_transport_failures_too(self, monkeypatch):
        """A connection failure in the fallback classifies as a search outage."""
        from backend.pipeline import query

        def boom(*_a, **_k):
            raise urllib.error.URLError("connection reset by peer")

        monkeypatch.setattr(query.urllib.request, "urlopen", boom)
        with pytest.raises(RuntimeError) as caught:
            query._search_snippets_only("https://example.invalid", "tok", "use of force", 10, "original 400")
        assert classify_error(caught.value)[0] == "upstream"

    def test_the_fallback_names_the_exception_class(self, monkeypatch):
        from backend.pipeline import query

        def boom(*_a, **_k):
            raise OSError("network is unreachable")

        monkeypatch.setattr(query.urllib.request, "urlopen", boom)
        with pytest.raises(RuntimeError) as caught:
            query._search_snippets_only("https://example.invalid", "tok", "use of force", 10, "original 400")
        assert "OSError" in str(caught.value)

    def test_the_fallback_preserves_the_cause(self, monkeypatch):
        """Chained so the original traceback survives into the logs."""
        from backend.pipeline import query

        original = urllib.error.URLError("dns failure")

        def boom(*_a, **_k):
            raise original

        monkeypatch.setattr(query.urllib.request, "urlopen", boom)
        with pytest.raises(RuntimeError) as caught:
            query._search_snippets_only("https://example.invalid", "tok", "use of force", 10, "original 400")
        assert caught.value.__cause__ is original


class TestSnippetsFallbackReturnContract:
    """The 400 fallback must return `(contexts, raw_count)` like the main path.

    This was the actual chat outage. Most data stores reject the
    extractive-content spec with a 400, so EVERY on-topic question took the
    fallback — which `return`ed the raw Discovery Engine payload instead of the
    parsed tuple. `retrieved, raw_count = _search_with_stats(...)` then unpacked
    a dict, binding `retrieved` to the string "results", and the next line died
    with `TypeError: string indices must be integers`.

    Search had SUCCEEDED; only the shape was wrong. That is why it surfaced as
    the `internal` catch-all ("An unexpected error occurred") and why wrapping
    search *exceptions* never touched it — there was no exception to wrap.
    """

    PAYLOAD = {
        "results": [
            {
                "document": {
                    "derivedStructData": {
                        "title": "AD 2024-15 Use of Force",
                        "snippets": [{"snippet": "Force must be reasonable."}],
                    }
                }
            },
        ],
        "totalSize": 1,
    }

    def _run(self, monkeypatch):
        import io
        import json as _json
        from backend.pipeline import query

        calls = {"n": 0}

        def fake_urlopen(_req, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError(
                    "u",
                    400,
                    "Bad Request",
                    {},
                    io.BytesIO(b'{"error":"extractive spec unsupported"}'),
                )

            class _Resp:
                def read(self):
                    return _json.dumps(TestSnippetsFallbackReturnContract.PAYLOAD).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *_a):
                    return False

            return _Resp()

        monkeypatch.setattr(query, "_get_token", lambda: "tok")
        monkeypatch.setattr(query.urllib.request, "urlopen", fake_urlopen)
        return query._search_with_stats("use of force", 10)

    def test_the_fallback_returns_a_tuple_not_the_raw_payload(self, monkeypatch):
        out = self._run(monkeypatch)
        assert isinstance(out, tuple) and len(out) == 2, f"expected (contexts, raw_count), got {type(out).__name__}"

    def test_the_fallback_returns_parsed_passages(self, monkeypatch):
        contexts, raw_count = self._run(monkeypatch)
        assert raw_count == 1
        assert [c["source"] for c in contexts] == ["AD 2024-15 Use of Force"]
        assert contexts[0]["text"].startswith("Force must be reasonable")

    def test_the_unpacked_result_survives_what_answer_question_does_next(self, monkeypatch):
        """The exact line that raised in production."""
        retrieved, _ = self._run(monkeypatch)
        assert retrieved[0]["source"][:60] == "AD 2024-15 Use of Force"

    def test_a_non_400_http_error_still_raises_a_classified_search_error(self, monkeypatch):
        """Restructuring the 400 branch must not swallow other HTTP errors."""
        import io
        from backend.pipeline import query

        def fake_urlopen(_req, timeout=None):
            raise urllib.error.HTTPError("u", 503, "Unavailable", {}, io.BytesIO(b"upstream down"))

        monkeypatch.setattr(query, "_get_token", lambda: "tok")
        monkeypatch.setattr(query.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(RuntimeError) as caught:
            query._search_with_stats("use of force", 10)
        assert classify_error(caught.value)[0] == "upstream"
