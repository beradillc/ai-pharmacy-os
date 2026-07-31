"""Prescription ports (implemented by infrastructure)."""

from __future__ import annotations

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
