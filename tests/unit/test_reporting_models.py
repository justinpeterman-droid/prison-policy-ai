import enum

from sqlalchemy.dialects.postgresql import JSONB

from backend.persistence.models.reporting import (
    Incident,
    IncidentRevision,
    Report,
    ReportAccess,
    ReportRevision,
    ReportStatus,
    ReportType,
    RevisionReason,
)


def _constraint_names(model):
    return {constraint.name for constraint in model.__table__.constraints}


def _index_names(model):
    return {index.name for index in model.__table__.indexes}


def test_reporting_enums_are_exact_and_string_serializable():
    assert issubclass(ReportStatus, str) and issubclass(ReportStatus, enum.Enum)
    assert {item.value for item in ReportStatus} == {
        "in_progress",
        "completed",
        "archived",
    }
    assert {item.value for item in ReportType} == {
        "first_person",
        "supervisor_summary",
        "cover_letter",
        "disciplinary",
        "investigation",
        "form_005",
    }
    assert {item.value for item in RevisionReason} == {
        "autosave",
        "manual_save",
        "ai_result",
        "restored",
        "status_change",
        "ownership_change",
        "recovery",
        "admin_edit",
    }


def test_incident_model_has_current_state_and_search_indexes():
    assert set(Incident.__table__.columns.keys()) >= {
        "id",
        "created_by_account_id",
        "created_by_staff_member_id",
        "status",
        "current_revision_number",
        "incident_date",
        "incident_time",
        "facility",
        "shift",
        "location",
        "category",
        "field_notes",
        "classification",
        "extracted_facts",
        "gap_answers",
        "charges",
        "validation",
        "created_at",
        "updated_at",
        "archived_at",
    }
    for field in (
        "classification",
        "extracted_facts",
        "gap_answers",
        "charges",
        "validation",
    ):
        assert isinstance(Incident.__table__.c[field].type, JSONB)
    assert "ck_incidents_status" in _constraint_names(Incident)
    assert "ck_incidents_current_revision_nonnegative" in _constraint_names(Incident)
    assert _index_names(Incident) >= {
        "ix_incidents_status_date",
        "ix_incidents_category_date",
        "ix_incidents_updated_at",
    }


def test_report_model_is_one_shared_current_row_with_bounded_type():
    assert set(Report.__table__.columns.keys()) >= {
        "id",
        "incident_id",
        "report_type",
        "reporting_staff_member_id",
        "prepared_by_staff_member_id",
        "status",
        "current_revision_number",
        "current_content",
        "created_by_account_id",
        "created_at",
        "updated_at",
        "archived_at",
    }
    assert isinstance(Report.__table__.c.current_content.type, JSONB)
    assert Report.__table__.c.report_type.type.name == "report_type"
    assert "uq_reports_incident_type_owner" in _constraint_names(Report)
    assert _index_names(Report) >= {
        "ix_reports_status_updated",
        "ix_reports_owner_updated",
        "ix_reports_preparer_updated",
        "ix_reports_incident",
    }


def test_access_and_revision_constraints_are_bounded_and_append_oriented():
    assert list(ReportAccess.__table__.primary_key.columns.keys()) == [
        "report_id",
        "staff_member_id",
    ]
    assert "ck_report_access_relationship" in _constraint_names(ReportAccess)
    assert "uq_incident_revisions_parent_number" in _constraint_names(IncidentRevision)
    assert "uq_report_revisions_parent_number" in _constraint_names(ReportRevision)
    assert "ck_incident_revisions_number_nonnegative" in _constraint_names(IncidentRevision)
    assert "ck_report_revisions_number_nonnegative" in _constraint_names(ReportRevision)
    assert isinstance(IncidentRevision.__table__.c.snapshot.type, JSONB)
    assert isinstance(ReportRevision.__table__.c.snapshot.type, JSONB)
    assert isinstance(ReportRevision.__table__.c.provenance.type, JSONB)
    assert set(ReportRevision.__table__.columns.keys()) >= {
        "source_incident_revision_id",
        "source_ai_job_id",
        "fast_model",
        "pro_model",
        "model_location",
        "classification_prompt_sha256",
        "generation_prompt_sha256",
        "checklist_sha256",
        "template_sha256",
        "cloud_run_revision",
        "source_commit",
    }


def test_all_reporting_foreign_keys_are_explicit():
    expected = {
        "incidents": {"accounts.id", "staff_members.id"},
        "incident_revisions": {"incidents.id", "accounts.id", "staff_members.id"},
        "reports": {"incidents.id", "accounts.id", "staff_members.id"},
        "report_access": {"reports.id", "staff_members.id", "accounts.id"},
        "report_revisions": {
            "reports.id",
            "accounts.id",
            "staff_members.id",
            "incident_revisions.id",
        },
    }
    for model in (Incident, IncidentRevision, Report, ReportAccess, ReportRevision):
        targets = {
            foreign_key.target_fullname for column in model.__table__.columns for foreign_key in column.foreign_keys
        }
        assert targets == expected[model.__tablename__]
