"""RP-08 — the Policy Expert `/api/v1` contract.

The Policy Expert is the one surface where the *request itself* is sensitive:
officers quote live incidents into their questions, and the answer quotes
policy back. So the tests below care about two things in equal measure — that
the route behaves like the rest of `/api/v1` (bounded history, closed request,
attributed idempotency, stable safe errors), and that neither the question, the
answer, nor a citation passage is ever written anywhere durable.

The idempotency-outcome tests need the real ID-06 record, so they borrow the
PostgreSQL fixtures from the integration conftest and skip without
`TEST_DATABASE_URL`, exactly like the integration suite does. The provider is
always a fake — no Google credentials or network are involved.
"""

from dataclasses import replace
from datetime import datetime, timedelta
import json
import os
import threading
import time

import pytest
from sqlalchemy import select, text

from backend.webapp.api_v1.policy import (
    MAX_HISTORY_FIELD_CHARS,
    MAX_HISTORY_ITEMS,
    clean_policy_history,
)
from backend.persistence.models.security import IdempotencyRecord

# Borrowed wholesale so the idempotency assertions run against a real record.
# `isolate_postgres_test` is autouse where it is defined and stays autouse here,
# which is what keeps each test's seeded fixtures from colliding on the shared
# database — tests/unit has no conftest of its own to provide it.
from tests.integration.conftest import (
    api_client,
    db_engine,
    db_session,
    db_session_factory,
    fictional_user_account,
    fictional_user_tokens,
    identity_fixed_now,
    isolate_postgres_test,
    user_bearer_headers,
)

_REGISTERED_FIXTURES = (
    api_client,
    db_engine,
    db_session,
    db_session_factory,
    fictional_user_account,
    fictional_user_tokens,
    identity_fixed_now,
    isolate_postgres_test,
    user_bearer_headers,
)


@pytest.fixture(autouse=True)
def _fictional_access_api_environment(monkeypatch, identity_fixed_now):
    """Pin the API environment and the clock, as the sibling API suites do.

    The seeded tokens are issued at a fixed past instant, so without freezing
    the middleware clock every request 401s the moment real time drifts past
    the 15-minute access TTL.
    """
    monkeypatch.setenv("ACCESS_API_ENABLED", "true")
    monkeypatch.setenv("IDENTITY_HASH_PEPPER", "p" * 32)
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "c" * 32)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.example.gov")
    import backend.webapp.api_v1.middleware as middleware

    fixed = identity_fixed_now + timedelta(minutes=1)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(middleware, "datetime", _FixedDateTime)


@pytest.fixture
def auth_headers(db_session, user_bearer_headers):
    """Bearer headers whose account is visible to the app's own session.

    The fixtures seed through `db_session`; the request handler opens a
    separate `session_scope()`, so without this commit every call 401s.
    """
    db_session.commit()
    return user_bearer_headers


FICTIONAL_ANSWER = "Fictional policy answer for the example unit only."
FICTIONAL_CITATIONS = [
    {"n": 1, "source": "Fictional Policy AD-00-00", "text": "Fictional passage text."},
]


def _provider_result():
    return {
        "answer": FICTIONAL_ANSWER,
        "citations": [dict(item) for item in FICTIONAL_CITATIONS],
        "sources": [item["source"] for item in FICTIONAL_CITATIONS],
        "retrieved_sources": ["Fictional Policy AD-00-00"],
    }


def _headers(base, key):
    return base | {"Idempotency-Key": key, "X-Request-ID": f"request_{key}"}


def _fake_provider(monkeypatch, *, calls=None, result=None, raises=None, delay=0.0):
    """Install a fake `answer_question`, recording every call it receives."""
    recorded = calls if calls is not None else []

    def fake(question, history=None, **kwargs):
        recorded.append({"question": question, "history": history, **kwargs})
        if delay:
            time.sleep(delay)
        if raises is not None:
            raise raises
        return result if result is not None else _provider_result()

    monkeypatch.setattr("backend.webapp.api_v1.policy.answer_question", fake)
    return recorded


