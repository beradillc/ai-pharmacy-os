from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.inventory.domain import InsufficientStockError
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability, allocate_fefo


def _b(expiry: date, qty: str) -> BatchAvailability:
    return BatchAvailability(batch_id=uuid4(), expiry_date=expiry, available=Decimal(qty))


def test_fefo_picks_nearest_expiry_first() -> None:
    near = _b(date(2026, 1, 1), "10")
    far = _b(date(2027, 1, 1), "10")
    # Pass in reverse order to prove sorting, not input order, drives it.
    allocs = allocate_fefo([far, near], Decimal("5"))
    assert len(allocs) == 1
    assert allocs[0].batch_id == near.batch_id
    assert allocs[0].quantity == Decimal("5")


def test_fefo_spans_multiple_batches() -> None:
    b1 = _b(date(2026, 1, 1), "8")
    b2 = _b(date(2026, 6, 1), "8")
    allocs = allocate_fefo([b1, b2], Decimal("12"))
    assert [(a.batch_id, a.quantity) for a in allocs] == [
        (b1.batch_id, Decimal("8")),
        (b2.batch_id, Decimal("4")),
    ]


def test_fefo_exact_total() -> None:
    b1 = _b(date(2026, 1, 1), "5")
    b2 = _b(date(2026, 2, 1), "5")
    allocs = allocate_fefo([b1, b2], Decimal("10"))
    assert sum(a.quantity for a in allocs) == Decimal("10")


def test_fefo_insufficient_raises() -> None:
    b1 = _b(date(2026, 1, 1), "3")
    with pytest.raises(InsufficientStockError) as exc:
        allocate_fefo([b1], Decimal("5"))
    assert exc.value.available == Decimal("3")
    assert exc.value.requested == Decimal("5")


def test_fefo_skips_zero_availability() -> None:
    empty = _b(date(2025, 1, 1), "0")
    good = _b(date(2026, 1, 1), "5")
    allocs = allocate_fefo([empty, good], Decimal("5"))
    assert len(allocs) == 1
    assert allocs[0].batch_id == good.batch_id


def test_fefo_rejects_non_positive_demand() -> None:
    with pytest.raises(ValueError):
        allocate_fefo([_b(date(2026, 1, 1), "5")], Decimal("0"))
