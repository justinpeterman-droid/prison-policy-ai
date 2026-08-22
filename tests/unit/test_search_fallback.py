"""Unit tests for the search-request fallback and shared error classification.

The extractive-content spec is optional: not every Discovery Engine data store
is provisioned for extractive answers/segments, and asking for them where they
aren't supported gets the WHOLE request rejected with a 400 — which took the
policy chat down entirely.
"""
import io
import json
import urllib.error

import pytest

try:
    from backend.pipeline import query
except ImportError as exc:  # pragma: no cover - environment-dependent
    query = None
    _import_error = str(exc)

from backend.webapp.errors import classify_error, ERROR_MESSAGES

pytestmark_query = pytest.mark.skipif(
    query is None,
    reason=f"google-genai not importable: {globals().get('_import_error', '')}",
)


@pytestmark_query
class TestSearchBody:
    def test_rich_body_requests_extractive_content(self):
        body = query._search_body("q", 10, rich=True)
        spec = body["contentSearchSpec"]
        assert "extractiveContentSpec" in spec
        assert "summarySpec" not in spec
        assert spec["snippetSpec"]["returnSnippet"] is True

    def test_grounded_answer_is_requested_from_agent_search(self):
        body = query._search_body(
            "q", 10, rich=True, generate_summary=True,
        )
        summary = body["contentSearchSpec"]["summarySpec"]
        assert summary["includeCitations"] is True
        assert summary["summaryResultCount"] == 10
        assert "policy assistant" in summary["modelPromptSpec"]["preamble"]

    def test_plain_body_omits_extractive_content(self):
        # The fallback shape: snippets only, which every data store supports.
        body = query._search_body("q", 10, rich=False)
        spec = body["contentSearchSpec"]
        assert "extractiveContentSpec" not in spec
        assert "summarySpec" not in spec
        assert "snippetSpec" in spec

    def test_query_and_page_size_carried_either_way(self):
        for rich in (True, False):
            body = query._search_body("use of force", 25, rich=rich)
            assert body["query"] == "use of force"
            assert body["pageSize"] == 25


@pytestmark_query
class TestAgentSearchGroundedAnswer:
    def test_summary_rejection_preserves_rich_passages(self, monkeypatch):
        requests = []
        payload = {
            "results": [{
                "document": {"derivedStructData": {
                    "title": "Policy 1",
                    "extractiveSegments": [{"content": "A complete rule."}],
                }},
            }],
        }

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(payload).encode()

        def fake_urlopen(request, **_kwargs):
            body = json.loads(request.data)
            requests.append(body)
            if len(requests) == 1:
                raise urllib.error.HTTPError(
                    "u", 400, "Bad Request", {},
                    io.BytesIO(b'{"error":"summary unsupported"}'),
                )
            return _Response()

        monkeypatch.setattr(query, "_get_token", lambda: "tok")
        monkeypatch.setattr(query.urllib.request, "urlopen", fake_urlopen)

        contexts, raw_count, returned_payload = query._search_with_stats(
            "q", generate_summary=True, include_payload=True,
        )

        assert "summarySpec" in requests[0]["contentSearchSpec"]
        assert "summarySpec" not in requests[1]["contentSearchSpec"]
        assert "extractiveContentSpec" in requests[1]["contentSearchSpec"]
        assert contexts == [{"source": "Policy 1", "text": "A complete rule."}]
        assert raw_count == 1
        assert returned_payload == payload

    def test_cited_summary_skips_general_vertex_generation(self, monkeypatch):
        retrieved = [
            {"source": "Policy 1", "text": "Staff must report the event."},
            {"source": "Policy 2", "text": "The report is due immediately."},
        ]
        payload = {
            "summary": {
                "summaryText": (
                    "Staff must report the event [1]. The report is due "
                    "immediately [2]."
                ),
            },
        }
        seen = {}

        monkeypatch.setattr(query, "_classify_query", lambda *_a, **_k: True)

        def fake_search(*_args, **kwargs):
            seen.update(kwargs)
            return retrieved, len(retrieved), payload

        monkeypatch.setattr(query, "_search_with_stats", fake_search)
        monkeypatch.setattr(
            query, "_get_gen_client",
            lambda: pytest.fail("Gemini fallback should not run"),
        )

        result = query.answer_question("When is the report due?")

        assert seen["generate_summary"] is True
        assert seen["include_payload"] is True
        assert result["answer"] == (
            "Staff must report the event [1]. The report is due immediately [2]."
        )
        assert result["sources"] == ["Policy 1", "Policy 2"]

    def test_history_disables_agent_summary_request(self, monkeypatch):
        seen = {}
        retrieved = [{"source": "Policy 1", "text": "A fictional rule."}]

        monkeypatch.setattr(query, "_classify_query", lambda *_a, **_k: True)

        def fake_search(*_args, **kwargs):
            seen.update(kwargs)
            return retrieved, 1, {}

        class _Models:
            @staticmethod
            def generate_content(**_kwargs):
                return type("Response", (), {"text": "A fictional rule [1]."})()

        client = type("Client", (), {"models": _Models()})()
        monkeypatch.setattr(query, "_search_with_stats", fake_search)
        monkeypatch.setattr(query, "_get_gen_client", lambda: client)

        result = query.answer_question(
            "And then?",
            history=[{"question": "What happens?", "answer": "A rule."}],
        )

        assert seen["generate_summary"] is False
        assert result["sources"] == ["Policy 1"]


class TestClassifyError:
    def test_missing_credentials(self):
        category, status = classify_error(
            RuntimeError("Your default credentials were not found"))
        assert category == "credentials" and status == 503

    def test_model_not_found_is_its_own_category(self):
        # The M-1 failure mode: a model id that doesn't exist in this project.
        category, status = classify_error(
            RuntimeError("Publisher Model `gemini-9.9-pro` was not found"))
        assert category == "model" and status == 503

    def test_search_api_error(self):
        category, status = classify_error(RuntimeError("Search API error 400"))
        assert category == "upstream" and status == 500

    def test_permission(self):
        assert classify_error(RuntimeError("403 permission denied"))[0] == "permission"

    def test_quota(self):
        assert classify_error(RuntimeError("429 RESOURCE_EXHAUSTED"))[0] == "quota"

    def test_timeout(self):
        assert classify_error(TimeoutError("timed out"))[0] == "timeout"

    def test_unknown_falls_back_to_internal(self):
        assert classify_error(ValueError("something odd"))[0] == "internal"

    def test_every_category_has_a_message(self):
        for category in ("credentials", "model", "permission", "upstream",
                         "timeout", "quota", "internal"):
            assert ERROR_MESSAGES[category]

    def test_messages_leak_no_internals(self):
        blob = " ".join(ERROR_MESSAGES.values()).lower()
        for banned in ("traceback", "gen-lang-client", "googleapis.com", "bearer"):
            assert banned not in blob
