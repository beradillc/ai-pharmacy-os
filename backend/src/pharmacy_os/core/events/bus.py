"""Event bus abstraction plus a synchronous in-memory implementation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

import structlog

from pharmacy_os.core.events.base import DomainEvent

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[DomainEvent], Awaitable[None]]

_log = structlog.get_logger(__name__)


class EventBus(Protocol):
    """Publish/subscribe port for domain events."""

    def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> None: ...

    async def publish(self, event: DomainEvent) -> None: ...


class InMemoryEventBus:
    """Dispatches events to subscribed handlers in the current process.

    Handler failures are isolated and logged so one faulty subscriber cannot
    break an unrelated one (see docs/09 plugin isolation rationale).
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = {}

    def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                await handler(event)
            except Exception:  # noqa: BLE001 — isolate subscriber failures
                _log.exception("event_handler_failed", event_name=event.name)
