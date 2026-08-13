"""Add durable AI job, transactional outbox, and export records.

Revision ID: 20260812_0005
Revises: 20260812_0004

RP-06: `ai_jobs` persists one row per classify/extract/generate/disciplinary
submission (queued through terminal), `task_outbox` is the transactional
outbox a later dispatcher (RP-07) drains, and `exports` records completed
Word exports (RP-08/RP-09). Every column here is a stable ID, digest,
status, or bounded error *category* -- never raw authorization headers,
field notes/report text, prompt/response content, or secrets.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260812_0005"
down_revision = "20260812_0004"
branch_labels = None
depends_on = None

AI_JOB_TYPE_VALUES = "'classify','extract','generate','disciplinary'"
AI_JOB_STATE_VALUES = "'queued','running','succeeded','failed','cancelled'"
AI_JOB_STAGE_VALUES = (
    "'queued','classifying','extracting','validating','generating',"
    "'disciplinary','completed','failed'"
)
TASK_OUTBOX_STATE_VALUES = "'pending','dispatched','completed','failed'"


def upgrade() -> None:
    op.create_table(
        "ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True)),
        sa.Column("requested_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_sha256", sa.LargeBinary(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_code", sa.String(64)),
        sa.Column("expected_incident_revision_number", sa.Integer(), nullable=False),
        sa.Column("fast_model", sa.String(120)),
        sa.Column("pro_model", sa.String(120)),
        sa.Column("model_location", sa.String(64)),
        sa.Column("prompt_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT",
                                name="fk_ai_jobs_incident_id_incidents"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT",
                                name="fk_ai_jobs_report_id_reports"),
        sa.ForeignKeyConstraint(["requested_by_account_id"], ["accounts.id"], ondelete="RESTRICT",
                                name="fk_ai_jobs_requested_by_account_id_accounts"),
        sa.UniqueConstraint("requested_by_account_id", "idempotency_key",
                            name="uq_ai_jobs_actor_idempotency_key"),
        sa.CheckConstraint(f"job_type IN ({AI_JOB_TYPE_VALUES})", name="job_type"),
        sa.CheckConstraint(f"state IN ({AI_JOB_STATE_VALUES})", name="state"),
        sa.CheckConstraint(f"stage IN ({AI_JOB_STAGE_VALUES})", name="stage"),
        sa.CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        sa.CheckConstraint("expected_incident_revision_number >= 0",
                           name="expected_incident_revision_nonnegative"),
        sa.CheckConstraint("octet_length(request_sha256) = 32",
                           name="ai_jobs_request_hash_length"),
    )
    op.create_index("ix_ai_jobs_queue_state", "ai_jobs", ["state", "created_at"])
    op.create_index("ix_ai_jobs_requested_actor", "ai_jobs",
                    ["requested_by_account_id", "created_at"])
    op.create_index("ix_ai_jobs_incident", "ai_jobs", ["incident_id", "created_at"])
    op.create_index("ix_ai_jobs_report", "ai_jobs", ["report_id", "created_at"])
    op.create_index("ix_ai_jobs_expiry", "ai_jobs", ["created_at"])

    op.create_table(
        "task_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ai_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["ai_job_id"], ["ai_jobs.id"], ondelete="CASCADE",
                                name="fk_task_outbox_ai_job_id_ai_jobs"),
        sa.UniqueConstraint("ai_job_id", name="uq_task_outbox_ai_job"),
        sa.CheckConstraint(f"state IN ({TASK_OUTBOX_STATE_VALUES})", name="state"),
        sa.CheckConstraint("attempts >= 0", name="attempts_nonnegative"),
    )
    op.create_index("ix_task_outbox_queue_state", "task_outbox", ["state", "available_at"])

    op.create_table(
        "exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exported_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version", sa.String(64), nullable=False),
        sa.Column("output_sha256", sa.LargeBinary(32), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("download_name", sa.String(255), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT",
                                name="fk_exports_report_id_reports"),
        sa.ForeignKeyConstraint(["report_revision_id"], ["report_revisions.id"], ondelete="RESTRICT",
                                name="fk_exports_report_revision_id_report_revisions"),
        sa.ForeignKeyConstraint(["exported_by_account_id"], ["accounts.id"], ondelete="RESTRICT",
                                name="fk_exports_exported_by_account_id_accounts"),
        sa.CheckConstraint("byte_length >= 0", name="byte_length_nonnegative"),
        sa.CheckConstraint("octet_length(output_sha256) = 32",
                           name="exports_output_hash_length"),
    )
    op.create_index("ix_exports_report", "exports", ["report_id", "created_at"])
    op.create_index("ix_exports_report_revision", "exports", ["report_revision_id"])


def downgrade() -> None:
    op.drop_index("ix_exports_report_revision", table_name="exports")
    op.drop_index("ix_exports_report", table_name="exports")
    op.drop_table("exports")

    op.drop_index("ix_task_outbox_queue_state", table_name="task_outbox")
    op.drop_table("task_outbox")

    op.drop_index("ix_ai_jobs_expiry", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_report", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_incident", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_requested_actor", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_queue_state", table_name="ai_jobs")
    op.drop_table("ai_jobs")
