"""PostgreSQL contracts for provenance-safe incident form population."""
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.forms.catalog import load_form_catalog, sync_form_catalog
from backend.forms.population import (
    FormPopulationNotAllowed,
    FormPopulationNotReady,
    populate_form_instance,
    render_form_preview,
)
from backend.persistence.models.forms import FormInstance, FormTemplate, IncidentPacketItem
from backend.persistence.models.reporting import IncidentRevision, ReportRevision
from tests.support.reporting import fictional_report_content


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "templates" / "paperwork" / "catalog.json"


def _saved_reviewed_state(
    db_session,
    *,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
    identity_fixed_now,
    reviewed: bool = True,
    source_matches: bool = True,
):
    fixed = identity_fixed_now + timedelta(minutes=10)
    snapshot = {
        "schema_version": 1,
        "incident_number": "2026-08-029",
        "incident_name": "Barracks 4 Fight",
        "incident_date": "2026-08-18",
        "incident_time": "13:42:00",
        "facility": "Fictional Unit",
        "shift": "A",
        "location": "Barracks 4",
        "category": "inmate_fight",
        "field_notes": "Saved reviewed field notes.",
        "classification": {},
        "extracted_facts": {
            "medical_disposition": "AI suggestion that was not accepted",
            "inmate_injuries": "Possible redness",
        },
        "gap_answers": {
            "medical_disposition": "No medical treatment required",
            "inmate_injuries": "No injuries reported",
        },
        "charges": [],
        "validation": {"facts_reviewed": reviewed},
        "warnings": [],
        "server_metadata": {
            "reporting_staff_ids": [
                str(fictional_staff_and_accounts.user.staff_member_id)
            ]
        },
    }
    incident_revision = IncidentRevision(
        incident_id=fictional_incident.id,
        revision_number=2,
        editor_account_id=fictional_staff_and_accounts.user.id,
        editor_staff_member_id=fictional_staff_and_accounts.user.staff_member_id,
        snapshot=snapshot,
        changed_fields={"fields": ["field_notes", "validation"]},
        reason="manual_save",
        client_version="1.0.0",
        request_id="request_fictional_form_incident_revision",
        created_at=fixed,
    )
    db_session.add(incident_revision)
    fictional_incident.current_revision_number = 2
    fictional_incident.incident_number = "2026-08-029"
    fictional_incident.incident_name = "Barracks 4 Fight"
    fictional_incident.location = "Barracks 4"
    fictional_incident.category = "inmate_fight"
    fictional_incident.field_notes = "Saved reviewed field notes."
    fictional_incident.extracted_facts = dict(snapshot["extracted_facts"])
    fictional_incident.gap_answers = dict(snapshot["gap_answers"])
    fictional_incident.validation = dict(snapshot["validation"])
    fictional_incident.updated_at = fixed
    db_session.flush()

    report_snapshot = fictional_report_content("Saved reviewed narrative.")
    report_snapshot["editable_fields"] = {
        "employee_number": "TEST-2101",
        "officer_first": "Alex",
        "officer_last": "Example",
        "rank": "Officer",
        "shift_assignment": "A",
    }
    report_revision = ReportRevision(
        report_id=fictional_report.id,
        revision_number=2,
        editor_account_id=fictional_staff_and_accounts.user.id,
        editor_staff_member_id=fictional_staff_and_accounts.user.staff_member_id,
        snapshot=report_snapshot,
        changed_fields={"fields": ["narrative", "editable_fields"]},
        reason="ai_result",
        source_incident_revision_id=(
            incident_revision.id if source_matches else None
        ),
        provenance={},
        client_version="1.0.0",
        request_id="request_fictional_form_report_revision",
        created_at=fixed + timedelta(minutes=1),
    )
    db_session.add(report_revision)
    fictional_report.current_revision_number = 2
    fictional_report.current_content = dict(report_snapshot)
    fictional_report.updated_at = fixed + timedelta(minutes=1)
    db_session.flush()
    return incident_revision, report_revision


