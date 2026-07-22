"""Procurement persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.procurement.domain.entities import (
    GoodsReceiptNote,
    PurchaseOrder,
    Supplier,
)


class SupplierRepository(Protocol):
    async def add(self, supplier: Supplier) -> None: ...

    async def update(self, supplier: Supplier) -> None: ...

    async def get(self, supplier_id: UUID) -> Supplier | None: ...

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Supplier]: ...


class PurchaseOrderRepository(Protocol):
    async def add(self, purchase_order: PurchaseOrder) -> None: ...

    async def update(self, purchase_order: PurchaseOrder) -> None: ...

    async def get(self, po_id: UUID) -> PurchaseOrder | None: ...


class GoodsReceiptRepository(Protocol):
    async def add(self, receipt: GoodsReceiptNote) -> None: ...

    async def update(self, receipt: GoodsReceiptNote) -> None: ...

    async def get(self, grn_id: UUID) -> GoodsReceiptNote | None: ...
