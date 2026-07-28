"""purchase_order_code

Gives every purchase order a number a human can say out loud (docs/19 khe hở G-2).

Before this, ``PurchaseOrderResponse`` carried only a UUID. The approved Sprint 9
design prints *"Đã tạo đơn mua nháp #PO-0412"* — a string that did not exist anywhere
in the system. The two ways to "fix" that without a migration were both worse: print
the UUID (unreadable over a phone) or print its first 8 characters (a thing that looks
like an order number, is not one, and collides).

Counter design, read before changing it: ``purchase_order_counters`` holds one row per
tenant rather than a database ``SEQUENCE``, because sequences are global to the database
and this number is per tenant — two pharmacies each start at PO-0001. Allocation is a
single ``UPDATE … RETURNING`` so the row lock is held by the statement itself; see
``SqlAlchemyPurchaseOrderRepository.next_code`` and the F-5 precedent (audit B-01).

Backfill runs in Python, not one clever SQL statement, so it behaves identically on
Postgres and on the SQLite the test suite builds its schema with (``UPDATE … FROM`` and
``LPAD`` are not portable). Existing orders are numbered per tenant in creation order,
which means an installation's oldest PO becomes PO-0001 — the numbering a human would
have used had it existed from the start.

Revision ID: 0034_purchase_order_code
Revises: 0033_movement_ref_batch_uq
Create Date: 2026-07-28 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_purchase_order_code"
down_revision: str | None = "0033_movement_ref_batch_uq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CODE_DIGITS = 4


def upgrade() -> None:
    op.create_table(
        "purchase_order_counters",
        sa.Column("tenant_id", sa.Uuid(), primary_key=True),
        sa.Column("last_value", sa.Integer(), nullable=False),
    )

    # Nullable first: the column has to exist before it can be filled, and existing
    # rows have no code yet.
    op.add_column("purchase_orders", sa.Column("code", sa.String(length=24), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, tenant_id FROM purchase_orders ORDER BY tenant_id, created_at, id")
    ).fetchall()

    counters: dict[object, int] = {}
    for row in rows:
        counters[row.tenant_id] = counters.get(row.tenant_id, 0) + 1
        bind.execute(
            sa.text("UPDATE purchase_orders SET code = :code WHERE id = :id"),
            {"code": f"PO-{counters[row.tenant_id]:0{_CODE_DIGITS}d}", "id": row.id},
        )

    for tenant_id, last_value in counters.items():
        bind.execute(
            sa.text(
                "INSERT INTO purchase_order_counters (tenant_id, last_value) "
                "VALUES (:tenant_id, :last_value)"
            ),
            {"tenant_id": tenant_id, "last_value": last_value},
        )

    # Only now can the column be required: every row has a value.
    with op.batch_alter_table("purchase_orders") as batch:
        batch.alter_column("code", existing_type=sa.String(length=24), nullable=False)
        batch.create_unique_constraint("uq_po_tenant_code", ["tenant_id", "code"])


def downgrade() -> None:
    with op.batch_alter_table("purchase_orders") as batch:
        batch.drop_constraint("uq_po_tenant_code", type_="unique")
        batch.drop_column("code")
    op.drop_table("purchase_order_counters")
