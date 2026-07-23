"""Reading the audit trail back — the minimum needed to prove it is queryable.

Scope is deliberately small (docs ROADMAP Sprint 7 still owns the full audit
dashboard/analytics): filter by time window, actor and action, page through the
result. No aggregation, no export, no cross-tenant view — building those here would
duplicate work Sprint 7 is already scheduled to do.

Two guards that are not optional:

* **Tenant scoping comes from the context, never from a parameter.** There is no way
  to ask this service for another tenant's trail.
* **``audit.read`` is required.** The trail names who touched patient data; reading
  it is itself a privileged act.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit.entry import AuditAction, AuditEntry
from pharmacy_os.core.audit.ports import AuditLogRepository
from pharmacy_os.core.audit.repository import SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ValidationError
from pharmacy_os.core.security import require_permission

AUDIT_READ = "audit.read"

RepoFactory = Callable[[AsyncSession], AuditLogRepository]


@dataclass(frozen=True, slots=True)
class AuditPage:
    """One page of entries plus the total, so a caller can page without guessing."""

    entries: list[AuditEntry]
    total: int
    limit: int
    offset: int


class AuditQueryService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repo_factory: RepoFactory = SqlAlchemyAuditLogRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repo_factory = repo_factory

    async def list(
        self,
        ctx: RequestContext,
        *,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        actor_user_id: UUID | None = None,
        action: AuditAction | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditPage:
        require_permission(ctx, AUDIT_READ)
        if occurred_from is not None and occurred_to is not None and occurred_from > occurred_to:
            raise ValidationError("Khoảng thời gian không hợp lệ: 'từ' sau 'đến'")

        async with self._session_factory() as session:
            repo = self._repo_factory(session)
            entries = await repo.list(
                ctx.tenant_id,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                actor_user_id=actor_user_id,
                action=action,
                limit=limit,
                offset=offset,
            )
            total = await repo.count(
                ctx.tenant_id,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                actor_user_id=actor_user_id,
                action=action,
            )
        return AuditPage(entries=entries, total=total, limit=limit, offset=offset)
