"""Retention policy in isolation: a fake repository, a frozen clock.

These pin *what may be deleted and when* — the decisions that matter, since the one
thing a bug here can do is destroy an undelivered event. Real SQL deletion is covered
in ``tests/integration/test_outbox_repository.py``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from pharmacy_os.core.outbox import OutboxRetention, OutboxRetentionConfig, OutboxStatus
from pharmacy_os.core.outbox.ports import TerminalStatus

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


class _FakeUow:
    def __init__(self) -> None:
        self.session = self
        self.commits = 0

    async def __aenter__(self) -> _FakeUow:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class _FakeRepo:
    """Rows keyed by id, with the age the retention query filters on."""

    rows: dict[UUID, tuple[OutboxStatus, datetime]] = field(default_factory=dict)

    def seed(self, status: OutboxStatus, created_at: datetime) -> UUID:
        row_id = uuid4()
        self.rows[row_id] = (status, created_at)
        return row_id

    async def purge_terminal(
        self, status: TerminalStatus, *, older_than: datetime, limit: int
    ) -> int:
        doomed = [
            row_id
            for row_id, (row_status, created) in self.rows.items()
            if row_status is status and created < older_than
        ][:limit]
        for row_id in doomed:
            del self.rows[row_id]
        return len(doomed)


def _retention(
    repo: _FakeRepo, config: OutboxRetentionConfig | None = None
) -> tuple[OutboxRetention, _FakeUow]:
    uow = _FakeUow()
    return (
        OutboxRetention(
            lambda: uow,  # type: ignore[arg-type,return-value]
            lambda _uow: repo,  # type: ignore[arg-type,return-value]
            config,
            clock=lambda: NOW,
        ),
        uow,
    )


def _days_ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


async def test_deletes_published_rows_past_the_window() -> None:
    repo = _FakeRepo()
    old = repo.seed(OutboxStatus.PUBLISHED, _days_ago(31))
    recent = repo.seed(OutboxStatus.PUBLISHED, _days_ago(29))

    result = await _retention(repo, OutboxRetentionConfig(published_after_days=30))[0].purge_once()

    assert result.published == 1
    assert old not in repo.rows
    assert recent in repo.rows  # inside the window: still delivery history worth having


async def test_never_deletes_pending_however_old() -> None:
    """The property everything else here exists to protect: PENDING is unsent work."""
    repo = _FakeRepo()
    ancient = repo.seed(OutboxStatus.PENDING, _days_ago(3650))

    result = await _retention(repo, OutboxRetentionConfig(published_after_days=1))[0].purge_once()

    assert result.deleted == 0
    assert ancient in repo.rows


async def test_keeps_dead_letters_forever_by_default() -> None:
    """A FAILED row is the only trace that something never got delivered."""
    repo = _FakeRepo()
    dead = repo.seed(OutboxStatus.FAILED, _days_ago(3650))

    result = await _retention(repo, OutboxRetentionConfig(published_after_days=1))[0].purge_once()

    assert result.failed == 0
    assert dead in repo.rows


async def test_deletes_dead_letters_when_a_window_is_configured() -> None:
    repo = _FakeRepo()
    old_dead = repo.seed(OutboxStatus.FAILED, _days_ago(400))
    recent_dead = repo.seed(OutboxStatus.FAILED, _days_ago(300))

    retention, _uow = _retention(
        repo, OutboxRetentionConfig(published_after_days=30, failed_after_days=365)
    )
    result = await retention.purge_once()

    assert result.failed == 1
    assert old_dead not in repo.rows
    assert recent_dead in repo.rows


async def test_a_large_backlog_is_cleared_in_batches() -> None:
    repo = _FakeRepo()
    for _ in range(25):
        repo.seed(OutboxStatus.PUBLISHED, _days_ago(60))

    retention, uow = _retention(
        repo, OutboxRetentionConfig(published_after_days=30, batch_size=10, max_batches=20)
    )
    result = await retention.purge_once()

    assert result.published == 25
    assert repo.rows == {}
    # 3 batches (10 + 10 + 5), each its own transaction — no single long lock.
    assert uow.commits == 3


async def test_max_batches_caps_one_sweep_and_leaves_the_rest() -> None:
    """A huge backlog must not turn one sweep into a transaction storm."""
    repo = _FakeRepo()
    for _ in range(100):
        repo.seed(OutboxStatus.PUBLISHED, _days_ago(60))

    retention, uow = _retention(
        repo, OutboxRetentionConfig(published_after_days=30, batch_size=10, max_batches=3)
    )
    result = await retention.purge_once()

    assert result.published == 30
    assert len(repo.rows) == 70  # the next sweep continues from here
    assert uow.commits == 3


async def test_empty_sweep_touches_nothing() -> None:
    repo = _FakeRepo()
    fresh = repo.seed(OutboxStatus.PUBLISHED, _days_ago(1))

    result = await _retention(repo)[0].purge_once()

    assert result.deleted == 0
    assert fresh in repo.rows


async def test_run_forever_keeps_sweeping_and_survives_a_failure() -> None:
    repo = _FakeRepo()
    retention, _uow = _retention(repo, OutboxRetentionConfig(published_after_days=30))
    calls = 0
    real_purge = repo.purge_terminal

    async def flaky(status: TerminalStatus, *, older_than: datetime, limit: int) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database unavailable")
        return await real_purge(status, older_than=older_than, limit=limit)

    repo.purge_terminal = flaky  # type: ignore[method-assign]
    repo.seed(OutboxStatus.PUBLISHED, _days_ago(60))

    task = asyncio.create_task(retention.run_forever(0.001))
    await _until(lambda: repo.rows == {})  # kept going after the first sweep blew up
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls >= 2


def test_default_window_is_documented_and_conservative() -> None:
    config = OutboxRetentionConfig()
    assert config.published_after_days == 30
    assert config.failed_after_days is None  # dead letters need a human, not a timer


async def _until(condition: Callable[[], bool], timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.001)
