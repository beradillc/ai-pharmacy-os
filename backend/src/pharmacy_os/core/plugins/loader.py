"""Discover and load plugins declared under the ``pharmacy_os.plugins`` group.

Discovery uses Python entry points (``importlib.metadata``), so a plugin is an
installed package rather than a name in a list inside the core. That gives a real
dependency boundary — a plugin package that never declares ``pharmacy_os.modules`` as
a dependency cannot import it — which is what the isolation promise in docs/09 rests
on. The trade-off is that a plugin is invisible until its package is installed.

**Enablement is separate from discovery.** :meth:`PluginLoader.discover` reports what
is installed; only the keys named in ``PLUGINS__ENABLED`` are actually loaded. That
split is what lets an operator switch a plugin on or off without touching core code
(ROADMAP Sprint 8 DoD, "bật/tắt plugin không sửa lõi") — see
:class:`~pharmacy_os.core.config.PluginsSettings`.

**Loading an enabled plugin is fail-fast** (Sprint 8 change): a plugin that is switched
on but cannot be loaded stops the app from starting, instead of being logged and
skipped as before. Skipping silently moves the failure to a cashier pressing "pay"
against a gateway that was never there. Refusing to start matches the discipline
already applied to ``APP__ENV=prod`` with ``ALLOW_DEV_AUTH=true``: a dangerous
configuration fails at deploy time, loudly. Teardown stays defensive — the process is
going down anyway and one bad plugin must not skip the others' cleanup.
"""

from __future__ import annotations

from collections.abc import Mapping
from importlib.metadata import EntryPoint, entry_points
from typing import Any

import structlog

from pharmacy_os.core.plugins.hooks import HookRegistry
from pharmacy_os.core.plugins.interfaces import (
    CORE_PLUGIN_API_VERSION,
    KNOWN_PORTS,
    Plugin,
    PluginContext,
    is_compatible_api_version,
)

_ENTRY_POINT_GROUP = "pharmacy_os.plugins"
_log = structlog.get_logger(__name__)


class PluginLoadError(RuntimeError):
    """An enabled plugin could not be loaded — raised at startup, never swallowed."""


class PluginLoader:
    def __init__(self, registry: HookRegistry | None = None) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._registry = registry if registry is not None else HookRegistry()

    @property
    def registry(self) -> HookRegistry:
        """Where resolved providers live, for call sites that need one at runtime."""
        return self._registry

    def discover(self) -> list[str]:
        """Keys of every plugin advertised via entry points, enabled or not."""
        return [ep.name for ep in entry_points(group=_ENTRY_POINT_GROUP)]

    def load_enabled(self, configs: Mapping[str, Mapping[str, Any]]) -> None:
        """Instantiate, validate, set up and register each plugin named in *configs*.

        Raises :class:`PluginLoadError` on the first plugin that cannot be loaded —
        including one enabled but not installed, otherwise the most confusing failure
        of all: a silent no-op that looks like the plugin ran.
        """
        available = {ep.name: ep for ep in entry_points(group=_ENTRY_POINT_GROUP)}
        for name in configs:
            entry_point = available.get(name)
            if entry_point is None:
                raise PluginLoadError(
                    f"Plugin '{name}' được bật trong PLUGINS__ENABLED nhưng không tìm thấy. "
                    f"Đã cài package chưa? Hiện có: {sorted(available) or 'không có plugin nào'}"
                )
            plugin = self._load_one(entry_point, dict(configs[name]))
            self._plugins[plugin.key] = plugin

        if unused := sorted(set(available) - set(configs)):
            # Not a problem, but the likeliest explanation for "the plugin is
            # installed and nothing happens" — worth one line at startup.
            _log.info("plugins_available_but_disabled", plugins=unused)

    def _load_one(self, entry_point: EntryPoint, config: dict[str, Any]) -> Plugin:
        try:
            plugin_cls = entry_point.load()
            plugin: Plugin = plugin_cls()
        except Exception as exc:
            raise PluginLoadError(f"Plugin '{entry_point.name}' nạp lỗi: {exc!r}") from exc

        # Validate before setup(): a plugin failing the contract must never run its
        # own code, or the failure mode becomes whatever that code happens to do.
        if not isinstance(plugin, Plugin):
            raise PluginLoadError(
                f"Plugin '{entry_point.name}' không đúng contract `Plugin` "
                f"(thiếu key/version/api_version/setup/teardown)"
            )
        if not is_compatible_api_version(plugin.api_version):
            raise PluginLoadError(
                f"Plugin '{plugin.key}' viết cho API lõi '{plugin.api_version}', "
                f"lõi hiện tại '{CORE_PLUGIN_API_VERSION}' — khác major, không nạp được"
            )

        try:
            plugin.setup(PluginContext(config=config))
        except Exception as exc:
            raise PluginLoadError(f"Plugin '{plugin.key}' setup() lỗi: {exc!r}") from exc

        ports = [port for port in KNOWN_PORTS if isinstance(plugin, port)]
        for port in ports:
            self._registry.register_provider(port, plugin)

        _log.info(
            "plugin_loaded",
            key=plugin.key,
            version=plugin.version,
            api_version=plugin.api_version,
            ports=[p.__name__ for p in ports],
        )
        if not ports:
            # Legal — a plugin may exist purely for its side effects — but almost
            # always a mistake: satisfying no port means nothing will ever call it.
            _log.warning("plugin_provides_no_known_port", key=plugin.key)
        return plugin

    def get(self, key: str) -> Plugin | None:
        return self._plugins.get(key)

    def teardown_all(self) -> None:
        """Tear every plugin down defensively — one failure must not skip the rest."""
        for plugin in self._plugins.values():
            try:
                plugin.teardown()
            except Exception:  # noqa: BLE001 — shutting down; log and keep going
                _log.exception("plugin_teardown_failed", key=plugin.key)
        self._plugins.clear()
        self._registry.clear()
