"""Inventory data-transfer objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID


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
