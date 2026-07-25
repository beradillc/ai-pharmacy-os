"""``/reports`` — Sprint 7 "report xuất khẩu" (PROJECT_STATE §7am/§7an).

Composition-root surface, not a business module: it exports data two modules
already own, without either importing the other. ``sales`` and ``inventory`` never
import each other (module-independence); each exposes its own report method
(``SalesService.revenue_report_rows`` / ``InventoryService.stock_report_rows``), and
this file is where both get wired to HTTP — the same role ``cross_module.py`` plays
for event subscriptions, just for a read instead of a reaction.

No new permission: revenue reuses ``sales.read``, stock reuses ``inventory.read`` —
this is not more sensitive than what the POS/inventory UI already shows a cashier or
warehouse clerk (PROJECT_STATE §7am, Chain duyệt). Both exports are CSV, streamed via
the same :func:`pharmacy_os.core.http.csv_stream_body` the audit dashboard uses
(§7al) — the trail can be large and so can a busy tenant's sales/stock, so neither
endpoint ever builds its file in memory.

Two endpoints, both read-only, both requiring a token (401 unauthenticated,
403 without the reused permission):

* ``GET /reports/revenue/export`` — revenue grouped by day/week/month, optionally
  narrowed to one branch, as CSV.
* ``GET /reports/inventory/stock/export`` — current on-hand by lot + expiry date,
  optionally narrowed to one branch, as CSV.
* ``GET /reports/top-drugs/export`` — top-selling drugs by quantity or revenue over
  a window, as CSV (Sprint 7 "report đợt 2", PROJECT_STATE §7ba). Reuses
  ``sales.read`` and the ``aggregate_sold_by_drug`` query already built for
  ``analytics`` (PROJECT_STATE §7am) — sorting/ranking/limiting is presentation-only,
  done here rather than in ``SalesService``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from pharmacy_os.api.deps import get_context
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.http import csv_stream_body
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.application.csv_export import STOCK_CSV_HEADER, stock_row_to_csv
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.application.csv_export import (
    REVENUE_CSV_HEADER,
    TOP_DRUGS_CSV_HEADER,
    drug_sales_row_to_csv,
    revenue_row_to_csv,
)
from pharmacy_os.modules.sales.application.dto import RevenueGranularity

router = APIRouter(prefix="/reports", tags=["reports"])


def _sales_service(request: Request) -> SalesService:
    service: SalesService = request.app.state.container.resolve(SalesService)
    return service


def _inventory_service(request: Request) -> InventoryService:
    service: InventoryService = request.app.state.container.resolve(InventoryService)
    return service


@router.get("/revenue/export")
async def export_revenue(
    date_from: date = Query(..., description="Từ ngày (bao gồm)"),
    date_to: date = Query(..., description="Đến ngày (bao gồm)"),
    granularity: RevenueGranularity = Query(
        RevenueGranularity.DAY, description="Nhóm theo ngày/tuần/tháng"
    ),
    branch_id: UUID | None = Query(None, description="Lọc theo chi nhánh (bỏ trống = toàn chuỗi)"),
    sold_by_user_id: UUID | None = Query(
        None, description="Lọc theo nhân viên bán (bỏ trống = mọi nhân viên)"
    ),
    service: SalesService = Depends(_sales_service),
    ctx: RequestContext = Depends(get_context),
) -> StreamingResponse:
    """Revenue grouped by period/branch/currency over ``[date_from, date_to]``, as a
    CSV attachment. Requires ``sales.read``; the permission and the date window are
    checked before any bytes stream (see :meth:`SalesService.revenue_report_rows`).

    ``sold_by_user_id`` narrows to one salesperson (PROJECT_STATE §7ao); orders
    recorded before that column existed have no salesperson and so never appear in a
    per-salesperson report, only in the unfiltered one.
    """
    rows = await service.revenue_report_rows(
        ctx,
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
        branch_id=branch_id,
        sold_by_user_id=sold_by_user_id,
    )
    csv_rows = (revenue_row_to_csv(row) async for row in rows)
    filename = f"revenue-{ctx.tenant_id}-{date_from}_{date_to}.csv"
    return StreamingResponse(
        csv_stream_body(REVENUE_CSV_HEADER, csv_rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventory/stock/export")
async def export_stock(
    branch_id: UUID | None = Query(None, description="Lọc theo chi nhánh (bỏ trống = toàn chuỗi)"),
    service: InventoryService = Depends(_inventory_service),
    ctx: RequestContext = Depends(get_context),
) -> StreamingResponse:
    """Current on-hand by lot + expiry date, soonest-expiring first, as a CSV
    attachment. Requires ``inventory.read`` (see
    :meth:`InventoryService.stock_report_rows`)."""
    rows = await service.stock_report_rows(ctx, branch_id=branch_id)
    csv_rows = (stock_row_to_csv(row) async for row in rows)
    filename = f"stock-{ctx.tenant_id}.csv"
    return StreamingResponse(
        csv_stream_body(STOCK_CSV_HEADER, csv_rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/top-drugs/export")
async def export_top_drugs(
    date_from: date = Query(..., description="Từ ngày (bao gồm)"),
    date_to: date = Query(..., description="Đến ngày (bao gồm)"),
    branch_id: UUID | None = Query(None, description="Lọc theo chi nhánh (bỏ trống = toàn chuỗi)"),
    sort_by: Literal["quantity", "revenue"] = Query(
        "quantity", description="Xếp hạng theo số lượng bán ròng hay doanh thu ròng"
    ),
    limit: int = Query(20, ge=1, le=500, description="Số thuốc tối đa trong file (đã xếp hạng)"),
    service: SalesService = Depends(_sales_service),
    ctx: RequestContext = Depends(get_context),
) -> StreamingResponse:
    """Top-selling drugs (net of returns) over ``[date_from, date_to]``, as a CSV
    attachment. Requires ``sales.read`` (reused, see
    :meth:`SalesService.aggregate_sold_by_drug`).

    Ranking and ``limit`` are applied here, not in the service — the underlying
    query returns every drug sold in the window (bounded by catalogue size, already
    a single non-streamed list), so sorting/truncating it for display is a
    presentation concern.
    """
    agg_rows = await service.aggregate_sold_by_drug(
        ctx, date_from=date_from, date_to=date_to, branch_id=branch_id
    )
    key = (lambda r: r.quantity_sold) if sort_by == "quantity" else (lambda r: r.revenue)
    ranked = sorted(agg_rows, key=key, reverse=True)[:limit]

    async def csv_rows() -> AsyncIterator[Sequence[str]]:
        for i, row in enumerate(ranked, start=1):
            yield drug_sales_row_to_csv(row, rank=i)

    filename = f"top-drugs-{ctx.tenant_id}-{date_from}_{date_to}.csv"
    return StreamingResponse(
        csv_stream_body(TOP_DRUGS_CSV_HEADER, csv_rows()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
