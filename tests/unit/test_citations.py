"""Unit tests for policy-chat citation post-processing (pure, no GCP)."""
from backend.pipeline.citations import (
    cited_indices, renumber, build_grounded, infer_citations, support_score,
)


def _ctx(n):
    return [{"source": f"Policy {i}", "text": f"passage {i}"} for i in range(1, n + 1)]


class TestCitedIndices:
    def test_first_appearance_order_deduped(self):
        assert cited_indices("a [3] b [1] c [3] d [1]", 5) == [3, 1]

    def test_out_of_range_ignored(self):
        assert cited_indices("x [9] y [2]", 3) == [2]

    def test_none_when_no_markers(self):
        assert cited_indices("no citations here", 5) == []

    def test_empty_answer(self):
        assert cited_indices("", 5) == []


class TestRenumber:
    def test_sequential_in_given_order(self):
        answer, mapping = renumber("first [3] then [1]", [3, 1])
        assert answer == "first [1] then [2]"
        assert mapping == {3: 1, 1: 2}

    def test_uncited_markers_untouched(self):
        # [4] isn't in the cited list, so it's left as-is.
        answer, _ = renumber("a [2] b [4]", [2])
        assert answer == "a [1] b [4]"


class TestBuildGrounded:
    def test_grounded_surfaces_only_cited_passages(self):
        raw = "Report within 24 hours [3]. Restrain first [1]."
        answer, citations, grounded = build_grounded(raw, _ctx(5))
        assert grounded is True
        # Renumbered in reading order: [3]->1, [1]->2.
        assert answer == "Report within 24 hours [1]. Restrain first [2]."
        assert [c["n"] for c in citations] == [1, 2]
        assert citations[0]["source"] == "Policy 3"
        assert citations[1]["source"] == "Policy 1"

    def test_ungrounded_when_no_citations(self):
        answer, citations, grounded = build_grounded("A plausible but uncited answer.", _ctx(3))
        assert grounded is False
        assert citations == []
        assert answer == "A plausible but uncited answer."

    def test_only_valid_citations_count(self):
        # [7] is out of range for 3 passages -> treated as no valid citation.
        answer, citations, grounded = build_grounded("see [7]", _ctx(3))
        assert grounded is False
        assert citations == []


class TestSupportScore:
    """RC-4: pure lexical containment used for inferred grounding."""

    def test_full_containment(self):
        assert support_score(
            "Use of force must be reported.",
            "Policy: any use of force must be reported within 24 hours.") == 1.0

    def test_no_overlap(self):
        assert support_score("Inmate visitation hours.",
                             "Chemical agents storage requirements.") == 0.0

    def test_partial_overlap(self):
        score = support_score("Restraints require supervisor approval.",
                              "Restraints require documentation.")
        assert 0.0 < score < 1.0

    def test_stopwords_and_short_words_ignored(self):
        # Sentence made only of stopwords has nothing to score.
        assert support_score("It is what it was.", "totally unrelated text") == 0.0

    def test_empty_inputs(self):
        assert support_score("", "something") == 0.0
        assert support_score("something meaningful here", "") == 0.0


class TestInferCitations:
    """The fallback must recover real grounding WITHOUT ever vouching for an
    answer the passages don't support."""

    PASSAGES = [
        {"source": "AD 14-15", "text": "Any use of force must be reported to the "
                                       "shift supervisor within 24 hours of the incident."},
        {"source": "Post Order 7", "text": "Officers shall conduct a formal count "
                                           "at the beginning of every shift."},
    ]

    def test_recovers_citations_when_markers_missing(self):
        answer = ("Any use of force must be reported to the shift supervisor "
                  "within 24 hours of the incident.")
        citations, grounded = infer_citations(answer, self.PASSAGES)
        assert grounded is True
        assert [c["source"] for c in citations] == ["AD 14-15"]

    def test_does_not_ground_an_invented_answer(self):
        # The safety-critical case: content absent from every passage must NOT
        # be presented as document-backed.
        answer = ("Inmates are entitled to four hours of recreation and may "
                  "keep personal electronics in their cell.")
        citations, grounded = infer_citations(answer, self.PASSAGES)
        assert grounded is False
        assert citations == []

    def test_mixed_answer_below_ratio_is_not_grounded(self):
        # One supported sentence out of four is not enough.
        answer = ("Any use of force must be reported to the shift supervisor "
                  "within 24 hours of the incident. "
                  "Inmates receive unlimited commissary credit. "
                  "Personal vehicles may be parked inside the secure perimeter. "
                  "Staff may accept gifts from inmate families.")
        _, grounded = infer_citations(answer, self.PASSAGES)
        assert grounded is False

    def test_numbers_citations_in_first_use_order(self):
        answer = ("Officers shall conduct a formal count at the beginning of "
                  "every shift. Any use of force must be reported to the shift "
                  "supervisor within 24 hours of the incident.")
        citations, grounded = infer_citations(answer, self.PASSAGES)
        assert grounded is True
        assert [c["n"] for c in citations] == [1, 2]
        assert [c["source"] for c in citations] == ["Post Order 7", "AD 14-15"]

    def test_trivial_sentences_are_not_evidence(self):
        citations, grounded = infer_citations("Yes. No. It is.", self.PASSAGES)
        assert grounded is False
        assert citations == []

    def test_no_contexts(self):
        assert infer_citations("anything at all here", []) == ([], False)


class TestBuildGroundedInference:
    def test_infer_off_by_default_preserves_old_behavior(self):
        raw = ("Any use of force must be reported to the shift supervisor "
               "within 24 hours of the incident.")
        ctx = [{"source": "AD 14-15", "text": raw}]
        _, citations, grounded = build_grounded(raw, ctx)
        assert grounded is False and citations == []

    def test_infer_recovers_grounding(self):
        raw = ("Any use of force must be reported to the shift supervisor "
               "within 24 hours of the incident.")
        ctx = [{"source": "AD 14-15", "text": raw}]
        answer, citations, grounded = build_grounded(raw, ctx, infer=True)
        assert grounded is True
        assert [c["source"] for c in citations] == ["AD 14-15"]
        # Model prose is never rewritten by the fallback.
        assert answer == raw

    def test_explicit_markers_still_win(self):
        raw = "Report within 24 hours [2]."
        ctx = [{"source": "A", "text": "x"}, {"source": "B", "text": "y"}]
        answer, citations, grounded = build_grounded(raw, ctx, infer=True)
        assert grounded is True
        assert answer == "Report within 24 hours [1]."
        assert [c["source"] for c in citations] == ["B"]

    def test_infer_cannot_rescue_an_unsupported_answer(self):
        _, citations, grounded = build_grounded(
            "Officers may release inmates at their own discretion.",
            [{"source": "A", "text": "Formal count occurs each shift."}],
            infer=True)
        assert grounded is False and citations == []
