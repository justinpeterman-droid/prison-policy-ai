"""Unit tests for the pure retrieval helpers (no AI, no GCP)."""
from backend.pipeline.retrieval import (
    augment_query, extract_passage_text, extract_source_label,
    format_history, parse_search_results, select_passages,
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


class TestRichPassagePreference:
    """RC-5: prefer the real policy language over clipped snippet fragments."""

    RICH_DOC = {
        "derivedStructData": {
            "title": "AD 14-15",
            "snippets": [{"snippet": "…use of force must be …reported…"}],
            "extractive_answers": [{"content": "Use of force must be reported to the shift supervisor."}],
            "extractive_segments": [{"content": "Section 4. Any use of force, including "
                                                "the display of a chemical agent, must be "
                                                "reported to the shift supervisor within 24 hours."}],
        }
    }

    def test_segments_win_over_answers_and_snippets(self):
        text = extract_passage_text(self.RICH_DOC)
        assert text.startswith("Section 4.")
        assert "…" not in text

    def test_answers_win_over_snippets(self):
        doc = {"derivedStructData": {
            "title": "T",
            "snippets": [{"snippet": "…clipped…"}],
            "extractive_answers": [{"content": "Full answer sentence."}],
        }}
        assert extract_passage_text(doc) == "Full answer sentence."

    def test_snippets_still_used_when_nothing_richer(self):
        doc = {"derivedStructData": {"title": "T",
                                     "snippets": [{"snippet": "Only a snippet."}]}}
        assert extract_passage_text(doc) == "Only a snippet."

    def test_truncates_on_sentence_boundary(self):
        doc = {"derivedStructData": {
            "title": "T",
            "extractive_segments": [{"content": "First sentence here. Second sentence here. "
                                                "Third sentence runs past the limit."}],
        }}
        out = extract_passage_text(doc, max_chars=45)
        assert out.endswith(".")
        assert "Third sentence" not in out

    def test_truncation_marks_a_hard_cut(self):
        doc = {"derivedStructData": {
            "title": "T",
            "extractive_segments": [{"content": "x" * 500}],
        }}
        out = extract_passage_text(doc, max_chars=100)
        assert len(out) <= 101 and out.endswith("…")

    def test_no_truncation_by_default(self):
        doc = {"derivedStructData": {
            "title": "T", "extractive_segments": [{"content": "y" * 5000}]}}
        assert len(extract_passage_text(doc)) == 5000

    def test_parse_search_results_applies_the_cap(self):
        payload = {"results": [{"document": {
            "derivedStructData": {"title": "T",
                                  "extractive_segments": [{"content": "z" * 900}]}}}]}
        ctx = parse_search_results(payload, max_chars=200)
        assert len(ctx[0]["text"]) <= 201


class TestContextBudget:
    def _p(self, source, text):
        return {"source": source, "text": text}

    def test_total_char_budget_stops_accumulation(self):
        ctx = [self._p(f"S{i}", "w" * 400) for i in range(10)]
        out = select_passages(ctx, 10, max_total_chars=1000)
        assert sum(len(c["text"]) for c in out) <= 1000
        assert len(out) < 10

    def test_first_passage_always_survives_the_budget(self):
        # Even one oversized passage beats sending the generator nothing.
        ctx = [self._p("S1", "w" * 5000), self._p("S2", "w" * 5000)]
        out = select_passages(ctx, 5, max_total_chars=100)
        assert len(out) == 1

    def test_budget_off_by_default(self):
        ctx = [self._p(f"S{i}", "w" * 400) for i in range(5)]
        assert len(select_passages(ctx, 10)) == 5


class TestFormatHistory:
    """RC-6: recent turns, compact, newest kept when the budget bites."""

    def _h(self, n):
        return [{"question": f"question {i}", "answer": f"answer {i}"}
                for i in range(n)]

    def test_empty_and_malformed(self):
        assert format_history(None) == ""
        assert format_history([]) == ""
        assert format_history(["not a dict", 42]) == ""
        assert format_history([{"answer": "no question"}]) == ""

    def test_renders_oldest_first(self):
        out = format_history(self._h(2))
        assert out.index("question 0") < out.index("question 1")
        assert "Officer:" in out and "Assistant:" in out

    def test_keeps_only_the_most_recent_turns(self):
        out = format_history(self._h(10), max_turns=3)
        assert "question 9" in out and "question 8" in out
        assert "question 5" not in out

    def test_drops_oldest_first_under_char_budget(self):
        # The nearest turn is the one a pronoun refers to, so it must survive.
        out = format_history(self._h(4), max_chars=60)
        assert "question 3" in out
        assert "question 0" not in out

    def test_question_without_answer_still_included(self):
        out = format_history([{"question": "did it fail?", "answer": ""}])
        assert "did it fail?" in out
        assert "Assistant:" not in out

    def test_long_answers_are_truncated(self):
        out = format_history([{"question": "q", "answer": "z" * 5000}])
        assert len(out) < 1000
