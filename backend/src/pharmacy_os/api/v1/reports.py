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

**Vietnamese-readable, 2026-08-04 (ROADMAP V3-5, ADR-0005):** all three exports were
"toàn mã máy, không đọc được" — UUID ids, ISO dates, raw ``Decimal``, no drug/branch
name anywhere. This file now resolves ``drug_id``/``branch_id`` → display name once
per request and hands the maps to the modules' pure ``*_row_to_csv`` functions, under
a **fixed system identity** (same pattern as ``CatalogDrugInfoProvider`` in
``cross_module.py``): a cashier exporting revenue holds only ``sales.read`` and must
not need ``catalog.read``/extra ``iam`` grants just so the file prints a name instead
of a UUID.
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
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.iam.application import IamService
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

# Same fixed system identity as api/v1/cross_module.py's ``_SYSTEM_USER`` — a
# composition-root adapter running under nobody's real token. Re-declared here
# (not imported) because that name is private to cross_module.py and the two files
# have no other reason to depend on each other; both must stay equal to remain the
# same auditable "system" actor in logs.
_SYSTEM_USER = UUID("00000000-0000-0000-0000-00005a1e5001")

#: Chunk size for resolving drug names against the streamed stock report. Matches
#: ``InventoryService._STOCK_REPORT_BATCH`` (500) so a chunk boundary always lines
#: up with a DB page boundary — not required for correctness, just avoids the
#: report doing two different batch sizes for no reason.
_DRUG_NAME_CHUNK = 500


def _sales_service(request: Request) -> SalesService:
    service: SalesService = request.app.state.container.resolve(SalesService)
    return service


def _inventory_service(request: Request) -> InventoryService:
    service: InventoryService = request.app.state.container.resolve(InventoryService)
    return service


def _catalog_service(request: Request) -> CatalogService:
    service: CatalogService = request.app.state.container.resolve(CatalogService)
    return service


def _iam_service(request: Request) -> IamService:
    service: IamService = request.app.state.container.resolve(IamService)
    return service


async def _branch_names(iam: IamService, tenant_id: UUID) -> dict[UUID, str]:
    """Every active branch's name for the tenant, under the fixed system identity.

    Not chunked: a tenant's branch count is a handful of outlets (see
    ``IamService.branch_names``), so one call per report request is cheap regardless
    of how large the report itself is.
    """
    system_ctx = RequestContext(
        tenant_id=tenant_id,
        branch_id=tenant_id,
        user_id=_SYSTEM_USER,
        permissions=frozenset({"iam.user.read"}),
    )
    return await iam.branch_names(system_ctx)


async def _drug_names(
    catalog: CatalogService, tenant_id: UUID, drug_ids: Sequence[UUID]
) -> dict[UUID, str]:
    """Bulk drug-name lookup under the fixed system identity. ``drug_ids`` is the
    caller's job to bound — see :func:`_chunked` for the streamed stock export,
    which cannot pass every id in the report at once."""
    if not drug_ids:
        return {}
    system_ctx = RequestContext(
        tenant_id=tenant_id,
        branch_id=tenant_id,
        user_id=_SYSTEM_USER,
        permissions=frozenset({"catalog.read"}),
    )
    return await catalog.drug_names(drug_ids, system_ctx)


async def _chunked[T](items: AsyncIterator[T], size: int) -> AsyncIterator[list[T]]:
    """Group an async stream into lists of at most ``size`` items.

    Exists so the stock export can resolve drug names in bulk (one query per chunk)
    without ever holding the *whole* report in memory — only ``size`` rows plus
    their resolved names at a time, same flat-memory intent
    ``InventoryService.stock_report_rows`` documents for the underlying DB paging.
    """
    batch: list[T] = []
    async for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


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
    iam: IamService = Depends(_iam_service),
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
    branch_names = await _branch_names(iam, ctx.tenant_id)
    csv_rows = (revenue_row_to_csv(row, branch_names) async for row in rows)
    filename = f"doanh-thu-{ctx.tenant_id}-{date_from}_{date_to}.csv"
    return StreamingResponse(
        csv_stream_body(REVENUE_CSV_HEADER, csv_rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventory/stock/export")
async def export_stock(
    branch_id: UUID | None = Query(None, description="Lọc theo chi nhánh (bỏ trống = toàn chuỗi)"),
    service: InventoryService = Depends(_inventory_service),
    catalog: CatalogService = Depends(_catalog_service),
    iam: IamService = Depends(_iam_service),
    ctx: RequestContext = Depends(get_context),
) -> StreamingResponse:
    """Current on-hand by lot + expiry date, soonest-expiring first, as a CSV
    attachment. Requires ``inventory.read`` (see
    :meth:`InventoryService.stock_report_rows`).

    Drug names are resolved in chunks of :data:`_DRUG_NAME_CHUNK` as the underlying
    stream is consumed (see :func:`_chunked`) — the report itself can be arbitrarily
    large, and materialising every id up front to do one bulk lookup would defeat the
    flat-memory streaming the service already guarantees.
    """
    rows = await service.stock_report_rows(ctx, branch_id=branch_id)
    branch_names = await _branch_names(iam, ctx.tenant_id)

    async def csv_rows() -> AsyncIterator[Sequence[str]]:
        async for batch in _chunked(rows, _DRUG_NAME_CHUNK):
            drug_ids = list({item.drug_id for item in batch})
            drug_names = await _drug_names(catalog, ctx.tenant_id, drug_ids)
            for item in batch:
                yield stock_row_to_csv(item, drug_names, branch_names)

    filename = f"ton-kho-{ctx.tenant_id}.csv"
    return StreamingResponse(
        csv_stream_body(STOCK_CSV_HEADER, csv_rows()),
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
    catalog: CatalogService = Depends(_catalog_service),
    iam: IamService = Depends(_iam_service),
    ctx: RequestContext = Depends(get_context),
) -> StreamingResponse:
    """Top-selling drugs (net of returns) over ``[date_from, date_to]``, as a CSV
    attachment. Requires ``sales.read`` (reused, see
    :meth:`SalesService.aggregate_sold_by_drug`).

    Ranking and ``limit`` are applied here, not in the service — the underlying
    query returns every drug sold in the window (bounded by catalogue size, already
    a single non-streamed list), so sorting/truncating it for display is a
    presentation concern. ``limit`` is capped at 500, so one un-chunked
    :func:`_drug_names` call after ranking is enough — no need for :func:`_chunked`
    here the way :func:`export_stock` needs it.
    """
    agg_rows = await service.aggregate_sold_by_drug(
        ctx, date_from=date_from, date_to=date_to, branch_id=branch_id
    )
    key = (lambda r: r.quantity_sold) if sort_by == "quantity" else (lambda r: r.revenue)
    ranked = sorted(agg_rows, key=key, reverse=True)[:limit]

    branch_names = await _branch_names(iam, ctx.tenant_id)
    drug_names = await _drug_names(catalog, ctx.tenant_id, list({r.drug_id for r in ranked}))

    async def csv_rows() -> AsyncIterator[Sequence[str]]:
        for i, row in enumerate(ranked, start=1):
            yield drug_sales_row_to_csv(
                row, rank=i, drug_names=drug_names, branch_names=branch_names
            )

    filename = f"thuoc-ban-chay-{ctx.tenant_id}-{date_from}_{date_to}.csv"
    return StreamingResponse(
        csv_stream_body(TOP_DRUGS_CSV_HEADER, csv_rows()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
