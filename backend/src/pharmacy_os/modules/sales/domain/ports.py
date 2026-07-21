"""Sales persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.sales.domain.entities import SalesOrder


class SalesRepository(Protocol):
    async def add(self, order: SalesOrder) -> None: ...

    async def get(self, order_id: UUID) -> SalesOrder | None: ...

    async def by_client_uuid(self, client_uuid: str) -> SalesOrder | None: ...
