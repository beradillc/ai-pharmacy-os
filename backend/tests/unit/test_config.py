import pytest
from pydantic import SecretStr

from pharmacy_os.core.config import AppSettings, SecuritySettings, Settings


def test_defaults_boot_in_dev() -> None:
    s = Settings(app=AppSettings(env="dev"))
    assert s.ai.model_reasoning == "claude-opus-4-8"
    assert s.security.jwt_ttl_minutes == 60


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
