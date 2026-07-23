"""``GET /audit-logs`` — read the trail back.

Lives in the ``api`` layer rather than a module because auditing is kernel
infrastructure owned by no business module (same reasoning as ``health``).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from pharmacy_os.api.deps import get_context
from pharmacy_os.core.audit.entry import AuditAction, AuditEntry
from pharmacy_os.core.audit.query import AuditQueryService
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


class AuditPageResponse(BaseModel):
    items: list[AuditEntryResponse]
    total: int
    limit: int
    offset: int


def _service(request: Request) -> AuditQueryService:
    service: AuditQueryService = request.app.state.container.resolve(AuditQueryService)
    return service


router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=AuditPageResponse)
async def list_audit_logs(
    service: AuditQueryService = Depends(_service),
    ctx: RequestContext = Depends(get_context),
    occurred_from: datetime | None = Query(None, description="Từ thời điểm (ISO 8601)"),
    occurred_to: datetime | None = Query(None, description="Đến thời điểm (ISO 8601)"),
    actor_user_id: UUID | None = Query(None, description="Lọc theo người thực hiện"),
    action: AuditAction | None = Query(None, description="Lọc theo loại hành vi"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditPageResponse:
    """Entries for the caller's own tenant, newest first. Requires ``audit.read``."""
    page = await service.list(
        ctx,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        actor_user_id=actor_user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return AuditPageResponse(
        items=[AuditEntryResponse.of(e) for e in page.entries],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
