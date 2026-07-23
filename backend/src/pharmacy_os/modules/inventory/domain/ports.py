"""Inventory persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.inventory.domain.entities import (
    ProductBatch,
    StockMovement,
    StockReconciliationNeeded,
)
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability


class BatchRepository(Protocol):
    async def add(self, batch: ProductBatch) -> None: ...

    async def update(self, batch: ProductBatch) -> None:
        """Persist ``quantity_received``/``cost_price`` after :meth:`ProductBatch.merge_receipt`."""
        ...

    async def get(self, batch_id: UUID) -> ProductBatch | None: ...

    async def find_by_lot(self, drug_id: UUID, branch_id: UUID, lot_no: str) -> ProductBatch | None:
        """Return the batch matching ``(drug_id, branch_id, lot_no)`` if one exists.

        Mirrors the ``uq_batch_lot`` uniqueness so a caller can check for a lot
        collision *before* inserting, rather than provoking an integrity error.
        """
        ...

    async def availabilities(
        self, drug_id: UUID, branch_id: UUID, *, not_expired_on: date
    ) -> list[BatchAvailability]: ...

    async def near_expiry(self, branch_id: UUID, *, before: date) -> list[ProductBatch]: ...


class MovementRepository(Protocol):
    async def add(self, movement: StockMovement) -> None: ...

    async def exists_for_ref(self, ref_type: str, ref_id: UUID) -> bool:
        """True if any movement already references *(ref_type, ref_id)* (idempotency)."""
        ...


class BalanceRepository(Protocol):
    async def adjust(
        self, drug_id: UUID, batch_id: UUID, branch_id: UUID, tenant_id: UUID, delta: Decimal
    ) -> Decimal:
        """Apply *delta* to the (drug, batch, branch) balance; return new on-hand."""

    async def on_hand(self, drug_id: UUID, branch_id: UUID) -> Decimal:
        """Total on-hand across all batches of a drug at a branch."""


class StockReconciliationRepository(Protocol):
    async def add(self, record: StockReconciliationNeeded) -> None:
        """Persist a reconciliation flag."""
        ...

    async def get(self, record_id: UUID, tenant_id: UUID) -> StockReconciliationNeeded | None: ...

    async def update(self, record: StockReconciliationNeeded) -> None:
        """Persist the ``resolved`` transition (the only field :meth:`resolve` changes)."""
        ...

    async def list(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        resolved: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StockReconciliationNeeded]:
        """List a branch's discrepancies, newest first; ``resolved=None`` returns both."""
        ...
