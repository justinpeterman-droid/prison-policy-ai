"""Unit tests for the policy-chat eval scorer (pure functions, no GCP)."""

from tests.eval.scorer import (
    contains_any,
    score_answer,
    score_retrieval,
    score_gate,
    summarize,
)


class TestContainsAny:
    def test_single_string(self):
        assert contains_any("PREA zero tolerance", "prea") is True
        assert contains_any("nothing here", "prea") is False

    def test_synonym_list_any_of(self):
        assert (
            contains_any(
                "Prison Rape Elimination Act", ["PREA", "Prison Rape Elimination Act"]
            )
            is True
        )
        assert contains_any("unrelated", ["PREA", "sexual misconduct"]) is False

    def test_empty_text(self):
        assert contains_any("", "anything") is False


class TestScoreAnswer:
    def test_all_requirements_met(self):
        r = score_answer(
            "PREA is a zero tolerance policy and strictly prohibited.",
            must_contain=[["PREA"], ["prohibited", "zero tolerance"]],
        )
        assert r["passed"] is True
        assert r["missing"] == []

    def test_missing_requirement_fails(self):
        r = score_answer("This is prohibited.", must_contain=[["PREA"], ["prohibited"]])
        assert r["passed"] is False
        assert [["PREA"]] == [m for m in r["missing"]]

    def test_forbidden_phrase_fails(self):
        r = score_answer(
            "Dating an inmate is allowed if discreet.",
            must_contain=[],
            must_not_contain=["is allowed"],
        )
        assert r["passed"] is False
        assert "is allowed" in r["forbidden_present"]

    def test_negation_does_not_trip_forbidden(self):
        # "is not allowed" must NOT match the forbidden phrase "is allowed".
        r = score_answer(
            "This is not allowed under any circumstance.",
            must_not_contain=["is allowed"],
        )
        assert r["passed"] is True

    def test_no_constraints_passes(self):
        assert score_answer("anything")["passed"] is True


class TestScoreRetrieval:
    def test_hit_when_expected_source_present(self):
        r = score_retrieval(["PREA", "800"], ["ADC Policy 800 - PREA", "Use of Force"])
        assert r["hit"] is True
        assert "PREA" in r["matched"]

    def test_miss_when_absent(self):
        r = score_retrieval(["grievance"], ["Use of Force", "Contraband"])
        assert r["hit"] is False
        assert r["matched"] == []

    def test_no_expectation_is_none(self):
        # None so it's excluded from the hit-rate average.
        assert score_retrieval([], ["whatever"])["hit"] is None


class TestScoreGate:
    def test_matches(self):
        assert score_gate(True, True) is True
        assert score_gate(False, False) is True

    def test_mismatch(self):
        assert score_gate(True, False) is False
        assert score_gate(False, True) is False


class TestSummarize:
    def test_rates_ignore_na(self):
        results = [
            {"gate_ok": True, "retrieval_hit": True, "answer_pass": True},
            {"gate_ok": False, "retrieval_hit": None, "answer_pass": False},
            {"gate_ok": True, "answer_pass": True},  # no retrieval key
        ]
        s = summarize(results)
        assert s["n"] == 3
        assert s["gate_accuracy"] == round(2 / 3, 3)
        # Only one case had a non-None retrieval_hit (True).
        assert s["retrieval_hit_rate"] == 1.0
        assert s["answer_pass_rate"] == round(2 / 3, 3)

    def test_empty(self):
        s = summarize([])
        assert s["n"] == 0
        assert s["gate_accuracy"] is None
