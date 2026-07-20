"""Shared test fixtures."""

from __future__ import annotations

import pytest

from pharmacy_os.core.config import (
    AISettings,
    AppSettings,
    DatabaseSettings,
    SecuritySettings,
    Settings,
)


@pytest.fixture
def settings() -> Settings:
    """Deterministic settings using an in-memory SQLite DB for tests."""
    return Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
        ai=AISettings(api_key="test-key"),  # type: ignore[arg-type]
        security=SecuritySettings(jwt_secret="test-secret-key-0123456789abcdef"),  # type: ignore[arg-type]
    )
