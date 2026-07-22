"""Procurement domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from pharmacy_os.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PurchaseOrdered(DomainEvent):
    """Emitted when a purchase order is sent to its supplier (DRAFT → ORDERED)."""

    po_id: UUID
    tenant_id: UUID
    branch_id: UUID
    supplier_id: UUID


@dataclass(frozen=True, slots=True)
class ReceivedItem:
    """A received drug line, carried on :class:`GoodsReceived` — the shape a
    composition-root handler needs to create an ``inventory.ProductBatch``.

    ``po_item_id`` traces the line back to its ``PurchaseOrderItem`` so a
    downstream reaction that can't create the batch (e.g. a lot collision) can
    record *which* line was affected, not just the GRN.
    """

    drug_id: UUID
    lot_no: str
    expiry_date: date
    unit_cost: Decimal
    quantity: Decimal
    po_item_id: UUID
    mfg_date: date | None = None


@dataclass(frozen=True, kw_only=True)
class GoodsReceived(DomainEvent):
    """Emitted when a goods receipt note is confirmed.

    ``inventory`` subscribes to this at the composition root to create
    ``ProductBatch``/``StockMovement`` (IN) records; ``grn_id`` is the
    idempotency key for that reaction (``StockMovement.ref_type/ref_id``
    convention already used by ``sales.SaleCompleted``).
    """

    grn_id: UUID
    po_id: UUID
    tenant_id: UUID
    branch_id: UUID
    received_by: UUID
    items: tuple[ReceivedItem, ...]
