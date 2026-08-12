import json
from pathlib import Path

import pytest

from backend.identity.roster_import import import_roster, roster_checksum


class EmptySession:
    def scalars(self, _statement):
        return self

    def all(self):
        return []

    def add_all(self, _rows):
        raise AssertionError("dry-run attempted a database write")

    def flush(self):
        raise AssertionError("dry-run attempted a flush")


FICTIONAL_RECORDS = [
    {
        "rank": "Officer",
        "first": "Avery",
        "last": "Morgan",
        "employee_number": " emp-001 ",
        "shift": "A",
    }
]


def test_roster_checksum_is_stable_for_key_order():
    reordered = [{key: FICTIONAL_RECORDS[0][key] for key in reversed(FICTIONAL_RECORDS[0])}]
    assert roster_checksum(FICTIONAL_RECORDS) == roster_checksum(reordered)
    assert len(roster_checksum(FICTIONAL_RECORDS)) == 64


def test_dry_run_validates_and_never_writes():
    summary = import_roster(EmptySession(), FICTIONAL_RECORDS, apply=False)
    assert summary.source_count == 1
    assert summary.inserted_count == 1
    assert summary.existing_count == 0
    assert summary.applied is False


def test_duplicate_normalized_employee_number_is_rejected_before_query():
    duplicate = [FICTIONAL_RECORDS[0], {**FICTIONAL_RECORDS[0], "employee_number": "EMP-001"}]
    with pytest.raises(ValueError, match="duplicate employee number"):
        import_roster(EmptySession(), duplicate, apply=False)


def test_unknown_or_missing_roster_fields_are_rejected():
    with pytest.raises(ValueError, match="roster record fields are invalid"):
        import_roster(EmptySession(), [{**FICTIONAL_RECORDS[0], "unexpected": "x"}], apply=False)


def test_empty_rank_is_allowed_when_field_is_present():
    summary = import_roster(EmptySession(), [{**FICTIONAL_RECORDS[0], "rank": ""}], apply=False)
    assert summary.source_count == 1


def test_checked_in_fictional_roster_has_expected_dry_run_count():
    payload = json.loads(Path("templates/staff_roster.json").read_text(encoding="utf-8"))
    summary = import_roster(EmptySession(), payload["staff"], apply=False)
    assert (summary.source_count, summary.inserted_count, summary.existing_count) == (13, 13, 0)
    assert summary.applied is False
