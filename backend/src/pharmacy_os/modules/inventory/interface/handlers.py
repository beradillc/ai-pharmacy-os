"""Inventory event handlers.

For Sprint 3 these observe inventory's own events and log them — proving the
event bus wiring end to end. Cross-module reactions (e.g. Sales' SaleCompleted
driving a dispense) arrive in Sprint 4.
"""

from __future__ import annotations

import structlog

from pharmacy_os.core.events import DomainEvent
from pharmacy_os.modules.inventory.domain import LowStockDetected, StockMovedIn, StockMovedOut

_log = structlog.get_logger("inventory.events")


async def on_stock_moved_in(event: DomainEvent) -> None:
    assert isinstance(event, StockMovedIn)
    _log.info("stock_moved_in", drug_id=str(event.drug_id), quantity=str(event.quantity))


async def on_stock_moved_out(event: DomainEvent) -> None:
    assert isinstance(event, StockMovedOut)
    _log.info("stock_moved_out", drug_id=str(event.drug_id), quantity=str(event.quantity))


async def on_low_stock(event: DomainEvent) -> None:
    assert isinstance(event, LowStockDetected)
    _log.warning(
        "low_stock_detected",
        drug_id=str(event.drug_id),
        on_hand=str(event.on_hand),
        reorder_point=str(event.reorder_point),
    )
