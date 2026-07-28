"""encrypt_customer_national_id — đổi tên + mã hoá số CCCD (audit B-06)

Hai việc, và cả hai đều cần thiết:

1. ``customers.national_id_hash`` → ``customers.national_id``. Cột chưa từng băm gì —
   client gửi gì lưu nấy. **Cái tên là một nửa của lỗi**: nó phát ra một bảo đảm sai
   cho mọi người đọc lược đồ, viết DPIA, hoặc trả lời thanh tra.
2. ``varchar(128)`` → ``text`` để chứa ciphertext (cùng lý do đã ghi ở ``0030``).

**Vì sao mã hoá chứ không thật sự băm:** số định danh phải **đọc lại được** — nó đi vào
biên bản nhận lại thuốc và các biểu mẫu có giá trị pháp lý. Băm xong thì không in ra
biểu mẫu được nữa.

Hướng đi được quyết bởi **tiền lệ nội bộ**, không phải sở thích: ``compliance`` đã mã
hoá ``drug_return_records.returner_id_number`` từ trước. Cùng một loại dữ liệu, hai
module không được đối xử khác nhau.

Migration này **không** mã hoá dữ liệu sẵn có — đó là việc của ``seeds.encrypt_backfill``
(migration chạy không có ngữ cảnh ứng dụng nên không có khoá). Trình tự: `docs/18` §B.3.

Revision ID: 0036_encrypt_national_id
Revises: 0035_encrypt_customer_name
Create Date: 2026-07-28 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_encrypt_national_id"
down_revision: str | None = "0035_encrypt_customer_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "customers",
        "national_id_hash",
        new_column_name="national_id",
        existing_type=sa.String(length=128),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Chỉ an toàn khi dữ liệu đã được giải mã lại về dạng rõ. Ciphertext dài hơn 128 ký
    # tự sẽ làm lệnh này nổ — và nổ là đúng: cắt cụt ciphertext là mất dữ liệu.
    op.alter_column(
        "customers",
        "national_id",
        new_column_name="national_id_hash",
        existing_type=sa.Text(),
        type_=sa.String(length=128),
        existing_nullable=True,
    )