def _packet_item(
    db_session,
    *,
    incident,
    account,
    template_code,
    incident_revision_number=2,
):
    sync_form_catalog(db_session, load_form_catalog(CATALOG_PATH))
    db_session.flush()
    template = db_session.scalar(
        select(FormTemplate).where(FormTemplate.code == template_code)
    )
    item = IncidentPacketItem(
        incident_id=incident.id,
        form_template_id=template.id,
        reporting_staff_member_id=(
            account.staff_member_id if template_code == "form_005_409" else None
        ),
        packet_group="required",
        packet_state="selected",
        source_incident_revision_number=incident_revision_number,
        selection_reason="Fictional required form population fixture.",
        added_by_account_id=account.id,
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_population_uses_saved_reviewed_revisions_and_is_idempotent(
    db_session,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
    identity_fixed_now,
    user_actor,
):
    incident_revision, _report_revision = _saved_reviewed_state(
        db_session,
        fictional_incident=fictional_incident,
        fictional_report=fictional_report,
        fictional_staff_and_accounts=fictional_staff_and_accounts,
        identity_fixed_now=identity_fixed_now,
    )
    item = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="form_005_409",
    )

    # These row-level values were never saved into a revision. Population must
    # ignore them and read the immutable incident/report revisions instead.
    fictional_incident.incident_number = "2099-01-999"
    fictional_report.current_content = fictional_report_content(
        "UNSAVED ROW-LEVEL NARRATIVE MUST NOT BE USED."
    )

    first = populate_form_instance(
        db_session,
        user_actor,
        packet_item_id=item.id,
        incident_revision_number=incident_revision.revision_number,
        now=identity_fixed_now + timedelta(minutes=20),
    )
    second = populate_form_instance(
        db_session,
        user_actor,
        packet_item_id=item.id,
        incident_revision_number=incident_revision.revision_number,
        now=identity_fixed_now + timedelta(minutes=21),
    )

    assert second.form_instance_id == first.form_instance_id
    assert first.source_incident_revision_number == 2
    assert first.populated_fields["incident_number"] == "2026-08-029"
    assert first.populated_fields["reporting_officer"] == "Officer Alex Example"
    assert first.populated_fields["narrative"] == "Saved reviewed narrative."
    assert first.populated_fields["document_metadata"]["employee_number"] == "TEST-2101"
    assert first.populated_fields["document_metadata"]["narrative"] == "Saved reviewed narrative."
    assert first.populated_fields["document_metadata"]["location"] == "Barracks 4"
    assert first.completeness.state == "needs_review"
    assert first.completeness.missing_fields == ()
    assert first.completeness.review_fields == ("narrative",)
    assert db_session.scalar(select(func.count()).select_from(FormInstance)) == 1

    preview = render_form_preview(
        db_session,
        user_actor,
        form_instance_id=first.form_instance_id,
    )
    assert preview.template_code == "form_005_409"
    assert preview.fields["incident_number"] == "2026-08-029"
    assert preview.fields["narrative"] == "Saved reviewed narrative."
    assert preview.completeness == first.completeness


def test_physical_forms_cannot_be_digitally_populated(
    db_session,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
    identity_fixed_now,
    user_actor,
):
    _saved_reviewed_state(
        db_session,
        fictional_incident=fictional_incident,
        fictional_report=fictional_report,
        fictional_staff_and_accounts=fictional_staff_and_accounts,
        identity_fixed_now=identity_fixed_now,
    )
    item = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="chain_of_custody_physical",
    )

    with pytest.raises(
        FormPopulationNotAllowed,
        match="Physical-only paperwork cannot be digitally populated",
    ):
        populate_form_instance(
            db_session,
            user_actor,
            packet_item_id=item.id,
            incident_revision_number=2,
        )


def test_population_requires_reviewed_facts_and_matching_report_provenance(
    db_session,
    fictional_incident,
    fictional_report,
    fictional_staff_and_accounts,
    identity_fixed_now,
    user_actor,
):
    _saved_reviewed_state(
        db_session,
        fictional_incident=fictional_incident,
        fictional_report=fictional_report,
        fictional_staff_and_accounts=fictional_staff_and_accounts,
        identity_fixed_now=identity_fixed_now,
        reviewed=False,
    )
    item = _packet_item(
        db_session,
        incident=fictional_incident,
        account=fictional_staff_and_accounts.user,
        template_code="form_005_409",
    )

    with pytest.raises(FormPopulationNotReady, match="facts must be reviewed"):
        populate_form_instance(
            db_session,
            user_actor,
            packet_item_id=item.id,
            incident_revision_number=2,
        )

    # Replace the unreviewed revision with a separate reviewed incident/report
    # so the immutable revision rows are never edited in place.
    db_session.rollback()
