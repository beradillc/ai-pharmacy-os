"""Vietnamese-locale display formatting — shared kernel, no framework/I-O.

Anything that turns a raw ``Decimal``/``date`` into text a Vietnamese pharmacy
owner reads without translating in their head belongs here, not duplicated per
module. Lives in ``core`` (not a business module) so every layer of every module
can import it under the layers contract (``api`` → ``modules`` → ``core`` →
``shared``) without a layering or module-independence violation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal


def format_money(amount: Decimal) -> str:
    """Vietnamese-style thousands separator; VND has no subunit worth printing.

    Moved here 2026-08-04 from ``sales.interface.receipt_rendering`` (its only
    prior home) so ``sales.application`` (report CSV export, PROJECT_STATE §7dt)
    can reuse it too — an ``application`` module importing its own
    ``interface`` layer would run the Hexagonal dependency arrow backwards.
    See ADR-0005.
    """
    return f"{int(amount):,}".replace(",", ".")


def format_qty(value: Decimal) -> str:
    """Drop trailing zero decimals from a ``Numeric(18, 3)`` quantity.

    The column returns ``"100.000"`` for 100 whole units; a person reads that as
    *"100 nghìn"*, not *"100 units"*. CLAUDE.md kỷ luật #26 documents a real
    incident with this exact shape (``formatQty`` on the frontend, "sổ ghi
    100.000 cho 100 viên — Chain đọc thành một trăm nghìn"). Real fractional
    quantities (37.5) are kept as-is.
    """
    return f"{value.normalize():f}"


def format_date_vn(value: date) -> str:
    """``dd/mm/yyyy`` — the format already used on printed receipts
    (``sales.interface.receipt_rendering``), reused here for VN-facing CSV
    report exports (PROJECT_STATE §7dt)."""
    return value.strftime("%d/%m/%Y")
