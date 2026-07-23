"""SQLAlchemy implementation of :class:`AuditLogRepository`.

Append and read only — there is no method that can change or remove a row, which is
what makes "append-only" a property of the code rather than a promise in a comment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.audit.entry import AuditAction, AuditEntry
from pharmacy_os.core.audit.models import AuditLogORM


def _as_utc(value: datetime) -> datetime:
    """SQLite drops the timezone that ``DateTime(timezone=True)`` preserves on
    Postgres; everything is written in UTC, so re-attaching it is a restatement."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_domain(row: AuditLogORM) -> AuditEntry:
    return AuditEntry(
        id=row.id,
        tenant_id=row.tenant_id,
        actor_user_id=row.actor_user_id,
        action=AuditAction(row.action),
        target_type=row.target_type,
        target_id=row.target_id,
        occurred_at=_as_utc(row.occurred_at),
        context=dict(row.context or {}),
    )


def _to_orm(entry: AuditEntry) -> AuditLogORM:
    return AuditLogORM(
        id=entry.id,
        tenant_id=entry.tenant_id,
        actor_user_id=entry.actor_user_id,
        action=entry.action.value,
        target_type=entry.target_type,
        target_id=entry.target_id,
        occurred_at=entry.occurred_at,
        context=dict(entry.context),
    )


class SqlAlchemyAuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: AuditEntry) -> None:
        self._session.add(_to_orm(entry))
        await self._session.flush()

    def _filters(
        self,
        tenant_id: UUID,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        actor_user_id: UUID | None,
        action: AuditAction | None,
    ) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = [AuditLogORM.tenant_id == tenant_id]
        if occurred_from is not None:
            clauses.append(AuditLogORM.occurred_at >= occurred_from)
        if occurred_to is not None:
            clauses.append(AuditLogORM.occurred_at <= occurred_to)
        if actor_user_id is not None:
            clauses.append(AuditLogORM.actor_user_id == actor_user_id)
        if action is not None:
            clauses.append(AuditLogORM.action == action.value)
        return clauses

    async def list(
        self,
        tenant_id: UUID,
        *,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        actor_user_id: UUID | None = None,
        action: AuditAction | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEntry]:
        stmt = (
            select(AuditLogORM)
            .where(*self._filters(tenant_id, occurred_from, occurred_to, actor_user_id, action))
            # id as tie-breaker: several entries can share a timestamp (a failed
            # login and the lock it triggers), and a paged read needs a total order.
            .order_by(AuditLogORM.occurred_at.desc(), AuditLogORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def count(
        self,
        tenant_id: UUID,
        *,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        actor_user_id: UUID | None = None,
        action: AuditAction | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AuditLogORM)
            .where(*self._filters(tenant_id, occurred_from, occurred_to, actor_user_id, action))
        )
        return int((await self._session.execute(stmt)).scalar_one())
