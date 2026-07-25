"""The app's background tasks are owned by the lifespan.

Two things worth pinning: each task starts only when its own switch is on (a timer
running inside the test harness would make the suite non-deterministic), and every one
of them is cancelled on shutdown — a leaked task holds a database connection and keeps
ticking for the life of the process.

Covers all three: the two outbox tasks and the national-DB sync retry relay (docs/13
mục D.4), which is switched separately because it is a different concern — retrying a
call to an external authority, not delivering internal events.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.config import (
    AISettings,
    AppSettings,
    DatabaseSettings,
    NationalSyncSettings,
    OutboxSettings,
    SecuritySettings,
    Settings,
)
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base

_BACKGROUND_TASKS = frozenset({"outbox-relay", "outbox-retention", "national-sync-retry"})


def _settings(
    tmp_path: Path, outbox: OutboxSettings, national_sync: NationalSyncSettings | None = None
) -> Settings:
    db_path = tmp_path / "lifespan.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    return Settings(
        app=AppSettings(env="dev", debug=False),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
        ai=AISettings(api_key="test-key"),  # type: ignore[arg-type]
        security=SecuritySettings(jwt_secret="test-secret-key-0123456789abcdef"),  # type: ignore[arg-type]
        outbox=outbox,
        national_sync=national_sync or NationalSyncSettings(),
    )


def _run(settings: Settings) -> tuple[set[str], list[asyncio.Task[None]]]:
    """Boot the app, look at its own event loop from inside, then shut it down.

    The tasks live on TestClient's loop, so they can only be observed from a coroutine
    running on it — an endpoint is the simplest place that is genuinely mid-lifespan.
    The task objects are handed back so the caller can check them *after* shutdown.
    """
    captured: list[asyncio.Task[None]] = []
    app = create_app(settings)

    @app.get("/__background-tasks")
    async def _tasks() -> dict[str, list[str]]:
        captured.extend(t for t in asyncio.all_tasks() if t.get_name() in _BACKGROUND_TASKS)  # type: ignore[misc]
        return {"tasks": sorted(t.get_name() for t in captured)}

    with TestClient(app) as client:
        names = set(client.get("/__background-tasks").json()["tasks"])
    return names, captured


def test_no_background_tasks_when_both_switches_are_off(tmp_path: Path) -> None:
    names, _ = _run(_settings(tmp_path, OutboxSettings()))
    assert names == set()


def test_relay_task_runs_only_when_enabled(tmp_path: Path) -> None:
    names, _ = _run(
        _settings(tmp_path, OutboxSettings(relay_enabled=True, retention_enabled=False))
    )
    assert names == {"outbox-relay"}


def test_retention_task_runs_independently_of_the_relay(tmp_path: Path) -> None:
    """Rows accumulate under sync_drain too, so retention must not require the relay."""
    names, _ = _run(
        _settings(
            tmp_path,
            OutboxSettings(sync_drain=True, relay_enabled=False, retention_enabled=True),
        )
    )
    assert names == {"outbox-retention"}


def test_national_sync_retry_task_runs_only_when_enabled(tmp_path: Path) -> None:
    """Its own switch, not the outbox's: the queue is written either way, but nothing
    drains it until NATIONAL_SYNC__RETRY_ENABLED is on (docs/13 mục D.4)."""
    off, _ = _run(_settings(tmp_path, OutboxSettings(), NationalSyncSettings()))
    assert off == set()

    on, _ = _run(_settings(tmp_path, OutboxSettings(), NationalSyncSettings(retry_enabled=True)))
    assert on == {"national-sync-retry"}


def test_shutdown_cancels_every_background_task(tmp_path: Path) -> None:
    names, tasks = _run(
        _settings(
            tmp_path,
            OutboxSettings(
                sync_drain=False,
                relay_enabled=True,
                retention_enabled=True,
                poll_interval_seconds=0.01,
                retention_interval_seconds=0.01,
            ),
            NationalSyncSettings(retry_enabled=True, poll_interval_seconds=0.01),
        )
    )
    assert names == {"outbox-relay", "outbox-retention", "national-sync-retry"}
    # The real assertion: nothing survived the lifespan exit.
    assert tasks and all(task.done() for task in tasks)
    assert all(task.cancelled() for task in tasks)
