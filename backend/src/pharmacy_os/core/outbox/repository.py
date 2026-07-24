"""SQLAlchemy implementation of :class:`OutboxRepository`."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.outbox.models import OutboxEventORM
from pharmacy_os.core.outbox.ports import TerminalStatus
from pharmacy_os.core.outbox.record import OutboxRecord, OutboxStatus


def _as_utc(value: datetime) -> datetime:
    """SQLite drops the tz that ``DateTime(timezone=True)`` keeps on Postgres; every
    value is written in UTC, so re-attaching it is a restatement, not a change."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_domain(row: OutboxEventORM) -> OutboxRecord:
    return OutboxRecord(
        id=row.id,
        event_id=row.event_id,
        event_type=row.event_type,
        tenant_id=row.tenant_id,
        payload=dict(row.payload),
        occurred_at=_as_utc(row.occurred_at),
        status=OutboxStatus(row.status),
        retry_count=row.retry_count,
        next_attempt_at=_as_utc(row.next_attempt_at) if row.next_attempt_at else None,
        published_at=_as_utc(row.published_at) if row.published_at else None,
        last_error=row.last_error,
    )


def _to_orm(record: OutboxRecord) -> OutboxEventORM:
    return OutboxEventORM(
        id=record.id,
        event_id=record.event_id,
        event_type=record.event_type,
        tenant_id=record.tenant_id,
        payload=dict(record.payload),
        status=record.status.value,
        occurred_at=record.occurred_at,
        retry_count=record.retry_count,
        next_attempt_at=record.next_attempt_at,
        published_at=record.published_at,
        last_error=record.last_error,
    )


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: OutboxRecord) -> None:
        self._session.add(_to_orm(record))
        await self._session.flush()

    async def claim_pending(self, now: datetime, *, limit: int) -> list[OutboxRecord]:
        stmt = (
            select(OutboxEventORM)
            .where(OutboxEventORM.status == OutboxStatus.PENDING.value)
            .where(
                or_(
                    OutboxEventORM.next_attempt_at.is_(None),
                    OutboxEventORM.next_attempt_at <= now,
                )
            )
            .order_by(OutboxEventORM.occurred_at, OutboxEventORM.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(row) for row in rows]

    async def mark_published(self, record_id: UUID, published_at: datetime) -> None:
        await self._update(
            record_id,
            status=OutboxStatus.PUBLISHED.value,
            published_at=published_at,
            last_error=None,
        )

    async def mark_retry(
        self,
        record_id: UUID,
        *,
        retry_count: int,
        next_attempt_at: datetime,
        last_error: str,
    ) -> None:
        await self._update(
            record_id,
            status=OutboxStatus.PENDING.value,
            retry_count=retry_count,
            next_attempt_at=next_attempt_at,
            last_error=last_error,
        )

    async def mark_failed(self, record_id: UUID, *, retry_count: int, last_error: str) -> None:
        await self._update(
            record_id,
            status=OutboxStatus.FAILED.value,
            retry_count=retry_count,
            last_error=last_error,
        )

    async def purge_terminal(
        self, status: TerminalStatus, *, older_than: datetime, limit: int
    ) -> int:
        # Delete by id from a bounded sub-select rather than `DELETE ... LIMIT` (which
        # Postgres does not have) — same statement works on both dialects, and the
        # bound keeps each sweep's transaction short instead of locking the whole table.
        doomed = (
            select(OutboxEventORM.id)
            .where(
                OutboxEventORM.status == status.value,
                OutboxEventORM.created_at < older_than,
            )
            .limit(limit)
        )
        result = await self._session.execute(
            delete(OutboxEventORM).where(OutboxEventORM.id.in_(doomed))
        )
        await self._session.flush()
        # CursorResult on every dialect we run; the base Result type doesn't say so.
        return int(cast("CursorResult[Any]", result).rowcount)

    async def _update(self, record_id: UUID, **values: Any) -> None:
        await self._session.execute(
            update(OutboxEventORM).where(OutboxEventORM.id == record_id).values(**values)
        )
        await self._session.flush()
