"""sale_payment_gateway_ref

Revision ID: 0032_sale_payment_gateway_ref
Revises: 0031_encrypt_crm_pii
Create Date: 2026-07-26 12:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_sale_payment_gateway_ref"
down_revision: str | None = "0031_encrypt_crm_pii"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable + unique: cash/card payments (the overwhelming majority) leave it
    # NULL forever, and standard SQL never treats two NULLs as a duplicate — only
    # a repeated real gateway transaction id collides. That collision is the
    # idempotency guard mục 4/4 (payment_vnpay) relies on for its webhook.
    op.add_column("sale_payments", sa.Column("gateway_ref", sa.String(length=64), nullable=True))
    op.create_unique_constraint(
        op.f("uq_sale_payments_gateway_ref"), "sale_payments", ["gateway_ref"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_sale_payments_gateway_ref"), "sale_payments", type_="unique")
    op.drop_column("sale_payments", "gateway_ref")
