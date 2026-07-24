"""The audit **dashboard** read model — the fuller Sprint 7 surface over the trail.

Separate from :class:`AuditQueryService` (the minimal ``/audit-logs`` query) on
purpose, along the two axes that make this a distinct capability:

* **Its own permission, ``audit.dashboard.read``.** The trail records *who read whose
  health record*; the dashboard is a lens built for exactly that data, so it is a
  sensitive surface in its own right and gets a permission that can be granted to a
  branch manager without also handing them the raw ``audit.read`` query. Reusing
  ``audit.read`` would couple two access decisions that the business wants separate
  (PROJECT_STATE §7ak, duyệt GĐ full-auto 2026-07-24).
* **Entity filter + export.** It filters on the ``target_type`` dimension the minimal
  query never exposed, and it streams the matching rows as CSV for an inspection or a
  periodic review — neither of which the minimal query does.

Both guards from :class:`AuditQueryService` still hold and are not optional: tenant
scope comes from the context (never a parameter, no cross-tenant view), and every
entry point checks the permission before touching the database.

Export is **paged internally** (never one unbounded query): the table can be very
large, so :meth:`export_rows` walks it in batches and yields row-by-row, keeping
memory flat regardless of how many rows match.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit.csv_export import entry_to_row
from pharmacy_os.core.audit.entry import AuditAction
from pharmacy_os.core.audit.ports import AuditLogRepository
from pharmacy_os.core.audit.query import AuditPage
from pharmacy_os.core.audit.repository import SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ValidationError
from pharmacy_os.core.security import require_permission

AUDIT_DASHBOARD_READ = "audit.dashboard.read"

#: One exported entry as CSV cells. Aliased at module scope so the annotation does
#: not resolve ``list`` to this class's ``list`` method (which shadows the builtin
#: inside the class body).
CsvRow = list[str]

#: How many rows an export pulls per round-trip. Big enough to amortise query cost,
#: small enough that one batch never dominates memory. Not user-tunable: it is an
#: internal streaming detail, not a page size the caller sees.
_EXPORT_BATCH = 500

RepoFactory = Callable[[AsyncSession], AuditLogRepository]


class AuditDashboardService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repo_factory: RepoFactory = SqlAlchemyAuditLogRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repo_factory = repo_factory

    @staticmethod
    def _validate_window(occurred_from: datetime | None, occurred_to: datetime | None) -> None:
        if occurred_from is not None and occurred_to is not None and occurred_from > occurred_to:
            raise ValidationError("Khoảng thời gian không hợp lệ: 'từ' sau 'đến'")

    async def list(
        self,
        ctx: RequestContext,
        *,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        actor_user_id: UUID | None = None,
        action: AuditAction | None = None,
        target_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditPage:
        require_permission(ctx, AUDIT_DASHBOARD_READ)
        self._validate_window(occurred_from, occurred_to)

        async with self._session_factory() as session:
            repo = self._repo_factory(session)
            entries = await repo.list(
                ctx.tenant_id,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                limit=limit,
                offset=offset,
            )
            total = await repo.count(
                ctx.tenant_id,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
            )
        return AuditPage(entries=entries, total=total, limit=limit, offset=offset)

    async def export_rows(
        self,
        ctx: RequestContext,
        *,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        actor_user_id: UUID | None = None,
        action: AuditAction | None = None,
        target_type: str | None = None,
    ) -> AsyncIterator[CsvRow]:
        """Every matching entry (same filters as :meth:`list`) as CSV cells, newest
        first, walking the trail in :data:`_EXPORT_BATCH`-sized pages.

        Permission and the time window are checked **eagerly** here — this method is a
        coroutine, not itself a generator, so ``await``-ing it raises 403/422 *before*
        any bytes are streamed, rather than mid-response once a 200 header is already
        out. The lazy paging lives in :meth:`_export_stream`. The header row is not
        included: the caller writes it once, then feeds each yielded row to :mod:`csv`.
        """
        require_permission(ctx, AUDIT_DASHBOARD_READ)
        self._validate_window(occurred_from, occurred_to)
        return self._export_stream(
            ctx,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
        )

    async def _export_stream(
        self,
        ctx: RequestContext,
        *,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        actor_user_id: UUID | None,
        action: AuditAction | None,
        target_type: str | None,
    ) -> AsyncIterator[CsvRow]:
        """Lazy pager behind :meth:`export_rows`. The ordering is the repository's
        stable ``(occurred_at desc, id desc)``, so paging by offset visits every row
        exactly once for a trail that only ever grows while an export runs."""
        offset = 0
        async with self._session_factory() as session:
            repo = self._repo_factory(session)
            while True:
                batch = await repo.list(
                    ctx.tenant_id,
                    occurred_from=occurred_from,
                    occurred_to=occurred_to,
                    actor_user_id=actor_user_id,
                    action=action,
                    target_type=target_type,
                    limit=_EXPORT_BATCH,
                    offset=offset,
                )
                for entry in batch:
                    yield entry_to_row(entry)
                if len(batch) < _EXPORT_BATCH:
                    return
                offset += _EXPORT_BATCH
