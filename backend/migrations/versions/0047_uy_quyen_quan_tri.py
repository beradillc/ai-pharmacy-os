"""uy quyen quan tri co thoi han: hai bang, chi ghi them

Chain chốt 2026-08-03: *"Uỷ quyền được, chủ chuỗi sẽ chịu trách nhiệm, thời hạn 24 tiếng
mỗi xác nhận."* Xem ``docs/features/uy-quyen-quan-tri/01_DECISIONS.md``.

Vai *Quản trị hệ thống* giữ 25 quyền chạm hồ sơ bệnh nhân — thường trực, không ai cấp,
không có hạn. Chain bác phương án cắt quyền (một người bảo trì làm việc mù sẽ mở ``psql``,
nơi không có vết kiểm toán nào). Đích không phải *ít quyền hơn* mà là **quyền cao nhất
phải đắt nhất để dùng**: hai bảng này là cái giá đó.

🔴 **CHỈ GHI THÊM — không có đường dọn hàng hết hạn, và đó là chủ ý.** Hàng hết hạn là
**bằng chứng**, không phải rác: nó trả lời *"ai đã mở quyền đọc hồ sơ bệnh nhân cho ai,
lúc nào, vì lý do gì"*. Khác hẳn ``two_factor_challenges``/``refresh_tokens`` — hai bảng
đó có ``delete_expired`` vì hàng cũ của chúng vô nghĩa. Hết hiệu lực ở đây là một **phép
so thời gian** (``het_han_luc <= now``), không phải một lượt ``DELETE``, nên không tác vụ
nền nào phải chạy đúng giờ: máy mất điện ba ngày rồi bật lại thì uỷ quyền cũ vẫn hết đúng
lúc nó phải hết.

``ly_do`` là ``Text`` chứ không ``String(n)``: nó do người đang xử lý sự cố gõ, và một
giới hạn ký tự ở đây chỉ dẫn tới lý do bị cắt cụt giữa chừng trong sổ kiểm toán. Bài học
``audit_logs.action`` varchar(32) áp theo **chiều ngược lại** — chỗ nào biết rõ độ rộng
thì khai chặt, chỗ nào là văn người viết thì đừng bịa một con số.

Revision ID: 0047_uy_quyen
Revises: 0046_tenant_co_so
Create Date: 2026-08-03 20:20:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0047_uy_quyen"
down_revision: str | None = "0046_tenant_co_so"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BANG = "uy_quyen_quan_tri"
_BANG_QUYEN = "uy_quyen_quan_tri_quyen"


def upgrade() -> None:
    op.create_table(
        _BANG,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        # ondelete CASCADE cho người NHẬN: xoá tài khoản họ thì uỷ quyền của họ hết nghĩa.
        sa.Column(
            "nguoi_nhan_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 🔴 KHÔNG CASCADE cho người CẤP — cố ý khác dòng trên. Xoá tài khoản người cấp mà
        # kéo theo cả vết uỷ quyền thì việc xoá một tài khoản trở thành cách xoá dấu vết
        # mình đã cấp quyền cho ai, tức đúng thứ sổ này sinh ra để chặn.
        sa.Column("nguoi_cap_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ly_do", sa.Text(), nullable=False),
        sa.Column("cap_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("het_han_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("thu_hoi_luc", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(f"ix_{_BANG}_tenant_id", _BANG, ["tenant_id"])
    op.create_index(f"ix_{_BANG}_nguoi_cap_id", _BANG, ["nguoi_cap_id"])
    # Đường nóng: mỗi request đã xác thực hỏi "người này có uỷ quyền nào còn sống không".
    # Bảng chỉ-ghi-thêm nên phần lịch sử tăng mãi trong khi phần còn hiệu lực gần như luôn
    # rỗng — không có chỉ mục này thì cái giá của tính năng rơi vào mọi request.
    op.create_index("ix_uy_quyen_nguoi_nhan_han", _BANG, ["nguoi_nhan_id", "het_han_luc"])

    op.create_table(
        _BANG_QUYEN,
        sa.Column(
            "uy_quyen_id",
            sa.Uuid(),
            sa.ForeignKey(f"{_BANG}.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # 64 khớp đúng ``role_permissions.permission`` — cùng loại dữ liệu thì cùng độ rộng,
        # để không có chuỗi nào vừa với bảng này mà không vừa với bảng kia.
        sa.Column("permission", sa.String(length=64), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table(_BANG_QUYEN)
    op.drop_index("ix_uy_quyen_nguoi_nhan_han", table_name=_BANG)
    op.drop_index(f"ix_{_BANG}_nguoi_cap_id", table_name=_BANG)
    op.drop_index(f"ix_{_BANG}_tenant_id", table_name=_BANG)
    op.drop_table(_BANG)
