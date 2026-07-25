"""Plugin contracts. Plugins depend only on these, never on business modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

CORE_PLUGIN_API_VERSION = "1.0"
"""Version of the plugin-facing surface itself — the Protocols in this module.

Three different version numbers meet here and are easy to confuse:

* this one — the **contract** a plugin is written against,
* ``Plugin.version`` — the plugin's own release,
* the app's release version (``pharmacy_os.__version__``).

Bump the **major** component only on a breaking change to these Protocols (a method
added, removed, renamed or re-typed); bump minor for additive, backward-compatible
changes. :func:`is_compatible_api_version` compares majors only, so a plugin built
against ``1.0`` keeps loading against core ``1.7`` and is refused by core ``2.0``.
docs/09 mục 6, "Xung đột phiên bản".
"""


@dataclass(frozen=True, slots=True)
class PluginContext:
    """Minimal, safe surface handed to a plugin at setup time.

    Carries configuration and nothing else — deliberately no DB session, no unit of
    work, no container (docs/09 mục 6: "Chỉ nhận DTO/context tối thiểu, không truyền
    session DB thô"). A plugin that cannot reach the database cannot corrupt it.
    """

    config: dict[str, Any]


@runtime_checkable
class Plugin(Protocol):
    key: str
    version: str
    """The plugin's own release version — not the contract version, see
    :attr:`api_version`."""

    api_version: str
    """Which :data:`CORE_PLUGIN_API_VERSION` this plugin was built against.

    Checked before :meth:`setup` is ever called, so a plugin written against a core
    that has since broken compatibility is refused with a clear reason instead of
    failing somewhere inside its own setup in a harder-to-diagnose way.
    """

    def setup(self, ctx: PluginContext) -> None: ...

    def teardown(self) -> None: ...


@runtime_checkable
class PaymentGateway(Plugin, Protocol):
    """A payment provider (docs/09: ``payment_vnpay``, ``payment_momo``).

    Both methods are ``async`` on purpose, and this is the load-bearing decision of
    the whole plugin surface. They talk to a payment provider over the network; a
    blocking call here would stall the whole event loop — every other counter in the
    pharmacy freezes while one terminal waits on a slow gateway. Being ``async`` also
    makes them the only shape ``asyncio.wait_for`` can actually time out, which is
    what turns docs/09 mục 6 ("timeout") from an aspiration into something
    enforceable.
    """

    async def create_charge(self, order_id: str, amount: int, method: str) -> dict[str, Any]: ...

    async def verify_callback(self, payload: dict[str, Any]) -> str: ...


@runtime_checkable
class RegulatoryConnector(Plugin, Protocol):
    """A regulator-facing connector (docs/09: ``dav_connector``)."""

    def map_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Reshape a domain event into the regulator's payload.

        Stays **synchronous**: this is a pure transformation with no I/O, so making it
        a coroutine would buy nothing and cost every caller an ``await``. Only
        :meth:`submit` crosses the network.
        """
        ...

    async def submit(self, payload: dict[str, Any]) -> dict[str, Any]: ...


#: Ports the loader will register a plugin against, checked in order. A plugin is
#: registered under **every** port it satisfies — nothing stops one package from being
#: both, though none is today. ``Plugin`` itself is deliberately absent: it is the base
#: every plugin satisfies, so registering against it would make "the active plugin for
#: Plugin" a meaningless contest between unrelated packages.
KNOWN_PORTS: tuple[type[Plugin], ...] = (PaymentGateway, RegulatoryConnector)


def is_compatible_api_version(plugin_api_version: str) -> bool:
    """Whether a plugin declaring *plugin_api_version* may be loaded.

    Pure and framework-free, so the compatibility rule is unit-testable on its own.
    Compares only the major component: a matching major means no breaking change lies
    between the two. A malformed value (empty, non-numeric major) is never compatible
    — it arrives from a plugin's own declaration, so it is untrusted input to reject,
    not a bug to raise on.
    """
    core_major = CORE_PLUGIN_API_VERSION.split(".", 1)[0]
    plugin_major = plugin_api_version.split(".", 1)[0]
    return plugin_major.isdigit() and core_major == plugin_major
