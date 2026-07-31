"""Unit tests for policy-chat citation post-processing (pure, no GCP)."""
from backend.pipeline.citations import cited_indices, renumber, build_grounded


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
