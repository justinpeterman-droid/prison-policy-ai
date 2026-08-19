"""Add revisioned operational-paperwork persistence.

Revision ID: 20260819_0009
Revises: 20260819_0008
Create Date: 2026-08-19
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260819_0009"
down_revision: str | None = "20260819_0008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


PAPERWORK_KIND_CHECK = (
    "kind IN ('count_sheet','assignment_roster','uniform_inspection',"
    "'metal_detector_test','perimeter_check','random_search_log',"
    "'detector_sign_out')"
)
PAPERWORK_REASON_CHECK = (
    "reason IN ('autosave','manual_save','recovery','restored')"
)


def upgrade() -> None:
    op.create_table(
        "paperwork_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("shift", sa.String(length=32), nullable=True),
        sa.Column(
            "current_revision_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "current_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_by_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_by_staff_member_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "last_editor_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "last_editor_staff_member_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name="fk_paperwork_records_creator_account",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_staff_member_id"],
            ["staff_members.id"],
            ondelete="RESTRICT",
            name="fk_paperwork_records_creator_staff",
        ),
        sa.ForeignKeyConstraint(
            ["last_editor_account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name="fk_paperwork_records_editor_account",
        ),
        sa.ForeignKeyConstraint(
            ["last_editor_staff_member_id"],
            ["staff_members.id"],
            ondelete="RESTRICT",
            name="fk_paperwork_records_editor_staff",
        ),
        sa.CheckConstraint(
            PAPERWORK_KIND_CHECK,
            name="ck_paperwork_records_kind",
        ),
        sa.CheckConstraint(
            "current_revision_number >= 1",
            name="ck_paperwork_records_current_revision_positive",
        ),
    )
    op.create_index(
        "ix_paperwork_records_kind_date_shift",
        "paperwork_records",
        ["kind", "work_date", "shift", "id"],
    )
    op.create_index(
        "ix_paperwork_records_creator_updated",
        "paperwork_records",
        ["created_by_staff_member_id", "updated_at", "id"],
    )
    op.create_index(
        "ix_paperwork_records_updated",
        "paperwork_records",
        ["updated_at", "id"],
    )

    op.create_table(
        "paperwork_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "editor_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "editor_staff_member_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "changed_fields",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("client_version", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["paperwork_records.id"],
            ondelete="CASCADE",
            name="fk_paperwork_revisions_record",
        ),
        sa.ForeignKeyConstraint(
            ["editor_account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name="fk_paperwork_revisions_editor_account",
        ),
        sa.ForeignKeyConstraint(
            ["editor_staff_member_id"],
            ["staff_members.id"],
            ondelete="RESTRICT",
            name="fk_paperwork_revisions_editor_staff",
        ),
        sa.UniqueConstraint(
            "record_id",
            "revision_number",
            name="uq_paperwork_revisions_record_number",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_paperwork_revisions_revision_number_positive",
        ),
        sa.CheckConstraint(
            PAPERWORK_REASON_CHECK,
            name="ck_paperwork_revisions_reason",
        ),
    )
    op.create_index(
        "ix_paperwork_revisions_record_created",
        "paperwork_revisions",
        ["record_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paperwork_revisions_record_created",
        table_name="paperwork_revisions",
    )
    op.drop_table("paperwork_revisions")
    op.drop_index(
        "ix_paperwork_records_updated",
        table_name="paperwork_records",
    )
    op.drop_index(
        "ix_paperwork_records_creator_updated",
        table_name="paperwork_records",
    )
    op.drop_index(
        "ix_paperwork_records_kind_date_shift",
        table_name="paperwork_records",
    )
    op.drop_table("paperwork_records")
