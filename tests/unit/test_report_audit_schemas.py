"""Tests for the report half of the validated audit catalog.

Audit rows outlive the report they describe and are exported to oversight, so
the catalog is an allowlist: an action may record stable identifiers, revision
numbers, counts, hashes and latency, and nothing that could carry a person's
name, an inmate identifier, or the text of a report.
"""

import pytest

from backend.identity.audit import AUDIT_ACTION_FIELDS, validate_details


REPORT_ACTIONS = {
    "incident.created",
    "incident.saved",
    "incident.restored",
    "incident.status_changed",
    "report.created",
    "report.viewed_by_admin",
    "report.saved",
    "report.restored",
    "report.recovery_created",
    "report.status_changed",
    "report.ownership_transferred",
    "report.exported",
    "report.exported_by_admin",
    "ai.job_submitted",
    "ai.job_succeeded",
    "ai.job_failed",
    "policy.question_answered",
    "admin.report_search",
    "admin.bulk_exported",
    "admin.audit_exported",
    "admin.health_viewed",
}

# One safe, fictional example per action. Every value here is a stable ID, a
# revision number, a bounded code, a count, a digest, or a latency.
SAFE_EXAMPLES = {
    "incident.created": {"incident_id": "11111111-1111-4111-8111-111111111111"},
    "incident.saved": {
        "incident_id": "11111111-1111-4111-8111-111111111111",
        "revision_number": 2,
        "changed_fields": ["field_notes"],
        "reason": "manual_save",
    },
    "incident.restored": {
        "incident_id": "11111111-1111-4111-8111-111111111111",
        "revision_number": 4,
        "source_revision_number": 2,
    },
    "incident.status_changed": {
        "incident_id": "11111111-1111-4111-8111-111111111111",
        "old_status": "in_progress",
        "new_status": "completed",
    },
    "report.created": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "incident_id": "11111111-1111-4111-8111-111111111111",
        "report_type": "first_person",
    },
    "report.viewed_by_admin": {"report_id": "22222222-2222-4222-8222-222222222222"},
    "report.saved": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "revision_number": 2,
        "changed_fields": ["narrative"],
        "reason": "manual_save",
    },
    "report.restored": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "revision_number": 5,
        "source_revision_number": 3,
    },
    "report.recovery_created": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "revision_number": 6,
        "source_revision_number": 4,
    },
    "report.status_changed": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "old_status": "in_progress",
        "new_status": "archived",
    },
    "report.ownership_transferred": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "old_owner_staff_id": "33333333-3333-4333-8333-333333333333",
        "new_owner_staff_id": "44444444-4444-4444-8444-444444444444",
    },
    "report.exported": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "export_id": "55555555-5555-4555-8555-555555555555",
        "export_format": "docx",
    },
    "report.exported_by_admin": {
        "report_id": "22222222-2222-4222-8222-222222222222",
        "export_id": "55555555-5555-4555-8555-555555555555",
        "export_format": "docx",
    },
    "ai.job_submitted": {
        "job_id": "66666666-6666-4666-8666-666666666666",
        "job_type": "generate",
        "incident_id": "11111111-1111-4111-8111-111111111111",
    },
    "ai.job_succeeded": {
        "job_id": "66666666-6666-4666-8666-666666666666",
        "job_type": "generate",
        "latency_ms": 1875,
    },
    "ai.job_failed": {
        "job_id": "66666666-6666-4666-8666-666666666666",
        "job_type": "generate",
        "result_code": "dependency_unavailable",
    },
    "policy.question_answered": {
        "question_sha256": "a" * 64,
        "document_count": 8,
        "latency_ms": 940,
    },
    "admin.report_search": {
        "filters": ["status", "incident_date_from"],
        "result_count": 12,
    },
    "admin.bulk_exported": {
        "export_id": "55555555-5555-4555-8555-555555555555",
        "report_count": 12,
    },
    "admin.audit_exported": {
        "export_id": "55555555-5555-4555-8555-555555555555",
        "event_count": 400,
    },
    "admin.health_viewed": {},
}

SENSITIVE_KEYS = {
    "field_notes": "Fictional field notes that must never be audited.",
    "narrative": "Fictional report narrative.",
    "report_text": "Fictional report text.",
    "question": "What is the PREA reporting deadline?",
    "answer": "Fictional policy answer text.",
    "staff_name": "Fictional Officer",
    "inmate_name": "Fictional Inmate",
    "inmate_adc_number": "111111",
    "employee_number": "100-411",
    "pin": "1234",
    "access_token": "fictional-token",
}


def test_catalog_contains_every_report_action_once():
    assert REPORT_ACTIONS <= set(AUDIT_ACTION_FIELDS)


def test_identity_actions_are_preserved():
    assert "auth.login_succeeded" in AUDIT_ACTION_FIELDS
    assert "admin.review_lab_handoff_issued" in AUDIT_ACTION_FIELDS


