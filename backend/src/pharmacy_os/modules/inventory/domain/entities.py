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

from pharmacy_os.modules.inventory.domain.exceptions import (
    LotExpiryMismatchError,
    ReconciliationAlreadyResolvedError,
)


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

    def merge_receipt(self, quantity: Decimal, cost_price: Decimal) -> None:
        """Fold another delivery of the *same physical lot* into this batch (PA B).

        Only valid when the incoming ``expiry_date`` matches this batch's — callers
        must check that themselves (:class:`LotExpiryMismatchError` otherwise) since
        this method only has this batch's own data. ``cost_price`` becomes the
        weighted average of the existing and incoming quantities; ``quantity_received``
        accumulates. Callers still record the matching ``StockMovement``/balance
        adjustment against *this* batch's id — merging never creates a new batch row.
        """
        if quantity <= 0:
            raise ValueError("Số lượng gộp lô phải > 0")
        total = self.quantity_received + quantity
        self.cost_price = (self.quantity_received * self.cost_price + quantity * cost_price) / total
        self.quantity_received = total

    def ensure_mergeable_expiry(self, expiry_date: date) -> None:
        """Raise :class:`LotExpiryMismatchError` if *expiry_date* doesn't match this batch's."""
        if self.expiry_date != expiry_date:
            raise LotExpiryMismatchError(
                f"Lô '{self.lot_no}' đã tồn tại với HSD {self.expiry_date}, "
                f"không khớp HSD mới {expiry_date} — không thể gộp"
            )


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
    #: Vị trí xuất phát / vị trí đích (BERAS V2 Phase 2). ``None`` ở cả hai nghĩa là **không
    #: rõ vị trí** — trạng thái của mọi dòng có từ trước Phase 2, và của mọi lượt nhập/xuất
    #: chưa gắn ô. Không phải lỗi, không cần backfill.
    from_location_id: UUID | None = None
    to_location_id: UUID | None = None
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
    can be looked up and reconciled by hand later. ``resolved`` defaults ``False``;
    :meth:`resolve` is the only transition (append-only otherwise — the reason/
    grn_id/po_item_id facts never change). ``po_item_id`` is ``None`` for whole-GRN
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

    def resolve(self) -> None:
        """Mark this discrepancy as handled. Who/when is the audit trail's job."""
        if self.resolved:
            raise ReconciliationAlreadyResolvedError(f"Mục {self.id} đã được xử lý")
        self.resolved = True
