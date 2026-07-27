"""Shared test fixtures — plus the one setting that decides how long the suite takes.

Nothing here changes what the code under test does; see :func:`_sqlite_test_pragmas`.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from pharmacy_os.core.config import (
    AISettings,
    AppSettings,
    DatabaseSettings,
    SecuritySettings,
    Settings,
)

_SQLITE_TEST_PRAGMAS = ("PRAGMA synchronous=OFF", "PRAGMA journal_mode=MEMORY")
"""Durability settings for **throwaway** SQLite databases. Measured, not guessed.

The e2e fixtures each build a fresh file-backed SQLite database and run
``create_all`` over **48 tables**. With SQLite's default ``synchronous=FULL`` that
is an ``fsync`` per DDL statement, and it costs **≈2.0 s per test** — on a suite
where the whole of ``tests/unit`` (453 tests) runs in 4,6 s.

Measured on this machine 2026-07-27, ``create_all`` of the full metadata:

===================================================  ==========
file-backed SQLite, defaults (what the suite did)     2004,1 ms
same file, these two pragmas                            47,5 ms
in-memory SQLite (for comparison)                       36,4 ms
===================================================  ==========

So **≈98 % of that 2 s was waiting on the disk**, not building the schema. Turning
durability off is free here in the only sense that matters: these databases live in
``tmp_path`` and are deleted at the end of the test. A crash mid-test loses a
database we were going to throw away anyway.

**Deliberately scoped to SQLite.** ``tests/concurrency`` runs on real Postgres and
must keep real durability — that suite exists to prove locking behaviour, and a
weakened storage engine underneath it would quietly hollow out the very thing it
checks. The guard below keys off the driver, not off which fixture is asking.
"""


@event.listens_for(Engine, "connect")
def _sqlite_test_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Apply :data:`_SQLITE_TEST_PRAGMAS` to every SQLite connection in the suite.

    Registered once, on the ``Engine`` class, so it reaches engines the test never
    sees — including the ones ``create_app`` builds inside the e2e fixtures. Doing
    it per-fixture instead would mean editing 21 files and getting it wrong in the
    22nd.
    """
    if "sqlite" not in type(dbapi_connection).__module__.lower():
        return  # Postgres (tests/concurrency) — leave durability alone
    cursor = dbapi_connection.cursor()
    try:
        for pragma in _SQLITE_TEST_PRAGMAS:
            cursor.execute(pragma)
    finally:
        cursor.close()


@pytest.fixture
def settings() -> Settings:
    """Deterministic settings using an in-memory SQLite DB for tests."""
    return Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
        ai=AISettings(api_key="test-key"),  # type: ignore[arg-type]
        security=SecuritySettings(jwt_secret="test-secret-key-0123456789abcdef"),  # type: ignore[arg-type]
    )
