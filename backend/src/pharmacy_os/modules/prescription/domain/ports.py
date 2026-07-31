"""Prescription ports (implemented by infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.prescription.domain.entities import Prescription


class PrescriptionRepository(Protocol):
    async def add(self, prescription: Prescription) -> None: ...

    async def update(self, prescription: Prescription) -> None:
        """Ghi lại **vòng đời** của đơn: trạng thái, người duyệt, lý do từ chối.

        Hẹp có chủ ý — không phải một `update()` ghi mọi trường. Ảnh đơn dùng cổng riêng
        :meth:`save_image`; xem lý do ở đó.
        """
        ...

    async def save_image(self, prescription: Prescription) -> None:
        """Ghi **chỉ** ảnh đơn và định dạng của nó.

        Tách khỏi :meth:`update` theo đúng khuôn `catalog.save_ingredients`/`save_price`:
        một cổng hẹp không thể vô tình ghi đè trạng thái đơn khi bên gọi chỉ muốn gắn ảnh —
        và với một đơn thuốc, ghi nhầm `status` là đổi cả tính hợp pháp của lượt bán.

        🔴 Việc cổng này phải TỒN TẠI là do test bắt: `update()` cũ chỉ ghi 3 trường vòng
        đời, nên lượt gắn ảnh đầu tiên trả **200** mà không lưu gì. Nối dây rồi mà không
        làm gì là dạng lỗi im lặng nhất của dự án này.
        """
        ...

    async def get(self, prescription_id: UUID) -> Prescription | None: ...

    async def list_archive(
        self, *, branch_id: UUID | None, limit: int = 50, offset: int = 0
    ) -> Sequence[Prescription]:
        """Đơn thuốc **có ảnh**, mới nhất trước — nguồn của màn Lưu trữ.

        ``branch_id is None`` nghĩa là **mọi chi nhánh của tenant**; tầng ứng dụng chỉ
        truyền ``None`` khi người gọi có ``archive.read.chain``. Đây là chỗ duy nhất phạm
        vi chi nhánh được nới, và nó nới bằng cách **bỏ một bộ lọc** — không phải bằng cách
        thêm một truy vấn thứ hai, để không có đường nào trả về dữ liệu của tenant khác.

        Chỉ trả đơn **đã có ảnh**: Lưu trữ là nơi tra chứng từ, còn một đơn chưa chụp thì
        không có gì để lưu trữ cả.

        **Không** kèm nội dung ảnh — xem `PrescriptionImageOutput` về lý do.
        """
        ...
