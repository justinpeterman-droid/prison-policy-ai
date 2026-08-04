"""Unit tests for the deterministic gap/validation engine (no AI, no GCP).

These lock in the anti-fabrication contract: a null slot must raise a gap
question rather than being silently filled, and UNKNOWN answers must surface
as [TO BE SUPPLEMENTED] markers instead of gaps.
"""
import pytest

from backend.reports.validate import (
    find_gaps, load_checklist, invented_facts, investigation_occurred, UNKNOWN,
)


CATEGORIES = [
    "contraband", "inmate_fight", "staff_assault", "forced_cell_movement",
    "prea", "incident_no_disciplinary", "use_of_force", "medical_emergency",
    "other_rule_violation",
]


def test_load_checklist_is_cached():
    # lru_cache should hand back the very same object each call.
    assert load_checklist() is load_checklist()


def test_checklist_covers_every_known_category():
    names = {c["name"] for c in load_checklist()["categories"]}
    assert set(CATEGORIES) <= names


@pytest.mark.parametrize("category", CATEGORIES)
def test_find_gaps_returns_expected_shape(category):
    result = find_gaps(category, {})
    for key in ("gaps", "blocking_remaining", "markers", "checklist", "auto_content"):
        assert key in result
    assert isinstance(result["gaps"], list)
    assert isinstance(result["blocking_remaining"], int)


def test_empty_slots_produce_blocking_gaps():
    # With nothing extracted, required slots must be asked (not invented).
    result = find_gaps("inmate_fight", {})
    assert result["gaps"], "expected gap questions for empty inmate_fight notes"
    assert result["blocking_remaining"] >= 1
    # Every gap carries the metadata the UI needs to render it.
    for gap in result["gaps"]:
        assert gap.get("slot")
        assert "blocking" in gap
        assert gap.get("answer_type") in ("text", "choice", "yes_no")


def test_filling_a_slot_removes_its_gap():
    empty = find_gaps("inmate_fight", {})
    target = next(g["slot"] for g in empty["gaps"] if g["blocking"])
    filled = find_gaps("inmate_fight", {target: "some value"})
    assert target not in {g["slot"] for g in filled["gaps"]}


def test_unknown_becomes_marker_not_gap():
    empty = find_gaps("inmate_fight", {})
    target = next(g["slot"] for g in empty["gaps"] if g["blocking"])
    result = find_gaps("inmate_fight", {target: UNKNOWN})
    # UNKNOWN is an answer: it stops the asking...
    assert target not in {g["slot"] for g in result["gaps"]}
    # ...and instead surfaces as a supplement marker.
    joined = " ".join(result["markers"])
    assert "TO BE SUPPLEMENTED" in joined
    assert target.replace("_", " ") in joined


def test_choice_gaps_always_offer_other_option():
    result = find_gaps("contraband", {})
    for gap in result["gaps"]:
        if gap.get("answer_type") == "choice":
            assert gap.get("options"), "choice gaps must carry options"
            assert any("Other" in o for o in gap["options"])


def test_unknown_category_raises():
    with pytest.raises(KeyError):
        find_gaps("not_a_real_category", {})


# ── invented_facts (RG-1) ────────────────────────────────────────────────────

def test_invented_facts_flags_a_genuinely_invented_adc_number():
    # An ADC# in the output that never appeared in the notes IS suspicious.
    flags = invented_facts("Inmate Smith ADC#999888.", notes="Inmate Smith fought.",
                           answers={})
    assert any("999888" in f for f in flags)


def test_invented_facts_does_not_flag_a_value_from_the_notes():
    flags = invented_facts("...at approximately 10:00pm...",
                           notes="fight at 10:00pm in 8 barracks", answers={})
    assert flags == []


def test_invented_facts_does_not_flag_values_from_gap_answers():
    flags = invented_facts("Inmate Jones ADC#123456 was charged.",
                           notes="Inmate Jones fought.",
                           answers={"adc": "ADC#123456"})
    assert flags == []


def test_allow_list_suppresses_a_normalized_time():
    # The officer wrote '10pm'; the pipeline normalized it to '10:00pm'. That
    # normalized form is the system's own correct output — never "invented".
    flags = invented_facts("On duty at approximately 10:00pm the fight began.",
                           notes="fight ~10pm in 8 barracks", answers={},
                           allow=["10:00pm"])
    assert flags == []
    # Without the allow-list, the normalized time WOULD be flagged (the bug).
    assert invented_facts("...at approximately 10:00pm...",
                          notes="fight ~10pm", answers={})


def test_allow_list_suppresses_a_fallback_date():
    # Notes stated no date; the pipeline supplied today's. Not invented.
    flags = invented_facts("On 08-01-2026 the incident occurred.",
                           notes="Inmate Smith fought in the dayroom.", answers={},
                           allow=["08-01-2026"])
    assert flags == []


def test_allow_list_suppresses_a_built_incident_number():
    flags = invented_facts("Incident 2026-08-141 refers.",
                           notes="Inmate Smith fought.", answers={},
                           allow=["2026-08-141"])
    assert flags == []


def test_allow_list_ignores_none_and_empty_entries():
    # slots.get(...) may hand back None/'' for unfilled code-derived values.
    flags = invented_facts("Inmate Smith ADC#777.", notes="Inmate Smith fought.",
                           answers={}, allow=[None, "", "unrelated"])
    assert any("777" in f for f in flags)


# ── use_of_force / medical_emergency (STYLE_RULINGS.md rulings 9 & 10) ───────

def _one_inmate():
    return [{"role": "inmate", "last": "Roe", "first": "Richard",
             "adc_number": "111111"}]


