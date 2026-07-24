import pytest
from pydantic import SecretStr

from pharmacy_os.core.config import AppSettings, OutboxSettings, SecuritySettings, Settings


def test_defaults_boot_in_dev() -> None:
    s = Settings(app=AppSettings(env="dev"))
    assert s.ai.model_reasoning == "claude-opus-4-8"
    assert s.security.jwt_ttl_minutes == 60
    # Dev/test shape: events are published in-line, no background poller.
    assert s.outbox.sync_drain is True
    assert s.outbox.relay_enabled is False


def test_prod_rejects_placeholder_secrets() -> None:
    with pytest.raises(ValueError):
        Settings(app=AppSettings(env="prod"))


def test_prod_boots_with_secrets() -> None:
    s = Settings(
        app=AppSettings(env="prod"),
        security=SecuritySettings(jwt_secret=SecretStr("real")),
        ai={"api_key": SecretStr("real")},  # type: ignore[arg-type]
    )
    assert s.app.env == "prod"


def test_prod_rejects_an_outbox_with_no_delivery_path() -> None:
    """Both switches off means events pile up in ``event_outbox`` forever — refuse."""
    with pytest.raises(ValueError, match="event_outbox"):
        Settings(
            app=AppSettings(env="prod"),
            security=SecuritySettings(jwt_secret=SecretStr("real")),
            ai={"api_key": SecretStr("real")},  # type: ignore[arg-type]
            outbox=OutboxSettings(sync_drain=False, relay_enabled=False),
        )


def test_prod_accepts_the_async_relay_shape() -> None:
    s = Settings(
        app=AppSettings(env="prod"),
        security=SecuritySettings(jwt_secret=SecretStr("real")),
        ai={"api_key": SecretStr("real")},  # type: ignore[arg-type]
        outbox=OutboxSettings(sync_drain=False, relay_enabled=True),
    )
    assert s.outbox.relay_enabled is True
