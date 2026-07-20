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
