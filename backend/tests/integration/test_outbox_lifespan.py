"""The outbox background tasks are owned by the app lifespan.

Two things worth pinning: each task starts only when its own switch is on (a timer
running inside the test harness would make the suite non-deterministic), and every one
of them is cancelled on shutdown — a leaked task holds a database connection and keeps
ticking for the life of the process.
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
    OutboxSettings,
    SecuritySettings,
    Settings,
)
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base


def _settings(tmp_path: Path, outbox: OutboxSettings) -> Settings:
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
    )


def _run(settings: Settings) -> tuple[set[str], list[asyncio.Task[None]]]:
    """Boot the app, look at its own event loop from inside, then shut it down.

    The tasks live on TestClient's loop, so they can only be observed from a coroutine
    running on it — an endpoint is the simplest place that is genuinely mid-lifespan.
    The task objects are handed back so the caller can check them *after* shutdown.
    """
    captured: list[asyncio.Task[None]] = []
    app = create_app(settings)

    @app.get("/__outbox-tasks")
    async def _tasks() -> dict[str, list[str]]:
        captured.extend(
            t
            for t in asyncio.all_tasks()
            if t.get_name().startswith("outbox-")  # type: ignore[misc]
        )
        return {"tasks": sorted(t.get_name() for t in captured)}

    with TestClient(app) as client:
        names = set(client.get("/__outbox-tasks").json()["tasks"])
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
        )
    )
    assert names == {"outbox-relay", "outbox-retention"}
    # The real assertion: nothing survived the lifespan exit.
    assert tasks and all(task.done() for task in tasks)
    assert all(task.cancelled() for task in tasks)