class TestSharedHistoryCleaner:
    """The cleaner is shared with the browser route; limits must not drift."""

    def test_limits_match_the_established_browser_bounds(self):
        assert MAX_HISTORY_ITEMS == 6
        assert MAX_HISTORY_FIELD_CHARS == 2000

    def test_non_list_inputs_are_dropped(self):
        for bad in (None, "history", 42, {"question": "q"}):
            assert clean_policy_history(bad) == []

    def test_malformed_entries_are_skipped_not_fatal(self):
        out = clean_policy_history(
            ["string", 7, None, {"answer": "orphan"}, {"question": "real one"}]
        )
        assert [item["question"] for item in out] == ["real one"]

    def test_caps_the_number_of_turns_keeping_the_most_recent(self):
        out = clean_policy_history(
            [{"question": f"q{i}", "answer": "a"} for i in range(50)]
        )
        assert len(out) == MAX_HISTORY_ITEMS
        assert out[-1]["question"] == "q49"

    def test_caps_field_length(self):
        out = clean_policy_history([{"question": "q" * 99999, "answer": "a" * 99999}])
        assert len(out[0]["question"]) == MAX_HISTORY_FIELD_CHARS
        assert len(out[0]["answer"]) == MAX_HISTORY_FIELD_CHARS

    def test_output_is_always_string_valued_pairs(self):
        out = clean_policy_history([{"question": 123, "answer": {"a": 1}}])
        assert out == [{"question": "123", "answer": "{'a': 1}"}]

    def test_whitespace_only_question_is_dropped(self):
        assert clean_policy_history([{"question": "   ", "answer": "a"}]) == []


class TestBrowserParity:
    """The browser route must keep using this exact cleaner, not a copy."""

    def test_browser_route_shares_the_promoted_cleaner(self):
        chat = pytest.importorskip("backend.webapp.routes.chat")
        assert chat._clean_history is clean_policy_history
        assert chat.MAX_HISTORY_ITEMS == MAX_HISTORY_ITEMS
        assert chat.MAX_HISTORY_FIELD_CHARS == MAX_HISTORY_FIELD_CHARS

    def test_browser_response_shape_is_unchanged(self, monkeypatch):
        chat = pytest.importorskip("backend.webapp.routes.chat")
        monkeypatch.setattr(
            chat, "answer_question", lambda q, history=None: _provider_result()
        )
        app = pytest.importorskip("flask").Flask(__name__)
        app.register_blueprint(chat.chat_bp)
        response = app.test_client().post("/api/chat", json={"question": "Fictional?"})
        assert response.status_code == 200
        # The browser contract is the bare pipeline dict — no /api/v1 envelope.
        assert set(response.json) == {
            "answer",
            "citations",
            "sources",
            "retrieved_sources",
        }
        assert response.json["answer"] == FICTIONAL_ANSWER


