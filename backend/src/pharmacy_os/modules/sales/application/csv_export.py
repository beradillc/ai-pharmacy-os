"""Shaping a revenue-report row into CSV cells — framework-free and pure.

Same convention as ``core/audit/csv_export.py`` (PROJECT_STATE §7al): a module-level
``*_HEADER`` tuple plus a pure ``*_to_row`` function, kept apart from the query/service
so the column contract has one home and is unit-testable without a database or an
HTTP layer.
"""

from __future__ import annotations

from pharmacy_os.modules.sales.application.dto import RevenueRow
from pharmacy_os.modules.sales.domain.ports import DrugSalesAggRow

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


#: Column order for the top-selling-drugs export (Sprint 7 report đợt 2,
#: PROJECT_STATE §7an/§7ba). ``rank`` is 1-based within the file, computed by the
#: caller after sorting — the underlying query (``aggregate_sold_by_drug``) has no
#: notion of rank, only unordered per-drug totals.
#:
#: No ``drug_name`` column: naming the drug lives in ``catalog``, and joining it in
#: would be a cross-module read (same documented limitation as the TT18 ledger book
#: export in ``compliance/application/csv_export.py`` — "phần đầu sổ chưa kết xuất
#: được"). This file carries ``drug_id`` only; resolving names is left to whoever
#: consumes the CSV, same tradeoff already accepted for the ledger book.
TOP_DRUGS_CSV_HEADER: tuple[str, ...] = (
    "rank",
    "drug_id",
    "branch_id",
    "quantity_sold",
    "revenue",
)


def drug_sales_row_to_csv(row: DrugSalesAggRow, *, rank: int) -> list[str]:
    """One top-seller row as a list of string cells, aligned to
    :data:`TOP_DRUGS_CSV_HEADER`. ``rank`` is supplied by the caller (1-based
    position after sorting), not stored on :class:`DrugSalesAggRow` itself."""
    return [
        str(rank),
        str(row.drug_id),
        str(row.branch_id),
        str(row.quantity_sold),
        str(row.revenue),
    ]
