"""Shaping a revenue-report row into CSV cells — framework-free and pure.

Same convention as ``core/audit/csv_export.py`` (PROJECT_STATE §7al): a module-level
``*_HEADER`` tuple plus a pure ``*_to_row`` function, kept apart from the query/service
so the column contract has one home and is unit-testable without a database or an
HTTP layer.

**Vietnamese-readable, 2026-08-04 (ROADMAP V3-5, ADR-0005):** headers and cell values
switched from machine columns (``period_start``, ``UUID`` ids, raw ``Decimal``) to
Vietnamese labels, ``dd/mm/yyyy`` dates and dot-separated money. ``drug_names``/
``branch_names`` are resolved once per request by the composition root
(``api/v1/reports.py``, under a system identity — sales/inventory never import
catalog/iam directly) and passed in here as plain dicts; this file still does no I/O
of its own. Raw ids are **kept alongside** the new name columns, not replaced — a
support person tracing a discrepancy still needs them, and nothing consumes this file
by column position (the frontend only triggers a browser download, never parses it;
PROJECT_STATE §7dt).
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pharmacy_os.core.formatting import format_date_vn, format_money, format_qty
from pharmacy_os.modules.sales.application.dto import RevenueRow
from pharmacy_os.modules.sales.domain.ports import DrugSalesAggRow

#: Column order for the exported file. Stable: append new columns at the end
#: rather than reordering (see ``core/audit/csv_export.py`` for why).
REVENUE_CSV_HEADER: tuple[str, ...] = (
    "Kỳ báo cáo",
    "Mã chi nhánh",
    "Chi nhánh",
    "Loại tiền",
    "Số đơn",
    "Doanh thu",
)


def revenue_row_to_csv(row: RevenueRow, branch_names: Mapping[UUID, str]) -> list[str]:
    """One revenue-report bucket as a list of string cells, aligned to
    :data:`REVENUE_CSV_HEADER`.

    ``branch_names`` misses a branch only if it was deactivated between the sale and
    the export — the raw id column still identifies the row, same tradeoff as
    :func:`drug_sales_row_to_csv` below.
    """
    return [
        format_date_vn(row.period_start),
        str(row.branch_id),
        branch_names.get(row.branch_id, str(row.branch_id)),
        row.currency,
        str(row.order_count),
        format_money(row.revenue_total),
    ]


#: Column order for the top-selling-drugs export (Sprint 7 report đợt 2,
#: PROJECT_STATE §7an/§7ba). ``rank`` is 1-based within the file, computed by the
#: caller after sorting — the underlying query (``aggregate_sold_by_drug``) has no
#: notion of rank, only unordered per-drug totals.
TOP_DRUGS_CSV_HEADER: tuple[str, ...] = (
    "Hạng",
    "Mã thuốc (hệ thống)",
    "Tên thuốc",
    "Mã chi nhánh",
    "Chi nhánh",
    "Số lượng bán",
    "Doanh thu",
)


def drug_sales_row_to_csv(
    row: DrugSalesAggRow,
    *,
    rank: int,
    drug_names: Mapping[UUID, str],
    branch_names: Mapping[UUID, str],
) -> list[str]:
    """One top-seller row as a list of string cells, aligned to
    :data:`TOP_DRUGS_CSV_HEADER`. ``rank`` is supplied by the caller (1-based
    position after sorting), not stored on :class:`DrugSalesAggRow` itself.

    A ``drug_id``/``branch_id`` missing from its map (deleted after the numbers were
    computed) falls back to the raw id rather than blanking the cell — the row still
    means something on its own, and a blank cell would read as a data-entry mistake.
    """
    return [
        str(rank),
        str(row.drug_id),
        drug_names.get(row.drug_id, str(row.drug_id)),
        str(row.branch_id),
        branch_names.get(row.branch_id, str(row.branch_id)),
        format_qty(row.quantity_sold),
        format_money(row.revenue),
    ]
