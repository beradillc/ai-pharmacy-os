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


@dataclass(frozen=True, kw_only=True)
class SaleReturned(DomainEvent):
    """Emitted after a (partial) return is registered against a completed sale.

    ``return_id`` is a fresh id minted per call — the idempotency key any future
    cross-module subscriber should key on (there is no subscriber yet: restocking
    a returned medicine requires a pharmacist to inspect it first, so today this
    only reaches the audit trail; see PROJECT_STATE for the reasoning).
    """

    return_id: UUID
    order_id: UUID
    branch_id: UUID
    line_id: UUID
    drug_id: UUID
    quantity: Decimal
