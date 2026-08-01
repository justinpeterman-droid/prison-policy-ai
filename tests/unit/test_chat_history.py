"""Unit tests for chat history sanitisation on /api/chat (RC-6).

History arrives from the browser, so it is untrusted input that lands straight
in a prompt we pay per token for. These assert it stays bounded and that a
malformed history degrades context rather than failing the request.
"""
import pytest

try:
    from backend.webapp.routes import chat
except ImportError as exc:  # pragma: no cover - environment-dependent
    chat = None
    _import_error = str(exc)

pytestmark = pytest.mark.skipif(
    chat is None,
    reason=f"google-genai not importable: {globals().get('_import_error', '')}",
)


class TestCleanHistory:
    def test_non_list_inputs_are_dropped(self):
        for bad in (None, "history", 42, {"question": "q"}):
            assert chat._clean_history(bad) == []

    def test_malformed_entries_are_skipped_not_fatal(self):
        out = chat._clean_history(
            ["string", 7, None, {"answer": "orphan"}, {"question": "real one"}])
        assert [h["question"] for h in out] == ["real one"]

    def test_caps_the_number_of_turns(self):
        raw = [{"question": f"q{i}", "answer": "a"} for i in range(50)]
        out = chat._clean_history(raw)
        assert len(out) == chat.MAX_HISTORY_ITEMS
        # Keeps the most recent, which are the ones a follow-up refers to.
        assert out[-1]["question"] == "q49"

    def test_caps_field_length(self):
        out = chat._clean_history([{"question": "q" * 99999, "answer": "a" * 99999}])
        assert len(out[0]["question"]) == chat.MAX_HISTORY_FIELD_CHARS
        assert len(out[0]["answer"]) == chat.MAX_HISTORY_FIELD_CHARS

    def test_non_string_fields_are_coerced(self):
        out = chat._clean_history([{"question": 123, "answer": {"a": 1}}])
        assert out[0]["question"] == "123"

    def test_whitespace_only_question_is_dropped(self):
        assert chat._clean_history([{"question": "   ", "answer": "a"}]) == []
