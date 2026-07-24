"""audit_logs_target_type_index

Adds the (tenant_id, target_type, occurred_at) index the audit dashboard's entity
filter reads: "everything that happened to this kind of object", newest first. The
existing (tenant_id, occurred_at) and (tenant_id, actor_user_id) indexes cover the
window and actor dimensions but not target_type.

Revision ID: 0020_audit_target_type_idx
Revises: 0019_outbox_retention_idx
Create Date: 2026-07-24 17:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020_audit_target_type_idx"
down_revision: str | None = "0019_outbox_retention_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_logs_tenant_target_type",
        "audit_logs",
        ["tenant_id", "target_type", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_target_type", table_name="audit_logs")
