"""Unit tests for the style validator and its auto-repair (no AI, no GCP).

The validator's first job is to not cry wolf: it runs on every generation, and a
rule that flags correct output trains officers to ignore it. So the first test
here is that a report written exactly to the shipped rulings scores a clean 1.0.
"""
import pytest

from backend.reports.report_validator import (
    repair, repair_all, required_sentences_for, summarize,
    validate_all, validate_report,
)

OFFICER = {"rank": "Sgt.", "first": "Dana", "last": "Ferraro"}
NOTES = ("8 barracks ~950pm Roe 111111 and Doe 222222 fighting, gave 3 orders, "
         "me and Ford cuffed em, both to RH")
ALLOW = ["9:50 pm", "August 4, 2026"]

# Written to STYLE_RULINGS.md exactly: 'ADC# 111111' (4), 'Sgt.' (2),
# lowercase mid-sentence 'inmate' (6), '9:50 pm' (11), no closer (13).
GOOD = ("I, Sgt. Dana Ferraro, was assigned to 8 Barracks when at approximately "
        "9:50 pm Inmate Roe, Richard ADC# 111111 and inmate Doe, John ADC# 222222 "
        "began fighting. I gave three direct orders to stop. Cpl. Amy Ford and I "
        "applied hand restraints to inmate Roe and inmate Doe. "
        "Inmate Roe, Richard ADC# 111111 was placed in Restrictive Housing.")


def _validate(text, report_type="first_person", **kw):
    kw.setdefault("notes", NOTES)
    kw.setdefault("allow", ALLOW)
    return validate_report(report_type, text, OFFICER, **kw)


def _rules(result):
    return {v.rule_id for v in result.violations}


class TestItDoesNotCryWolf:
    """The rule that matters most: correct output must score clean."""

    def test_a_correct_report_has_no_violations(self):
        r = _validate(GOOD)
        assert r.violations == [], [v.message for v in r.violations]
        assert r.score == 1.0

    def test_an_adc_number_written_bare_in_the_notes_is_not_fabrication(self):
        """Officers write 'Roe 111111'; the report renders 'ADC# 111111'. A
        literal comparison read every correctly-cited ADC number as invented."""
        assert "RW-030" not in _rules(_validate(GOOD))

    def test_a_supplement_marker_is_not_a_forbidden_placeholder(self):
        """[TO BE SUPPLEMENTED: ...] is produced deliberately by validate.py
        when the officer answers UNKNOWN — flagging it fights the design."""
        text = GOOD + " [TO BE SUPPLEMENTED: weapon involved]"
        assert "RW-033" not in _rules(_validate(text))

    def test_lowercase_inmate_mid_sentence_is_accepted(self):
        assert "RW-001" not in _rules(_validate(GOOD))

    def test_an_empty_report_is_blocking(self):
        r = _validate("")
        assert r.has_blocking
        assert "RW-000" in _rules(r)


class TestRulingConformance:
    def test_adc_number_without_a_space_is_blocking(self):
        r = _validate(GOOD.replace("ADC# 111111", "ADC#111111"))
        assert "RW-002" in _rules(r)
        assert r.has_blocking

    def test_rank_without_its_period_is_blocking(self):
        r = _validate(GOOD.replace("Cpl. Amy Ford", "Cpl Amy Ford"))
        assert "RW-003" in _rules(r)

    def test_a_24_hour_time_is_blocking(self):
        assert "RW-005" in _rules(_validate(GOOD.replace("9:50 pm", "21:50 PM")))

    def test_military_time_is_blocking(self):
        assert "RW-005" in _rules(_validate(GOOD + " Relieved at 2200 hours."))

    @pytest.mark.parametrize("closer", [
        "End of report.", "End of Statement.", "Disciplinary action taken."])
    def test_a_statement_closer_is_blocking(self, closer):
        assert "RW-014" in _rules(_validate(GOOD + " " + closer))

    def test_medical_detail_is_blocking(self):
        assert "RW-031" in _rules(_validate(GOOD + " He had a laceration."))

    def test_subjective_language_is_only_a_warning(self):
        r = _validate(GOOD + " Clearly he was at fault.")
        assert "RW-034" in _rules(r)
        assert not [v for v in r.violations
                    if v.rule_id == "RW-034" and v.severity == "BLOCKING"]

    def test_a_placeholder_used_as_a_name_is_blocking(self):
        assert "RW-006" in _rules(_validate("I, Sgt. Dana Ferraro, saw Inmate Unknown."))

    def test_a_genuinely_invented_adc_number_is_still_caught(self):
        """The false-positive fix must not blunt the real check."""
        assert "RW-030" in _rules(_validate(GOOD.replace("ADC# 111111", "ADC# 987654")))


