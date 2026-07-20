"""Inventory persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.inventory.domain.entities import ProductBatch, StockMovement
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability


class BatchRepository(Protocol):
    async def add(self, batch: ProductBatch) -> None: ...

    async def get(self, batch_id: UUID) -> ProductBatch | None: ...

    async def availabilities(
        self, drug_id: UUID, branch_id: UUID, *, not_expired_on: date
    ) -> list[BatchAvailability]: ...

    async def near_expiry(self, branch_id: UUID, *, before: date) -> list[ProductBatch]: ...


class MovementRepository(Protocol):
    async def add(self, movement: StockMovement) -> None: ...


class BalanceRepository(Protocol):
    async def adjust(
        self, drug_id: UUID, batch_id: UUID, branch_id: UUID, tenant_id: UUID, delta: Decimal
    ) -> Decimal:
        """Apply *delta* to the (drug, batch, branch) balance; return new on-hand."""

    async def on_hand(self, drug_id: UUID, branch_id: UUID) -> Decimal:
        """Total on-hand across all batches of a drug at a branch."""
