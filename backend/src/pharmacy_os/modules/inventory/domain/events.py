"""Inventory domain events."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from pharmacy_os.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class StockMovedIn(DomainEvent):
    drug_id: UUID
    batch_id: UUID
    branch_id: UUID
    quantity: Decimal


@dataclass(frozen=True, kw_only=True)
class StockMovedOut(DomainEvent):
    drug_id: UUID
    branch_id: UUID
    quantity: Decimal


@dataclass(frozen=True, kw_only=True)
class LowStockDetected(DomainEvent):
    drug_id: UUID
    branch_id: UUID
    on_hand: Decimal
    reorder_point: Decimal


@dataclass(frozen=True, kw_only=True)
class StockShortfallDetected(DomainEvent):
    """A dispense could not be met in full (e.g. an offline sale oversold).

    The available portion is still dispensed; ``requested - available`` is the
    shortfall to reconcile. Raised, never silently dropped, so the sale is not
    blocked but the discrepancy is visible.
    """

    drug_id: UUID
    branch_id: UUID
    requested: Decimal
    available: Decimal
    ref_type: str | None = None
    ref_id: UUID | None = None
