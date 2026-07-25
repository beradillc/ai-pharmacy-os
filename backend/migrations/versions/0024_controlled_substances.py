"""controlled_substances — danh mục dược chất kiểm soát đặc biệt (TT18 PL I/II/III)

Bảng tham chiếu dùng chung (không tenant-scoped), nguồn TT 18/2026/TT-BYT Phụ lục I/II/III
kèm ngưỡng nồng độ/hàm lượng Phụ lục IV/V/VI. Xem docs/13_COMPLIANCE_SPEC.md mục C.1.

Dữ liệu nạp bằng ``python -m seeds.run`` (idempotent, có nhánh cập nhật khi văn bản đổi).

Revision ID: 0024_controlled_substances
Revises: 0023_audit_action_width
Create Date: 2026-07-25 04:15:12.742702+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_controlled_substances"
down_revision: str | None = "0023_audit_action_width"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "controlled_substances",
        sa.Column("name_intl", sa.String(length=128), nullable=False),
        sa.Column("common_name", sa.String(length=128), nullable=True),
        sa.Column("scientific_name", sa.Text(), nullable=False),
        sa.Column("appendix", sa.String(length=8), nullable=False),
        sa.Column("limit_per_unit_mg", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("limit_concentration_pct", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("limit_note", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_intl", name="uq_controlled_substances_name_intl"),
    )


def downgrade() -> None:
    op.drop_table("controlled_substances")
