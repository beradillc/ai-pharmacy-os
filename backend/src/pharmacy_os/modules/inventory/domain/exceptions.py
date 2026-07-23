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


class ReconciliationAlreadyResolvedError(InventoryError):
    """Raised when resolving a :class:`StockReconciliationNeeded` already marked resolved."""


class LotExpiryMismatchError(InventoryError):
    """Raised when a lot number collides but the expiry date does not match (PA B — gộp lô).

    Same ``lot_no`` from a manufacturer implies the same ``expiry_date``; a mismatch
    is a data-entry problem, not a legitimate re-delivery, so it is never merged.
    """
