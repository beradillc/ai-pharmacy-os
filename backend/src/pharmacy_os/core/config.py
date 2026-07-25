"""Layered application configuration (Pydantic Settings).

Precedence (low -> high): code defaults -> env vars. Business/runtime config
(VAT, near-expiry days, ...) lives in the DB ``settings`` table and is *not*
modelled here — see docs/10_CONFIG.md.

Env var format uses a nested delimiter, e.g. ``AI__API_KEY``, ``DB__URL``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

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


class OutboxSettings(BaseSettings):
    """How domain events get from the ``event_outbox`` table to their subscribers.

    Defaults are the **dev/test** shape: publish inline right after the commit, no
    background task, so a request's subscribers finish before it returns and the test
    suite stays deterministic. A production deployment sets ``OUTBOX__SYNC_DRAIN=false``
    + ``OUTBOX__RELAY_ENABLED=true`` to get real async delivery; running both is also
    valid (inline for latency, relay as the sweeper that picks up what a crash left).
    """

    sync_drain: bool = True
    """Publish collected events immediately after the business commit (same request)."""

    relay_enabled: bool = False
    """Run the background :class:`~pharmacy_os.core.outbox.OutboxRelay` in the app.

    This is what makes the outbox worth having: it re-delivers rows left ``PENDING`` by
    a crash between the commit and the dispatch. Off by default only because a poller
    inside the test harness would make the suite non-deterministic."""

    poll_interval_seconds: float = 1.0
    batch_size: int = 100
    max_retries: int = 5
    base_backoff_seconds: float = 2.0

    retention_enabled: bool = False
    """Run the background sweep that ages finished rows out of ``event_outbox``.

    Independent of :attr:`relay_enabled`: rows pile up under ``sync_drain`` exactly as
    they do under the relay, so a deployment needs this on either way. Off by default
    for the same reason as the relay — a timer inside the test harness would make the
    suite non-deterministic — but **a production deployment must turn it on**, or the
    table grows without bound."""

    retention_interval_seconds: float = 3600.0
    retention_published_days: int = 30
    """How long a delivered row is kept. Operational history, not legal evidence — the
    business record and the audit trail live in their own tables."""

    retention_failed_days: int | None = None
    """How long a dead letter is kept; ``None`` (default) keeps them forever, because
    deleting one silently discards the only trace of an undelivered event."""

    retention_batch_size: int = 500
    retention_max_batches: int = 20


class NationalSyncSettings(BaseSettings):
    """Gửi lại tự động các bản ghi liên thông CSDL Dược đang treo (docs/13 mục D.4).

    Tách khỏi :class:`OutboxSettings` vì là mối lo khác: outbox giao *sự kiện nội bộ* tới
    subscriber, còn đây là *gọi ra cổng ngoài* (CSDL Dược Quốc gia) — hỏng theo kiểu khác,
    cần nhịp chậm hơn hẳn và một điểm dừng.
    """

    retry_enabled: bool = False
    """Chạy :class:`~pharmacy_os.modules.compliance.application.NationalSyncRetryRelay` trong app.

    Mặc định TẮT, cùng lý do với ``OUTBOX__RELAY_ENABLED``: một bộ quét nền trong harness
    test sẽ làm bộ test hết tất định. **Deployment thật phải bật** — không bật thì bản ghi
    bị cổng từ chối vẫn nằm trong hàng đợi chờ người POST lại tay, đúng cái lỗ hổng cơ chế
    này sinh ra để vá (QĐ1867 mục I.2 đòi liên thông *kịp thời*).

    Việc gửi lại vẫn được **ghi vào hàng đợi bất kể cờ này** — cờ chỉ quyết định có ai rút
    hàng đợi ra hay không, y hệt outbox vẫn ghi ``event_outbox`` khi relay tắt. Nhờ vậy bật
    cờ lên là đẩy được cả những bản ghi hỏng từ trước đó.
    """

    poll_interval_seconds: float = 30.0
    """Chậm hơn outbox (1s) hai bậc: cổng quốc gia không phải event bus trong tiến trình,
    và bản ghi tới hạn sớm nhất cũng phải chờ hết ``base_backoff_seconds``."""

    batch_size: int = 20
    max_retries: int = 8
    base_backoff_seconds: float = 60.0
    lease_seconds: float = 300.0


class PluginsSettings(BaseSettings):
    """Which plugins run, and what each one is configured with (docs/09).

    Enablement is deliberately separate from discovery: the loader finds every
    installed plugin via entry points, but only the keys listed here are loaded. That
    is what satisfies the Sprint 8 DoD "bật/tắt plugin không sửa lõi" — switching a
    plugin on or off is a deployment decision, never a code change.

    Defaults to **empty**, matching ``OUTBOX__RELAY_ENABLED`` and
    ``NATIONAL_SYNC__RETRY_ENABLED``: no plugin runs unless somebody deliberately turns
    it on. Enabling a plugin that is not installed is fail-fast at startup (see
    ``PluginLoader.load_enabled``) rather than a silent no-op.
    """

    enabled: list[str] = Field(default_factory=list)
    """Entry-point names to load, e.g. ``PLUGINS__ENABLED=["vnpay"]``."""

    config: dict[str, dict[str, Any]] = Field(default_factory=dict)
    """Per-plugin settings, keyed by the same entry-point name, handed to the plugin as
    :class:`~pharmacy_os.core.plugins.PluginContext`. A plugin with no entry here still
    loads, with an empty config. Secrets belong here rather than hard-coded in the
    plugin (docs/09 mục 6)."""


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
    outbox: OutboxSettings = Field(default_factory=OutboxSettings)
    national_sync: NationalSyncSettings = Field(default_factory=NationalSyncSettings)
    plugins: PluginsSettings = Field(default_factory=PluginsSettings)

    @model_validator(mode="after")
    def _fail_fast_in_prod(self) -> Settings:
        """Refuse to boot with placeholder secrets — or dev auth — in production."""
        if self.app.env == "prod":
            if self.security.allow_dev_auth:
                raise ValueError(
                    "SECURITY__ALLOW_DEV_AUTH must be false in prod: it accepts "
                    "unauthenticated requests with a full permission set"
                )
            if not self.outbox.sync_drain and not self.outbox.relay_enabled:
                raise ValueError(
                    "OUTBOX__SYNC_DRAIN and OUTBOX__RELAY_ENABLED are both false: "
                    "events would be written to event_outbox and never delivered"
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