class TestRequestContract:
    def test_passes_only_bounded_clean_history_to_the_provider(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        history = [
            {"question": f"Question {i}", "answer": "A" * 100} for i in range(10)
        ]
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0001"),
            json={
                "question": "What does the fictional policy say?",
                "history": history,
            },
        )
        assert response.status_code == 200
        assert len(calls) == 1
        assert len(calls[0]["history"]) <= MAX_HISTORY_ITEMS
        assert calls[0]["history"][-1]["question"] == "Question 9"

    def test_returns_answer_citations_and_sources(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        _fake_provider(monkeypatch)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0002"),
            json={"question": "What does the fictional policy say?"},
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["answer"] == FICTIONAL_ANSWER
        assert data["citations"] == FICTIONAL_CITATIONS
        assert data["sources"] == ["Fictional Policy AD-00-00"]

    def test_rejects_unknown_request_field(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0003"),
            json={"question": "Fictional?", "model": "gemini-fictional"},
        )
        assert response.status_code == 400
        assert response.json["error"]["code"] == "validation_failed"
        assert calls == []

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"question": ""},
            {"question": "   "},
            {"question": 42},
            {"question": "Fictional?", "history": "not-a-list"},
        ],
    )
    def test_rejects_invalid_question_bodies(
        self,
        api_client,
        auth_headers,
        monkeypatch,
        body,
    ):
        calls = _fake_provider(monkeypatch)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0004"),
            json=body,
        )
        assert response.status_code == 400
        assert response.json["error"]["code"] == "validation_failed"
        assert calls == []

    def test_requires_an_idempotency_key(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=auth_headers,
            json={"question": "Fictional?"},
        )
        assert response.status_code == 400
        assert response.json["error"]["code"] == "validation_failed"
        assert calls == []

    @pytest.mark.parametrize("request_id_value", [None, "bad id!"])
    def test_requires_a_valid_explicit_request_id(
        self,
        api_client,
        auth_headers,
        monkeypatch,
        request_id_value,
    ):
        calls = _fake_provider(monkeypatch)
        headers = auth_headers | {"Idempotency-Key": "policy-fictional-request-id"}
        if request_id_value is not None:
            headers["X-Request-ID"] = request_id_value
        else:
            headers.pop("X-Request-ID", None)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=headers,
            json={"question": "Fictional request identifier check?"},
        )
        assert response.status_code == 400
        assert response.json["error"]["code"] == "validation_failed"
        assert calls == []

    def test_requires_a_compatible_write_client(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        settings = api_client.application.config["IDENTITY_SETTINGS"]
        api_client.application.config["IDENTITY_SETTINGS"] = replace(
            settings,
            minimum_client_version="9.0.0",
        )
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-version"),
            json={"question": "Fictional compatibility check?"},
        )
        assert response.status_code == 409
        assert response.json["error"]["code"] == "client_upgrade_required"
        assert calls == []

    @pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="requires disposable PostgreSQL"
    )
    def test_requires_authentication(self, api_client, monkeypatch):
        calls = _fake_provider(monkeypatch)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers={
                "X-Client-Version": "1.0.0",
                "Idempotency-Key": "policy-fictional-0005",
            },
            json={"question": "Fictional?"},
        )
        assert response.status_code == 401
        assert calls == []


