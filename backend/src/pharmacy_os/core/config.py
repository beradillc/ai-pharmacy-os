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
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    """Browser origins allowed to call the API directly (S4.6 FE POS).

    The backend has no session cookie of its own to protect — auth is a bearer
    token the client attaches per request — so this only controls which origins the
    browser lets read the response, not who can reach the API (curl/mobile clients
    are unaffected either way). Still explicit rather than ``["*"]`` so a stray
    origin can't silently start reading responses in prod."""


class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os"
    pool_size: int = 10


class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"


class AISettings(BaseSettings):
    """Deployment-wide AI tuning. Whether AI runs at all for a given pharmacy is a
    **per-tenant** flag (``clinical.TenantAiSettings``, Sprint 6 SaaS requirement),
    not modelled here — a single global on/off switch doesn't fit multi-tenant.
    """

    provider: str = "anthropic"
    model_reasoning: str = "claude-opus-4-8"
    model_fast: str = "claude-sonnet-5"
    api_key: SecretStr = SecretStr(_PLACEHOLDER)
    max_tokens: int = 2048
    min_confidence: float = 0.6


class OrgSettings(BaseSettings):
    """Pharmacy header printed on receipts (in bill, S7).

    Single global default — there is no per-tenant organisation-profile module
    yet. Promote to the DB ``settings`` table (docs/10_CONFIG.md §3, scope
    TENANT) if/when multi-tenant deployments need a distinct header per pharmacy;
    tracked as a known simplification, not silently assumed.
    """

    pharmacy_name: str = "Nhà thuốc"
    address: str = ""
    phone: str = ""
    tax_code: str = ""


class SecuritySettings(BaseSettings):
    jwt_secret: SecretStr = SecretStr(_PLACEHOLDER)
    jwt_ttl_minutes: int = 60
    """Access-token lifetime. Kept at 60 (docs/15 D2): revoking a role therefore takes
    effect within one hour, which is the accepted trade against an offline-first POS
    being logged out mid-shift on a shorter window."""

    jwt_algorithm: str = "HS256"
    refresh_ttl_days: int = 30
    require_2fa_roles: list[str] = Field(default_factory=lambda: ["pharmacist", "admin"])

    allow_dev_auth: bool = False
    """Accept ``X-Tenant-Id``/``X-Branch-Id``/``X-User-Id`` headers with a full
    permission set when no Bearer token is present (``api.deps.get_context``).

    Defaults to **off** so a misconfigured deployment fails closed: before iam the
    fallback was on for everything except ``env == "prod"``, which meant one wrong
    environment variable on staging left the API wide open (docs/15 §5 Q3)."""


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
    org: OrgSettings = Field(default_factory=OrgSettings)

    @model_validator(mode="after")
    def _fail_fast_in_prod(self) -> Settings:
        """Refuse to boot with placeholder secrets — or dev auth — in production."""
        if self.app.env == "prod":
            if self.security.allow_dev_auth:
                raise ValueError(
                    "SECURITY__ALLOW_DEV_AUTH must be false in prod: it accepts "
                    "unauthenticated requests with a full permission set"
                )
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
