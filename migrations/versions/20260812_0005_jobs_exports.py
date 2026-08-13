"""Add durable AI jobs, transactional task outbox, and export metadata.

Revision ID: 20260812_0005
Revises: 20260812_0004

The records intentionally contain bounded control metadata only. Incident and
report content remains in their revision tables; provider input/output and
authorization material never enter these tables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260812_0005"
down_revision = "20260812_0004"
branch_labels = None
depends_on = None


JOB_TYPE_CHECK = "job_type IN ('classify','extract','generate','disciplinary')"
JOB_STATE_CHECK = "state IN ('queued','running','succeeded','failed','cancelled')"
JOB_STAGE_CHECK = (
    "stage IN ('queued','classifying','extracting','validating','generating',"
    "'disciplinary','completed','failed')"
)


def upgrade() -> None:
    op.create_table(
        "ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True)),
        sa.Column("requested_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(24), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_sha256", sa.LargeBinary(32), nullable=False),
        sa.Column("base_incident_revision", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("claim_token", postgresql.UUID(as_uuid=True)),
        sa.Column("request_metadata", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("result_reference", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(64)),
        sa.Column("fast_model", sa.String(120)),
        sa.Column("pro_model", sa.String(120)),
        sa.Column("model_location", sa.String(64)),
        sa.Column("classification_prompt_sha256", sa.String(64)),
        sa.Column("generation_prompt_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT",
                                name="fk_ai_jobs_incident_id_incidents"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT",
                                name="fk_ai_jobs_report_id_reports"),
        sa.ForeignKeyConstraint(["requested_by_account_id"], ["accounts.id"],
                                ondelete="RESTRICT",
                                name="fk_ai_jobs_requested_by_account_id_accounts"),
        sa.CheckConstraint(JOB_TYPE_CHECK, name="ck_ai_jobs_job_type"),
        sa.CheckConstraint(JOB_STATE_CHECK, name="ck_ai_jobs_state"),
        sa.CheckConstraint(JOB_STAGE_CHECK, name="ck_ai_jobs_stage"),
        sa.CheckConstraint("base_incident_revision >= 1",
                           name="ck_ai_jobs_base_revision_positive"),
        sa.CheckConstraint("attempts >= 0", name="ck_ai_jobs_attempts_nonnegative"),
        sa.CheckConstraint("octet_length(request_sha256) = 32",
                           name="ck_ai_jobs_request_hash_length"),
        sa.CheckConstraint("octet_length(request_metadata::text) <= 4096",
                           name="ck_ai_jobs_request_metadata_size"),
        sa.CheckConstraint("octet_length(result_reference::text) <= 4096",
                           name="ck_ai_jobs_result_reference_size"),
        sa.CheckConstraint("jsonb_typeof(result_reference) = 'object'",
                           name="ck_ai_jobs_result_reference_object"),
        sa.CheckConstraint(
            "(result_reference - 'incident_revision_number' - 'reports') = '{}'::jsonb",
            name="ck_ai_jobs_result_reference_keys",
        ),
        sa.CheckConstraint(
            "CASE WHEN result_reference ? 'incident_revision_number' THEN "
            "jsonb_typeof(result_reference->'incident_revision_number') = 'number' "
            "AND (result_reference->>'incident_revision_number') ~ '^[1-9][0-9]*$' "
            "ELSE TRUE END",
            name="ck_ai_jobs_result_reference_incident_revision",
        ),
        sa.CheckConstraint(
            "CASE WHEN result_reference ? 'reports' THEN CASE WHEN "
            "jsonb_typeof(result_reference->'reports') = 'array' THEN "
            "jsonb_array_length(result_reference->'reports') <= 20 "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (@.type() != \"object\")') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (!exists(@.report_id) || !exists(@.revision_number))') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*].keyvalue() ? "
            "(@.key != \"report_id\" && @.key != \"revision_number\")') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (@.report_id.type() != \"string\" || "
            "@.revision_number.type() != \"number\")') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (!(@.report_id like_regex "
            "\"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            "[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$\"))') "
            "AND NOT jsonb_path_exists(result_reference, "
            "'$.reports[*] ? (!(@.revision_number.string() like_regex "
            "\"^[1-9][0-9]*$\"))') ELSE FALSE END ELSE TRUE END",
            name="ck_ai_jobs_result_reference_reports",
        ),
        sa.CheckConstraint(
            "((state = 'running') = "
            "(lease_expires_at IS NOT NULL AND claim_token IS NOT NULL))",
            name="ck_ai_jobs_lease_matches_running_state",
        ),
        sa.CheckConstraint(
            "lease_expires_at IS NULL OR started_at IS NOT NULL",
            name="ck_ai_jobs_lease_requires_start",
        ),
        sa.CheckConstraint(
            "error_code IS NULL OR error_code ~ '^[a-z][a-z0-9_]{0,63}$'",
            name="ck_ai_jobs_error_code_format",
        ),
    )
    op.create_index("ix_ai_jobs_queue", "ai_jobs", ["state", "created_at", "id"])
    op.create_index("ix_ai_jobs_claim", "ai_jobs",
                    ["state", "lease_expires_at", "created_at", "id"])
    op.create_index("ix_ai_jobs_requested_actor", "ai_jobs",
                    ["requested_by_account_id", "created_at", "id"])
    op.create_index("ix_ai_jobs_incident", "ai_jobs", ["incident_id", "created_at", "id"])
    op.create_index("ix_ai_jobs_report", "ai_jobs", ["report_id", "created_at", "id"])

    op.create_table(
        "task_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ai_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["ai_job_id"], ["ai_jobs.id"], ondelete="RESTRICT",
                                name="fk_task_outbox_ai_job_id_ai_jobs"),
        sa.UniqueConstraint("ai_job_id", name="uq_task_outbox_ai_job_id"),
        sa.CheckConstraint("state IN ('pending','dispatched','failed')",
                           name="ck_task_outbox_state"),
        sa.CheckConstraint("attempts >= 0", name="ck_task_outbox_attempts_nonnegative"),
        sa.CheckConstraint(
            "last_error_code IS NULL OR "
            "last_error_code ~ '^[a-z][a-z0-9_]{0,63}$'",
            name="ck_task_outbox_last_error_code_format",
        ),
    )
    op.create_index("ix_task_outbox_available", "task_outbox",
                    ["state", "available_at", "id"])

    op.create_table(
        "exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exported_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version", sa.String(128), nullable=False),
        sa.Column("output_sha256", sa.LargeBinary(32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("download_name", sa.String(255), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT",
                                name="fk_exports_report_id_reports"),
        sa.ForeignKeyConstraint(["report_revision_id"], ["report_revisions.id"],
                                ondelete="RESTRICT",
                                name="fk_exports_report_revision_id_report_revisions"),
        sa.ForeignKeyConstraint(["exported_by_account_id"], ["accounts.id"],
                                ondelete="RESTRICT",
                                name="fk_exports_exported_by_account_id_accounts"),
        sa.CheckConstraint("octet_length(output_sha256) = 32",
                           name="ck_exports_output_hash_length"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_exports_size_nonnegative"),
    )
    op.create_index("ix_exports_report_revision", "exports",
                    ["report_id", "report_revision_id", "id"])
    op.create_index("ix_exports_actor_created", "exports",
                    ["exported_by_account_id", "created_at", "id"])
    op.create_foreign_key(
        "fk_report_revisions_source_ai_job_id_ai_jobs",
        "report_revisions",
        "ai_jobs",
        ["source_ai_job_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_report_revisions_source_ai_job_id_ai_jobs",
        "report_revisions",
        type_="foreignkey",
    )
    op.drop_table("exports")
    op.drop_table("task_outbox")
    op.drop_table("ai_jobs")
