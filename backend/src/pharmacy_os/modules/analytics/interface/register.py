"""Analytics module interface wiring.

Unlike a self-contained module, analytics' service depends on cross-module adapters
that only the composition root can build, so the ``AnalyticsService`` instance is
registered there (``api/v1/analytics_wiring.py``), not here. This ``register`` only
mounts the router, which resolves the service from the container per request.
"""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.di import Container
from pharmacy_os.modules.analytics.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    return build_router(get_context)


__all__ = ["register"]
