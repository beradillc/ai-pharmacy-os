"""Inventory entities: product batches, stock movements, and reconciliation flags.

Stock levels are derived from an append-only stream of :class:`StockMovement`
records (event-sourced); :class:`ProductBatch` holds lot/expiry metadata.
:class:`StockReconciliationNeeded` is an audit-only flag written when a confirmed
goods-receipt note cannot be fully turned into stock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class MovementType(StrEnum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"
    TRANSFER = "TRANSFER"


@dataclass(slots=True)
class ProductBatch:
    """A received lot of a drug at a branch, with its expiry."""

    drug_id: UUID
    branch_id: UUID
    tenant_id: UUID
    lot_no: str
    expiry_date: date
    cost_price: Decimal
    quantity_received: Decimal
    mfg_date: date | None = None
    id: UUID = field(default_factory=uuid4)

    def is_expired(self, on: date | None = None) -> bool:
        return self.expiry_date < (on or date.today())


@dataclass(slots=True)
class StockMovement:
    """An immutable stock change against a batch (the source of truth)."""

    drug_id: UUID
    batch_id: UUID
    branch_id: UUID
    tenant_id: UUID
    type: MovementType
    quantity: Decimal  # always positive; direction implied by ``type``
    ref_type: str | None = None
    ref_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def signed_quantity(self) -> Decimal:
        """Return the quantity signed by direction (negative for OUT moves)."""
        if self.type in (MovementType.OUT,):
            return -self.quantity
        return self.quantity


@dataclass(slots=True)
class StockReconciliationNeeded:
    """Audit flag: a confirmed goods-receipt note whose stock-in didn't fully land.

    Written when a received line couldn't create an inventory batch — a lot-number
    collision (skipped, not merged) or any unexpected failure — so the discrepancy
    can be looked up and reconciled by hand later. There is no resolve workflow yet;
    ``resolved`` defaults ``False``. ``po_item_id`` is ``None`` for whole-GRN
    failures (e.g. the transaction aborted before any line was reached).
    """

    tenant_id: UUID
    branch_id: UUID
    grn_id: UUID
    reason: str
    po_item_id: UUID | None = None
    resolved: bool = False
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
