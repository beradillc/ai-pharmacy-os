"""Inventory persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class BatchStockRow:
    """One batch's current on-hand, as read for the Sprint 7 stock report.

    ``quantity`` is the live ``stock_balances`` projection, not
    ``quantity_received`` — the report shows what's actually left, same
    source as :meth:`BalanceRepository.on_hand`."""

    batch_id: UUID
    drug_id: UUID
    branch_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class DrugOnHandRow:
    """Total on-hand of a drug at a branch, summed across its batches.

    The bulk counterpart of :meth:`BalanceRepository.on_hand` (single drug) —
    the analytics reorder run needs current stock for every drug at once, and a
    per-drug round-trip would be N queries. Only drugs with positive stock appear."""

    drug_id: UUID
    branch_id: UUID
    on_hand: Decimal


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

    async def stock_report(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[BatchStockRow]:
        """Page of batches with on-hand > 0, tenant-wide (or narrowed to one branch),
        soonest-expiring first, ``batch_id`` as the pagination tie-break."""
        ...


class MovementRepository(Protocol):
    async def add(self, movement: StockMovement) -> None:
        """Append one movement.

        Raises :class:`DuplicateMovementError` when a movement for the same
        ``(tenant, ref_type, ref_id, batch_id)`` already exists — the store's own
        uniqueness, which is what makes idempotency hold under concurrency where
        :meth:`exists_for_ref` alone cannot (audit B-02). Movements without a
        ``ref_id`` are never constrained: they carry no identity to be duplicate of.
        """
        ...

    async def exists_for_ref(self, ref_type: str, ref_id: UUID) -> bool:
        """True if any movement already references *(ref_type, ref_id)* (idempotency).

        A **fast path only**, never the guarantee: between this read and the write
        that follows, another transaction can insert. The guarantee lives in
        :meth:`add`'s :class:`DuplicateMovementError`; callers must handle it too.
        """
        ...


class BalanceRepository(Protocol):
    async def adjust(
        self, drug_id: UUID, batch_id: UUID, branch_id: UUID, tenant_id: UUID, delta: Decimal
    ) -> Decimal:
        """Apply *delta* to the (drug, batch, branch) balance; return new on-hand.

        Two guarantees the caller may rely on, both enforced by the store rather
        than by a preceding read (audit B-01/B-04):

        * **No lost update.** Concurrent adjusts compose — 100 − 10 − 10 is 80, not
          90. Read-then-write in application code cannot promise this.
        * **Never negative.** A *delta* that would drive the balance below zero is
          refused with :class:`InsufficientStockError` carrying the quantity that
          *was* available. A pharmacy cannot hand over stock it does not have, and
          a ledger that goes negative is a ledger nobody can use.
        """

    async def on_hand(self, drug_id: UUID, branch_id: UUID) -> Decimal:
        """Total on-hand across all batches of a drug at a branch."""

    async def on_hand_by_drug(self, branch_id: UUID) -> list[DrugOnHandRow]:
        """On-hand per drug at a branch (all drugs with positive stock), summed in
        SQL. Bulk read for the analytics reorder run — see :class:`DrugOnHandRow`."""
        ...


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
