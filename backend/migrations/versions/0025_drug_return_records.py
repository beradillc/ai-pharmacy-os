"""drug_return_records + drug_return_items — biên bản nhận lại thuốc (TT18 Phụ lục XVIII)

Bước 4/6 mạch TT18, docs/13_COMPLIANCE_SPEC.md mục C.6 — TT18 Điều 6.2 + Điều 12.1.d. Immutable
theo domain rule (chỉ INSERT); ``drug_return_items`` là bảng con 1-nhiều, xóa theo cascade khi
xóa bản ghi cha (không xảy ra trong vận hành bình thường — chỉ để toàn vẹn tham chiếu).

Revision ID: 0025_drug_return_records
Revises: 0024_controlled_substances
Create Date: 2026-07-25 07:10:23.739760+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_drug_return_records"
down_revision: str | None = "0024_controlled_substances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drug_return_records",
        sa.Column("returner_name", sa.String(length=255), nullable=False),
        sa.Column("returner_address", sa.String(length=500), nullable=False),
        sa.Column("returner_id_number", sa.String(length=32), nullable=False),
        sa.Column("returner_id_issuer", sa.String(length=255), nullable=False),
        sa.Column("returner_id_issued_at", sa.Date(), nullable=False),
        sa.Column("returner_is_patient", sa.Boolean(), nullable=False),
        sa.Column("receiving_pharmacist_name", sa.String(length=255), nullable=False),
        sa.Column("handover_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("handover_location", sa.String(length=500), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_drug_return_records_branch_id"), "drug_return_records", ["branch_id"], unique=False
    )
    op.create_index(
        op.f("ix_drug_return_records_tenant_id"), "drug_return_records", ["tenant_id"], unique=False
    )
    op.create_table(
        "drug_return_items",
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("lot_no", sa.String(length=64), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("condition_note", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["drug_return_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_drug_return_items_record_id"), "drug_return_items", ["record_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_drug_return_items_record_id"), table_name="drug_return_items")
    op.drop_table("drug_return_items")
    op.drop_index(op.f("ix_drug_return_records_tenant_id"), table_name="drug_return_records")
    op.drop_index(op.f("ix_drug_return_records_branch_id"), table_name="drug_return_records")
    op.drop_table("drug_return_records")
