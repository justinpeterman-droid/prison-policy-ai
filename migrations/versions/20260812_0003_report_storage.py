"""Add incident, shared report access, and immutable revision storage.

Revision ID: 20260812_0003
Revises: 20260812_0002

This is an expansion-only production migration. On an empty test database it is
expected to finish in seconds and takes only catalog/table-creation locks.
Production rollback retains the expanded schema; downgrade is for isolated test
lifecycle verification only. Verify with ``alembic current`` and catalog queries
for the five tables and ``report_type`` enum after upgrade.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260812_0003"
down_revision = "20260812_0002"
branch_labels = None
depends_on = None


REPORT_TYPES = (
    "first_person", "supervisor_summary", "cover_letter", "disciplinary",
    "investigation", "form_005",
)
STATUS_CHECK = "status IN ('in_progress','completed','archived')"
INCIDENT_REASON_CHECK = (
    "reason IN ('autosave','manual_save','ai_result','restored','status_change',"
    "'ownership_change','recovery')"
)
REPORT_REASON_CHECK = (
    "reason IN ('autosave','manual_save','ai_result','restored','status_change',"
    "'ownership_change','recovery','admin_edit')"
)


def upgrade() -> None:
    report_type = postgresql.ENUM(*REPORT_TYPES, name="report_type", create_type=False)
    report_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="in_progress"),
        sa.Column("current_revision_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incident_date", sa.Date()),
        sa.Column("incident_time", sa.Time()),
        sa.Column("facility", sa.String(120)),
        sa.Column("shift", sa.String(32)),
        sa.Column("location", sa.String(200)),
        sa.Column("category", sa.String(120)),
        sa.Column("field_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("classification", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("extracted_facts", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("gap_answers", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("charges", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("validation", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["created_by_account_id"], ["accounts.id"], ondelete="RESTRICT",
            name="fk_incidents_created_by_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_staff_member_id"], ["staff_members.id"], ondelete="RESTRICT",
            name="fk_incidents_created_by_staff_member_id_staff_members",
        ),
        sa.CheckConstraint(STATUS_CHECK, name="ck_incidents_status"),
        sa.CheckConstraint(
            "current_revision_number >= 0", name="ck_incidents_current_revision_nonnegative",
        ),
    )
    op.create_index("ix_incidents_status_date", "incidents", ["status", "incident_date", "id"])
    op.create_index("ix_incidents_category_date", "incidents", ["category", "incident_date", "id"])
    op.create_index("ix_incidents_updated_at", "incidents", ["updated_at", "id"])

    op.create_table(
        "incident_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("editor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("editor_staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("client_version", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT",
                                name="fk_incident_revisions_incident_id_incidents"),
        sa.ForeignKeyConstraint(["editor_account_id"], ["accounts.id"], ondelete="RESTRICT",
                                name="fk_incident_revisions_editor_account_id_accounts"),
        sa.ForeignKeyConstraint(["editor_staff_member_id"], ["staff_members.id"], ondelete="RESTRICT",
                                name="fk_incident_revisions_editor_staff_member_id_staff_members"),
        sa.UniqueConstraint("incident_id", "revision_number",
                            name="uq_incident_revisions_parent_number"),
        sa.CheckConstraint("revision_number >= 0",
                           name="ck_incident_revisions_number_nonnegative"),
        sa.CheckConstraint(INCIDENT_REASON_CHECK, name="ck_incident_revisions_reason"),
    )
    op.create_index("ix_incident_revisions_parent_created", "incident_revisions",
                    ["incident_id", "created_at"])

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", report_type, nullable=False),
        sa.Column("reporting_staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prepared_by_staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="in_progress"),
        sa.Column("current_revision_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_content", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT",
                                name="fk_reports_incident_id_incidents"),
        sa.ForeignKeyConstraint(["reporting_staff_member_id"], ["staff_members.id"],
                                ondelete="RESTRICT", name="fk_reports_reporting_staff_member_id_staff_members"),
        sa.ForeignKeyConstraint(["prepared_by_staff_member_id"], ["staff_members.id"],
                                ondelete="RESTRICT", name="fk_reports_prepared_by_staff_member_id_staff_members"),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"],
                                ondelete="RESTRICT", name="fk_reports_created_by_account_id_accounts"),
        sa.CheckConstraint(STATUS_CHECK, name="ck_reports_status"),
        sa.CheckConstraint("current_revision_number >= 0",
                           name="ck_reports_current_revision_nonnegative"),
        sa.UniqueConstraint(
            "incident_id", "report_type", "reporting_staff_member_id",
            name="uq_reports_incident_type_owner",
        ),
    )
    op.create_index("ix_reports_incident", "reports", ["incident_id", "id"])
    op.create_index("ix_reports_status_updated", "reports", ["status", "updated_at", "id"])
    op.create_index("ix_reports_owner_updated", "reports", ["reporting_staff_member_id", "updated_at", "id"])
    op.create_index("ix_reports_preparer_updated", "reports", ["prepared_by_staff_member_id", "updated_at", "id"])

    op.create_table(
        "report_access",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("relationship", sa.String(16), nullable=False),
        sa.Column("granted_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT",
                                name="fk_report_access_report_id_reports"),
        sa.ForeignKeyConstraint(["staff_member_id"], ["staff_members.id"], ondelete="RESTRICT",
                                name="fk_report_access_staff_member_id_staff_members"),
        sa.ForeignKeyConstraint(["granted_by_account_id"], ["accounts.id"], ondelete="RESTRICT",
                                name="fk_report_access_granted_by_account_id_accounts"),
        sa.CheckConstraint("relationship IN ('owner','preparer')",
                           name="ck_report_access_relationship"),
    )
    op.create_index("ix_report_access_staff_relationship", "report_access",
                    ["staff_member_id", "relationship", "report_id"])

    op.create_table(
        "report_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("editor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("editor_staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("source_incident_revision_id", postgresql.UUID(as_uuid=True)),
        sa.Column("source_ai_job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("provenance", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("fast_model", sa.String(120)),
        sa.Column("pro_model", sa.String(120)),
        sa.Column("model_location", sa.String(64)),
        sa.Column("classification_prompt_sha256", sa.String(64)),
        sa.Column("generation_prompt_sha256", sa.String(64)),
        sa.Column("checklist_sha256", sa.String(64)),
        sa.Column("template_sha256", sa.String(64)),
        sa.Column("cloud_run_revision", sa.String(128)),
        sa.Column("source_commit", sa.String(128)),
        sa.Column("client_version", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT",
                                name="fk_report_revisions_report_id_reports"),
        sa.ForeignKeyConstraint(["editor_account_id"], ["accounts.id"], ondelete="RESTRICT",
                                name="fk_report_revisions_editor_account_id_accounts"),
        sa.ForeignKeyConstraint(["editor_staff_member_id"], ["staff_members.id"], ondelete="RESTRICT",
                                name="fk_report_revisions_editor_staff_member_id_staff_members"),
        sa.ForeignKeyConstraint(["source_incident_revision_id"], ["incident_revisions.id"],
                                ondelete="SET NULL", name="fk_report_revisions_source_incident_revision"),
        sa.UniqueConstraint("report_id", "revision_number",
                            name="uq_report_revisions_parent_number"),
        sa.CheckConstraint("revision_number >= 0",
                           name="ck_report_revisions_number_nonnegative"),
        sa.CheckConstraint(REPORT_REASON_CHECK, name="ck_report_revisions_reason"),
    )
    op.create_index("ix_report_revisions_parent_created", "report_revisions",
                    ["report_id", "created_at"])
    op.create_index("ix_report_revisions_editor_created", "report_revisions",
                    ["editor_staff_member_id", "created_at"])
    op.execute("""
        CREATE FUNCTION reject_report_revision_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'report revision history is immutable';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_incident_revisions_immutable
        BEFORE UPDATE OR DELETE ON incident_revisions
        FOR EACH ROW EXECUTE FUNCTION reject_report_revision_mutation()
    """)
    op.execute("""
        CREATE TRIGGER trg_report_revisions_immutable
        BEFORE UPDATE OR DELETE ON report_revisions
        FOR EACH ROW EXECUTE FUNCTION reject_report_revision_mutation()
    """)


def downgrade() -> None:
    op.drop_table("report_revisions")
    op.drop_table("report_access")
    op.drop_table("reports")
    op.drop_table("incident_revisions")
    op.drop_table("incidents")
    op.execute("DROP FUNCTION reject_report_revision_mutation()")
    postgresql.ENUM(*REPORT_TYPES, name="report_type").drop(
        op.get_bind(), checkfirst=True,
    )
