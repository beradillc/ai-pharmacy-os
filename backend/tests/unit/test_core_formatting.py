"""Pure formatting helpers — no DB, no HTTP needed."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pharmacy_os.core.formatting import format_date_vn, format_money, format_qty


def test_format_money_uses_dot_as_thousands_separator() -> None:
    assert format_money(Decimal("1234567")) == "1.234.567"
    assert format_money(Decimal("0")) == "0"
    assert format_money(Decimal("999")) == "999"


def test_format_qty_drops_trailing_zero_decimals() -> None:
    """The regression this guards: kỷ luật #26's real incident — a
    ``Numeric(18, 3)`` quantity of 100 whole units prints as "100.000" and gets
    misread as one hundred thousand, not one hundred."""
    assert format_qty(Decimal("100.000")) == "100"
    assert format_qty(Decimal("1.000")) == "1"


def test_format_qty_keeps_real_fractional_quantities() -> None:
    assert format_qty(Decimal("37.500")) == "37.5"


def test_format_date_vn_is_day_month_year() -> None:
    assert format_date_vn(date(2026, 8, 4)) == "04/08/2026"
