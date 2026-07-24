"""Shaping a stock-report row into CSV cells — framework-free and pure.

Same convention as ``core/audit/csv_export.py`` (PROJECT_STATE §7al): a module-level
``*_HEADER`` tuple plus a pure ``*_to_row`` function.
"""

from __future__ import annotations

from pharmacy_os.modules.inventory.application.dto import StockReportItem

#: Column order for the exported file. Stable: append new columns at the end
#: rather than reordering (see ``core/audit/csv_export.py`` for why).
STOCK_CSV_HEADER: tuple[str, ...] = (
    "batch_id",
    "drug_id",
    "branch_id",
    "lot_no",
    "expiry_date",
    "quantity",
)


def stock_row_to_csv(row: StockReportItem) -> list[str]:
    """One batch's on-hand as a list of string cells, aligned to :data:`STOCK_CSV_HEADER`."""
    return [
        str(row.batch_id),
        str(row.drug_id),
        str(row.branch_id),
        row.lot_no,
        row.expiry_date.isoformat(),
        str(row.quantity),
    ]
