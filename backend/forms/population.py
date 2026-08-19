"""Populate incident forms from saved, reviewed facts without another model call."""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal


CompletenessState = Literal["ready", "needs_review", "missing_information"]


class FormPopulationConfigurationError(ValueError):
    """A catalog field cannot be resolved by the closed population policy."""


@dataclass(frozen=True)
class FormCompleteness:
    state: CompletenessState
    missing_fields: tuple[str, ...]
    review_fields: tuple[str, ...]


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _reviewed_fact(snapshot: Mapping[str, object], key: str):
    """Prefer reviewed officer answers over extracted model suggestions."""
    for container_name in ("gap_answers", "extracted_facts", "classification"):
        container = snapshot.get(container_name)
        if isinstance(container, Mapping) and key in container:
            return container[key]
    return snapshot.get(key)


def _canonical(snapshot: Mapping[str, object], key: str):
    return snapshot.get(key)


def _injury_summary(snapshot: Mapping[str, object]):
    parts: list[str] = []
    inmate = _reviewed_fact(snapshot, "inmate_injuries")
    officer = _reviewed_fact(snapshot, "officer_injuries")
    if _has_value(inmate):
        parts.append(f"Inmate injuries: {inmate}")
    if _has_value(officer):
        parts.append(f"Officer injuries: {officer}")
    return "; ".join(parts) if parts else None


def _treatment_location(snapshot: Mapping[str, object]):
    for key in ("treatment_location", "medical_treatment_location"):
        value = _reviewed_fact(snapshot, key)
        if _has_value(value):
            return value
    return None


def _attachment_summary(snapshot: Mapping[str, object]):
    for key in (
        "attachment_summary",
        "photo_video_description",
        "attachment_description",
    ):
        value = _reviewed_fact(snapshot, key)
        if _has_value(value):
            return value
    return None


def _incident_summary(snapshot: Mapping[str, object], narrative: str | None):
    value = _reviewed_fact(snapshot, "incident_summary")
    if _has_value(value):
        return value
    return narrative if _has_value(narrative) else None


_CANONICAL_FIELDS = frozenset({
    "incident_number",
    "incident_date",
    "incident_time",
    "location",
    "category",
})
_REVIEWED_FACT_FIELDS = frozenset({
    "supervisor_name",
    "medical_disposition",
    "inmates_involved",
    "employees_involved",
    "job_code",
    "section",
    "sequence_number",
    "prea_notification_made",
    "allegation_summary",
    "evidence_description",
    "recovery_location",
    "attachment_description",
    "field_test_result_summary",
    "drug_test_disposition",
    "money_amount",
    "money_receipt_number",
    "authorization",
    "orders_given",
    "company_nurse_confirmation_number",
    "officer_injuries",
})
_CONTEXT_FIELDS = frozenset({
    "reporting_officer",
    "narrative",
    "other_involved_officers",
})
_COMPUTED_FIELDS = frozenset({
    "injury_summary",
    "treatment_location",
    "attachment_summary",
    "incident_summary",
})
_SUPPORTED_FIELDS = (
    _CANONICAL_FIELDS | _REVIEWED_FACT_FIELDS | _CONTEXT_FIELDS | _COMPUTED_FIELDS
)


def resolve_form_fields(
    snapshot: Mapping[str, object],
    field_names: Iterable[str],
    *,
    reporting_officer: str | None = None,
    narrative: str | None = None,
    other_involved_officers: Iterable[str] = (),
) -> dict[str, object]:
    """Resolve a closed set of catalog fields from one saved incident snapshot."""
    if not isinstance(snapshot, Mapping):
        raise FormPopulationConfigurationError("incident snapshot must be an object")

    resolved: dict[str, object] = {}
    officers = tuple(
        value.strip()
        for value in other_involved_officers
        if isinstance(value, str) and value.strip()
    )
    for field_name in field_names:
        if field_name not in _SUPPORTED_FIELDS:
            raise FormPopulationConfigurationError(
                f"unsupported form field: {field_name}"
            )
        if field_name in _CANONICAL_FIELDS:
            value = _canonical(snapshot, field_name)
        elif field_name in _REVIEWED_FACT_FIELDS:
            value = _reviewed_fact(snapshot, field_name)
        elif field_name == "reporting_officer":
            value = reporting_officer
        elif field_name == "narrative":
            value = narrative
        elif field_name == "other_involved_officers":
            value = list(officers) if officers else None
        elif field_name == "injury_summary":
            value = _injury_summary(snapshot)
        elif field_name == "treatment_location":
            value = _treatment_location(snapshot)
        elif field_name == "attachment_summary":
            value = _attachment_summary(snapshot)
        else:
            value = _incident_summary(snapshot, narrative)
        resolved[field_name] = value
    return resolved


def calculate_form_completeness(
    *,
    required_fields: Iterable[str],
    review_fields: Iterable[str],
    populated_fields: Mapping[str, object],
    manual_fields: Mapping[str, object] | None = None,
) -> FormCompleteness:
    """Calculate form readiness after manual values override automatic values."""
    values = dict(populated_fields)
    if manual_fields:
        values.update(manual_fields)

    required = tuple(required_fields)
    review = tuple(review_fields)
    missing = tuple(field for field in required if not _has_value(values.get(field)))
    needs_review = tuple(field for field in review if _has_value(values.get(field)))
    if missing:
        state: CompletenessState = "missing_information"
    elif needs_review:
        state = "needs_review"
    else:
        state = "ready"
    return FormCompleteness(
        state=state,
        missing_fields=missing,
        review_fields=needs_review,
    )
