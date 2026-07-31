"""Unit tests for the deterministic gap/validation engine (no AI, no GCP).

These lock in the anti-fabrication contract: a null slot must raise a gap
question rather than being silently filled, and UNKNOWN answers must surface
as [TO BE SUPPLEMENTED] markers instead of gaps.
"""
import pytest

from backend.reports.validate import find_gaps, load_checklist, UNKNOWN


CATEGORIES = [
    "contraband", "inmate_fight", "staff_assault", "forced_cell_movement",
    "prea", "incident_no_disciplinary", "other_rule_violation",
]


def test_load_checklist_is_cached():
    # lru_cache should hand back the very same object each call.
    assert load_checklist() is load_checklist()


def test_checklist_has_seven_categories():
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
