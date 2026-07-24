"""audit_logs: nhật ký truy vết append-only

Revision ID: 0014_audit_logs
Revises: 0013_iam
Create Date: 2026-07-23 05:44:46.036265+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_audit_logs"
down_revision: str | None = "0013_iam"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "context",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_tenant_actor", "audit_logs", ["tenant_id", "actor_user_id"], unique=False
    )
    op.create_index(
        "ix_audit_logs_tenant_occurred", "audit_logs", ["tenant_id", "occurred_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_occurred", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_actor", table_name="audit_logs")
    op.drop_table("audit_logs")
