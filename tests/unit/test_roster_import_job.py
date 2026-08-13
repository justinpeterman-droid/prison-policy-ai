import hashlib
import json

from backend.jobs.roster_import import build_roster_plan


def test_roster_plan_rejects_duplicate_normalized_employee_numbers_and_invalid_shift():
    rows = [
        {"employee_number": "FX-100", "first_name": "Avery", "last_name": "North", "rank": "Officer", "shift": "A"},
        {"employee_number": "fx-100", "first_name": "Avery", "last_name": "North", "rank": "Officer", "shift": "Z"},
    ]
    plan = build_roster_plan(rows, corrections={})
    assert not plan.ready
    assert {finding.code for finding in plan.findings} == {"duplicate_employee_number", "invalid_shift"}
    assert plan.inserts == ()


def test_roster_plan_is_hash_bound():
    rows = [{"employee_number": "FX-200", "first_name": "Jordan", "last_name": "West", "rank": "Sergeant", "shift": "D"}]
    plan = build_roster_plan(rows, corrections={}, expected_sha256="0" * 64)
    assert not plan.ready
    assert [finding.code for finding in plan.findings] == ["source_hash_mismatch"]


def test_roster_plan_accepts_a_matching_canonical_hash():
    rows = [{"employee_number": "FX-200", "first_name": "Jordan", "last_name": "West", "rank": "Sergeant", "shift": "D"}]
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    plan = build_roster_plan(rows, corrections={}, expected_sha256=digest)
    assert plan.ready
    assert plan.source_sha256 == digest
