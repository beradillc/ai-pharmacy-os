"""``/audit-dashboard`` — the Sprint 7 investigation/inspection lens over the trail.

Kernel infrastructure owned by no business module (same placement as ``audit``),
but a **separate surface** from ``/audit-logs``: it filters on the entity dimension
(``target_type``) the minimal query never exposed, exports the matching rows as CSV,
and is guarded by its own ``audit.dashboard.read`` permission so a branch manager can
be granted it without the raw ``audit.read`` query (PROJECT_STATE §7ak).

Two endpoints, both read-only:

* ``GET /audit-dashboard`` — one page of entries + the total, newest first.
* ``GET /audit-dashboard/export`` — the same filtered set streamed as ``text/csv``.
  Streamed (not built in memory) because the trail can be very large; the service
  pages the database internally.
"""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pharmacy_os.api.deps import get_context
from pharmacy_os.core.audit.csv_export import CSV_HEADER
from pharmacy_os.core.audit.dashboard import AuditDashboardService
from pharmacy_os.core.audit.entry import AuditAction, AuditEntry
from pharmacy_os.core.context import RequestContext


class AuditEntryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    actor_user_id: UUID | None
    action: AuditAction
    target_type: str
    target_id: str | None
    occurred_at: datetime
    context: dict[str, str]

    @classmethod
    def of(cls, entry: AuditEntry) -> AuditEntryResponse:
        return cls(
            id=entry.id,
            tenant_id=entry.tenant_id,
            actor_user_id=entry.actor_user_id,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            occurred_at=entry.occurred_at,
            context=entry.context,
        )


class AuditDashboardPageResponse(BaseModel):
    items: list[AuditEntryResponse]
    total: int
    limit: int
    offset: int


def _service(request: Request) -> AuditDashboardService:
    service: AuditDashboardService = request.app.state.container.resolve(AuditDashboardService)
    return service


router = APIRouter(prefix="/audit-dashboard", tags=["audit"])


@router.get("", response_model=AuditDashboardPageResponse)
async def list_dashboard(
    service: AuditDashboardService = Depends(_service),
    ctx: RequestContext = Depends(get_context),
    occurred_from: datetime | None = Query(None, description="Từ thời điểm (ISO 8601)"),
    occurred_to: datetime | None = Query(None, description="Đến thời điểm (ISO 8601)"),
    actor_user_id: UUID | None = Query(None, description="Lọc theo người thực hiện"),
    action: AuditAction | None = Query(None, description="Lọc theo loại hành vi"),
    target_type: str | None = Query(None, description="Lọc theo loại đối tượng (VD Prescription)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditDashboardPageResponse:
    """Entries for the caller's own tenant, newest first. Requires
    ``audit.dashboard.read``. All filters are optional and ANDed."""
    page = await service.list(
        ctx,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        limit=limit,
        offset=offset,
    )
    return AuditDashboardPageResponse(
        items=[AuditEntryResponse.of(e) for e in page.entries],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


async def _csv_body(rows: AsyncIterator[list[str]]) -> AsyncIterator[str]:
    """Header once, then one CSV line per entry, using :mod:`csv` for quoting so a
    comma or newline inside ``context`` cannot break the file. A single reused buffer
    keeps the whole response flat in memory regardless of row count."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def _drain() -> str:
        line = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return line

    writer.writerow(CSV_HEADER)
    yield _drain()
    async for row in rows:
        writer.writerow(row)
        yield _drain()


@router.get("/export")
async def export_dashboard(
    service: AuditDashboardService = Depends(_service),
    ctx: RequestContext = Depends(get_context),
    occurred_from: datetime | None = Query(None, description="Từ thời điểm (ISO 8601)"),
    occurred_to: datetime | None = Query(None, description="Đến thời điểm (ISO 8601)"),
    actor_user_id: UUID | None = Query(None, description="Lọc theo người thực hiện"),
    action: AuditAction | None = Query(None, description="Lọc theo loại hành vi"),
    target_type: str | None = Query(None, description="Lọc theo loại đối tượng (VD Prescription)"),
) -> StreamingResponse:
    """The filtered trail as a CSV attachment. Requires ``audit.dashboard.read``;
    the permission and time-window checks run before any bytes are streamed."""
    rows = await service.export_rows(
        ctx,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
    )
    filename = f"audit-{ctx.tenant_id}.csv"
    return StreamingResponse(
        _csv_body(rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
