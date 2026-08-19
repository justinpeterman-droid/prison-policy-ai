from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.paperwork.models import PaperworkKind
from backend.paperwork.policy import can_edit_paperwork, can_read_paperwork
from backend.paperwork.schemas import (
    SavePaperworkRequest,
    changed_field_paths,
)


def _actor(*, role="user", staff_id=None):
    return SimpleNamespace(
        account_id=uuid4(),
        staff_member_id=staff_id or uuid4(),
        session_id=uuid4(),
        role=role,
    )


def test_paperwork_kind_is_closed_to_approved_operational_forms():
    assert {kind.value for kind in PaperworkKind} == {
        "count_sheet",
        "assignment_roster",
        "uniform_inspection",
        "metal_detector_test",
        "perimeter_check",
        "random_search_log",
        "detector_sign_out",
    }


def test_creator_and_admin_can_read_and_edit_but_unrelated_officer_cannot():
    creator_id = uuid4()
    record = SimpleNamespace(created_by_staff_member_id=creator_id)
    creator = _actor(staff_id=creator_id)
    unrelated = _actor()
    admin = _actor(role="admin")

    assert can_read_paperwork(creator, record) is True
    assert can_edit_paperwork(creator, record) is True
    assert can_read_paperwork(admin, record) is True
    assert can_edit_paperwork(admin, record) is True
    assert can_read_paperwork(unrelated, record) is False
    assert can_edit_paperwork(unrelated, record) is False


def test_save_request_is_strict_bounded_and_normalizes_shift():
    request = SavePaperworkRequest.model_validate({
        "schema_version": 1,
        "work_date": date(2026, 8, 19),
        "shift": "  A   Shift  ",
        "payload": {"cells": {}, "note": "Fictional"},
        "base_revision_number": None,
        "reason": "manual_save",
    })

    assert request.shift == "A Shift"
    assert request.payload == {"cells": {}, "note": "Fictional"}

    with pytest.raises(ValidationError):
        SavePaperworkRequest.model_validate({
            **request.model_dump(mode="python"),
            "unexpected": True,
        })
    with pytest.raises(ValidationError):
        SavePaperworkRequest.model_validate({
            **request.model_dump(mode="python"),
            "reason": "restored",
        })
    with pytest.raises(ValidationError):
        SavePaperworkRequest.model_validate({
            **request.model_dump(mode="python"),
            "base_revision_number": 0,
        })


def test_changed_field_paths_name_structure_not_values():
    previous = {
        "schema_version": 1,
        "kind": "count_sheet",
        "work_date": "2026-08-19",
        "shift": "A",
        "payload": {
            "cells": {"Fictional Area": {"1": 4}},
            "operational": {"on_site": 4},
        },
    }
    current = {
        **previous,
        "shift": "B",
        "payload": {
            "cells": {"Fictional Area": {"1": 7}},
            "operational": {"on_site": 7},
        },
    }

    paths = changed_field_paths(previous, current)

    assert paths == ("payload.cells", "payload.operational", "shift")
    serialized = repr(paths)
    assert "Fictional Area" not in serialized
    assert "4" not in serialized
    assert "7" not in serialized
