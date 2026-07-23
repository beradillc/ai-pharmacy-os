"""Inventory domain: batches, event-sourced movements, FEFO. Framework-free."""

from pharmacy_os.modules.inventory.domain.entities import (
    MovementType,
    ProductBatch,
    StockMovement,
    StockReconciliationNeeded,
)
from pharmacy_os.modules.inventory.domain.events import (
    LowStockDetected,
    StockMovedIn,
    StockMovedOut,
    StockShortfallDetected,
)
from pharmacy_os.modules.inventory.domain.exceptions import (
    InsufficientStockError,
    ReconciliationAlreadyResolvedError,
)
from pharmacy_os.modules.inventory.domain.fefo import Allocation, BatchAvailability, allocate_fefo
from pharmacy_os.modules.inventory.domain.ports import (
    BalanceRepository,
    BatchRepository,
    MovementRepository,
    StockReconciliationRepository,
)

__all__ = [
    "MovementType",
    "ProductBatch",
    "StockMovement",
    "StockReconciliationNeeded",
    "StockMovedIn",
    "StockMovedOut",
    "LowStockDetected",
    "StockShortfallDetected",
    "InsufficientStockError",
    "ReconciliationAlreadyResolvedError",
    "Allocation",
    "BatchAvailability",
    "allocate_fefo",
    "BatchRepository",
    "MovementRepository",
    "BalanceRepository",
    "StockReconciliationRepository",
]
