"""FastAPI application factory and process entrypoint.

The app owns a DI container built from settings, mounts the versioned API and
loads enabled plugins on startup. Business modules attach here from Sprint 3.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pharmacy_os import __version__
from pharmacy_os.api.deps import warn_if_dev_auth_enabled
from pharmacy_os.api.v1 import build_api_router
from pharmacy_os.core.bootstrap import build_container
from pharmacy_os.core.config import Settings, get_settings
from pharmacy_os.core.errors import register_error_handlers
from pharmacy_os.core.plugins import PluginLoader
from pharmacy_os.logging import configure_logging


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    loader: PluginLoader = app.state.container.resolve(PluginLoader)
    discovered = loader.discover()
    if discovered:
        loader.load_enabled({name: {} for name in discovered})
    yield
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
    app.state.container = build_container(settings)
    register_error_handlers(app)
    app.include_router(build_api_router(app.state.container))
    return app


app = create_app()
