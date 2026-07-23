"""Inventory data-transfer objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.inventory.domain.entities import StockReconciliationNeeded


@dataclass(slots=True)
class ReceiveStockInput:
    drug_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal
    cost_price: Decimal
    mfg_date: date | None = None


@dataclass(slots=True)
class ReceiptOutput:
    batch_id: UUID
    drug_id: UUID
    quantity_received: Decimal
    on_hand: Decimal


@dataclass(slots=True)
class DispenseInput:
    drug_id: UUID
    quantity: Decimal
    ref_type: str | None = None
    ref_id: UUID | None = None


@dataclass(slots=True)
class SaleDispenseItem:
    """One line of a completed sale to dispense (base-unit quantity)."""

    drug_id: UUID
    quantity: Decimal


@dataclass(slots=True)
class GoodsReceiptLine:
    """One received line from a confirmed goods-receipt note (cross-module input).

    ``inventory``'s own shape for a receipt line — the composition-root handler
    maps ``procurement``'s ``ReceivedItem`` onto this, so inventory never imports
    procurement. ``po_item_id`` is carried through only so a skipped line can be
    named in a reconciliation flag.
    """

    drug_id: UUID
    lot_no: str
    expiry_date: date
    unit_cost: Decimal
    quantity: Decimal
    po_item_id: UUID | None = None
    mfg_date: date | None = None


@dataclass(slots=True)
class AllocationOutput:
    batch_id: UUID
    quantity: Decimal


@dataclass(slots=True)
class DispenseOutput:
    drug_id: UUID
    dispensed: Decimal
    on_hand: Decimal
    allocations: list[AllocationOutput] = field(default_factory=list)


@dataclass(slots=True)
class NearExpiryItem:
    batch_id: UUID
    drug_id: UUID
    lot_no: str
    expiry_date: date
    quantity_received: Decimal


@dataclass(slots=True)
class ReconciliationOutput:
    id: UUID
    branch_id: UUID
    grn_id: UUID
    po_item_id: UUID | None
    reason: str
    resolved: bool
    occurred_at: datetime

    @classmethod
    def of(cls, record: StockReconciliationNeeded) -> ReconciliationOutput:
        return cls(
            id=record.id,
            branch_id=record.branch_id,
            grn_id=record.grn_id,
            po_item_id=record.po_item_id,
            reason=record.reason,
            resolved=record.resolved,
            occurred_at=record.occurred_at,
        )
