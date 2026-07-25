"""iam_two_factor — 2FA cho vai trò nhạy cảm (Sprint 8, docs/features/2fa-vai-tro-nhay-cam)

Ba bảng vận hành, không cái nào là bảng audit:

- ``user_two_factor``: tối đa 1 dòng/user. "Tắt 2FA" là **không có dòng**, không phải
  cờ tắt — disable xoá hẳn, không để lại secret chết trong CSDL.
- ``two_factor_backup_codes``: mã dự phòng dùng 1 lần, lưu hash SHA-256, dòng đã dùng
  **giữ lại** (đánh dấu ``used_at``) làm dấu vết.
- ``two_factor_challenges``: đăng nhập đã qua mật khẩu, còn nợ bước 2. Bản ghi mờ
  (opaque token, hash SHA-256) — cố ý không phải JWT ngắn hạn, xem lý do trong
  ``iam/infrastructure/models.py`` (``TwoFactorChallengeORM``).

Revision ID: 0028_iam_two_factor
Revises: 0027_national_sync_retry_tasks
Create Date: 2026-07-25 17:23:07.066195+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_iam_two_factor"
down_revision: str | None = "0027_national_sync_retry_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "two_factor_challenges",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_two_factor_challenges_user_id"),
        "two_factor_challenges",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "user_two_factor",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_timestep", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_user_two_factor_tenant_id"), "user_two_factor", ["tenant_id"], unique=False
    )
    op.create_table(
        "two_factor_backup_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("two_factor_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["two_factor_id"], ["user_two_factor.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_two_factor_backup_codes_two_factor_id"),
        "two_factor_backup_codes",
        ["two_factor_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_two_factor_backup_codes_two_factor_id"), table_name="two_factor_backup_codes"
    )
    op.drop_table("two_factor_backup_codes")
    op.drop_index(op.f("ix_user_two_factor_tenant_id"), table_name="user_two_factor")
    op.drop_table("user_two_factor")
    op.drop_index(op.f("ix_two_factor_challenges_user_id"), table_name="two_factor_challenges")
    op.drop_table("two_factor_challenges")
