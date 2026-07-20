from decimal import Decimal

import pytest

from pharmacy_os.shared import Money, Quantity


def test_money_quantises_to_two_places() -> None:
    assert Money(Decimal("10.005")).amount == Decimal("10.01")


def test_money_add_same_currency() -> None:
    total = Money(Decimal("10")).add(Money(Decimal("5.50")))
    assert total.amount == Decimal("15.50")


def test_money_currency_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("1"), "VND").add(Money(Decimal("1"), "USD"))


def test_money_multiply() -> None:
    assert Money(Decimal("12000")).multiply(3).amount == Decimal("36000.00")


def test_quantity_rejects_negative() -> None:
    with pytest.raises(ValueError):
        Quantity(Decimal("-1"), "viên")


def test_quantity_add_unit_mismatch() -> None:
    with pytest.raises(ValueError):
        Quantity(Decimal("1"), "viên").add(Quantity(Decimal("1"), "vỉ"))
