"""Shaping a stock-report row into CSV cells — framework-free and pure.

Same convention as ``core/audit/csv_export.py`` (PROJECT_STATE §7al): a module-level
``*_HEADER`` tuple plus a pure ``*_to_row`` function.

**Vietnamese-readable, 2026-08-04 (ROADMAP V3-5, ADR-0005):** see
``sales/application/csv_export.py`` for the full rationale — same treatment here.
``drug_names``/``branch_names`` are resolved by the composition root
(``api/v1/reports.py``) in bounded chunks (this report streams, unlike revenue/
top-drugs) and passed in as plain dicts; this file still does no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pharmacy_os.core.formatting import format_date_vn, format_qty
from pharmacy_os.modules.inventory.application.dto import StockReportItem

#: Column order for the exported file. Stable: append new columns at the end
#: rather than reordering (see ``core/audit/csv_export.py`` for why).
STOCK_CSV_HEADER: tuple[str, ...] = (
    "Mã lô (hệ thống)",
    "Mã thuốc (hệ thống)",
    "Tên thuốc",
    "Mã chi nhánh",
    "Chi nhánh",
    "Số lô",
    "Hạn dùng",
    "Số lượng",
)


def stock_row_to_csv(
    row: StockReportItem,
    drug_names: Mapping[UUID, str],
    branch_names: Mapping[UUID, str],
) -> list[str]:
    """One batch's on-hand as a list of string cells, aligned to :data:`STOCK_CSV_HEADER`.

    A missing id in either map falls back to the raw id (see
    ``sales/application/csv_export.py::drug_sales_row_to_csv`` for why: never blank
    a cell, the row must still identify itself on its own).
    """
    return [
        str(row.batch_id),
        str(row.drug_id),
        drug_names.get(row.drug_id, str(row.drug_id)),
        str(row.branch_id),
        branch_names.get(row.branch_id, str(row.branch_id)),
        row.lot_no,
        format_date_vn(row.expiry_date),
        format_qty(row.quantity),
    ]
