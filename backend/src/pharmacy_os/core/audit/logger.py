"""Audit logger — persists every recorded action, and mirrors it to the log stream.

Both sinks, not one instead of the other: the table is what an inspection queries
(NĐ 356/2025 Điều 4.2 asks the deployment to show *who accessed what*), the log
stream is what operations tail live and what ships to any external collector.

**Own transaction.** An entry is written on its own session rather than joining the
caller's unit of work, so recording never depends on where in a use-case the call
sits — several call sites record after their business transaction has already
committed.

**Failures propagate.** A failed audit write is not swallowed: the audit table lives
in the same database as the business data, so an insert that fails means the
business write was almost certainly failing too. Catching it would not keep the
pharmacy trading, it would only hide that the trail has a hole. The structlog line
is emitted *before* the insert, so even on a failure the fact is not lost entirely —
it is merely not queryable.
"""

from __future__ import annotations

from collections.abc import Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit.entry import AuditEntry
from pharmacy_os.core.audit.ports import AuditLogRepository
from pharmacy_os.core.audit.repository import SqlAlchemyAuditLogRepository

_log = structlog.get_logger("audit")

RepoFactory = Callable[[AsyncSession], AuditLogRepository]


class AuditLogger:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repo_factory: RepoFactory = SqlAlchemyAuditLogRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repo_factory = repo_factory

    async def record(self, entry: AuditEntry) -> None:
        _log.info(
            "audit",
            audit_id=str(entry.id),
            tenant_id=str(entry.tenant_id),
            actor_user_id=str(entry.actor_user_id) if entry.actor_user_id else None,
            action=entry.action.value,
            target_type=entry.target_type,
            target_id=entry.target_id,
            occurred_at=entry.occurred_at.isoformat(),
            context=entry.context,
        )
        async with self._session_factory() as session:
            await self._repo_factory(session).add(entry)
            await session.commit()
