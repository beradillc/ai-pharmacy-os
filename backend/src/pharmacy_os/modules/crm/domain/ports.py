"""CRM persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.crm.domain.entities import Customer


class CustomerRepository(Protocol):
    async def add(self, customer: Customer) -> None: ...

    async def get(self, customer_id: UUID) -> Customer | None: ...

    async def find_by_phone(self, phone: str) -> Customer | None: ...

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Customer]: ...

    async def update(self, customer: Customer) -> None: ...


class LoyaltyAccrualReader(Protocol):
    """Đọc tiền khách đã mua trong kỳ — `crm` cần, nhưng dữ liệu nằm ở `sales`.

    Khai ở **đây**, trong domain của bên DÙNG, không phải bên có dữ liệu: `crm` nói nó
    cần gì, `sales` không phải biết `crm` tồn tại. Bản cài đặt nối hai bên nằm ở
    composition root (`api/v1/cross_module.py`), giữ nguyên contract module-independence.

    Trả về `None` khi chưa nối dây — màn Khách hàng vẫn chạy, chỉ là không có cột điểm.
    Một tính năng phụ không được làm hỏng màn chính.
    """

    async def accrued_this_year(
        self, customer_ids: Sequence[UUID], tenant_id: UUID
    ) -> dict[UUID, Decimal]: ...
