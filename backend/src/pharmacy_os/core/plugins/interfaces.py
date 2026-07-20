"""Plugin contracts. Plugins depend only on these, never on business modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class PluginContext:
    """Minimal, safe surface handed to a plugin at setup time."""

    config: dict[str, Any]


@runtime_checkable
class Plugin(Protocol):
    key: str
    version: str

    def setup(self, ctx: PluginContext) -> None: ...

    def teardown(self) -> None: ...


class PaymentGateway(Plugin, Protocol):
    def create_charge(self, order_id: str, amount: int, method: str) -> dict[str, Any]: ...

    def verify_callback(self, payload: dict[str, Any]) -> str: ...


class RegulatoryConnector(Plugin, Protocol):
    def map_event(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]: ...
