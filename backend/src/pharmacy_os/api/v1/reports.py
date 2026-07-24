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
"""

from __future__ import annotations

from datetime import date
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
    service: SalesService = Depends(_sales_service),
    ctx: RequestContext = Depends(get_context),
) -> StreamingResponse:
    """Revenue grouped by period/branch/currency over ``[date_from, date_to]``, as a
    CSV attachment. Requires ``sales.read``; the permission and the date window are
    checked before any bytes stream (see :meth:`SalesService.revenue_report_rows`).

    No salesperson filter: ``SalesOrder`` persists no actor/cashier column today —
    documented gap, PROJECT_STATE §7an.
    """
    rows = await service.revenue_report_rows(
        ctx,
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
        branch_id=branch_id,
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
