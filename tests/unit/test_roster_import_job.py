import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.jobs.roster_import import apply_roster_plan, build_roster_plan
from backend.jobs.roster_import import GooglePrivateObjectStore, main as roster_main


def test_roster_plan_rejects_duplicate_normalized_employee_numbers_and_invalid_shift():
    rows = [
        {
            "employee_number": "FX-100",
            "first_name": "Avery",
            "last_name": "North",
            "rank": "Officer",
            "shift": "A",
        },
        {
            "employee_number": "fx-100",
            "first_name": "Avery",
            "last_name": "North",
            "rank": "Officer",
            "shift": "Z",
        },
    ]
    plan = build_roster_plan(rows, corrections={})
    assert not plan.ready
    assert {finding.code for finding in plan.findings} == {
        "duplicate_employee_number",
        "invalid_shift",
    }
    assert plan.inserts == ()


def test_roster_plan_classifies_missing_shift_only_as_invalid_shift():
    rows = [
        {
            "employee_number": "FX-101",
            "first_name": "Morgan",
            "last_name": "Lake",
            "rank": "Officer",
            "shift": "",
        }
    ]

    plan = build_roster_plan(rows, corrections={})

    assert [finding.code for finding in plan.findings] == ["invalid_shift"]
    assert plan.inserts == ()


def test_roster_plan_is_hash_bound():
    rows = [
        {
            "employee_number": "FX-200",
            "first_name": "Jordan",
            "last_name": "West",
            "rank": "Sergeant",
            "shift": "D",
        }
    ]
    plan = build_roster_plan(rows, corrections={}, expected_sha256="0" * 64)
    assert not plan.ready
    assert [finding.code for finding in plan.findings] == ["source_hash_mismatch"]


def test_roster_plan_reports_hash_mismatch_alongside_an_invalid_source_schema():
    """A tampered source that is also malformed must still surface the tamper."""
    plan = build_roster_plan(
        {"staff": []},  # not a list -> invalid_source_schema early return
        corrections={},
        expected_sha256="0" * 64,
        source_bytes=b"{}",
    )

    assert not plan.ready
    assert [finding.code for finding in plan.findings] == [
        "source_hash_mismatch",
        "invalid_source_schema",
    ]
    assert plan.inserts == ()
    assert plan.updates == ()


def test_roster_plan_accepts_a_matching_canonical_hash():
    rows = [
        {
            "employee_number": "FX-200",
            "first_name": "Jordan",
            "last_name": "West",
            "rank": "Sergeant",
            "shift": "D",
        }
    ]
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    plan = build_roster_plan(rows, corrections={}, expected_sha256=digest)
    assert plan.ready
    assert plan.source_sha256 == digest


def test_roster_hash_is_over_exact_approved_source_bytes():
    rows = [
        {
            "employee_number": "FX-200",
            "first_name": "Jordan",
            "last_name": "West",
            "rank": "Sergeant",
            "shift": "D",
        }
    ]
    exact_bytes = b'{"staff": [ {"employee_number":"FX-200"} ]}\n'
    digest = hashlib.sha256(exact_bytes).hexdigest()
    plan = build_roster_plan(rows, corrections={}, expected_sha256=digest, source_bytes=exact_bytes)
    assert plan.ready
    assert plan.source_sha256 == digest


def test_changed_existing_staff_requires_approved_correction_and_preserves_uuid():
    staff_id = uuid4()
    existing = [
        SimpleNamespace(
            id=staff_id,
            employee_number="FX-200",
            first_name="Jordan",
            last_name="West",
            rank="Officer",
            shift="D",
        )
    ]
    rows = [
        {
            "employee_number": "FX-200",
            "first_name": "Jordan",
            "last_name": "West",
            "rank": "Sergeant",
            "shift": "D",
        }
    ]
    refused = build_roster_plan(rows, corrections={}, existing_staff=existing)
    assert [finding.code for finding in refused.findings] == ["unapproved_correction"]
    approved = build_roster_plan(
        rows,
        corrections={"FX-200": {"staff_member_id": str(staff_id), "approved": True}},
        existing_staff=existing,
    )
    assert approved.ready
    assert approved.updates[0]["staff_member_id"] == str(staff_id)


def test_apply_refuses_hash_recheck_mismatch_before_opening_transaction():
    rows = [
        {
            "employee_number": "FX-200",
            "first_name": "Jordan",
            "last_name": "West",
            "rank": "Sergeant",
            "shift": "D",
        }
    ]
    plan = build_roster_plan(rows, corrections={})
    called = False

    def factory():
        nonlocal called
        called = True
        raise AssertionError("must not open a transaction")

    with pytest.raises(ValueError, match="approved source hash"):
        apply_roster_plan(
            plan,
            session_factory=factory,
            import_run_id=str(uuid4()),
            source_bytes=b"changed bytes",
        )
    assert called is False


def test_validation_cli_writes_private_findings_and_prints_safe_counts(monkeypatch, capsys):
    source = json.dumps(
        {
            "staff": [
                {
                    "employee_number": "FX-200",
                    "first_name": "Jordan",
                    "last_name": "West",
                    "rank": "Sergeant",
                    "shift": "D",
                }
            ]
        }
    ).encode()
    digest = hashlib.sha256(source).hexdigest()
    writes = []

    class Store:
        def read(self, uri, *, max_bytes):
            return source if uri.endswith("source.json") else b"{}"

        def write(self, uri, payload):
            writes.append((uri, payload))

    class Session:
        def scalars(self, statement):
            return SimpleNamespace(all=lambda: [])

        def close(self):
            pass

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://fixture.invalid/test")
    monkeypatch.setattr("backend.jobs.roster_import.GooglePrivateObjectStore", Store)
    monkeypatch.setattr(
        "backend.jobs.roster_import.create_engine",
        lambda *args, **kwargs: SimpleNamespace(dispose=lambda: None),
    )
    monkeypatch.setattr("backend.jobs.roster_import.sessionmaker", lambda **kwargs: Session)
    monkeypatch.setattr(
        "backend.jobs.roster_import._current_migration_revision",
        lambda session: "20260812_0005",
    )
    assert (
        roster_main(
            [
                "--source-uri",
                "gs://fixture/source.json",
                "--corrections-uri",
                "gs://fixture/corrections.json",
                "--report-uri",
                "gs://fixture/reports/result.json",
                "--expected-sha256",
                digest,
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert json.loads(output)["status"] == "validated"
    assert json.loads(output)["migration_revision"] == "20260812_0005"
    assert "FX-200" not in output
    assert "Jordan" not in output
    assert writes and writes[0][0] == "gs://fixture/reports/result.json"


def test_private_report_adapter_enforces_create_only_generation():
    calls = []

    class Blob:
        def upload_from_string(self, *args, **kwargs):
            calls.append((args, kwargs))

    class Bucket:
        def blob(self, object_name):
            assert object_name == "reports/result.json"
            return Blob()

    class Client:
        def bucket(self, bucket):
            assert bucket == "fixture"
            return Bucket()

    GooglePrivateObjectStore(Client()).write("gs://fixture/reports/result.json", b'{"safe":"fixture"}')
    assert calls == [
        (
            (b'{"safe":"fixture"}',),
            {"content_type": "application/json", "if_generation_match": 0},
        )
    ]
