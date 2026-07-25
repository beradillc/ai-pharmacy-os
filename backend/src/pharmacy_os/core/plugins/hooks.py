"""Provider-hook resolution (docs/09 mục 5): one active plugin per port.

A **provider hook** answers "which plugin currently backs this port" — e.g. the single
enabled :class:`~.interfaces.PaymentGateway` a checkout flow should call.

Deliberately narrower than the **event hook** docs/09 also describes (many plugins
reacting to one domain event, the shape ``dav_connector`` would eventually want).
Event hooks are out of scope here: the only plugin queued behind this one,
``payment_vnpay``, is a provider, and designing a fan-out mechanism with no consumer
would be guessing at requirements. Left for whoever builds the first event-shaped
plugin, against a real need.

Pure and I/O-free: no entry points, no config, no logging, no framework. The loader is
the only expected writer; anything needing a plugin at runtime is a reader.
"""

from __future__ import annotations

from typing import TypeVar, cast

from pharmacy_os.core.plugins.interfaces import Plugin

PortT = TypeVar("PortT", bound=Plugin)


class ProviderConflictError(Exception):
    """Two enabled plugins both claim the same port.

    Refusing to pick a winner is the point. A silent "last registration wins" would
    make which payment gateway actually charges the customer depend on entry-point
    iteration order — invisible in the code, stable in dev, and eventually wrong in
    production.
    """


class HookRegistry:
    """Which plugin backs which port, for the lifetime of the process."""

    def __init__(self) -> None:
        self._providers: dict[type[Plugin], Plugin] = {}

    def register_provider(self, port: type[Plugin], plugin: Plugin) -> None:
        """Declare *plugin* as the active implementation of *port*.

        *port* is the Protocol class (e.g. ``PaymentGateway``), not an instance: the
        registry is keyed by contract because a caller resolving later knows only the
        port it needs, never which plugin — if any — happens to provide it.

        Registering the same plugin against the same port twice is a no-op rather than
        a conflict, so a repeated load is harmless; two *different* plugins raise.
        """
        existing = self._providers.get(port)
        if existing is not None and existing is not plugin:
            raise ProviderConflictError(
                f"Port {port.__name__} đã có plugin '{existing.key}' cung cấp — "
                f"'{plugin.key}' không thể cùng cung cấp port này. "
                f"Chỉ bật một trong hai trong PLUGINS__ENABLED."
            )
        self._providers[port] = plugin

    def resolve(self, port: type[PortT]) -> PortT | None:
        """The plugin currently backing *port*, or ``None`` when none is enabled.

        ``None`` is an ordinary outcome, not an error: no plugin enabled is the
        default and current state of every deployment, so each call site must already
        have a "no provider configured" path.
        """
        found = self._providers.get(port)
        # Safe: register_provider is the only writer and only ever files a plugin
        # under the port it was registered against.
        return cast("PortT | None", found)

    def clear(self) -> None:
        """Drop every registration — mirrors ``PluginLoader.teardown_all``."""
        self._providers.clear()
