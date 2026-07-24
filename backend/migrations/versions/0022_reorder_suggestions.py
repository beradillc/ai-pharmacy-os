"""reorder_suggestions

Revision ID: 0022_reorder_suggestions
Revises: 0021_sales_order_sold_by
Create Date: 2026-07-25 06:13:55.604925+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_reorder_suggestions"
down_revision: str | None = "0021_sales_order_sold_by"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reorder_suggestions",
        sa.Column("drug_id", sa.Uuid(), nullable=False),
        sa.Column("avg_daily_velocity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("reorder_point", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("on_hand_at_calc", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("suggested_qty", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("po_id", sa.Uuid(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reorder_suggestions_branch_id"), "reorder_suggestions", ["branch_id"], unique=False
    )
    op.create_index(
        op.f("ix_reorder_suggestions_drug_id"), "reorder_suggestions", ["drug_id"], unique=False
    )
    op.create_index(
        op.f("ix_reorder_suggestions_status"), "reorder_suggestions", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_reorder_suggestions_tenant_id"), "reorder_suggestions", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reorder_suggestions_tenant_id"), table_name="reorder_suggestions")
    op.drop_index(op.f("ix_reorder_suggestions_status"), table_name="reorder_suggestions")
    op.drop_index(op.f("ix_reorder_suggestions_drug_id"), table_name="reorder_suggestions")
    op.drop_index(op.f("ix_reorder_suggestions_branch_id"), table_name="reorder_suggestions")
    op.drop_table("reorder_suggestions")
