"""Shared canonical demo catalog and deterministic review-answer behavior."""

from backend.reports.demo_scenarios import (
    get_demo_scenario,
    load_demo_scenarios,
)
from backend.reports.gap_answers import merge_gap_answers
from backend.reports.validate import find_gaps


def test_catalog_returns_copies_that_cannot_mutate_cached_demo_data():
    scenarios = load_demo_scenarios()
    scenarios[0]["notes"] = "changed by caller"

    fresh = load_demo_scenarios()

    assert fresh[0]["notes"] != "changed by caller"


def test_lookup_returns_none_for_an_unknown_demo():
    assert get_demo_scenario("not-a-demo") is None


def test_oc_review_answer_stays_separate_and_closes_the_chemical_gap():
    scenario = get_demo_scenario("use_of_force_oc")
    notes = scenario["notes"].lower()
    assert all(word not in notes for word in ("lot", "mfg", "serial", "pmf"))

    slots = {
        "force_type": "Chemical agent (OC/MK-3)",
        "chemical_agent": None,
        "decontamination": "Cool water and fresh air",
    }
    before = find_gaps("use_of_force", slots)
    assert any(g["slot"] == "chemical_agent" and g["blocking"]
               for g in before["gaps"])

    merged = merge_gap_answers(slots, scenario["review_answers"])
    after = find_gaps("use_of_force", merged)

    assert merged["chemical_agent"] == scenario["review_answers"]["chemical_agent"]
    assert slots["chemical_agent"] is None
    assert not any(g["slot"] == "chemical_agent" for g in after["gaps"])
