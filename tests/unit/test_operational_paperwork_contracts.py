from datetime import date

import pytest
from pydantic import ValidationError

from backend.paperwork.contracts import (
    PAPERWORK_TYPES,
    OperationalPaperworkContentV1,
    PaperworkIdentity,
    SaveOperationalPaperworkRequest,
    changed_field_names,
)


def test_supported_paperwork_types_cover_count_and_daily_operations():
    assert PAPERWORK_TYPES == frozenset({
        "ncu_days_count",
        "assignment_roster",
        "uniform_inspection",
        "walkthrough_metal_detector_test",
        "perimeter_check",
        "random_searches",
        "handheld_metal_detector_signout",
    })


def test_identity_normalizes_shift_and_record_key_without_inventing_values():
    identity = PaperworkIdentity(
        paperwork_type="ncu_days_count",
        record_date=date(2026, 8, 19),
        shift="  A   Shift ",
        record_key="  primary  ",
    )

    assert identity.model_dump(mode="json") == {
        "paperwork_type": "ncu_days_count",
        "record_date": "2026-08-19",
        "shift": "A Shift",
        "record_key": "primary",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {
            "paperwork_type": "invented_form",
            "record_date": date(2026, 8, 19),
            "shift": "A",
            "record_key": "primary",
        },
        {
            "paperwork_type": "ncu_days_count",
            "record_date": date(2026, 8, 19),
            "shift": "",
            "record_key": "primary",
        },
        {
            "paperwork_type": "ncu_days_count",
            "record_date": date(2026, 8, 19),
            "shift": "A",
            "record_key": "../unsafe",
        },
    ],
)
def test_identity_rejects_unknown_or_unsafe_record_identity(payload):
    with pytest.raises(ValidationError):
        PaperworkIdentity.model_validate(payload)


def test_content_is_closed_bounded_and_rejects_server_owned_keys():
    content = OperationalPaperworkContentV1(
        fields={
            "housing_total": 42,
            "out_of_housing_total": 3,
            "reconciliation_note": "Fictional training value.",
        },
    )
    assert content.schema_version == 1
    assert content.fields["housing_total"] == 42

    with pytest.raises(ValidationError):
        OperationalPaperworkContentV1(
            fields={"actor_account_id": "00000000-0000-4000-8000-000000000001"}
        )

    with pytest.raises(ValidationError):
        OperationalPaperworkContentV1(
            fields={f"field_{index}": index for index in range(201)}
        )

    with pytest.raises(ValidationError):
        OperationalPaperworkContentV1(
            fields={"notes": "x" * 30_001}
        )


def test_save_request_is_strict_and_revision_aware():
    request = SaveOperationalPaperworkRequest(
        content=OperationalPaperworkContentV1(fields={"count": 12}),
        base_revision_number=4,
        reason="autosave",
    )
    assert request.base_revision_number == 4
    assert request.reason == "autosave"

    with pytest.raises(ValidationError):
        SaveOperationalPaperworkRequest.model_validate({
            "content": {"schema_version": 1, "fields": {"count": 12}},
            "base_revision_number": 4,
            "reason": "autosave",
            "status": "complete",
        })


def test_changed_field_names_records_only_field_names_not_values():
    previous = {
        "schema_version": 1,
        "fields": {"housing_total": 40, "note": "Old private content"},
    }
    current = {
        "schema_version": 1,
        "fields": {"housing_total": 41, "note": "New private content"},
    }

    assert changed_field_names(previous, current) == ["fields"]
    assert "Old private content" not in repr(changed_field_names(previous, current))
    assert "New private content" not in repr(changed_field_names(previous, current))
