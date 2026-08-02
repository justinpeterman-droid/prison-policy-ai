"""Unit tests for the search-request fallback and shared error classification.

The extractive-content spec is optional: not every Discovery Engine data store
is provisioned for extractive answers/segments, and asking for them where they
aren't supported gets the WHOLE request rejected with a 400 — which took the
policy chat down entirely.
"""
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
        assert spec["snippetSpec"]["returnSnippet"] is True

    def test_plain_body_omits_extractive_content(self):
        # The fallback shape: snippets only, which every data store supports.
        body = query._search_body("q", 10, rich=False)
        spec = body["contentSearchSpec"]
        assert "extractiveContentSpec" not in spec
        assert "snippetSpec" in spec

    def test_query_and_page_size_carried_either_way(self):
        for rich in (True, False):
            body = query._search_body("use of force", 25, rich=rich)
            assert body["query"] == "use of force"
            assert body["pageSize"] == 25


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
