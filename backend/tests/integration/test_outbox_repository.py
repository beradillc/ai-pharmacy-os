"""Persistence contract for the outbox repository against a real (SQLite) session.

Covers what the in-memory relay tests can't: the due-filter and ordering of
``claim_pending``, the unique constraint on ``event_id``, and that the mark_*
transitions round-trip through the table.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.outbox import (
    OutboxRecord,
    OutboxStatus,
    SqlAlchemyOutboxRepository,
)
from pharmacy_os.core.outbox.models import OutboxEventORM


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


async def _age_row(
    session_factory: async_sessionmaker[AsyncSession],
    event_id: UUID,
    *,
    status: OutboxStatus,
    created_at: datetime,
) -> None:
    """Backdate a row. ``created_at`` is a server default, so a test that cares about
    age has to set it after the fact."""
    async with session_factory() as session:
        await session.execute(
            update(OutboxEventORM)
            .where(OutboxEventORM.event_id == event_id)
            .values(status=status.value, created_at=created_at)
        )
        await session.commit()


async def _surviving_event_ids(session_factory: async_sessionmaker[AsyncSession]) -> set[UUID]:
    async with session_factory() as session:
        rows = await session.execute(select(OutboxEventORM.event_id))
        return set(rows.scalars().all())


async def test_purge_deletes_only_finished_rows_past_the_cutoff(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    old_published = _record(occurred_at=now)
    recent_published = _record(occurred_at=now)
    old_pending = _record(occurred_at=now)
    old_failed = _record(occurred_at=now)
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        for rec in (old_published, recent_published, old_pending, old_failed):
            await repo.add(rec)
        await session.commit()

    await _age_row(
        session_factory,
        old_published.event_id,
        status=OutboxStatus.PUBLISHED,
        created_at=now - timedelta(days=60),
    )
    await _age_row(
        session_factory,
        recent_published.event_id,
        status=OutboxStatus.PUBLISHED,
        created_at=now - timedelta(days=1),
    )
    await _age_row(
        session_factory,
        old_pending.event_id,
        status=OutboxStatus.PENDING,
        created_at=now - timedelta(days=3650),
    )
    await _age_row(
        session_factory,
        old_failed.event_id,
        status=OutboxStatus.FAILED,
        created_at=now - timedelta(days=3650),
    )

    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        deleted = await repo.purge_terminal(
            OutboxStatus.PUBLISHED, older_than=now - timedelta(days=30), limit=100
        )
        await session.commit()

    assert deleted == 1
    survivors = await _surviving_event_ids(session_factory)
    assert old_published.event_id not in survivors
    # Inside the window, undelivered, and a dead letter: all untouched by this sweep.
    assert recent_published.event_id in survivors
    assert old_pending.event_id in survivors
    assert old_failed.event_id in survivors


async def test_purge_respects_its_batch_limit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    records = [_record(occurred_at=now) for _ in range(5)]
    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        for rec in records:
            await repo.add(rec)
        await session.commit()
    for rec in records:
        await _age_row(
            session_factory,
            rec.event_id,
            status=OutboxStatus.PUBLISHED,
            created_at=now - timedelta(days=60),
        )

    async with session_factory() as session:
        repo = SqlAlchemyOutboxRepository(session)
        deleted = await repo.purge_terminal(
            OutboxStatus.PUBLISHED, older_than=now - timedelta(days=30), limit=2
        )
        await session.commit()

    assert deleted == 2
    assert len(await _surviving_event_ids(session_factory)) == 3
