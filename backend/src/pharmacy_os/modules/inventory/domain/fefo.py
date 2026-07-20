"""FEFO (First-Expired-First-Out) allocation — pure domain logic.

Given the available quantity per batch and a demand, decide how much to draw
from each batch, consuming those nearest to expiry first. Expired batches are
excluded by the caller (they should not be passed in as available).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.inventory.domain.exceptions import InsufficientStockError


@dataclass(frozen=True, slots=True)
class BatchAvailability:
    batch_id: UUID
    expiry_date: date
    available: Decimal


@dataclass(frozen=True, slots=True)
class Allocation:
    batch_id: UUID
    quantity: Decimal


def allocate_fefo(availabilities: list[BatchAvailability], demand: Decimal) -> list[Allocation]:
    """Allocate *demand* across batches, nearest expiry first.

    Raises :class:`InsufficientStockError` if total available < demand. Batches
    with zero availability are skipped. Ties on expiry are stable by input order.
    """
    if demand <= 0:
        raise ValueError("Số lượng xuất phải > 0")

    ordered = sorted(
        (b for b in availabilities if b.available > 0),
        key=lambda b: b.expiry_date,
    )
    total = sum((b.available for b in ordered), Decimal("0"))
    if total < demand:
        raise InsufficientStockError(requested=demand, available=total)

    allocations: list[Allocation] = []
    remaining = demand
    for batch in ordered:
        if remaining <= 0:
            break
        take = min(batch.available, remaining)
        allocations.append(Allocation(batch_id=batch.batch_id, quantity=take))
        remaining -= take
    return allocations
