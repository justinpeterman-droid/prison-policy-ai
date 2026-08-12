"""Add transactional identity idempotency controls.

Revision ID: 20260812_0002
Revises: 20260812_0001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260812_0002"
down_revision = "20260812_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_sha256", sa.LargeBinary(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("response_status", sa.Integer()),
        sa.Column("response_reference", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_account_id"], ["accounts.id"], ondelete="CASCADE",
                                name="fk_idempotency_records_actor_account_id_accounts"),
        sa.UniqueConstraint("actor_account_id", "action", "idempotency_key",
                            name="uq_idempotency_actor_action_key"),
        sa.CheckConstraint("status IN ('in_progress','completed')", name="idempotency_status"),
        sa.CheckConstraint("octet_length(request_sha256) = 32",
                           name="idempotency_request_hash_length"),
        sa.CheckConstraint("octet_length(response_reference::text) <= 4096",
                           name="idempotency_response_reference_size"),
    )
    op.create_index("ix_idempotency_expiry", "idempotency_records", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_records")
