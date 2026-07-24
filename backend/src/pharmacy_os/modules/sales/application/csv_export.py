"""Shaping a revenue-report row into CSV cells — framework-free and pure.

Same convention as ``core/audit/csv_export.py`` (PROJECT_STATE §7al): a module-level
``*_HEADER`` tuple plus a pure ``*_to_row`` function, kept apart from the query/service
so the column contract has one home and is unit-testable without a database or an
HTTP layer.
"""

from __future__ import annotations

from pharmacy_os.modules.sales.application.dto import RevenueRow

#: Column order for the exported file. Stable: append new columns at the end
#: rather than reordering (see ``core/audit/csv_export.py`` for why).
REVENUE_CSV_HEADER: tuple[str, ...] = (
    "period_start",
    "branch_id",
    "currency",
    "order_count",
    "revenue_total",
)


def revenue_row_to_csv(row: RevenueRow) -> list[str]:
    """One revenue-report bucket as a list of string cells, aligned to
    :data:`REVENUE_CSV_HEADER`."""
    return [
        row.period_start.isoformat(),
        str(row.branch_id),
        row.currency,
        str(row.order_count),
        str(row.revenue_total),
    ]
