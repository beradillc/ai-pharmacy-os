"""SQLAlchemy models cho sơ đồ kho. Cross-dialect (Postgres + SQLite cho test)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin, TimestampMixin


class LocationORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    """Một nút trong sơ đồ kho.

    ``TenantScopedMixin`` cho ``tenant_id`` + ``branch_id``: vị trí **theo chi nhánh**
    (GĐ chốt 2026-07-31). Kệ A01 của cơ sở 1 và cơ sở 2 là hai chỗ khác nhau; dùng chung
    sẽ buộc mọi truy vấn tồn phải nhớ lọc thêm chi nhánh ở tầng ứng dụng — chỗ dễ quên nhất.
    """

    __tablename__ = "locations"
    __table_args__ = (
        # 🔴 Khoá duy nhất theo (chi nhánh, cha, mã) chứ KHÔNG theo (chi nhánh, mã):
        # ô "01" dưới kệ A và ô "01" dưới kệ B là hai chỗ khác nhau, và bắt nhà thuốc đặt
        # mã duy nhất toàn kho là bắt họ bỏ đúng cách đánh số đang dán trên kệ.
        #
        # ⚠️ `parent_id` NULL (các kho gốc) KHÔNG được ràng buộc bởi khoá này — chuẩn SQL
        # coi NULL khác nhau. Trùng mã giữa hai kho gốc vì thế phải chặn ở tầng ứng dụng
        # (`by_code_under`). Ghi ra đây để người sửa sau không tưởng CSDL đã lo hết.
        UniqueConstraint("branch_id", "parent_id", "code", name="uq_location_sibling_code"),
        # Đường dẫn là duy nhất trong một chi nhánh — đây mới là thứ chặn được cả trùng
        # giữa các kho gốc, vì đường dẫn của kho gốc chính là mã của nó.
        UniqueConstraint("branch_id", "path", name="uq_location_path"),
        # Phục vụ truy vấn tiền tố "mọi thứ nằm dưới khu A" mà không phải đệ quy.
        Index("ix_location_branch_path", "branch_id", "path"),
    )

    #: Tự tham chiếu. `ondelete` cố ý KHÔNG đặt CASCADE: xoá một kệ mà kéo theo mọi ô bên
    #: dưới là cách mất dữ liệu nhanh nhất. Vòng đời đúng của một vị trí là **ngừng hoạt
    #: động** (`is_active=False`), không phải xoá.
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id"), index=True, nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Đường dẫn vật chất hoá (``KHO1/A/A01/03``). Dữ liệu THỪA, suy ra được từ cha — giữ
    #: sẵn để đổi truy vấn đệ quy thành một phép so tiền tố. `code` bất biến chính là thứ
    #: giữ cho nó không lệch.
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Thứ tự đi lấy hàng trong cùng một cha — xem `Location.pick_order`.
    pick_order: Mapped[int] = mapped_column(nullable=False, default=0)
