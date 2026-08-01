"""thong tin co so: ten, dia chi, dien thoai, ma so thue theo tung tenant

UAT lỗi M-02 (2026-08-01). Trước đó bốn trường này là **biến môi trường toàn cục**
(``core.config.OrgSettings``) — nghĩa là mọi nhà thuốc dùng chung một bản triển khai đều
in ra cùng một tên trên hoá đơn, và không ai đổi được từ trong ứng dụng.

🔴 **Mở rộng bảng đã có, KHÔNG dựng bảng mới.** ``tenant_compliance_configs`` vốn giữ
*"mã cơ sở do Cục QLD cấp"* — bốn trường này nằm trên **cùng một tờ giấy chứng nhận đủ
điều kiện kinh doanh dược**. Dựng một bảng ``tenant_profile`` song song là chia đôi hồ sơ
pháp lý của cơ sở thành hai chỗ, và chỗ thứ hai sẽ lệch với chỗ thứ nhất.

Tất cả **nullable**: các tenant đang chạy chưa có dữ liệu này, và ép ``NOT NULL`` sẽ hoặc
làm migration hỏng hoặc buộc phải bịa một giá trị mặc định — mà một cái tên nhà thuốc bịa
ra rồi in lên hoá đơn thì tệ hơn hẳn một ô trống. Ứng dụng rơi về ``OrgSettings`` khi trống.

Revision ID: 0046_tenant_co_so
Revises: 0045_stock_counts
Create Date: 2026-08-01 13:32:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046_tenant_co_so"
down_revision: str | None = "0045_stock_counts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BANG = "tenant_compliance_configs"

#: Độ rộng bám đúng thực tế chứ không đặt bừa. Bài học varchar(32) của ``audit_logs.action``:
#: SQLite nuốt chuỗi quá dài trong im lặng nên 734 test vẫn xanh, còn Postgres từ chối insert
#: và lỗi chỉ lộ ra trên deployment (kỷ luật #7 bổ sung).
_COT = (
    # Tên cơ sở trên giấy phép có thể rất dài: "Nhà thuốc Bệnh viện Đa khoa khu vực …".
    ("ten_co_so", sa.String(length=255)),
    ("dia_chi", sa.String(length=255)),
    # 32 chứ không 15: chỗ này người ta hay gõ cả hai số ("028 3822 1234 - 0909 123 456").
    ("dien_thoai", sa.String(length=32)),
    # Mã số thuế Việt Nam là 10 hoặc 13 ký tự (có gạch nối). 20 là dư an toàn.
    ("ma_so_thue", sa.String(length=20)),
)


def upgrade() -> None:
    for ten, kieu in _COT:
        op.add_column(_BANG, sa.Column(ten, kieu, nullable=True))


def downgrade() -> None:
    for ten, _ in reversed(_COT):
        op.drop_column(_BANG, ten)
