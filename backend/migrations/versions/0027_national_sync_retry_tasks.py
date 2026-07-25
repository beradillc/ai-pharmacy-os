"""national_sync_retry_tasks — hàng đợi gửi lại liên thông CSDL Dược (docs/13 mục D.4)

Bảng **vận hành**, không phải bảng audit: chỗ duy nhất giữ payload thô để gửi lại được đúng
nội dung cũ, và chỉ giữ tới khi cổng ACK (dòng bị xoá) hoặc hết lượt thử (``DEAD``).
``national_sync_logs`` (mục D.2) không đổi — vẫn chỉ ``payload_hash``.

Không FK sang ``national_sync_logs`` (cùng lý do ``event_outbox`` không có FK: hàng đợi giao
vận không ràng vòng đời vào bảng nó nhắc tới). ``uq_..._client_uuid`` trùng khóa idempotency
của log ⇒ 1 bản ghi cần gửi = tối đa 1 việc gửi lại. ``ix_..._due`` phục vụ đúng truy vấn
nóng của relay: "việc PENDING đã tới hạn".

Revision ID: 0027_national_sync_retry_tasks
Revises: 0026_ledger_book_signatures
Create Date: 2026-07-25 12:59:53.768978+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_national_sync_retry_tasks"
down_revision: str | None = "0026_ledger_book_signatures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "national_sync_retry_tasks",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("sync_log_id", sa.Uuid(), nullable=False),
        sa.Column("payload_type", sa.String(length=16), nullable=False),
        sa.Column("client_uuid", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.UniqueConstraint(
            "tenant_id", "client_uuid", name="uq_national_sync_retry_tasks_client_uuid"
        ),
    )
    op.create_index(
        "ix_national_sync_retry_tasks_due",
        "national_sync_retry_tasks",
        ["status", "next_attempt_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_national_sync_retry_tasks_tenant_id"),
        "national_sync_retry_tasks",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_national_sync_retry_tasks_tenant_id"), table_name="national_sync_retry_tasks"
    )
    op.drop_index("ix_national_sync_retry_tasks_due", table_name="national_sync_retry_tasks")
    op.drop_table("national_sync_retry_tasks")
