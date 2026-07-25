"""audit_logs.action varchar(32) -> varchar(64)

Three ``AuditAction`` values are longer than 32 characters
(``CUSTOMER_MEDICATION_HISTORY_RECORDED`` 36, ``INVENTORY_RECONCILIATION_RESOLVED`` 33,
``ANALYTICS_SUGGESTION_MATERIALIZED`` 33). On Postgres those inserts fail with
``StringDataRightTruncationError`` and take the whole request down with a 500; SQLite
ignores declared string lengths, which is why the test suite never saw it. Widened to
64 to match ``target_type``/``target_id``. ``tests/unit/test_audit_entry.py`` now guards
the invariant so a new long action name fails a test instead of production.

Revision ID: 0023_audit_action_width
Revises: 0022_reorder_suggestions
Create Date: 2026-07-25 09:40:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_audit_action_width"
down_revision: str | None = "0022_reorder_suggestions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "audit_logs",
        "action",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Audit rows are append-only, so a row written with a >32-char action after the
    # upgrade would block this narrowing. Drop nothing: fail loudly instead of
    # truncating a compliance trail.
    op.alter_column(
        "audit_logs",
        "action",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
