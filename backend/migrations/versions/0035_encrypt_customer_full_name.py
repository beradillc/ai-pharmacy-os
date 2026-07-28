"""encrypt_customer_full_name — tên khách hàng sang ciphertext (Chain quyết 2026-07-28)

Đóng nợ cuối cùng của mã hoá at-rest CRM. Migration ``0031`` cố ý **bỏ lại** cột này và
ghi rõ lý do: ``list()`` đang ``ORDER BY full_name``, mà ciphertext sắp xếp ngẫu nhiên và
blind index không cứu được (fingerprint giữ *đẳng thức*, không giữ *thứ tự*). Đó là một
đánh đổi nghiệp vụ, không phải câu hỏi kỹ thuật, nên nó được đưa lên cho Chain.

**Chain chọn: mã hoá, chấp nhận bỏ sắp xếp theo bảng chữ cái** (28/07). Hai lý do:
nhà thuốc tra khách bằng **số điện thoại** nhiều hơn bằng tên — mà đường đó không mất gì
vì ``phone_fingerprint`` vẫn trả lời được tra cứu chính xác; và tên bệnh nhân dạng rõ
**đi theo mọi bản dump ra ngoài cơ sở**, nơi Luật BVDLCN 91/2025 áp dụng còn sự tiện lợi
khi sắp xếp thì không.

``list()`` nay sắp theo ``created_at DESC, id`` — xem docstring ở
``SqlAlchemyCustomerRepository.list``.

**Migration này KHÔNG mã hoá dữ liệu sẵn có**, giống hệt ``0030``/``0031``: nó chỉ nới
kiểu cột để chứa được ciphertext. Việc mã hoá dòng cũ do ``seeds.encrypt_backfill`` làm —
migration chạy không có ngữ cảnh ứng dụng nên **không có khoá**, về mặt vật lý không mã
hoá được gì. Trình tự đầy đủ: `docs/18` §B.3.

``varchar(255)`` → ``text``: cùng lý do đã ghi ở ``0030`` — đoán một độ rộng varchar mới
là cách tự đặt một quả mìn tràn cột, còn ``text`` thì không có độ rộng để đoán sai.

Revision ID: 0035_encrypt_customer_name
Revises: 0034_purchase_order_code
Create Date: 2026-07-28 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_encrypt_customer_name"
down_revision: str | None = "0034_purchase_order_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "customers",
        "full_name",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # 🔴 Hạ cấp CHỈ an toàn khi dữ liệu đã được giải mã lại về dạng rõ trước đó. Một
    # ciphertext dài hơn 255 ký tự sẽ làm lệnh này nổ — và nổ là đúng: cắt cụt ciphertext
    # là mất dữ liệu vĩnh viễn, không phải một lần hạ cấp.
    op.alter_column(
        "customers",
        "full_name",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