class TestPerReportRules:
    def test_missing_self_reference_is_blocking_in_first_person(self):
        r = _validate("Inmate Roe, Richard ADC# 111111 was restrained.")
        assert "RW-004" in _rules(r)

    def test_a_repeated_self_reference_is_blocking(self):
        assert "RW-004" in _rules(_validate(GOOD + " I, Sgt. Dana Ferraro, then left."))

    def test_self_reference_is_not_required_in_a_supervisor_summary(self):
        r = _validate("On August 4, 2026 Sgt. Ferraro responded to 8 Barracks.",
                      report_type="supervisor_summary")
        assert "RW-004" not in _rules(r)

    def test_first_person_in_a_supervisor_summary_is_blocking(self):
        r = _validate("On August 4, 2026 I responded to 8 Barracks.",
                      report_type="supervisor_summary")
        assert "RW-035" in _rules(r)

    def test_a_quoted_i_does_not_trip_the_third_person_rule(self):
        r = _validate('On August 4, 2026 Sgt. Ferraro heard him yell "I did not do it".',
                      report_type="supervisor_summary")
        assert "RW-035" not in _rules(r)

    def test_disciplinary_requires_the_charging_closer(self):
        r = _validate("I, Sgt. Dana Ferraro, saw the fight.", report_type="disciplinary")
        assert "RW-013" in _rules(r)

    def test_disciplinary_closer_worded_per_ruling_5_passes(self):
        text = ("I, Sgt. Dana Ferraro, observed the altercation. Due to the above "
                "stated facts I, Sgt. Dana Ferraro, am charging inmate Roe, Richard "
                "ADC# 111111 with major rule violation 12-1 pending DCR.")
        assert "RW-013" not in _rules(_validate(text, report_type="disciplinary"))

    def test_investigation_opening_formula(self):
        good = ("I, Sgt. Dana Ferraro, started an investigation at 9:50 pm and "
                "concluded it at 11:15 pm on August 4, 2026 with the following "
                "findings: I reviewed the camera footage.")
        assert "RW-010" not in _rules(
            _validate(good, report_type="investigation", allow=ALLOW + ["11:15 pm"]))
        bad = "The investigation found that a fight occurred."
        assert "RW-010" in _rules(_validate(bad, report_type="investigation"))


class TestRequiredSentenceRouting:
    AUTO = [
        {"id": "a", "insert_into": ["first_person"], "text": "Alpha sentence."},
        {"id": "b", "insert_into": ["cover_letter"], "text": "Bravo sentence."},
        {"id": "c", "insert_into": ["first_person", "cover_letter"],
         "text": "Charlie sentence."},
    ]

    def test_each_report_gets_only_its_own_sentences(self):
        assert required_sentences_for("first_person", self.AUTO) == [
            "Alpha sentence.", "Charlie sentence."]
        assert required_sentences_for("cover_letter", self.AUTO) == [
            "Bravo sentence.", "Charlie sentence."]
        assert required_sentences_for("supervisor_summary", self.AUTO) == []

    def test_a_plain_string_list_still_applies_everywhere(self):
        assert required_sentences_for("anything", ["One.", "Two."]) == ["One.", "Two."]

    def test_a_cover_letter_is_not_flagged_for_the_narratives_sentences(self):
        """Checking every report against every sentence produced three false
        BLOCKING violations on a perfectly good set of reports."""
        reports = {"cover_letter": "On August 4, 2026 I, Sgt. Dana Ferraro, was "
                                   "notified. Bravo sentence. Charlie sentence."}
        results = validate_all(reports, OFFICER, NOTES, self.AUTO, ALLOW)
        assert "RW-032" not in _rules(results["cover_letter"])


