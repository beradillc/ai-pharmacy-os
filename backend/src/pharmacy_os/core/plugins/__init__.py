"""Plugin system: contracts + entry-point loader (see docs/09)."""

from pharmacy_os.core.plugins.hooks import HookRegistry, ProviderConflictError
from pharmacy_os.core.plugins.interfaces import (
    CORE_PLUGIN_API_VERSION,
    KNOWN_PORTS,
    PaymentGateway,
    Plugin,
    PluginContext,
    RegulatoryConnector,
    is_compatible_api_version,
)
from pharmacy_os.core.plugins.loader import PluginLoader

__all__ = [
    "CORE_PLUGIN_API_VERSION",
    "KNOWN_PORTS",
    "HookRegistry",
    "Plugin",
    "PluginContext",
    "PaymentGateway",
    "ProviderConflictError",
    "RegulatoryConnector",
    "PluginLoader",
    "is_compatible_api_version",
]
