"""Add official incident identity and paperwork packet persistence.

Revision ID: 20260818_0007
Revises: 20260818_0006
Create Date: 2026-08-19
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260818_0007"
down_revision: str | None = "20260818_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


OUTPUT_KIND_CHECK = "output_kind IN ('digital_document','physical_only')"
PACKET_GROUP_CHECK = "packet_group IN ('required','recommended','additional')"
PACKET_STATE_CHECK = "packet_state IN ('selected','not_applicable','removed')"
COMPLETENESS_CHECK = (
    "completeness IN ('ready','needs_review','missing_information')"
)
DOCUMENT_ACTION_CHECK = (
    "action IN ('preview','print','download_word','download_pdf','copy_text')"
)


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("incident_number", sa.String(length=11), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("incident_name", sa.String(length=160), nullable=True),
    )
    op.create_index(
        "uq_incidents_incident_number",
        "incidents",
        ["incident_number"],
        unique=True,
        postgresql_where=sa.text("incident_number IS NOT NULL"),
    )

    op.create_table(
        "form_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("output_kind", sa.String(length=32), nullable=False),
        sa.Column("revision_label", sa.String(length=120), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "definition",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
        sa.UniqueConstraint("code", name="uq_form_templates_code"),
        sa.CheckConstraint(
            OUTPUT_KIND_CHECK,
            name="ck_form_templates_output_kind",
        ),
    )
    op.create_index(
        "ix_form_templates_active_category",
        "form_templates",
        ["active", "category", "code"],
    )

    op.create_table(
        "incident_packet_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "form_template_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("packet_group", sa.String(length=16), nullable=False),
        sa.Column(
            "packet_state",
            sa.String(length=24),
            nullable=False,
            server_default="selected",
        ),
        sa.Column(
            "source_incident_revision_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("selection_reason", sa.String(length=240), nullable=True),
        sa.Column(
            "not_applicable_reason",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "added_by_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
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
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
            name="fk_incident_packet_items_incident_id_incidents",
        ),
        sa.ForeignKeyConstraint(
            ["form_template_id"],
            ["form_templates.id"],
            ondelete="RESTRICT",
            name="fk_incident_packet_items_form_template_id_form_templates",
        ),
        sa.ForeignKeyConstraint(
            ["added_by_account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
            name="fk_incident_packet_items_added_by_account_id_accounts",
        ),
        sa.UniqueConstraint(
            "incident_id",
            "form_template_id",
            name="uq_incident_packet_items_incident_template",
        ),
        sa.CheckConstraint(
            PACKET_GROUP_CHECK,
            name="ck_incident_packet_items_packet_group",
        ),
        sa.CheckConstraint(
            PACKET_STATE_CHECK,
            name="ck_incident_packet_items_packet_state",
        ),
        sa.CheckConstraint(
            "source_incident_revision_number >= 0",
            name="ck_incident_packet_items_source_revision_nonnegative",
        ),
    )
    op.create_index(
        "ix_incident_packet_items_incident_group",
        "incident_packet_items",
        ["incident_id", "packet_group", "packet_state", "id"],
    )

    op.create_table(
        "form_instances",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "packet_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_incident_revision_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "populated_fields",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "manual_fields",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "completeness",
            sa.String(length=32),
            nullable=False,
            server_default="missing_information",
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
            ["packet_item_id"],
            ["incident_packet_items.id"],
            ondelete="CASCADE",
            name="fk_form_instances_packet_item_id_incident_packet_items",
        ),
        sa.UniqueConstraint(
            "packet_item_id",
            name="uq_form_instances_packet_item_id",
        ),
        sa.CheckConstraint(
            "source_incident_revision_number >= 0",
            name="ck_form_instances_source_revision_nonnegative",
        ),
        sa.CheckConstraint(
            COMPLETENESS_CHECK,
            name="ck_form_instances_completeness",
        ),
    )

    op.create_table(
        "physical_paperwork_acknowledgments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "packet_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "acknowledged_by_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "acknowledged_by_staff_member_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["packet_item_id"],
            ["incident_packet_items.id"],
            ondelete="CASCADE",
            name="fk_physical_ack_packet_item",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name="fk_physical_ack_account",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_staff_member_id"],
            ["staff_members.id"],
            ondelete="RESTRICT",
            name="fk_physical_ack_staff_member",
        ),
        sa.UniqueConstraint(
            "packet_item_id",
            name="uq_physical_paperwork_acknowledgments_packet_item_id",
        ),
    )

    op.create_table(
        "document_action_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "packet_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "actor_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "actor_staff_member_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("incident_revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
            name="fk_document_action_events_incident_id_incidents",
        ),
        sa.ForeignKeyConstraint(
            ["packet_item_id"],
            ["incident_packet_items.id"],
            ondelete="SET NULL",
            name=(
                "fk_document_action_events_packet_item_id_"
                "incident_packet_items"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            ondelete="SET NULL",
            name="fk_document_action_events_report_id_reports",
        ),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name="fk_document_action_events_actor_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["actor_staff_member_id"],
            ["staff_members.id"],
            ondelete="RESTRICT",
            name=(
                "fk_document_action_events_actor_staff_member_id_"
                "staff_members"
            ),
        ),
        sa.CheckConstraint(
            DOCUMENT_ACTION_CHECK,
            name="ck_document_action_events_action",
        ),
        sa.CheckConstraint(
            "incident_revision_number >= 0",
            name="ck_document_action_events_incident_revision_nonnegative",
        ),
    )
    op.create_index(
        "ix_document_action_events_incident_created",
        "document_action_events",
        ["incident_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_action_events_incident_created",
        table_name="document_action_events",
    )
    op.drop_table("document_action_events")
    op.drop_table("physical_paperwork_acknowledgments")
    op.drop_table("form_instances")
    op.drop_index(
        "ix_incident_packet_items_incident_group",
        table_name="incident_packet_items",
    )
    op.drop_table("incident_packet_items")
    op.drop_index(
        "ix_form_templates_active_category",
        table_name="form_templates",
    )
    op.drop_table("form_templates")
    op.drop_index(
        "uq_incidents_incident_number",
        table_name="incidents",
    )
    op.drop_column("incidents", "incident_name")
    op.drop_column("incidents", "incident_number")
