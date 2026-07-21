"""Inventory domain: batches, event-sourced movements, FEFO. Framework-free."""

from pharmacy_os.modules.inventory.domain.entities import (
    MovementType,
    ProductBatch,
    StockMovement,
)
from pharmacy_os.modules.inventory.domain.events import (
    LowStockDetected,
    StockMovedIn,
    StockMovedOut,
    StockShortfallDetected,
)
from pharmacy_os.modules.inventory.domain.exceptions import InsufficientStockError
from pharmacy_os.modules.inventory.domain.fefo import Allocation, BatchAvailability, allocate_fefo
from pharmacy_os.modules.inventory.domain.ports import (
    BalanceRepository,
    BatchRepository,
    MovementRepository,
)

__all__ = [
    "MovementType",
    "ProductBatch",
    "StockMovement",
    "StockMovedIn",
    "StockMovedOut",
    "LowStockDetected",
    "StockShortfallDetected",
    "InsufficientStockError",
    "Allocation",
    "BatchAvailability",
    "allocate_fefo",
    "BatchRepository",
    "MovementRepository",
    "BalanceRepository",
]
