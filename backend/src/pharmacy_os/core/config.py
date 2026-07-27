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

_MIN_JWT_SECRET_BYTES = 32
"""Độ dài tối thiểu của khoá ký HS256 ở prod (A-02).

32 byte = đúng kích thước digest của SHA-256, mức RFC 2104 §3 khuyến nghị cho HMAC.
Ngắn hơn digest thì khoá trở thành mắt xích yếu nhất và chữ ký chỉ còn là hình thức."""


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


class EncryptionSettings(BaseSettings):
    """Keys for at-rest field encryption (Sprint 8, ``core.security.crypto``).

    **Never commit these and never put them beside a database dump.** Losing them is
    not a recoverable incident: the encrypted columns become permanently unreadable,
    and no ``git revert`` helps. Back the keys up separately from the database, and
    rehearse a restore before enabling this anywhere that holds real data.
    """

    enabled: bool = False
    """Encrypt on write. Off by default so an upgrade never starts writing ciphertext
    a deployment has no key for; reads handle both shapes regardless, which is what
    lets a backfill run while the application is live."""

    keys: dict[int, SecretStr] = Field(default_factory=dict)
    """Base64 AES-256 keys by version, e.g.
    ``ENCRYPTION__KEYS={"1": "<base64>"}``. Several versions coexist so rotation never
    needs a big-bang re-encryption — old ciphertexts keep their tag and their key."""

    current_version: int = 1
    """Which version new writes use. Rotating = add the next version, then point here."""

    allow_plaintext_in_prod: bool = False
    """Đường thoát **cố ý** cho ``ENCRYPTION__ENABLED=false`` ở prod (A-03).

    Tồn tại vì có một tình huống hợp lệ: deployment đang chạy dở dang việc bật mã hoá
    lần đầu (backfill chưa xong). Nhưng nó phải là một **hành động khai báo**, không
    phải một biến bị quên — mặc định ``False`` nghĩa là *"quên đặt = ứng dụng không
    khởi động"*, chứ không phải *"quên đặt = dữ liệu bệnh nhân nằm nguyên văn"*.

    Cùng khuôn với ``SECURITY__ALLOW_DEV_AUTH``: fail-closed, và bật lên là một quyết
    định có người chịu trách nhiệm."""

    blind_index_key: SecretStr = SecretStr(_PLACEHOLDER)
    """Separate base64 key for searchable fingerprints (``BlindIndex``). Deliberately
    not the encryption key: one key per purpose, so a weakness in one is not a break
    in the other."""


class SecuritySettings(BaseSettings):
    jwt_secret: SecretStr = SecretStr(_PLACEHOLDER)
    jwt_ttl_minutes: int = 60
    """Access-token lifetime. Kept at 60 (docs/15 D2): revoking a role therefore takes
    effect within one hour, which is the accepted trade against an offline-first POS
    being logged out mid-shift on a shorter window."""

    jwt_algorithm: str = "HS256"
    refresh_ttl_days: int = 30

    two_factor_enforced: bool = False
    """Require 2FA from accounts holding a sensitive permission
    (``iam.domain.two_factor.TWO_FACTOR_PERMISSIONS`` — signing the controlled-substance
    ledger, or editing/assigning roles).

    Defaults to **off**, the same shape as ``OUTBOX__RELAY_ENABLED`` and
    ``NATIONAL_SYNC__RETRY_ENABLED``: turning the feature on is a deployment decision,
    never a side effect of upgrading. With it off, a user who enrols voluntarily is
    still challenged — the flag governs *compulsion*, not whether 2FA works.

    Switching it on does **not** lock anybody out. In-scope users who have not enrolled
    keep logging in and working; they receive ``must_enroll_two_factor`` in the session
    payload so the client can prompt, and only the legally binding act (signing the
    ledger) is refused until they enrol. Nudge broadly, block narrowly.

    Replaces the former ``require_2fa_roles``, which was dead code naming two role
    codes (``pharmacist``/``admin``) that have never existed in this system — the real
    ones are ``chain_pharmacist``/``branch_pharmacist``/``system_admin``/``cashier``/
    ``warehouse``. Scope is now derived from permissions held, not a copied list.
    """

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
    encryption: EncryptionSettings = Field(default_factory=EncryptionSettings)

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

            # A-02. "Không phải chuỗi mặc định" là một bài kiểm tra quá dễ: kiểm toán
            # 2026-07-26 khởi động được prod với JWT_SECRET dài **3 byte**. Một khoá
            # HS256 ngắn hơn digest của chính nó thì chữ ký chỉ còn là trang trí — mọi
            # phiên đăng nhập, mọi phân quyền của hệ thống đứng trên nó.
            secret_bytes = len(self.security.jwt_secret.get_secret_value().encode("utf-8"))
            if secret_bytes < _MIN_JWT_SECRET_BYTES:
                raise ValueError(
                    f"SECURITY__JWT_SECRET chỉ {secret_bytes} byte, tối thiểu "
                    f"{_MIN_JWT_SECRET_BYTES} byte trong prod (HS256 ký bằng khoá này; "
                    f"khoá ngắn hơn digest thì chữ ký không còn giá trị bảo vệ). "
                    f'Sinh khoá: `python -c "import secrets;print(secrets.token_urlsafe(48))"`'
                )

            # A-03. Mã hoá at-rest **tắt được** ở prod là cách dữ liệu bệnh nhân nằm
            # nguyên văn trong CSDL mà không ai phải quyết định điều đó — chỉ cần quên
            # đặt một biến. Bật là mặc định của prod; tắt phải là một hành động cố ý,
            # khai báo thành lời, và có người chịu trách nhiệm.
            if not self.encryption.enabled and not self.encryption.allow_plaintext_in_prod:
                raise ValueError(
                    "ENCRYPTION__ENABLED=false trong prod: dữ liệu bệnh nhân sẽ nằm "
                    "nguyên văn trong CSDL (Luật BVDLCN 91/2025). Bật mã hoá, hoặc — nếu "
                    "thực sự cố ý — đặt ENCRYPTION__ALLOW_PLAINTEXT_IN_PROD=true và ghi "
                    "lý do vào nhật ký vận hành."
                )

        # Applies in every environment, not just prod: writing ciphertext nobody can
        # read back is unrecoverable, so the misconfiguration must stop the app now
        # rather than after it has encrypted a day of patient records.
        if self.encryption.enabled:
            if not self.encryption.keys:
                raise ValueError(
                    "ENCRYPTION__ENABLED=true nhưng ENCRYPTION__KEYS rỗng: "
                    "sẽ ghi dữ liệu không ai đọc lại được"
                )
            if self.encryption.current_version not in self.encryption.keys:
                raise ValueError(
                    f"ENCRYPTION__CURRENT_VERSION={self.encryption.current_version} "
                    f"không có trong ENCRYPTION__KEYS {sorted(self.encryption.keys)}"
                )
            if self.encryption.blind_index_key.get_secret_value() == _PLACEHOLDER:
                raise ValueError("ENCRYPTION__BLIND_INDEX_KEY chưa đặt: tra cứu theo SĐT sẽ hỏng")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
