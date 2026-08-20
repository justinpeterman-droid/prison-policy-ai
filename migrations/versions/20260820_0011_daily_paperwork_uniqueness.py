"""Prevent duplicate daily paperwork for one kind, date, and shift.

Revision ID: 20260820_0011
Revises: 20260819_0010
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260820_0011"
down_revision: Union[str, None] = "20260819_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_paperwork_records_daily_date_shift",
        "paperwork_records",
        ["kind", "work_date", "shift"],
        unique=True,
        postgresql_where=sa.text("kind <> 'count_sheet'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_paperwork_records_daily_date_shift",
        table_name="paperwork_records",
    )
