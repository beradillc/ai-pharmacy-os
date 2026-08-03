"""Quyền đến từ **uỷ quyền quản trị có thời hạn**, đọc lại ở mỗi request (Chain chốt 03/08).

Xem ``docs/features/uy-quyen-quan-tri/01_DECISIONS.md`` ràng buộc cài đặt số 1.

**Vì sao KHÔNG nhét vào JWT.** Quyền hôm nay nằm trong token đã ký, và đó là lựa chọn đúng
cho quyền đến từ **vai trò**: vai đổi hiếm, và token sống 60 phút. Nhưng một uỷ quyền có
hạn **24 giờ** mà nằm trong token thì nó **sống dai hơn cửa sổ của chính nó** — token cấp
lúc 23:59 vẫn mang quyền ấy sau khi uỷ quyền đã hết, cho tới lúc token hết hạn. Cơ chế kiểm
soát hỏng đúng ở chỗ nó tồn tại để canh. Đổi lại: thêm **một lượt đọc CSDL có chỉ mục** trên
mỗi request đã xác thực (``TokenScopeGuard`` đã có 2 lượt; đây là lượt thứ ba).

🔴 **VÀ VÌ SAO GUARD NÀY CỐ Ý KHÔNG CÓ CACHE — khác hẳn ``TokenScopeGuard`` ngay bên cạnh.**
Cache của guard kia an toàn vì nó nhớ một sự thật **vĩnh viễn đúng**: một chi nhánh đã thuộc
một tenant thì không bao giờ đổi tenant. Uỷ quyền thì ngược lại — nó **được sinh ra để hết
hạn**. Cache nó lại chính là tái tạo đúng lỗi mà việc không-nhét-vào-JWT vừa tránh, chỉ là ở
tầng khác và khó thấy hơn. Nếu một ngày cần cache vì hiệu năng, thứ được cache phải là
**thời điểm hết hạn** (để tự vô hiệu), không phải tập quyền.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UyQuyenGuard:
    """Tập quyền **thêm** mà một người đang mượn qua uỷ quyền còn hiệu lực."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def quyen_duoc_uy_quyen(
        self, tenant_id: UUID, user_id: UUID, bay_gio: datetime | None = None
    ) -> frozenset[str]:
        """Quyền đang mượn của *user_id* trong *tenant_id*; rỗng là ca thường gặp nhất.

        Ba điều kiện lọc **ở CSDL**, không đọc hết rồi lọc trong Python — bảng chỉ-ghi-thêm
        nên phần lịch sử tăng mãi trong khi phần còn hiệu lực gần như luôn rỗng:

        * ``thu_hoi_luc IS NULL`` — chưa bị rút sớm;
        * ``het_han_luc > bay_gio`` — chưa tới hạn. Là một **phép so thời gian**, nên máy mất
          điện ba ngày rồi bật lại thì uỷ quyền cũ vẫn hết đúng lúc, không job nào phải đuổi kịp;
        * ``tenant_id`` khớp — uỷ quyền cấp ở tenant này không theo người sang tenant khác.
          Thừa về lý thuyết (``nguoi_nhan_id`` đã thuộc một tenant), nhưng cùng tinh thần
          ``TokenScopeGuard``: biến một tính chất của *một đường mã nguồn hôm nay* thành một
          **ràng buộc** áp cho mọi đường vào, kể cả đường chưa được viết.
        """
        bay_gio = bay_gio or datetime.now(UTC)
        uy_quyen = _table("uy_quyen_quan_tri")
        quyen = _table("uy_quyen_quan_tri_quyen")

        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(quyen.c.permission)
                    .select_from(quyen.join(uy_quyen, quyen.c.uy_quyen_id == uy_quyen.c.id))
                    .where(
                        uy_quyen.c.nguoi_nhan_id == user_id,
                        uy_quyen.c.tenant_id == tenant_id,
                        uy_quyen.c.thu_hoi_luc.is_(None),
                        uy_quyen.c.het_han_luc > bay_gio,
                    )
                )
            ).scalars()
        return frozenset(rows)


def _table(name: str) -> Table:
    """Bảng lấy từ metadata dùng chung — xem ghi chú cùng tên ở ``branch_scope``.

    Nhập trong hàm chứ không ở đầu tệp: ``core`` **cấm** import ``modules`` (contract
    ``kernel-knows-no-business``).
    """
    from pharmacy_os.core.db.base import Base

    return Base.metadata.tables[name]
