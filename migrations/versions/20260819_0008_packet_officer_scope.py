"""Allow one incident form instance per reporting officer.

Revision ID: 20260819_0008
Revises: 20260818_0007
Create Date: 2026-08-19
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260819_0008"
down_revision: str | None = "20260818_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_incident_packet_items_incident_template",
        "incident_packet_items",
        type_="unique",
    )
    op.add_column(
        "incident_packet_items",
        sa.Column(
            "reporting_staff_member_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_packet_item_reporting_staff",
        "incident_packet_items",
        "staff_members",
        ["reporting_staff_member_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_packet_items_global_template",
        "incident_packet_items",
        ["incident_id", "form_template_id"],
        unique=True,
        postgresql_where=sa.text("reporting_staff_member_id IS NULL"),
    )
    op.create_index(
        "uq_packet_items_officer_template",
        "incident_packet_items",
        ["incident_id", "form_template_id", "reporting_staff_member_id"],
        unique=True,
        postgresql_where=sa.text("reporting_staff_member_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_packet_items_officer_template",
        table_name="incident_packet_items",
    )
    op.drop_index(
        "uq_packet_items_global_template",
        table_name="incident_packet_items",
    )
    op.drop_constraint(
        "fk_packet_item_reporting_staff",
        "incident_packet_items",
        type_="foreignkey",
    )
    op.drop_column("incident_packet_items", "reporting_staff_member_id")
    op.create_unique_constraint(
        "uq_incident_packet_items_incident_template",
        "incident_packet_items",
        ["incident_id", "form_template_id"],
    )
