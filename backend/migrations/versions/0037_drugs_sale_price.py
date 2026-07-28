"""0037_drugs_sale_price — giá bán lẻ cho mặt hàng (Sprint 10, D10)

Vì sao cột này tồn tại: màn bán hàng trước đây hỏi giá bằng ``window.prompt`` cho
TỪNG dòng, vì backend không có chỗ nào giữ giá bán — catalog chỉ biết mô tả thuốc,
còn ``product_batches.cost_price`` là giá **vốn** của một lô nhập. Thu ngân gõ tay
giá Paracetamol mỗi lần bán không phải là một chi tiết giao diện; đó là một khoảng
trống dữ liệu, và nó nằm đúng giữa luồng dùng nhiều nhất của cả sản phẩm.

Nullable, và sẽ mãi nullable: nhà thuốc nhập danh mục từ nhà phân phối trước rồi
chốt giá sau, nên một thuốc chưa có giá phải nhập được. Nơi bán hàng đọc cột này để
**điền sẵn**, không phải để khoá — thu ngân vẫn sửa từng dòng (khuyến mãi, giá lẻ).

``Numeric(18,2)`` — cùng độ rộng mọi cột tiền khác trong hệ thống (PROJECT_STATE
§7aq đã rà một lượt độ rộng cột; đừng mở một hình dạng tiền thứ hai).

Không backfill: mọi thuốc đang có sẽ mang ``NULL`` cho tới khi ai đó đặt giá. Đoán
một con số hộ nhà thuốc là việc migration không được phép làm.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_drugs_sale_price"
down_revision: str | None = "0036_encrypt_national_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "drugs", sa.Column("sale_price", sa.Numeric(precision=18, scale=2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("drugs", "sale_price")
