"""CRM persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.crm.domain.entities import Customer


class CustomerRepository(Protocol):
    async def add(self, customer: Customer) -> None: ...

    async def get(self, customer_id: UUID) -> Customer | None: ...

    async def find_by_phone(self, phone: str) -> Customer | None: ...

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Customer]: ...

    async def update(self, customer: Customer) -> None: ...
