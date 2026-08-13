"""Versioned, server-owned schema for report review submissions."""

from datetime import datetime, timezone
import re

import pytest

from backend.pipeline.config import FAST_MODEL, MODEL_LOCATION, PRO_MODEL
from backend.reports.demo_scenarios import get_demo_scenario
from backend.reports.review_schema import (
    ReviewValidationError,
    build_review_submission,
    review_summary,
)


FIXED_NOW = datetime(2026, 8, 11, 1, 2, 3, tzinfo=timezone.utc)


def valid_payload(**overrides):
    payload = {
        "scenario_id": "inmate_fight_dayroom",
        "notes": "browser-supplied notes must be ignored",
        "pipeline": {
            "classification": {"incident_type": "inmate_fight"},
            "extraction": {"slots": {"location": "8 Barracks"}},
            "initial_gaps": {"gaps": []},
            "gap_answers": {},
            "generation_response": {"style": {"score": 1.0}},
        },
        "reports": [
            {
                "report_type": "first_person",
                "reporter_id": "EMP 100-411",
                "generated_text": "generated",
                "edited_text": "edited",
            }
        ],
        "reviewed_fields": {"location": "8 Barracks"},
        "review": {"score": 4, "comments": "Tighten the opening sentence."},
        "metadata": {"generation_model": "attacker-model"},
    }
    payload.update(overrides)
    return payload


def test_server_owns_canonical_scenario_identity_and_notes():
    record = build_review_submission(
        valid_payload(), now=FIXED_NOW, id_factory=lambda: "abc123"
    )
    canonical = get_demo_scenario("inmate_fight_dayroom")

    assert record["submission_id"] == "review_20260811T010203Z_abc123"
    assert record["submitted_at"] == "2026-08-11T01:02:03Z"
    assert record["scenario"] == {
        "scenario_id": canonical["id"],
        "category": canonical["category"],
        "label": canonical["label"],
        "notes": canonical["notes"],
    }


def test_server_owns_model_revision_and_prompt_metadata(monkeypatch):
    monkeypatch.setenv("K_REVISION", "revision-151")
    monkeypatch.setenv("SOURCE_COMMIT", "deadbeef")

    record = build_review_submission(valid_payload(), now=FIXED_NOW)
    metadata = record["metadata"]

    assert metadata["classification_model"] == FAST_MODEL
    assert metadata["extraction_model"] == FAST_MODEL
    assert metadata["generation_model"] == PRO_MODEL
    assert metadata["model_location"] == MODEL_LOCATION
    assert metadata["cloud_run_revision"] == "revision-151"
    assert metadata["source_commit"] == "deadbeef"
    assert set(metadata["prompt_fingerprints"]) == {
        "classification",
        "generation",
        "checklist",
        "charges",
    }
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", value)
        for value in metadata["prompt_fingerprints"].values()
    )


def test_report_ids_are_stable_and_both_versions_are_retained():
    report = build_review_submission(valid_payload(), now=FIXED_NOW)["reports"][0]

    assert report == {
        "report_id": "inmate_fight_dayroom:first_person:emp-100-411",
        "report_type": "first_person",
        "reporter_id": "emp-100-411",
        "generated_text": "generated",
        "edited_text": "edited",
        "changed": True,
    }


def test_review_summary_contains_only_history_list_fields():
    record = build_review_submission(
        valid_payload(), now=FIXED_NOW, id_factory=lambda: "abc123"
    )

    assert review_summary(record) == {
        "submission_id": "review_20260811T010203Z_abc123",
        "submitted_at": "2026-08-11T01:02:03Z",
        "scenario_id": "inmate_fight_dayroom",
        "scenario_label": "Inmate on inmate fight",
        "score": 4,
        "report_count": 1,
        "changed_count": 1,
    }


@pytest.mark.parametrize("score", [0, 6, "five", True])
def test_score_must_be_an_integer_from_one_to_five(score):
    payload = valid_payload(review={"score": score, "comments": ""})

    with pytest.raises(ReviewValidationError, match="score"):
        build_review_submission(payload)


@pytest.mark.parametrize("scenario_id", ["", "not-a-demo", "../roster"])
def test_unknown_scenarios_are_rejected(scenario_id):
    with pytest.raises(ReviewValidationError, match="scenario"):
        build_review_submission(valid_payload(scenario_id=scenario_id))


def test_unknown_report_types_are_rejected():
    payload = valid_payload(
        reports=[
            {
                "report_type": "raw_prompt",
                "reporter_id": None,
                "generated_text": "a",
                "edited_text": "b",
            }
        ]
    )

    with pytest.raises(ReviewValidationError, match="report type"):
        build_review_submission(payload)


def test_at_least_one_generated_report_is_required():
    with pytest.raises(ReviewValidationError, match="report"):
        build_review_submission(valid_payload(reports=[]))


def test_comments_and_report_text_are_bounded():
    with pytest.raises(ReviewValidationError, match="comments"):
        build_review_submission(
            valid_payload(review={"score": 3, "comments": "x" * 5001})
        )

    oversized = valid_payload()["reports"][0] | {"edited_text": "x" * 30001}
    with pytest.raises(ReviewValidationError, match="report text"):
        build_review_submission(valid_payload(reports=[oversized]))
