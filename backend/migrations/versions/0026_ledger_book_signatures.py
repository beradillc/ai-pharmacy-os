"""ledger_book_signatures — ký xác nhận điện tử sổ kiểm soát đặc biệt (TT18 Điều 15.1.d)

Bước 6/6 mạch TT18, docs/13_COMPLIANCE_SPEC.md mục C.5, hướng A. Không dùng
``TenantScopedMixin``/``TimestampMixin`` — khai tay ``tenant_id`` để đặt trong unique constraint
cùng ``book_type``/``book_date`` (chặn ký lại ở tầng CSDL, không chỉ tầng service); ``signed_at``
đã là mốc thời gian nghiệp vụ nên không cần thêm ``created_at``/``updated_at``. Không có
``branch_id``/``drug_id`` — sổ là hồ sơ theo cơ sở (tenant), phạm vi cả sổ trong ngày (mọi thuốc),
xem docs/features/tt18-kiem-soat-dac-biet/02_DECISIONS_KY_SO.md Bước 2.

Revision ID: 0026_ledger_book_signatures
Revises: 0025_drug_return_records
Create Date: 2026-07-25 08:36:14.396857+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_ledger_book_signatures"
down_revision: str | None = "0025_drug_return_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ledger_book_signatures",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("book_type", sa.String(length=8), nullable=False),
        sa.Column("book_date", sa.Date(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=True),
        sa.Column("signed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "book_type", "book_date", name="uq_ledger_book_signatures_day"
        ),
    )
    op.create_index(
        op.f("ix_ledger_book_signatures_tenant_id"),
        "ledger_book_signatures",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ledger_book_signatures_tenant_id"), table_name="ledger_book_signatures")
    op.drop_table("ledger_book_signatures")
