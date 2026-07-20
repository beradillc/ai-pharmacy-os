"""Discover and load plugins declared under the ``pharmacy_os.plugins`` group.

Discovery uses Python entry points (importlib.metadata). Loading is defensive:
a broken plugin is logged and skipped rather than crashing startup.
"""

from __future__ import annotations

from importlib.metadata import entry_points

import structlog

from pharmacy_os.core.plugins.interfaces import Plugin, PluginContext

_ENTRY_POINT_GROUP = "pharmacy_os.plugins"
_log = structlog.get_logger(__name__)


class PluginLoader:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def discover(self) -> list[str]:
        """Return the keys of plugins advertised via entry points."""
        return [ep.name for ep in entry_points(group=_ENTRY_POINT_GROUP)]

    def load_enabled(self, configs: dict[str, dict[str, object]]) -> None:
        """Instantiate and set up the plugins named in *configs*."""
        for ep in entry_points(group=_ENTRY_POINT_GROUP):
            if ep.name not in configs:
                continue
            try:
                plugin_cls = ep.load()
                plugin: Plugin = plugin_cls()
                plugin.setup(PluginContext(config=dict(configs[ep.name])))
                self._plugins[plugin.key] = plugin
                _log.info("plugin_loaded", key=plugin.key, version=plugin.version)
            except Exception:  # noqa: BLE001 — isolate plugin failures
                _log.exception("plugin_load_failed", plugin=ep.name)

    def get(self, key: str) -> Plugin | None:
        return self._plugins.get(key)

    def teardown_all(self) -> None:
        for plugin in self._plugins.values():
            try:
                plugin.teardown()
            except Exception:  # noqa: BLE001
                _log.exception("plugin_teardown_failed", key=plugin.key)
        self._plugins.clear()