@pytest.mark.parametrize("category", ["use_of_force", "medical_emergency"])
def test_new_category_never_asks_the_same_slot_twice(category):
    """A slot listed in required_slots AND covered by a universal rule used to
    render the same question twice on the Missing Information screen."""
    slots = [g["slot"] for g in find_gaps(category, {"persons": _one_inmate()})["gaps"]]
    assert len(slots) == len(set(slots)), f"duplicate gap questions: {slots}"


def test_use_of_force_carries_the_409_designation():
    """Ruling 9: a use of force files as a 005 that also carries the 409."""
    cat = next(c for c in load_checklist()["categories"]
               if c["name"] == "use_of_force")
    assert cat["form_designation"] == ["005", "409"]
    assert "use_of_force_report_409" in cat["forms_required"]


def test_use_of_force_asks_for_agent_detail_only_when_chemical():
    base = {"persons": _one_inmate()}
    assert not any(g["slot"] == "chemical_agent"
                   for g in find_gaps("use_of_force", base)["gaps"])
    chem = {**base, "force_type": "Chemical agent (OC/MK-3)"}
    slots = {g["slot"] for g in find_gaps("use_of_force", chem)["gaps"]}
    assert {"chemical_agent", "decontamination"} <= slots


def test_medical_emergency_generates_no_disciplinary_report():
    """A medical emergency is not a rule violation — there is nothing to charge."""
    cat = next(c for c in load_checklist()["categories"]
               if c["name"] == "medical_emergency")
    assert "disciplinary" not in cat["reports"]


def test_medical_emergency_auto_content_reads_as_grammatical_prose():
    answered = {
        "persons": _one_inmate(),
        "medical_condition": "having a seizure",
        "medical_response": "I called a Code Blue and cleared the area.",
        "escort_destination": "Infirmary ward for observation",
    }
    lines = {a["id"]: a["text"]
             for a in find_gaps("medical_emergency", answered)["auto_content"]}
    # The evaluation clause used to run on without a subject:
    # "Medical staff evaluated Inmate Roe and was escorted to ..."
    assert lines["medical_evaluation_line"] == "Medical staff evaluated inmate Roe."
    assert lines["medical_escort_line"].startswith("Inmate Roe was then escorted")


def test_escort_line_is_dropped_when_the_optional_slot_is_unanswered():
    """escort_destination is non-blocking, so an unanswered one must not inject
    a [NEEDED: ...] marker into the narrative."""
    ids = {a["id"] for a in find_gaps(
        "medical_emergency", {"persons": _one_inmate()})["auto_content"]}
    assert "medical_escort_line" not in ids


def test_inmate_object_is_lowercase_mid_sentence():
    """Ruling 6: 'inmate' is lowercase when it isn't opening a sentence."""
    lines = {a["id"]: a["text"] for a in find_gaps("use_of_force", {
        "persons": _one_inmate(),
        "force_type": "Chemical agent (OC/MK-3)",
        "decontamination": "the 8 Barracks shower",
        "charges": ["12-1"],
    })["auto_content"]}
    disciplinary = lines["disciplinary_action_line"]
    assert "against inmate Roe" in disciplinary
    assert "against Inmate Roe" not in disciplinary


# ── investigation report gate (STYLE_RULINGS.md ruling 8) ───────────────────
#
# The 5th report type exists only when an investigation actually happened.
# "A simple incident must not produce an empty investigation report."

def test_no_investigation_signal_means_no_report():
    for slots in ({}, {"investigation_findings": None},
                  {"investigation_findings": []}):
        assert investigation_occurred(slots) is False


def test_blank_and_unknown_findings_do_not_count_as_an_investigation():
    # UNKNOWN is the officer answering "I don't know" — not a finding.
    assert investigation_occurred({"investigation_findings": ["  ", ""]}) is False
    assert investigation_occurred({"investigation_findings": [UNKNOWN]}) is False


def test_real_findings_trigger_the_report():
    assert investigation_occurred(
        {"investigation_findings": ["Reviewed camera footage."]}) is True


def test_a_single_string_finding_is_accepted():
    # Defensive: the schema asks for an array, but a model that returns one
    # string must not silently suppress the report.
    assert investigation_occurred(
        {"investigation_findings": "Reviewed camera footage."}) is True


def test_find_gaps_exposes_the_investigation_flag():
    base = {"persons": _one_inmate()}
    assert find_gaps("inmate_fight", base)["investigation"] is False
    assert find_gaps("inmate_fight",
                     {**base, "investigation_findings": ["Took a statement."]}
                     )["investigation"] is True


def test_ordinary_incident_is_never_asked_investigation_questions():
    slots = {g["slot"] for g in find_gaps("inmate_fight", {"persons": _one_inmate()})["gaps"]}
    assert not [s for s in slots if s.startswith("investigation")]


def test_investigation_questions_appear_once_findings_exist():
    """An empty findings list is not null, so the rules must gate on the derived
    flag — testing `investigation_findings != null` would fire on every incident."""
    slots = {g["slot"] for g in find_gaps(
        "inmate_fight",
        {"persons": _one_inmate(),
         "investigation_findings": ["Reviewed camera footage."]})["gaps"]}
    assert {"investigation_start_time", "investigation_end_time",
            "investigation_disposition"} <= slots


def test_empty_findings_list_does_not_open_the_investigation_questions():
    slots = {g["slot"] for g in find_gaps(
        "inmate_fight",
        {"persons": _one_inmate(), "investigation_findings": []})["gaps"]}
    assert not [s for s in slots if s.startswith("investigation")]
