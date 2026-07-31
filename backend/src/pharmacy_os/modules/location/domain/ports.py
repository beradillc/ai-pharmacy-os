"""Location persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.location.domain.entities import Location


class LocationRepository(Protocol):
    async def add(self, location: Location) -> None: ...

    async def get(self, location_id: UUID) -> Location | None: ...

    async def save(self, location: Location) -> None:
        """Ghi lại **tên hiển thị, thứ tự lấy hàng và trạng thái** của một vị trí.

        Hẹp có chủ ý — cùng khuôn ``catalog.save_ingredients``/``save_price``. Mã và đường
        dẫn không nằm trong danh sách ghi được: chúng bất biến sau khi tạo, và một cổng ghi
        rộng là đường duy nhất để chúng đổi mà không ai nhận ra.
        """
        ...

    async def by_code_under(self, parent_id: UUID | None, code: str) -> Location | None:
        """Tìm anh em cùng cha theo mã — nguồn của :class:`DuplicateLocationCodeError`.

        ``parent_id is None`` nghĩa là tìm trong các **kho gốc** của chi nhánh.
        """
        ...

    async def list_branch(self, *, include_inactive: bool = False) -> Sequence[Location]:
        """Toàn bộ sơ đồ của chi nhánh đang đăng nhập, sắp theo ``path``.

        Sắp theo đường dẫn cho ra **đúng thứ tự cây khi duyệt tuyến tính** — màn hình dựng
        được sơ đồ mà không phải đệ quy, và thứ tự đó ổn định giữa hai lượt gọi.
        """
        ...

    async def count_active_children(self, location_id: UUID) -> int: ...