class TestRepair:
    def test_it_adds_the_missing_adc_space(self):
        out, fixed = repair("Inmate Roe ADC#111111 was restrained.")
        assert "ADC# 111111" in out
        assert fixed == ["RW-002"]

    def test_it_restores_a_rank_period(self):
        out, fixed = repair("Sgt Ford responded.")
        assert out.startswith("Sgt. Ford")
        assert "RW-003" in fixed

    def test_it_strips_a_statement_closer(self):
        out, fixed = repair("He was restrained. End of report.")
        assert out == "He was restrained."
        assert "RW-014" in fixed

    def test_correct_text_is_left_exactly_alone(self):
        out, fixed = repair(GOOD)
        assert out == GOOD
        assert fixed == []

    def test_repair_never_touches_a_fact(self):
        """Every ADC#, date and time must survive a repair pass unchanged —
        a repair that alters a fact is the failure this system exists to stop."""
        import re
        messy = ("Sgt Ford saw Inmate Roe ADC#111111 at 9:50 pm on 08-04-2026. "
                 "End of report.")
        out, _ = repair(messy)
        assert re.findall(r"\d+", messy) == re.findall(r"\d+", out)

    def test_repair_all_reports_and_records_what_changed(self):
        reports, repaired = repair_all(
            {"first_person": "Sgt Ford responded. End of report.",
             "cover_letter": "On August 4, 2026 the incident occurred."})
        assert repaired == {"first_person": ["RW-003", "RW-014"]}
        assert reports["cover_letter"] == "On August 4, 2026 the incident occurred."

    def test_repair_all_passes_non_string_values_through(self):
        # generate_all_reports puts a list under '_errors'.
        reports, _ = repair_all({"_errors": ["first_person"], "cover_letter": "x"})
        assert reports["_errors"] == ["first_person"]

    def test_an_empty_report_is_safe(self):
        assert repair("") == ("", [])


class TestSummarize:
    def test_it_reports_blocking_across_every_report(self):
        results = validate_all(
            {"first_person": GOOD.replace("ADC# 111111", "ADC#111111"),
             "cover_letter": "On August 4, 2026 I, Sgt. Dana Ferraro, was notified."},
            OFFICER, NOTES, None, ALLOW)
        out = summarize(results)
        assert out["blocking_count"] >= 1
        assert any(b["rule_id"] == "RW-002" and b["report_type"] == "first_person"
                   for b in out["blocking"])
        assert 0.0 <= out["score"] <= 1.0

    def test_a_clean_set_summarizes_to_a_perfect_score(self):
        out = summarize(validate_all({"first_person": GOOD}, OFFICER, NOTES, None, ALLOW))
        assert out["blocking_count"] == 0
        assert out["score"] == 1.0

    def test_empty_input_does_not_divide_by_zero(self):
        assert summarize({})["score"] == 1.0


class TestSentenceSplitting:
    """Ruling 2 requires the period on ranks, which a naive sentence split
    reads as the end of a sentence — tearing 'I, Sgt. Dana Ferraro, was...' into
    'I, Sgt.' and failing the opening check on correct text."""

    def test_a_rank_period_does_not_end_a_sentence(self):
        from backend.reports.report_validator import _split_sentences
        assert _split_sentences(
            "I, Sgt. Dana Ferraro, was assigned. I applied restraints."
        ) == ["I, Sgt. Dana Ferraro, was assigned.", "I applied restraints."]

    def test_the_opening_check_passes_on_a_ranked_officer(self):
        assert "RW-010" not in _rules(_validate(GOOD))

    def test_the_form_time_prefix_does_not_split(self):
        from backend.reports.report_validator import _split_sentences
        assert len(_split_sentences("Logged at APX. 9:50 PM by the officer.")) == 1
