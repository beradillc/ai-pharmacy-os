"""encrypt_two_factor_secret — nới cột cho ciphertext (Sprint 8 mục 3/4)

Chỉ **nới độ rộng cột**, không đụng dữ liệu. Mã hoá là việc của tầng ứng dụng
(``core.db.encrypted_types.EncryptedString``); phía CSDL vẫn chỉ là ``varchar``, nên
migration này cố ý dùng ``sa.String`` chứ không phải kiểu tuỳ biến — Alembic tự sinh ra
tham chiếu ``pharmacy_os.core.db.encrypted_types...`` mà **không import**, chạy sẽ
``NameError``; và gắn kiểu của tầng ứng dụng vào lịch sử migration là buộc migration cũ
phụ thuộc code mới mãi mãi.

**Vì sao 512 cho một bí mật 32 ký tự:** dạng lưu là ``v{n}:base64(nonce||ct||tag)`` ≈ 83
ký tự. Thiếu chỗ sẽ là ``StringDataRightTruncation`` (500) trên Postgres mà SQLite không
tái hiện — đúng loại lỗi PROJECT_STATE §7ap/§7aq. Dư chỗ không tốn gì: Postgres
``varchar(n)`` chỉ lưu đúng số ký tự thực có.

**Downgrade có rủi ro, ghi rõ:** thu về ``varchar(64)`` sẽ **thất bại** (chứ không cắt
cụt âm thầm) nếu đã có ciphertext trong cột — Postgres từ chối khi dữ liệu không vừa.
Đó là hành vi ĐÚNG: muốn lùi thật thì phải giải mã về bản rõ **trước**, không được để
migration tự ý làm mất dữ liệu.

Revision ID: 0029_encrypt_two_factor_secret
Revises: 0028_iam_two_factor
Create Date: 2026-07-26 00:30:26.415589+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_encrypt_two_factor_secret"
down_revision: str | None = "0028_iam_two_factor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "user_two_factor",
        "secret",
        existing_type=sa.String(length=64),
        type_=sa.String(length=512),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user_two_factor",
        "secret",
        existing_type=sa.String(length=512),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
