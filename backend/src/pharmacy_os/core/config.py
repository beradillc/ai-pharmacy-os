"""Layered application configuration (Pydantic Settings).

Precedence (low -> high): code defaults -> env vars. Business/runtime config
(VAT, near-expiry days, ...) lives in the DB ``settings`` table and is *not*
modelled here — see docs/10_CONFIG.md.

Env var format uses a nested delimiter, e.g. ``AI__API_KEY``, ``DB__URL``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER = "__set_me__"


class AppSettings(BaseSettings):
    env: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = False


class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os"
    pool_size: int = 10


class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"


class AISettings(BaseSettings):
    provider: str = "anthropic"
    model_reasoning: str = "claude-opus-4-8"
    model_fast: str = "claude-sonnet-5"
    api_key: SecretStr = SecretStr(_PLACEHOLDER)
    max_tokens: int = 2048
    enable_clinical_ai: bool = True
    min_confidence: float = 0.6


class SecuritySettings(BaseSettings):
    jwt_secret: SecretStr = SecretStr(_PLACEHOLDER)
    jwt_ttl_minutes: int = 60
    jwt_algorithm: str = "HS256"
    require_2fa_roles: list[str] = Field(default_factory=lambda: ["pharmacist", "admin"])


class Settings(BaseSettings):
    """Root settings object; the single entry point for configuration."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ai: AISettings = Field(default_factory=AISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @model_validator(mode="after")
    def _fail_fast_in_prod(self) -> Settings:
        """Refuse to boot with placeholder secrets outside development."""
        if self.app.env == "prod":
            missing = [
                name
                for name, secret in (
                    ("SECURITY__JWT_SECRET", self.security.jwt_secret),
                    ("AI__API_KEY", self.ai.api_key),
                )
                if secret.get_secret_value() == _PLACEHOLDER
            ]
            if missing:
                raise ValueError(f"Missing required secrets in prod: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
