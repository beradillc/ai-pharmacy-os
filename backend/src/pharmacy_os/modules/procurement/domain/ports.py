"""Procurement persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.procurement.domain.entities import (
    GoodsReceiptNote,
    PurchaseOrder,
    PurchaseOrderStatus,
    Supplier,
)


class SupplierRepository(Protocol):
    async def add(self, supplier: Supplier) -> None: ...

    async def update(self, supplier: Supplier) -> None: ...

    async def get(self, supplier_id: UUID) -> Supplier | None: ...

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Supplier]: ...

    async def names_by_ids(self, supplier_ids: Sequence[UUID]) -> dict[UUID, str]:
        """Name-only projection for many ids in one query. Mirrors
        ``DrugRepository.names_by_ids``: ids the tenant can't see are absent rather than
        an error, because a screen that lists ids must not die on one stale row."""
        ...


class PurchaseOrderRepository(Protocol):
    async def next_code(self) -> str:
        """Allocate the tenant's next order number ("PO-0001").

        Must be safe under concurrent creates — two pharmacists pressing "tạo đơn" at
        once must never receive the same number. Gaps are acceptable (a rolled-back
        transaction burns a number); collisions are not.
        """
        ...

    async def add(self, purchase_order: PurchaseOrder) -> None: ...

    async def update(self, purchase_order: PurchaseOrder) -> None: ...

    async def get(self, po_id: UUID) -> PurchaseOrder | None: ...

    async def count_by_status(self, status: PurchaseOrderStatus, branch_id: UUID) -> int:
        """How many POs are in *status* at *branch_id* — the analytics dashboard
        counts ``DRAFT`` to show "PO nháp chờ duyệt" (PROJECT_STATE §7am)."""
        ...

    async def last_supplier_for_drug(self, drug_id: UUID) -> UUID | None:
        """The supplier of the most recently **placed** PO (status past ``DRAFT``)
        that ordered *drug_id*, tenant-wide, or ``None`` if the drug was never
        ordered. This is how an analytics reorder suggestion picks a supplier for its
        draft PO (PROJECT_STATE §7am, Q3): a never-before-ordered drug yields ``None``
        and the suggestion is flagged "chưa có NCC" instead of materialising."""
        ...


class GoodsReceiptRepository(Protocol):
    async def add(self, receipt: GoodsReceiptNote) -> None: ...

    async def update(self, receipt: GoodsReceiptNote) -> None: ...

    async def get(self, grn_id: UUID) -> GoodsReceiptNote | None: ...
