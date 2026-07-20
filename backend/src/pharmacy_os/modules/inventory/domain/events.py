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
