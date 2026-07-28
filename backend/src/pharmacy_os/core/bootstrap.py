"""Compose the kernel: build the DI container from settings.

This is the single place where concrete kernel implementations are chosen and
registered. Business modules will call ``container.resolve(...)`` for the
capabilities they need — never constructing kernel objects themselves.
"""

from __future__ import annotations

import os

import structlog
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from pharmacy_os.core.ai import LLMProvider, MockLLMProvider
from pharmacy_os.core.audit import AuditDashboardService, AuditLogger, AuditQueryService
from pharmacy_os.core.config import _PLACEHOLDER as _PLACEHOLDER_SECRET
from pharmacy_os.core.config import Settings
from pharmacy_os.core.db import (
    OutboxSink,
    UnitOfWorkFactory,
    build_engine,
    build_sessionmaker,
    configure_field_encryption,
)
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus, InMemoryEventBus
from pharmacy_os.core.outbox import OutboxEventSink
from pharmacy_os.core.plugins import HookRegistry, PluginLoader
from pharmacy_os.core.security.branch_scope import BranchScopeGuard
from pharmacy_os.core.security.crypto import BlindIndex, FieldCipher, KeyRing, decode_key
from pharmacy_os.core.security.jwt import JwtService

_log = structlog.get_logger("core.bootstrap")

ALLOW_MOCKS_IN_PROD_ENV = "PHARMACY_ALLOW_MOCKS_IN_PROD"
"""Đường thoát **cố ý** cho :func:`refuse_mock_in_prod`, đặt qua biến môi trường.

Là biến môi trường chứ không phải trường trong ``Settings``: nó dành cho diễn tập
vận hành (dựng thử prod-like không có nhà cung cấp thật), và không nên nằm lẫn trong
file cấu hình mà một ngày nào đó được sao chép lên máy chủ thật.
"""


def refuse_mock_in_prod(settings: Settings, mock_name: str, what_it_fakes: str) -> None:
    """Từ chối khởi động nếu một cổng giả bị nạp ở ``APP__ENV=prod`` (kiểm toán A-07).

    Mock ở prod không hỏng ồn ào — nó **trả lời**. ``MockLLMProvider`` trả về kết quả
    kiểm tra tương tác thuốc trông y như thật, nên một nhà thuốc đang chạy pilot sẽ
    thấy "không có tương tác" và tin. Đó là rủi ro an toàn người bệnh, và nó im lặng.

    Cùng khuôn fail-closed với ``SECURITY__ALLOW_DEV_AUTH``: hỏng lúc khởi động, chỗ
    có người đang nhìn, thay vì hỏng lúc dược sĩ đang bán thuốc.
    """
    if settings.app.env != "prod":
        return
    if os.environ.get(ALLOW_MOCKS_IN_PROD_ENV, "").lower() in {"1", "true", "yes"}:
        _log.warning(
            "mock_allowed_in_prod",
            mock=mock_name,
            fakes=what_it_fakes,
            detail="Cổng giả chạy ở prod vì có người bật đường thoát. KHÔNG dùng cho "
            "deployment phục vụ bệnh nhân thật.",
        )
        return
    raise RuntimeError(
        f"{mock_name} bị nạp khi APP__ENV=prod — nó giả lập {what_it_fakes} và trả lời "
        f"như thật, nên sai sót sẽ không lộ ra. Nối nhà cung cấp thật, hoặc — nếu đây "
        f"là diễn tập vận hành — đặt {ALLOW_MOCKS_IN_PROD_ENV}=true."
    )


def build_field_cipher(settings: Settings) -> FieldCipher | None:
    """The at-rest cipher, or ``None`` when this deployment has no keys.

    Keys are loaded whenever they are present, even with ``ENCRYPTION__ENABLED=false``:
    that combination is exactly what a deployment needs to *read* already-encrypted
    columns after switching writing off, and it is the safe direction to fail — a
    deployment can always stop writing ciphertext, but must never lose the ability to
    read what it already wrote.
    """
    if not settings.encryption.keys:
        return None
    ring = KeyRing(
        keys={
            version: decode_key(secret.get_secret_value())
            for version, secret in settings.encryption.keys.items()
        },
        current_version=settings.encryption.current_version,
    )
    return FieldCipher(ring)


