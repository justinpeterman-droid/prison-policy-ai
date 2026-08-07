"""Validation for templates/demo_notes.json — the canned field notes behind
the /reports 'Try a demo' CTA.

These are pure data checks, no GCP needed. The point is to catch the two ways
demo notes rot: an officer name that isn't on the roster (which turns a
showcase run into a spurious gap panel), and the deliberate-gap scenario
quietly becoming complete.
"""
import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent.parent
DEMO_PATH = _ROOT / "templates" / "demo_notes.json"
ROSTER_PATH = _ROOT / "templates" / "staff_roster.json"
CHECKLIST_PATH = _ROOT / "templates" / "incident_checklist_v2.json"

# Categories come from the checklist, which CLAUDE.md names as authoritative.
# Reading it here (rather than importing classifier.VALID_CATEGORIES) keeps this
# module runnable without the Vertex SDK — see the cross-check test below.
VALID_CATEGORIES = {
    c["name"] for c in
    json.loads(CHECKLIST_PATH.read_text(encoding="utf-8"))["categories"]
}

try:
    from backend.reports import classifier
except ImportError:  # pragma: no cover - environment-dependent
    classifier = None


@pytest.fixture(scope="module")
def scenarios():
    return json.loads(DEMO_PATH.read_text(encoding="utf-8"))["scenarios"]


@pytest.fixture(scope="module")
def roster_last_names():
    staff = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["staff"]
    return {s["last"].lower() for s in staff}


def test_there_are_three_scenarios(scenarios):
    assert len(scenarios) == 3


def test_ids_are_unique(scenarios):
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids))


def test_every_scenario_has_the_required_fields(scenarios):
    for s in scenarios:
        for key in ("id", "category", "label", "teaches", "expect_gap", "notes"):
            assert key in s, f"{s.get('id', '?')} is missing {key!r}"
        assert s["notes"].strip(), f"{s['id']} has empty notes"


def test_categories_are_real_categories(scenarios):
    for s in scenarios:
        assert s["category"] in VALID_CATEGORIES, (
            f"{s['id']} uses category {s['category']!r}, which is not one of the "
            f"nine in VALID_CATEGORIES"
        )


@pytest.mark.skipif(classifier is None, reason="google-genai not importable")
def test_checklist_and_classifier_agree_on_the_category_list():
    """Guards the nine-places-hardcoded rule from the angle this file cares
    about: if the two lists drift, the category check above is testing nothing."""
    assert VALID_CATEGORIES == set(classifier.VALID_CATEGORIES)


def test_the_three_scenarios_cover_distinct_categories(scenarios):
    cats = [s["category"] for s in scenarios]
    assert len(set(cats)) == 3, f"demo scenarios should not repeat a category: {cats}"


# "Sgt Halvorsen", "Cpl. Alvarez", "Capt Lindholm" — rank followed by a surname.
_RANKED_NAME = re.compile(
    r"\b(?:Sgt|Cpl|Lt|Capt|Cpt|Maj|Col|Ofc)\.?\s+([A-Z][a-z]+)\b"
)


def test_every_officer_named_in_the_notes_is_on_the_roster(scenarios, roster_last_names):
    """A demo officer who isn't on the roster produces a gap panel, which
    defeats the purpose of a showcase run."""
    for s in scenarios:
        for surname in _RANKED_NAME.findall(s["notes"]):
            assert surname.lower() in roster_last_names, (
                f"{s['id']} names officer {surname!r}, who is not in "
                f"staff_roster.json — the demo would open on a gap panel"
            )


def test_exactly_one_scenario_expects_a_gap(scenarios):
    gapped = [s["id"] for s in scenarios if s["expect_gap"]]
    assert gapped == ["use_of_force_oc"], (
        "the OC scenario is the anti-fabrication demo — it must be the one "
        f"and only scenario withholding a required fact (got {gapped})"
    )


def test_the_gap_scenario_still_withholds_the_canister_details(scenarios):
    """The OC demo works only while the notes establish chemical-agent force
    without the MFG year / lot number / serial the checklist marks blocking.
    If someone 'helpfully' adds them, the refusal disappears."""
    oc = next(s for s in scenarios if s["id"] == "use_of_force_oc")
    notes = oc["notes"].lower()
    assert "oc" in notes, "the scenario must establish a chemical agent was used"
    for leaked in ("lot", "mfg", "serial", "pmf"):
        assert leaked not in notes, (
            f"{oc['id']} now mentions {leaked!r} — the blocking gap this demo "
            f"exists to show will no longer fire"
        )


def test_the_reports_placeholder_is_not_a_copy_of_a_scenario(scenarios):
    """Regression: the placeholder used to duplicate the demo string by hand,
    so the two silently drifted apart."""
    html = (_ROOT / "backend" / "webapp" / "templates" / "reports.html").read_text(
        encoding="utf-8")
    match = re.search(r'<textarea id="notes"[^>]*placeholder="([^"]*)"', html)
    assert match, "could not find the field-notes textarea placeholder"
    placeholder = match.group(1)
    for s in scenarios:
        assert placeholder.strip() != s["notes"].strip()


def test_no_scenario_reuses_a_staff_surname_for_an_inmate(scenarios, roster_last_names):
    """Inmates are written 'Surname ADC#nnnnnn'. Overlapping an inmate surname
    with a roster officer is exactly the collision name_fixer.py was written to
    survive — don't ship it as a demo."""
    for s in scenarios:
        for surname in re.findall(r"\b([A-Z][a-z]+)\s+ADC#", s["notes"]):
            assert surname.lower() not in roster_last_names, (
                f"{s['id']} uses {surname!r} as both an inmate and a roster officer"
            )