@pytest.mark.parametrize("action", sorted(REPORT_ACTIONS))
def test_safe_example_is_accepted(action):
    details = SAFE_EXAMPLES[action]

    assert validate_details(action, details) == details


@pytest.mark.parametrize("action", sorted(REPORT_ACTIONS))
def test_empty_details_are_accepted(action):
    assert validate_details(action, {}) == {}


@pytest.mark.parametrize("action", sorted(REPORT_ACTIONS))
@pytest.mark.parametrize("key", sorted(SENSITIVE_KEYS))
def test_sensitive_keys_are_rejected(action, key):
    details = dict(SAFE_EXAMPLES[action]) | {key: SENSITIVE_KEYS[key]}

    with pytest.raises(ValueError):
        validate_details(action, details)


@pytest.mark.parametrize("action", sorted(REPORT_ACTIONS))
def test_unknown_keys_are_rejected(action):
    details = dict(SAFE_EXAMPLES[action]) | {"unexpected": "value"}

    with pytest.raises(ValueError):
        validate_details(action, details)


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError):
        validate_details("report.invented", {})


def test_changed_field_names_must_be_stable_codes():
    with pytest.raises(ValueError):
        validate_details(
            "report.saved",
            {
                "report_id": "22222222-2222-4222-8222-222222222222",
                "changed_fields": ["Fictional Inmate was moved to segregation"],
            },
        )


def test_changed_field_names_are_bounded_in_number():
    with pytest.raises(ValueError):
        validate_details(
            "report.saved",
            {
                "changed_fields": [f"field_{index}" for index in range(101)],
            },
        )


def test_search_filter_names_must_be_stable_codes():
    with pytest.raises(ValueError):
        validate_details(
            "admin.report_search",
            {
                "filters": ["owner=Fictional Officer"],
                "result_count": 1,
            },
        )


@pytest.mark.parametrize(
    "key",
    [
        "incident_id",
        "report_id",
        "job_id",
        "export_id",
        "old_owner_staff_id",
        "new_owner_staff_id",
    ],
)
def test_stable_id_fields_require_uuid_values(key):
    action = next(action for action, fields in AUDIT_ACTION_FIELDS.items() if key in fields)

    with pytest.raises(ValueError):
        validate_details(action, {key: "Fictional Officer raw identity text"})


def test_sha256_fields_require_lowercase_hex_digest():
    with pytest.raises(ValueError):
        validate_details(
            "policy.question_answered",
            {
                "question_sha256": "Fictional policy question text",
            },
        )
    with pytest.raises(ValueError):
        validate_details(
            "policy.question_answered",
            {
                "question_sha256": "A" * 64,
            },
        )


@pytest.mark.parametrize("value", [-1, True, 1.5, "12", 1_000_000_001])
def test_count_latency_and_revision_fields_require_bounded_integers(value):
    with pytest.raises(ValueError):
        validate_details("ai.job_succeeded", {"latency_ms": value})


@pytest.mark.parametrize(
    "key,value",
    [
        ("reason", "Fictional report narrative"),
        ("reason", "admin_edit"),
        ("job_type", "invented_job"),
        ("export_format", "pdf"),
        ("new_status", "deleted"),
    ],
)
def test_code_and_enum_fields_reject_raw_or_unapproved_values(key, value):
    action = {
        "reason": "incident.saved",
        "job_type": "ai.job_submitted",
        "export_format": "report.exported",
        "new_status": "report.status_changed",
    }[key]

    with pytest.raises(ValueError):
        validate_details(action, {key: value})


@pytest.mark.parametrize(
    "action,key",
    [
        ("auth.login_failed", "reason"),
        ("auth.session_revoked", "reason"),
        ("auth.step_up_failed", "purpose"),
    ],
)
def test_identity_code_fields_reject_content_disguised_as_codes(action, key):
    with pytest.raises(ValueError):
        validate_details(action, {key: "fictional_officer_private_detail"})


def test_name_lists_reject_duplicates_and_unapproved_names():
    with pytest.raises(ValueError):
        validate_details(
            "report.saved",
            {
                "changed_fields": ["narrative", "narrative"],
            },
        )
    with pytest.raises(ValueError):
        validate_details(
            "report.saved",
            {
                "changed_fields": ["fictional_inmate_confession"],
            },
        )
    with pytest.raises(ValueError):
        validate_details(
            "admin.report_search",
            {
                "filters": ["fictional_employee_name"],
            },
        )

    with pytest.raises(ValueError):
        validate_details(
            "report.saved",
            {
                "changed_fields": [{"narrative": "Fictional raw text"}],
            },
        )


def test_oversized_details_are_rejected():
    # Every name here is a valid stable code, so only the total size can reject
    # it — the size rule and the name rule are tested apart from each other.
    with pytest.raises(ValueError):
        validate_details(
            "report.saved",
            {
                "changed_fields": [f"{'f' * 58}_{index:03d}" for index in range(100)],
            },
        )
