"""Sales domain events."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from pharmacy_os.core.events import DomainEvent


@dataclass(frozen=True, slots=True)
class SoldItem:
    """A drug and the base-unit quantity sold, carried on :class:`SaleCompleted`."""

    drug_id: UUID
    quantity: Decimal


@dataclass(frozen=True, kw_only=True)
class SaleCompleted(DomainEvent):
    """Emitted after a sale is finalised and committed.

    Inventory subscribes to this at the composition root to dispense stock
    (FEFO); ``client_uuid`` lets that reaction stay idempotent across re-syncs.
    """

    order_id: UUID
    branch_id: UUID
    client_uuid: str
    items: tuple[SoldItem, ...]