def build_blind_index(settings: Settings) -> BlindIndex | None:
    """The fingerprinter for searchable encrypted columns, if a key is configured.

    Loaded independently of ``ENCRYPTION__ENABLED`` for the same reason as the cipher:
    a deployment that has stopped writing ciphertext still has to *find* the rows it
    already fingerprinted.
    """
    raw = settings.encryption.blind_index_key.get_secret_value()
    if raw == _PLACEHOLDER_SECRET:
        return None
    return BlindIndex(decode_key(raw))


def build_container(settings: Settings) -> Container:
    container = Container()
    container.register_instance(Settings, settings)

    # Install the at-rest cipher before anything can touch the database: the encrypted
    # column types read it at query time, so a session opened before this point would
    # silently store plaintext. Settings has already refused to build if encryption is
    # switched on without a usable key set.
    configure_field_encryption(
        build_field_cipher(settings),
        write_enabled=settings.encryption.enabled,
        blind_index=build_blind_index(settings),
    )

    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size, echo=settings.app.debug)
    container.register_instance(AsyncEngine, engine)

    session_factory = build_sessionmaker(engine)
    container.register_instance(async_sessionmaker[AsyncSession], session_factory)

    # Audit B-07: mọi request có token đều đi qua guard này để xác nhận cặp
    # (tenant, chi nhánh) là có thật. Singleton vì nó giữ cache các cặp đã xác nhận —
    # một instance mới mỗi request thì cache vô nghĩa.
    container.register_instance(BranchScopeGuard, BranchScopeGuard(session_factory))

    # EventBus is a Protocol used as a service key; concrete impl is InMemoryEventBus.
    container.register_singleton(EventBus, lambda _c: InMemoryEventBus())  # type: ignore[type-abstract]
    # Every UoW in the app writes its events to event_outbox inside the business
    # transaction (see core.outbox.sink); OUTBOX__SYNC_DRAIN decides whether they are
    # also published inline. Modules get their UoWs from UnitOfWorkFactory so none of
    # them can accidentally build one without the outbox.
    container.register_singleton(
        OutboxSink,  # type: ignore[type-abstract]
        lambda c: OutboxEventSink(
            c.resolve(async_sessionmaker[AsyncSession]),
            c.resolve(EventBus),  # type: ignore[type-abstract]
            sync_drain=c.resolve(Settings).outbox.sync_drain,
        ),
    )
    container.register_singleton(
        UnitOfWorkFactory,
        lambda c: UnitOfWorkFactory(
            c.resolve(async_sessionmaker[AsyncSession]),
            c.resolve(EventBus),  # type: ignore[type-abstract]
            c.resolve(OutboxSink),  # type: ignore[type-abstract]
        ),
    )
    # LLM port: mock implementation only in S5.5 — no real vendor call is made.
    # BLOCKER: AI__API_KEY thật — swap in the AnthropicProvider here (chosen from
    # settings.ai.provider / api_key) once a live key + the vendor SDK are wired.
    refuse_mock_in_prod(settings, "MockLLMProvider", "AI lâm sàng (tương tác thuốc, cảnh báo)")
    container.register_singleton(LLMProvider, lambda _c: MockLLMProvider())  # type: ignore[type-abstract]
    container.register_singleton(
        AuditLogger,
        lambda c: AuditLogger(c.resolve(async_sessionmaker[AsyncSession])),
    )
    container.register_singleton(
        AuditQueryService,
        lambda c: AuditQueryService(c.resolve(async_sessionmaker[AsyncSession])),
    )
    container.register_singleton(
        AuditDashboardService,
        lambda c: AuditDashboardService(c.resolve(async_sessionmaker[AsyncSession])),
    )
    container.register_singleton(PluginLoader, lambda _c: PluginLoader())
    # The registry the loader fills, exposed on its own so a call site can ask "which
    # plugin backs this port" without reaching through the loader (and without being
    # able to load anything itself).
    container.register_singleton(HookRegistry, lambda c: c.resolve(PluginLoader).registry)
    container.register_singleton(
        JwtService,
        lambda c: JwtService(
            c.resolve(Settings).security.jwt_secret.get_secret_value(),
            algorithm=c.resolve(Settings).security.jwt_algorithm,
            ttl_minutes=c.resolve(Settings).security.jwt_ttl_minutes,
        ),
    )
    return container
