"""customer_consents + customers.anonymised_at

Revision ID: 0015_customer_consents
Revises: 0014_audit_logs
Create Date: 2026-07-23 06:51:29.367195+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_customer_consents"
down_revision: str | None = "0014_audit_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_consents",
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("terms_version", sa.String(length=32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_consents_customer_id"), "customer_consents", ["customer_id"], unique=False
    )
    op.add_column(
        "customers", sa.Column("anonymised_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("customers", "anonymised_at")
    op.drop_index(op.f("ix_customer_consents_customer_id"), table_name="customer_consents")
    op.drop_table("customer_consents")
