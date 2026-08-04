"""``period_start`` is pure — no DB, no HTTP needed.

Shared bucketing for the revenue report and the profit report (ROADMAP V3-7a);
QUARTER/YEAR added 2026-08-04 alongside DAY/WEEK/MONTH.
"""

from __future__ import annotations

from datetime import date, datetime

from pharmacy_os.modules.sales.application.dto import RevenueGranularity, period_start


def _at(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, 14, 30)


def test_day_returns_the_calendar_day() -> None:
    assert period_start(_at(2026, 8, 4), RevenueGranularity.DAY) == date(2026, 8, 4)


def test_week_returns_the_monday() -> None:
    # 2026-08-04 is a Tuesday.
    assert period_start(_at(2026, 8, 4), RevenueGranularity.WEEK) == date(2026, 8, 3)


def test_month_returns_the_first() -> None:
    assert period_start(_at(2026, 8, 4), RevenueGranularity.MONTH) == date(2026, 8, 1)


def test_quarter_returns_the_quarters_first_month() -> None:
    assert period_start(_at(2026, 8, 4), RevenueGranularity.QUARTER) == date(2026, 7, 1)
    assert period_start(_at(2026, 1, 15), RevenueGranularity.QUARTER) == date(2026, 1, 1)
    assert period_start(_at(2026, 3, 31), RevenueGranularity.QUARTER) == date(2026, 1, 1)
    assert period_start(_at(2026, 4, 1), RevenueGranularity.QUARTER) == date(2026, 4, 1)
    assert period_start(_at(2026, 12, 31), RevenueGranularity.QUARTER) == date(2026, 10, 1)


def test_year_returns_january_first() -> None:
    assert period_start(_at(2026, 8, 4), RevenueGranularity.YEAR) == date(2026, 1, 1)
    assert period_start(_at(2026, 12, 31), RevenueGranularity.YEAR) == date(2026, 1, 1)
