"""Plugin system: contracts + entry-point loader (see docs/09)."""

from pharmacy_os.core.plugins.interfaces import (
    PaymentGateway,
    Plugin,
    PluginContext,
    RegulatoryConnector,
)
from pharmacy_os.core.plugins.loader import PluginLoader

__all__ = [
    "Plugin",
    "PluginContext",
    "PaymentGateway",
    "RegulatoryConnector",
    "PluginLoader",
]