class TestIdempotencyOutcomes:
    def test_completed_duplicate_never_repeats_the_provider_call(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        headers = _headers(auth_headers, "policy-fictional-0010")
        body = {"question": "What does the fictional policy say?"}

        first = api_client.post("/api/v1/policy/questions", headers=headers, json=body)
        second = api_client.post("/api/v1/policy/questions", headers=headers, json=body)

        assert first.status_code == 200
        # The answer is deliberately not stored, so a replay cannot be served.
        assert second.status_code == 409
        assert second.json["error"]["code"] == "idempotent_response_unavailable"
        assert len(calls) == 1

    def test_changed_payload_with_the_same_key_conflicts(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        headers = _headers(auth_headers, "policy-fictional-0011")
        api_client.post(
            "/api/v1/policy/questions",
            headers=headers,
            json={"question": "First fictional question?"},
        )
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=headers,
            json={"question": "Different fictional question?"},
        )
        assert response.status_code == 409
        assert response.json["error"]["code"] == "idempotency_conflict"
        assert len(calls) == 1

    def test_duplicate_while_the_first_call_is_running_is_rejected(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        """The claim must be committed before the provider call, or a concurrent
        duplicate would be invisible and buy a second provider request."""
        started = threading.Event()
        release = threading.Event()
        calls = []

        def slow(question, history=None, **_kwargs):
            calls.append(question)
            started.set()
            release.wait(timeout=10)
            return _provider_result()

        monkeypatch.setattr("backend.webapp.api_v1.policy.answer_question", slow)
        headers = _headers(auth_headers, "policy-fictional-0012")
        body = {"question": "Fictional concurrent question?"}
        outcome = {}

        def first_call():
            outcome["first"] = api_client.post(
                "/api/v1/policy/questions",
                headers=headers,
                json=body,
            ).status_code

        worker = threading.Thread(target=first_call)
        worker.start()
        assert started.wait(timeout=10)

        duplicate = api_client.post(
            "/api/v1/policy/questions", headers=headers, json=body
        )
        release.set()
        worker.join(timeout=10)

        assert duplicate.status_code == 409
        assert duplicate.json["error"]["code"] == "request_in_progress"
        assert outcome["first"] == 200
        assert len(calls) == 1

    def test_a_new_key_lets_the_officer_ask_again(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        body = {"question": "What does the fictional policy say?"}
        first = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0013"),
            json=body,
        )
        second = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0014"),
            json=body,
        )
        assert first.status_code == second.status_code == 200
        assert len(calls) == 2


class TestNothingSensitiveIsPersisted:
    SECRET_QUESTION = "Does fictional inmate Roe 111111 qualify under the policy?"

    def test_idempotency_record_stores_only_safe_references(
        self,
        api_client,
        auth_headers,
        db_session,
        monkeypatch,
    ):
        _fake_provider(monkeypatch)
        api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0020"),
            json={"question": self.SECRET_QUESTION},
        )
        record = db_session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.idempotency_key == "policy-fictional-0020"
            )
        )
        assert record is not None
        assert record.status == "completed"
        encoded = json.dumps(record.response_reference)
        for leak in (
            self.SECRET_QUESTION,
            FICTIONAL_ANSWER,
            "Fictional passage text",
            "111111",
        ):
            assert leak not in encoded
        # A digest of the answer is fine; the answer itself is not.
        assert set(record.response_reference) <= {
            "result",
            "latency_bucket",
            "response_sha256",
            "citation_count",
        }

    def test_audit_event_records_only_safe_result_metadata(
        self,
        api_client,
        auth_headers,
        db_session,
        monkeypatch,
    ):
        _fake_provider(monkeypatch)
        api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0021"),
            json={"question": self.SECRET_QUESTION},
        )
        rows = db_session.execute(
            text(
                "SELECT action, details FROM audit_events WHERE action = 'policy.question_answered'"
            )
        ).all()
        assert rows, "the policy question should be audited"
        for _action, details in rows:
            encoded = json.dumps(details)
            for leak in (
                self.SECRET_QUESTION,
                FICTIONAL_ANSWER,
                "Fictional passage text",
            ):
                assert leak not in encoded
            assert set(details) <= {"document_count", "latency_ms"}

    def test_the_question_never_reaches_the_request_log(
        self,
        api_client,
        auth_headers,
        monkeypatch,
        caplog,
    ):
        _fake_provider(monkeypatch)
        with caplog.at_level("DEBUG"):
            api_client.post(
                "/api/v1/policy/questions",
                headers=_headers(auth_headers, "policy-fictional-0022"),
                json={"question": self.SECRET_QUESTION},
            )
        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert self.SECRET_QUESTION not in logged
        assert FICTIONAL_ANSWER not in logged
        assert "111111" not in logged

    def test_shared_search_logs_only_question_length(self, monkeypatch):
        """Exercise the real Discovery Engine logging path, not a route fake."""
        import backend.pipeline.query as query

        secret = "Does fictional inmate Roe 111111 qualify under this policy?"

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"results": []}'

        messages = []
        monkeypatch.setattr(query, "_get_token", lambda **_kwargs: "fictional-token")
        monkeypatch.setattr(
            query.logger,
            "info",
            lambda message, *args: messages.append(message % args),
        )
        monkeypatch.setattr(
            query.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response()
        )
        query._search_with_stats(secret)
        logged = "\n".join(messages)
        assert secret not in logged
        assert "111111" not in logged
        assert f"query_chars={len(secret)}" in logged

    def test_shared_search_binds_network_timeout_to_the_api_deadline(self, monkeypatch):
        import backend.pipeline.query as query

        seen = []

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"results": []}'

        monkeypatch.setattr(query, "_get_token", lambda **_kwargs: "fictional-token")
        monkeypatch.setattr(
            query.urllib.request,
            "urlopen",
            lambda _request, *, timeout: seen.append(timeout) or _Response(),
        )
        deadline = time.monotonic() + 0.2
        query._search_with_stats(
            "fictional policy question", deadline_monotonic=deadline
        )
        assert 0 < seen[0] <= 0.2

    def test_expired_shared_deadline_never_falls_open_to_search(self, monkeypatch):
        import backend.pipeline.query as query

        monkeypatch.setattr(query, "classify_by_keyword", lambda _question: None)
        with pytest.raises(TimeoutError):
            query._classify_query(
                "fictional ambiguous question",
                deadline_monotonic=time.monotonic() - 0.01,
            )

    def test_policy_response_projects_provider_values_to_closed_schema(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        _fake_provider(
            monkeypatch,
            result={
                "answer": "Fictional answer.",
                "citations": [
                    {"n": 1, "source": "S" * 400, "text": "P" * 9000, "extra": "drop"},
                    {"n": "bad", "source": "bad", "text": "bad"},
                ],
                "sources": ["A" * 400, {"not": "text"}],
                "retrieved_sources": ["B" * 400],
            },
        )
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-projection"),
            json={"question": "Fictional response projection?"},
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["citations"] == [{"n": 1, "source": "S" * 300, "text": "P" * 8000}]
        assert data["sources"] == ["A" * 300]
        assert data["retrieved_sources"] == ["B" * 300]


class TestSafeUpstreamErrors:
    @pytest.mark.parametrize(
        "exc,code,status",
        [
            (
                RuntimeError("Default credentials were not found."),
                "dependency_unavailable",
                503,
            ),
            (
                RuntimeError("Publisher Model was not found"),
                "dependency_unavailable",
                503,
            ),
            (
                RuntimeError("403 permission denied on resource"),
                "dependency_unavailable",
                503,
            ),
            (
                RuntimeError("Search API error: upstream refused"),
                "dependency_unavailable",
                503,
            ),
            (
                RuntimeError("RESOURCE_EXHAUSTED: quota exceeded"),
                "dependency_unavailable",
                503,
            ),
            (ValueError("something unexpected"), "internal_error", 500),
        ],
    )
    def test_provider_failures_become_stable_safe_errors(
        self,
        api_client,
        auth_headers,
        monkeypatch,
        exc,
        code,
        status,
    ):
        _fake_provider(monkeypatch, raises=exc)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, f"policy-fictional-err-{code}-{status}"),
            json={"question": "Fictional failing question?"},
        )
        assert response.status_code == status
        assert response.json["error"]["code"] == code
        message = response.json["error"]["message"]
        # No stack, no HTML, no infrastructure detail leaks to the client.
        for leak in ("Traceback", "<html", "google", "gemini", str(exc)):
            assert leak.lower() not in message.lower()

    def test_exceeding_the_server_budget_is_a_safe_timeout(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        import backend.webapp.api_v1.policy as policy_module

        monkeypatch.setattr(policy_module, "POLICY_BUDGET_SECONDS", 0.2)

        def deadline_aware_provider(question, history=None, *, deadline_monotonic):
            time.sleep(0.25)
            if time.monotonic() >= deadline_monotonic:
                raise TimeoutError("fictional provider deadline")
            return _provider_result()

        monkeypatch.setattr(policy_module, "answer_question", deadline_aware_provider)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-0030"),
            json={"question": "Fictional slow question?"},
        )
        assert response.status_code == 504
        assert response.json["error"]["code"] == "dependency_timeout"
        assert response.json["error"]["retryable"] is True

    def test_passes_a_deadline_to_the_shared_pipeline(
        self,
        api_client,
        auth_headers,
        monkeypatch,
    ):
        calls = _fake_provider(monkeypatch)
        response = api_client.post(
            "/api/v1/policy/questions",
            headers=_headers(auth_headers, "policy-fictional-deadline"),
            json={"question": "Fictional deadline propagation?"},
        )
        assert response.status_code == 200
        assert isinstance(calls[0]["deadline_monotonic"], float)

    def test_a_failed_call_does_not_strand_the_key_as_in_progress(
        self,
        api_client,
        auth_headers,
        db_session,
        monkeypatch,
    ):
        """A provider failure must settle the record, so the officer can retry
        with the same key rather than being locked out by a dead claim."""
        _fake_provider(
            monkeypatch, raises=RuntimeError("Search API error: upstream refused")
        )
        headers = _headers(auth_headers, "policy-fictional-0031")
        body = {"question": "Fictional failing question?"}
        first = api_client.post("/api/v1/policy/questions", headers=headers, json=body)
        assert first.status_code == 503

        record = db_session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.idempotency_key == "policy-fictional-0031"
            )
        )
        assert record is None or record.status != "in_progress"
