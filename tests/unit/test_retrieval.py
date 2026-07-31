"""Unit tests for the pure retrieval helpers (no AI, no GCP)."""
from backend.pipeline.retrieval import augment_query, select_passages


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
