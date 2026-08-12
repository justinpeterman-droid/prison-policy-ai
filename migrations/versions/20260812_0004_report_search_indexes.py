"""Add bounded, reversible indexes for Admin structured report search.

Revision ID: 20260812_0004
Revises: 20260812_0003

Index-only expansion for the RP-05 Admin search surface: no schema or data
changes. `AdminReportFilters` (backend.reports.persistence) queries only
structured columns -- report/incident fields and structured
`extracted_facts` persons entries -- never the free-text narrative or field
notes, so the indexes here mirror exactly those columns.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0004"
down_revision = "20260812_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_incidents_extracted_facts_gin", "incidents", ["extracted_facts"],
        postgresql_using="gin", postgresql_ops={"extracted_facts": "jsonb_path_ops"},
    )
    op.create_index("ix_incidents_facility", "incidents", ["facility", "id"])
    op.create_index("ix_incidents_location", "incidents", ["location", "id"])
    op.create_index("ix_incidents_shift", "incidents", ["shift", "id"])
    op.create_index("ix_reports_created_at", "reports", ["created_at", "id"])
    op.create_index("ix_reports_updated_at", "reports", ["updated_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_reports_updated_at", table_name="reports")
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_incidents_shift", table_name="incidents")
    op.drop_index("ix_incidents_location", table_name="incidents")
    op.drop_index("ix_incidents_facility", table_name="incidents")
    op.drop_index("ix_incidents_extracted_facts_gin", table_name="incidents")
