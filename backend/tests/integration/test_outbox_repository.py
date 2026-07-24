"""Persistence contract for the outbox repository against a real (SQLite) session.

Covers what the in-memory relay tests can't: the due-filter and ordering of
``claim_pending``, the unique constraint on ``event_id``, and that the mark_*
transitions round-trip through the table.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.outbox import (
    OutboxRecord,
    OutboxStatus,
    SqlAlchemyOutboxRepository,
)


def _record(*, occurred_at: datetime, event_type: str = "SampleEvent") -> OutboxRecord:
    return OutboxRecord.pending(
        event_id=uuid4(),
        event_type=event_type,
        tenant_id=uuid4(),
        payload={"note": "hi"},
        occurred_at=occurred_at,
    )


async def test_add_and_claim_oldest_first(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    base = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        newer = _record(occurred_at=base + timedelta(minutes=5))
        older = _record(occurred_at=base)
        await repo.add(newer)
        await repo.add(older)
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        claimed = await repo.claim_pending(base + timedelta(hours=1), limit=10)
        assert [c.event_id for c in claimed] == [older.event_id, newer.event_id]


async def test_claim_skips_rows_not_yet_due(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        rec = _record(occurred_at=now)
        await repo.add(rec)
        await repo.mark_retry(
            rec.id,
            retry_count=1,
            next_attempt_at=now + timedelta(minutes=10),
            last_error="boom",
        )
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        assert await repo.claim_pending(now, limit=10) == []  # backoff not elapsed
        due = await repo.claim_pending(now + timedelta(minutes=11), limit=10)
        assert [c.event_id for c in due] == [rec.event_id]
        assert due[0].retry_count == 1 and due[0].last_error == "boom"


async def test_mark_published_leaves_the_row_unclaimd(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        rec = _record(occurred_at=now)
        await repo.add(rec)
        await repo.mark_published(rec.id, now)
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        assert await repo.claim_pending(now + timedelta(hours=1), limit=10) == []


async def test_mark_failed_is_terminal(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        rec = _record(occurred_at=now)
        await repo.add(rec)
        await repo.mark_failed(rec.id, retry_count=5, last_error="dead")
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        # FAILED rows are never re-claimed.
        assert await repo.claim_pending(now + timedelta(days=1), limit=10) == []


async def test_duplicate_event_id_rejected(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    rec = _record(occurred_at=now)
    dupe = OutboxRecord.pending(
        event_id=rec.event_id,  # same event id, different row
        event_type=rec.event_type,
        tenant_id=rec.tenant_id,
        payload=rec.payload,
        occurred_at=now,
    )
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        await repo.add(rec)
        with pytest.raises(IntegrityError):
            await repo.add(dupe)


async def test_claim_respects_limit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    base = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        for i in range(5):
            await repo.add(_record(occurred_at=base + timedelta(seconds=i)))
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        claimed = await repo.claim_pending(base + timedelta(hours=1), limit=2)
        assert len(claimed) == 2
        assert claimed[0].status is OutboxStatus.PENDING
