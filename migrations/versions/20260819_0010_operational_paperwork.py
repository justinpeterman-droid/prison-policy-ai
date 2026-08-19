"""Add revisioned operational paperwork storage.

Revision ID: 20260819_0010
Revises: 20260819_0009
Create Date: 2026-08-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260819_0010"
down_revision: Union[str, None] = "20260819_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_paperwork",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("paperwork_type", sa.String(length=64), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("shift", sa.String(length=32), nullable=False),
        sa.Column("created_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="in_progress", nullable=False),
        sa.Column("current_revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("current_content", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('in_progress','completed','archived')", name="ck_operational_paperwork_status"),
        sa.CheckConstraint("current_revision_number >= 1", name="ck_operational_paperwork_current_revision_positive"),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_staff_member_id"], ["staff_members.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_operational_paperwork_type_date_shift",
        "operational_paperwork",
        ["paperwork_type", "record_date", "shift", "id"],
        unique=False,
    )
    op.create_index(
        "ix_operational_paperwork_creator_updated",
        "operational_paperwork",
        ["created_by_staff_member_id", "updated_at", "id"],
        unique=False,
    )
    op.create_table(
        "operational_paperwork_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("paperwork_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("editor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("editor_staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("client_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("revision_number >= 1", name="ck_operational_paperwork_revisions_revision_positive"),
        sa.CheckConstraint("reason IN ('autosave','manual_save','restored','status_change')", name="ck_operational_paperwork_revisions_reason"),
        sa.ForeignKeyConstraint(["editor_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["editor_staff_member_id"], ["staff_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["paperwork_id"], ["operational_paperwork.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paperwork_id", "revision_number", name="uq_operational_paperwork_revisions_parent_number"),
    )
    op.create_index(
        "ix_operational_paperwork_revisions_parent_created",
        "operational_paperwork_revisions",
        ["paperwork_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operational_paperwork_revisions_parent_created",
        table_name="operational_paperwork_revisions",
    )
    op.drop_table("operational_paperwork_revisions")
    op.drop_index(
        "ix_operational_paperwork_creator_updated",
        table_name="operational_paperwork",
    )
    op.drop_index(
        "ix_operational_paperwork_type_date_shift",
        table_name="operational_paperwork",
    )
    op.drop_table("operational_paperwork")
