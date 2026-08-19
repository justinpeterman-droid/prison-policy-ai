from math import inf, nan

import pytest

from backend.paperwork.service import (
    OperationalPaperworkValidationError,
    SUPPORTED_PAPERWORK_TYPES,
    validate_paperwork_content,
)
from backend.persistence.models.paperwork import (
    OperationalPaperwork,
    OperationalPaperworkRevision,
)


def test_initial_paperwork_type_is_ncu_days_count():
    assert SUPPORTED_PAPERWORK_TYPES == {"ncu_days_count"}


def test_content_is_detached_and_json_canonical():
    source = {
        "rows": [{"label": "Fictional Housing A", "count": 12}],
        "reconciliation": {"expected": 12, "actual": 12},
    }

    validated = validate_paperwork_content(source)
    source["rows"][0]["count"] = 99

    assert validated["rows"][0]["count"] == 12


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_content_rejects_non_finite_numbers(value):
    with pytest.raises(OperationalPaperworkValidationError, match="non-finite"):
        validate_paperwork_content({"count": value})


def test_content_rejects_nested_credentials():
    with pytest.raises(OperationalPaperworkValidationError, match="Credential"):
        validate_paperwork_content({
            "officer": {
                "display_name": "Fictional Officer",
                "access_token": "must-not-be-stored",
            }
        })


def test_content_rejects_excessive_depth():
    value = {}
    current = value
    for index in range(12):
        current["child"] = {}
        current = current["child"]
        current["index"] = index

    with pytest.raises(OperationalPaperworkValidationError, match="complex"):
        validate_paperwork_content(value)


def test_models_use_immutable_revision_tables():
    assert OperationalPaperwork.__tablename__ == "operational_paperwork"
    assert (
        OperationalPaperworkRevision.__tablename__
        == "operational_paperwork_revisions"
    )
    columns = OperationalPaperwork.__table__.columns
    assert columns.current_revision_number.nullable is False
    assert columns.current_content.nullable is False
    revision_columns = OperationalPaperworkRevision.__table__.columns
    assert revision_columns.snapshot.nullable is False
    assert revision_columns.request_id.nullable is False
    assert revision_columns.client_version.nullable is False
