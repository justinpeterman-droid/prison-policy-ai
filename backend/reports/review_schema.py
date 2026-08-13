"""Validation and normalization for persisted demo review submissions."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import re
from collections.abc import Callable
from uuid import uuid4

from backend.pipeline.config import (
    FAST_MODEL,
    MODEL_LOCATION,
    PROJECT_ID,
    PRO_MODEL,
)
from backend.reports.demo_scenarios import get_demo_scenario
from backend.reports.provenance import source_fingerprints


#: The subset of shared provenance sources Review Lab records. The digests come
#: from `backend.reports.provenance` so a Review Lab submission and a stored
#: report describe the same prompt files the same way.
REVIEW_FINGERPRINT_SOURCES = ("classification", "generation", "checklist", "charges")
REPORT_TYPES = {
    "first_person",
    "supervisor_summary",
    "cover_letter",
    "disciplinary",
    "investigation",
}
PIPELINE_FIELDS = {
    "classification",
    "extraction",
    "initial_gaps",
    "gap_answers",
    "generation_response",
}
MAX_COMMENTS = 5_000
MAX_REPORT_TEXT = 30_000
MAX_REPORTS = 25
MAX_REVIEWED_FIELDS = 100
MAX_FIELD_VALUE = 5_000
MAX_PIPELINE_JSON = 750_000


class ReviewValidationError(ValueError):
    """The browser supplied an invalid review payload."""


def _utc(value: datetime | None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_z(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _text(value, label: str, max_len: int, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ReviewValidationError(f"{label} must be text")
    value = value.strip()
    if required and not value:
        raise ReviewValidationError(f"{label} is required")
    if len(value) > max_len:
        raise ReviewValidationError(f"{label} is too long")
    return value


def _reporter_id(value) -> str:
    if value in (None, ""):
        return "primary"
    raw = _text(value, "reporter id", 120).lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-_")
    return normalized or "primary"


def _pipeline(value) -> dict:
    if not isinstance(value, dict):
        raise ReviewValidationError("pipeline must be an object")
    copied = {key: deepcopy(value.get(key, {})) for key in PIPELINE_FIELDS}
    try:
        encoded = json.dumps(copied, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ReviewValidationError("pipeline must contain JSON values") from exc
    if len(encoded.encode("utf-8")) > MAX_PIPELINE_JSON:
        raise ReviewValidationError("pipeline data is too large")
    return copied


def _reports(value, scenario_id: str) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise ReviewValidationError("at least one report is required")
    if len(value) > MAX_REPORTS:
        raise ReviewValidationError("too many reports")
    normalized = []
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            raise ReviewValidationError("each report must be an object")
        report_type = item.get("report_type")
        if report_type not in REPORT_TYPES:
            raise ReviewValidationError("unknown report type")
        reporter_id = _reporter_id(item.get("reporter_id"))
        report_id = f"{scenario_id}:{report_type}:{reporter_id}"
        if report_id in seen:
            raise ReviewValidationError("duplicate report id")
        seen.add(report_id)
        generated = _text(item.get("generated_text"), "report text", MAX_REPORT_TEXT)
        edited = _text(item.get("edited_text"), "report text", MAX_REPORT_TEXT)
        normalized.append(
            {
                "report_id": report_id,
                "report_type": report_type,
                "reporter_id": reporter_id,
                "generated_text": generated,
                "edited_text": edited,
                "changed": generated != edited,
            }
        )
    return normalized


def _reviewed_fields(value) -> dict:
    if value in (None, {}):
        return {}
    if not isinstance(value, dict) or len(value) > MAX_REVIEWED_FIELDS:
        raise ReviewValidationError("reviewed fields are invalid")
    result = {}
    for key, raw in value.items():
        clean_key = _text(key, "reviewed field name", 120, required=True)
        result[clean_key] = _text(raw, "reviewed field value", MAX_FIELD_VALUE)
    return result


def _prompt_fingerprints() -> dict[str, str]:
    return source_fingerprints(REVIEW_FINGERPRINT_SOURCES)


def build_review_submission(
    payload: dict,
    *,
    now: datetime | None = None,
    id_factory: Callable[[], str] | None = None,
) -> dict:
    if not isinstance(payload, dict):
        raise ReviewValidationError("review payload must be an object")
    scenario = get_demo_scenario(payload.get("scenario_id", ""))
    if scenario is None:
        raise ReviewValidationError("unknown review scenario")

    review = payload.get("review")
    if not isinstance(review, dict):
        raise ReviewValidationError("review must be an object")
    score = review.get("score")
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
        raise ReviewValidationError("review score must be an integer from 1 to 5")
    comments = _text(review.get("comments", ""), "review comments", MAX_COMMENTS)

    submitted = _utc(now)
    suffix_factory = id_factory or (lambda: uuid4().hex[:12])
    suffix = re.sub(r"[^a-zA-Z0-9_-]", "", str(suffix_factory()))[:64]
    if len(suffix) < 6:
        raise ReviewValidationError("submission id suffix is invalid")
    submission_id = f"review_{submitted.strftime('%Y%m%dT%H%M%SZ')}_{suffix}"
    reports = _reports(payload.get("reports"), scenario["id"])

    return {
        "schema_version": 1,
        "submission_id": submission_id,
        "submitted_at": _iso_z(submitted),
        "scenario": {
            "scenario_id": scenario["id"],
            "category": scenario["category"],
            "label": scenario["label"],
            "notes": scenario["notes"],
        },
        "pipeline": _pipeline(payload.get("pipeline")),
        "reports": reports,
        "reviewed_fields": _reviewed_fields(payload.get("reviewed_fields")),
        "review": {"score": score, "comments": comments},
        "metadata": {
            "vertex_project": PROJECT_ID,
            "model_location": MODEL_LOCATION,
            "classification_model": FAST_MODEL,
            "extraction_model": FAST_MODEL,
            "generation_model": PRO_MODEL,
            "cloud_run_revision": os.getenv("K_REVISION") or None,
            "source_commit": os.getenv("SOURCE_COMMIT") or None,
            "prompt_fingerprints": _prompt_fingerprints(),
            "step_timings_ms": deepcopy(payload.get("step_timings_ms") or {}),
        },
    }


def review_summary(record: dict) -> dict:
    reports = record.get("reports") or []
    scenario = record.get("scenario") or {}
    review = record.get("review") or {}
    return {
        "submission_id": record.get("submission_id"),
        "submitted_at": record.get("submitted_at"),
        "scenario_id": scenario.get("scenario_id"),
        "scenario_label": scenario.get("label"),
        "score": review.get("score"),
        "report_count": len(reports),
        "changed_count": sum(1 for item in reports if item.get("changed")),
    }
