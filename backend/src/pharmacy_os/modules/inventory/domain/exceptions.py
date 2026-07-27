"""Inventory domain exceptions (pure — no framework)."""

from __future__ import annotations

from decimal import Decimal


class InventoryError(Exception):
    """Base for inventory domain rule violations."""


class InsufficientStockError(InventoryError):
    """Raised when demand exceeds available (non-expired) stock."""

    def __init__(self, requested: Decimal, available: Decimal) -> None:
        super().__init__(f"Không đủ tồn: cần {requested}, còn {available} (đơn vị cơ sở)")
        self.requested = requested
        self.available = available


class DuplicateMovementError(InventoryError):
    """Raised when a movement for ``(ref_type, ref_id, batch_id)`` already exists.

    The database's own uniqueness — not a preceding ``SELECT`` — is what decides
    this: a check-then-act pair lets two concurrent deliveries of the same sale
    both read "not dispensed yet" and both write (audit B-02). Callers treat it as
    *"someone else already did this work"*, i.e. as idempotent success, not as a
    failure to report.
    """

    def __init__(self, ref_type: str, ref_id: object) -> None:
        super().__init__(f"Đã có phiếu xuất/nhập cho {ref_type} {ref_id} — bỏ qua lần lặp")
        self.ref_type = ref_type
        self.ref_id = ref_id


class ReconciliationAlreadyResolvedError(InventoryError):
    """Raised when resolving a :class:`StockReconciliationNeeded` already marked resolved."""


class LotExpiryMismatchError(InventoryError):
    """Raised when a lot number collides but the expiry date does not match (PA B — gộp lô).

    Same ``lot_no`` from a manufacturer implies the same ``expiry_date``; a mismatch
    is a data-entry problem, not a legitimate re-delivery, so it is never merged.
    """
