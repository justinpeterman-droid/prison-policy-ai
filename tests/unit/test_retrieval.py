"""Unit tests for the pure retrieval helpers (no AI, no GCP)."""
from backend.pipeline.retrieval import (
    augment_query, extract_passage_text, extract_source_label,
    parse_search_results, select_passages,
)


def _result(document: dict) -> dict:
    """Wrap a document the way a Discovery Engine search payload does."""
    return {"results": [{"document": document}]}


class TestAugmentQuery:
    def test_maps_slang_and_appends(self):
        out = augment_query("can I date an inmate")
        assert out.startswith("can I date an inmate")
        assert "PREA" in out and "sexual misconduct" in out

    def test_unmatched_question_unchanged(self):
        q = "what is the count procedure"
        assert augment_query(q) == q

    def test_case_insensitive_trigger(self):
        assert "PREA" in augment_query("HOOKING UP with an inmate")

    def test_terms_are_deduped(self):
        # Two triggers ('hooking up' + 'romantic') both add 'PREA'/'sexual'/'misconduct'.
        out = augment_query("romantic hooking up")
        assert out.lower().split().count("prea") == 1

    def test_empty(self):
        assert augment_query("") == ""


class TestSelectPassages:
    def _p(self, src, text):
        return {"source": src, "text": text}

    def test_trims_to_k(self):
        ctx = [self._p(f"S{i}", f"t{i}") for i in range(10)]
        assert len(select_passages(ctx, 4)) == 4

    def test_drops_exact_duplicates(self):
        ctx = [self._p("A", "same"), self._p("A", "same"), self._p("B", "other")]
        out = select_passages(ctx, 10)
        assert len(out) == 2
        assert {c["source"] for c in out} == {"A", "B"}

    def test_caps_per_source(self):
        ctx = [self._p("A", f"t{i}") for i in range(5)] + [self._p("B", "x")]
        out = select_passages(ctx, 10, max_per_source=3)
        assert sum(1 for c in out if c["source"] == "A") == 3
        assert any(c["source"] == "B" for c in out)

    def test_skips_empty_text(self):
        ctx = [self._p("A", ""), self._p("B", "real")]
        out = select_passages(ctx, 10)
        assert [c["source"] for c in out] == ["B"]

    def test_preserves_order(self):
        ctx = [self._p("A", "1"), self._p("B", "2"), self._p("C", "3")]
        assert [c["source"] for c in select_passages(ctx, 2)] == ["A", "B"]


class TestParseSearchResults:
    """RC-1: a hit must not be dropped just because its text lives in an
    unexpected place. Dropping it makes a working search look like an empty
    corpus."""

    def test_snippets(self):
        ctx = parse_search_results(_result({
            "derivedStructData": {
                "title": "AD 14-15 PREA",
                "snippets": [{"snippet": "Zero tolerance.",
                              "snippet_status": "SUCCESS"}],
            }}))
        assert ctx == [{"text": "Zero tolerance.", "source": "AD 14-15 PREA"}]

    def test_joins_multiple_snippets(self):
        ctx = parse_search_results(_result({
            "derivedStructData": {
                "title": "T",
                "snippets": [{"snippet": "One."}, {"snippet": "Two."}],
            }}))
        assert ctx[0]["text"] == "One. Two."

    def test_no_snippet_available_falls_through_to_extractive(self):
        # The exact shape that produced the bug: a real hit whose snippet the
        # API could not build. Previously dropped -> "no documents found".
        ctx = parse_search_results(_result({
            "derivedStructData": {
                "title": "Post Order 7",
                "snippets": [{"snippet": "", "snippet_status": "NO_SNIPPET_AVAILABLE"}],
                "extractive_answers": [{"content": "Officers shall maintain."}],
            }}))
        assert ctx[0]["text"] == "Officers shall maintain."
        assert ctx[0]["source"] == "Post Order 7"

    def test_extractive_answers_camel_case(self):
        ctx = parse_search_results(_result({
            "derivedStructData": {
                "title": "T", "extractiveAnswers": [{"content": "Body text."}],
            }}))
        assert ctx[0]["text"] == "Body text."

    def test_uses_all_extractive_answers_not_just_the_first(self):
        ctx = parse_search_results(_result({
            "derivedStructData": {
                "title": "T",
                "extractive_answers": [{"content": "First."}, {"content": "Second."}],
            }}))
        assert ctx[0]["text"] == "First. Second."

    def test_extractive_segments_fallback(self):
        ctx = parse_search_results(_result({
            "derivedStructData": {
                "title": "T", "extractive_segments": [{"content": "Segment text."}],
            }}))
        assert ctx[0]["text"] == "Segment text."

    def test_raw_content_fallback(self):
        ctx = parse_search_results(_result({
            "derivedStructData": {"title": "T"},
            "content": {"rawText": "Raw policy body."},
        }))
        assert ctx[0]["text"] == "Raw policy body."

    def test_drops_only_documents_with_no_text_anywhere(self):
        payload = {"results": [
            {"document": {"derivedStructData": {"title": "Empty"}}},
            {"document": {"derivedStructData": {
                "title": "Real", "snippets": [{"snippet": "Text."}]}}},
        ]}
        assert [c["source"] for c in parse_search_results(payload)] == ["Real"]

    def test_empty_and_malformed_payloads(self):
        assert parse_search_results({}) == []
        assert parse_search_results({"results": []}) == []
        assert parse_search_results({"results": [{}]}) == []
        assert parse_search_results(None) == []


class TestSourceLabel:
    def test_prefers_title(self):
        assert extract_source_label(
            {"derivedStructData": {"title": "AD 14-15"}}) == "AD 14-15"

    def test_struct_data_title_is_reachable(self):
        # Previously unreachable: the code read structData from *inside*
        # derivedStructData, so this fallback never fired.
        assert extract_source_label(
            {"structData": {"title": "From structData"}}) == "From structData"

    def test_falls_back_to_file_name_from_link(self):
        assert extract_source_label(
            {"derivedStructData": {"link": "gs://bucket/policies/AD-14-15.pdf"}}
        ) == "AD-14-15.pdf"

    def test_default_label(self):
        assert extract_source_label({}) == "Policy Document"
        assert extract_source_label(None) == "Policy Document"


class TestExtractPassageText:
    def test_returns_empty_for_textless_document(self):
        assert extract_passage_text({"derivedStructData": {"title": "T"}}) == ""
        assert extract_passage_text({}) == ""
        assert extract_passage_text(None) == ""
