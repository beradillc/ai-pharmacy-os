"""movement_ref_batch_unique

Makes "the same sale/GRN moves stock exactly once" a property of the database
rather than a hope about timing (audit B-02, patched in F-5).

``InventoryService`` guarded replays with ``exists_for_ref`` — a SELECT, then a
write, with nothing holding the gap. Two at-least-once deliveries of one sale
both read "not dispensed yet" and both dispensed it; the audit reproduced 16
units leaving a batch that had received 10.

Scope of the key, read before changing it: ``(tenant_id, ref_type, ref_id,
batch_id)``. ``batch_id`` is load-bearing — a single FEFO dispense legitimately
spans several lots and writes one row per lot under one ``ref_id``, so a key
without it would reject correct pharmacy work. Partial on ``ref_id IS NOT NULL``:
a movement with no reference has no identity to be a duplicate of.

Revision ID: 0033_movement_ref_batch_uq
Revises: 0032_sale_payment_gateway_ref
Create Date: 2026-07-27 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_movement_ref_batch_uq"
down_revision: str | None = "0032_sale_payment_gateway_ref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Creating this on an installation that already double-dispensed will fail here
    # rather than silently keep the duplicates. That is the intended outcome: the
    # rows have to be reconciled by a human — the stock really did leave twice —
    # and the query that finds them is
    #   SELECT tenant_id, ref_type, ref_id, batch_id, count(*)
    #     FROM stock_movements WHERE ref_id IS NOT NULL
    #    GROUP BY 1,2,3,4 HAVING count(*) > 1;
    op.create_index(
        "uq_movement_ref_batch",
        "stock_movements",
        ["tenant_id", "ref_type", "ref_id", "batch_id"],
        unique=True,
        postgresql_where=sa.text("ref_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_movement_ref_batch", table_name="stock_movements")
