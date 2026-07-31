"""kiem ke theo o — chenh lech cho duyet (BERAS V2 Phase 11)

Hai bảng MỚI, không đụng bảng nào đang chạy: `stock_counts` + `stock_count_lines`.

🔴 Vì sao không mở rộng `stock_reconciliation_needed`: bảng đó có `grn_id` NOT NULL — nó là
cờ cho một phiếu nhập không trọn vẹn, không phải bản ghi sai lệch tổng quát. Nới thành
nullable là đổi lược đồ của một thứ đang chạy và đang có test.

Lùi được trọn vẹn: `downgrade` chỉ xoá đúng hai bảng vừa tạo, không có dữ liệu nào của
bảng khác phụ thuộc vào chúng.

Revision ID: 0045_stock_counts
Revises: 0044_rx_created_by
Create Date: 2026-07-31 16:40:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045_stock_counts"
down_revision: str | None = "0044_rx_created_by"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_counts",
        sa.Column("location_id", sa.Uuid(), nullable=False),
        # varchar chứ không enum CSDL: thêm trạng thái về sau cần `ALTER TYPE` trên Postgres
        # mà SQLite không có, và bộ test chạy cả hai nền (kỷ luật #7 bổ sung).
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("counted_by", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        # 🔴 `server_default` BẮT BUỘC, không phải trang trí. `TimestampMixin` khai
        # `server_default=func.now()`; bản đầu của migration này bỏ sót nó và Postgres từ
        # chối INSERT với NotNullViolation — trong khi **1439 test SQLite xanh hết**, vì
        # `create_all` dựng bảng thẳng từ ORM nên ở đó server_default luôn có mặt.
        # Chỉ cổng trình duyệt chạy trên Postgres thật mới bắt được (kỷ luật #7 bổ sung).
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
        "ix_stock_counts_branch_status", "stock_counts", ["branch_id", "status"], unique=False
    )
    op.create_index(op.f("ix_stock_counts_branch_id"), "stock_counts", ["branch_id"], unique=False)
    op.create_index(op.f("ix_stock_counts_tenant_id"), "stock_counts", ["tenant_id"], unique=False)

    op.create_table(
        "stock_count_lines",
        sa.Column("count_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("counted_qty", sa.Numeric(precision=18, scale=3), nullable=False),
        # NULLABLE có chủ ý: chỉ có nghĩa sau khi nộp. Để 0 khi chưa chốt sẽ đọc y hệt
        # "đã chốt và khớp" — một tín hiệu chứng minh mệnh đề khác với mệnh đề người đọc
        # tưởng nó chứng minh (kỷ luật #14).
        sa.Column("system_qty", sa.Numeric(precision=18, scale=3), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("count_id", "batch_id", name="uq_count_line_batch"),
    )
    op.create_index("ix_stock_count_lines_count", "stock_count_lines", ["count_id"], unique=False)
    op.create_index(
        op.f("ix_stock_count_lines_branch_id"), "stock_count_lines", ["branch_id"], unique=False
    )
    op.create_index(
        op.f("ix_stock_count_lines_tenant_id"), "stock_count_lines", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_stock_count_lines_count", table_name="stock_count_lines")
    op.drop_index(op.f("ix_stock_count_lines_branch_id"), table_name="stock_count_lines")
    op.drop_index(op.f("ix_stock_count_lines_tenant_id"), table_name="stock_count_lines")
    op.drop_table("stock_count_lines")

    op.drop_index("ix_stock_counts_branch_status", table_name="stock_counts")
    op.drop_index(op.f("ix_stock_counts_branch_id"), table_name="stock_counts")
    op.drop_index(op.f("ix_stock_counts_tenant_id"), table_name="stock_counts")
    op.drop_table("stock_counts")
