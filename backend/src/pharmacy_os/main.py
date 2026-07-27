"""FastAPI application factory and process entrypoint.

The app owns a DI container built from settings, mounts the versioned API and
loads enabled plugins on startup. Business modules attach here from Sprint 3.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pharmacy_os import __version__
from pharmacy_os.api.deps import warn_if_dev_auth_enabled
from pharmacy_os.api.v1 import build_api_router
from pharmacy_os.core.bootstrap import build_container
from pharmacy_os.core.config import Settings, get_settings
from pharmacy_os.core.errors import register_error_handlers
from pharmacy_os.core.outbox import OutboxRelay, OutboxRetention
from pharmacy_os.core.plugins import PluginLoader
from pharmacy_os.core.security import RateLimiter
from pharmacy_os.logging import configure_logging
from pharmacy_os.modules.compliance.application import NationalSyncRetryRelay


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = app.state.container
    settings: Settings = container.resolve(Settings)

    # Only the plugins an operator switched on, each with its own config — not
    # everything that happens to be installed (Sprint 8; previously this loaded every
    # discovered plugin with an empty config, so installing a package was the same as
    # enabling it). An enabled-but-unloadable plugin raises here and the app refuses
    # to start, deliberately: see PluginLoader.load_enabled.
    loader: PluginLoader = container.resolve(PluginLoader)
    if settings.plugins.enabled:
        loader.load_enabled(
            {name: settings.plugins.config.get(name, {}) for name in settings.plugins.enabled}
        )

    # Two process-lifetime background tasks around the outbox, both tied to the app's
    # lifespan so a shutdown cannot leave one running: the relay delivers events that
    # were committed but not yet dispatched (including whatever a crash left behind),
    # and retention ages finished rows out so the table stops growing.
    tasks: list[asyncio.Task[None]] = []
    if settings.outbox.relay_enabled:
        relay: OutboxRelay = container.resolve(OutboxRelay)
        tasks.append(
            asyncio.create_task(
                relay.run_forever(settings.outbox.poll_interval_seconds),
                name="outbox-relay",
            )
        )
    if settings.outbox.retention_enabled:
        retention: OutboxRetention = container.resolve(OutboxRetention)
        tasks.append(
            asyncio.create_task(
                retention.run_forever(settings.outbox.retention_interval_seconds),
                name="outbox-retention",
            )
        )
    # Third background task, same lifespan discipline: re-drives national-DB pushes the
    # gateway rejected. Separate from the outbox pair on purpose — that one delivers
    # internal events to subscribers, this one retries a call to an external authority
    # (docs/13 mục D.4), which fails differently and must back off far more slowly.
    if settings.national_sync.retry_enabled:
        sync_retry: NationalSyncRetryRelay = container.resolve(NationalSyncRetryRelay)
        tasks.append(
            asyncio.create_task(
                sync_retry.run_forever(settings.national_sync.poll_interval_seconds),
                name="national-sync-retry",
            )
        )
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task
    loader.teardown_all()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(debug=settings.app.debug)
    warn_if_dev_auth_enabled(settings)

    app = FastAPI(
        title="AI Pharmacy OS",
        version=__version__,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=_lifespan,
    )
    # S4.6: the FE POS is a separate browser origin (Next.js dev server), so it
    # needs the browser's permission to read cross-origin responses. Bearer tokens
    # aren't cookies, so this widens no attack surface beyond "which origins can
    # read the JSON" — see AppSettings.cors_origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.container = build_container(settings)
    # Bộ đếm tần suất sống theo vòng đời ứng dụng, không theo request (F-9). Đặt trên
    # app.state chứ không trong container vì nó là **trạng thái của tiến trình phục vụ
    # HTTP**, không phải một dịch vụ nghiệp vụ — và vì mỗi TestClient dựng app riêng,
    # nên bộ test không bị rò bộ đếm từ test này sang test khác.
    app.state.rate_limiter = RateLimiter()
    register_error_handlers(app)
    app.include_router(build_api_router(app.state.container))
    return app


app = create_app()
