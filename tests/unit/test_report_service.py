"""Credential-free parity tests for route-neutral report engine adapters."""

import inspect
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.reports import service
from backend.reports.roster import (
    SqlStaffProvider,
    StaffProvider,
    resolve_staff_from_persons,
)


def test_public_engine_adapter_signatures_match_the_locked_roadmap():
    assert list(inspect.signature(service.classify_incident_notes).parameters) == ["notes"]
    assert list(inspect.signature(service.extract_incident_notes).parameters) == [
        "notes",
        "category",
        "staff_provider",
    ]
    generate = list(inspect.signature(service.generate_report_set).parameters.values())
    disciplinary = list(inspect.signature(service.generate_disciplinary_report).parameters.values())
    assert [parameter.name for parameter in generate] == ["payload", "staff_provider"]
    assert [parameter.name for parameter in disciplinary] == [
        "payload",
        "staff_provider",
    ]
    assert generate[1].kind is inspect.Parameter.KEYWORD_ONLY
    assert disciplinary[1].kind is inspect.Parameter.KEYWORD_ONLY


def test_classify_adapter_preserves_the_legacy_response_shape(monkeypatch):
    monkeypatch.setattr(
        service,
        "classify_incident",
        lambda notes: {
            "incident_type": "fictional_incident",
            "label": "Fictional incident",
            "charges_applicable": ["TEST-01"],
            "charge_descriptions": {"TEST-01": "Fictional charge."},
            "engine_private": "not part of the legacy route response",
        },
    )

    assert service.classify_incident_notes("Fictional field notes.") == {
        "incident_type": "fictional_incident",
        "label": "Fictional incident",
        "charges": ["TEST-01"],
        "charge_descriptions": {"TEST-01": "Fictional charge."},
    }


class _FictionalProvider:
    def lookup(self, name_hint: str):
        if name_hint.strip().lower() in {"example", "alex example"}:
            return {
                "rank": "Officer",
                "first": "Alex",
                "last": "Example",
                "employee_number": "TEST-2101",
                "shift": "A",
            }
        return None

    def search(self, query: str, *, limit: int = 25):
        return []


def test_extract_adapter_uses_injected_staff_provider_and_keeps_wire_shape(monkeypatch):
    monkeypatch.setattr(
        service,
        "extract_slots",
        lambda notes, category: {
            "date": "08-12-2026",
            "time": "1400",
            "location": "Fictional Dayroom",
            "persons": [{"role": "security_staff", "name": "Alex Example", "last": "Example"}],
        },
    )
    monkeypatch.setattr(
        service,
        "find_gaps",
        lambda category, slots: {
            "gaps": [],
            "markers": [],
            "checklist": ["fictional_check"],
            "auto_content": ["Fictional approved content."],
        },
    )
    monkeypatch.setattr(service, "compute_provenance", lambda notes, slots: {"date": "notes"})
    monkeypatch.setattr(
        service,
        "security_staff",
        lambda slots: [person for person in slots["persons"] if person["role"] == "security_staff"],
    )

    result = service.extract_incident_notes("Fictional field notes.", "fictional_incident", _FictionalProvider())

    assert set(result) == {
        "slots",
        "gaps",
        "blocking_remaining",
        "markers",
        "checklist",
        "auto_content",
        "officers",
        "provenance",
    }
    assert result["slots"]["persons"][0]["_roster_match"] is True
    assert result["slots"]["employee_number"] == "TEST-2101"
    assert result["slots"]["shift_assignment"] == "A Shift"


def test_generate_adapter_runs_existing_generation_and_finalization(monkeypatch):
    provider = _FictionalProvider()
    context = {"slots": {"charges": "TEST-01"}, "category": "fictional_incident"}
    monkeypatch.setattr(service, "_prepare_generation", lambda payload, staff_provider: context)
    monkeypatch.setattr(
        service,
        "generate_all_reports",
        lambda slots, category, auto_content=None, include_disciplinary=True: {
            "first_person": "Fictional report.",
        },
    )
    monkeypatch.setattr(
        service,
        "_finalize_generation",
        lambda reports, ctx: {"reports": reports, "flags": [], "markers": []},
    )
    monkeypatch.setattr(service, "has_charges", lambda slots: True)

    result = service.generate_report_set(
        {"notes": "Fictional notes.", "category": "fictional_incident"},
        staff_provider=provider,
    )

    assert result["reports"] == {"first_person": "Fictional report."}
    assert result["disciplinary_deferred"] is False


def test_disciplinary_adapter_drops_unknown_prior_report_keys(monkeypatch):
    provider = _FictionalProvider()
    context = {"slots": {"charges": "TEST-01"}, "auto_content": []}
    monkeypatch.setattr(service, "_prepare_generation", lambda payload, staff_provider: context)
    monkeypatch.setattr(
        service,
        "generate_disciplinary_only",
        lambda slots, first_person, auto_content: {"disciplinary": "Fictional supplement."},
    )
    monkeypatch.setattr(
        service,
        "_finalize_generation",
        lambda reports, ctx: {"reports": reports, "flags": [], "markers": []},
    )

    result = service.generate_disciplinary_report(
        {
            "notes": "Fictional notes.",
            "category": "fictional_incident",
            "reports": {"first_person": "Fictional report.", "untrusted": "drop me"},
        },
        staff_provider=provider,
    )

    assert result["reports"] == {
        "first_person": "Fictional report.",
        "disciplinary": "Fictional supplement.",
    }
    assert result["disciplinary_deferred"] is False


def test_staff_resolution_consumes_provider_without_mutating_legacy_store(monkeypatch):
    monkeypatch.setattr(
        "backend.reports.roster.roster_store.update",
        lambda *_args, **_kwargs: pytest.fail("SQL staff resolution must not update the legacy roster"),
    )

    resolved, gaps = resolve_staff_from_persons(
        [
            {"role": "security_staff", "name": "Alex Example", "last": "Example"},
        ],
        staff_provider=_FictionalProvider(),
    )

    assert gaps == []
    assert resolved[0]["employee_number"] == "TEST-2101"


def test_sql_staff_provider_returns_active_bounded_wire_records():
    row = SimpleNamespace(
        id=uuid4(),
        employee_number="TEST-2101",
        rank="Officer",
        first_name="Alex",
        last_name="Example",
        shift="A",
        is_active=True,
        created_at=__import__("datetime").datetime(2026, 8, 12),
    )

    class _Scalars:
        def all(self):
            return [row]

    class _Session:
        statement = None

        def scalars(self, statement):
            self.statement = statement
            return _Scalars()

    session = _Session()
    provider: StaffProvider = SqlStaffProvider(session)

    assert provider.search("Example", limit=1) == [
        {
            "staff_id": str(row.id),
            "employee_number": "TEST-2101",
            "display_name": "Officer Alex Example",
            "rank": "Officer",
            "first": "Alex",
            "last": "Example",
            "shift": "A",
            "is_active": True,
        }
    ]
    rendered = str(session.statement).lower()
    assert "staff_members.is_active" in rendered
    assert "limit" in rendered
