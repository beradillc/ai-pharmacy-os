"""Compose the kernel: build the DI container from settings.

This is the single place where concrete kernel implementations are chosen and
registered. Business modules will call ``container.resolve(...)`` for the
capabilities they need — never constructing kernel objects themselves.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from pharmacy_os.core.ai import LLMProvider, MockLLMProvider
from pharmacy_os.core.audit import AuditLogger, AuditQueryService
from pharmacy_os.core.config import Settings
from pharmacy_os.core.db import build_engine, build_sessionmaker
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus, InMemoryEventBus
from pharmacy_os.core.plugins import PluginLoader
from pharmacy_os.core.security.jwt import JwtService


def build_container(settings: Settings) -> Container:
    container = Container()
    container.register_instance(Settings, settings)

    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size, echo=settings.app.debug)
    container.register_instance(AsyncEngine, engine)

    session_factory = build_sessionmaker(engine)
    container.register_instance(async_sessionmaker[AsyncSession], session_factory)

    # EventBus is a Protocol used as a service key; concrete impl is InMemoryEventBus.
    container.register_singleton(EventBus, lambda _c: InMemoryEventBus())  # type: ignore[type-abstract]
    # LLM port: mock implementation only in S5.5 — no real vendor call is made.
    # BLOCKER: AI__API_KEY thật — swap in the AnthropicProvider here (chosen from
    # settings.ai.provider / api_key) once a live key + the vendor SDK are wired.
    container.register_singleton(LLMProvider, lambda _c: MockLLMProvider())  # type: ignore[type-abstract]
    container.register_singleton(
        AuditLogger,
        lambda c: AuditLogger(c.resolve(async_sessionmaker[AsyncSession])),
    )
    container.register_singleton(
        AuditQueryService,
        lambda c: AuditQueryService(c.resolve(async_sessionmaker[AsyncSession])),
    )
    container.register_singleton(PluginLoader, lambda _c: PluginLoader())
    container.register_singleton(
        JwtService,
        lambda c: JwtService(
            c.resolve(Settings).security.jwt_secret.get_secret_value(),
            algorithm=c.resolve(Settings).security.jwt_algorithm,
            ttl_minutes=c.resolve(Settings).security.jwt_ttl_minutes,
        ),
    )
    return container
