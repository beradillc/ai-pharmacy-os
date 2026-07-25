"""Loader behaviour: validate → activate, and fail-fast when an enabled plugin can't.

Entry points are faked via monkeypatch rather than by installing real packages: the
loader's job is to react correctly to what discovery returns, and installing a package
per test case would make the suite depend on the environment it runs in.
"""

from __future__ import annotations

from typing import Any

import pytest

from pharmacy_os.core.plugins import loader as loader_module
from pharmacy_os.core.plugins.hooks import ProviderConflictError
from pharmacy_os.core.plugins.interfaces import (
    CORE_PLUGIN_API_VERSION,
    PaymentGateway,
    PluginContext,
    RegulatoryConnector,
)
from pharmacy_os.core.plugins.loader import PluginLoader, PluginLoadError


class _Gateway:
    key = "vnpay_fake"
    version = "0.1.0"
    api_version = CORE_PLUGIN_API_VERSION

    def __init__(self) -> None:
        self.received_config: dict[str, Any] | None = None
        self.torn_down = False

    def setup(self, ctx: PluginContext) -> None:
        self.received_config = ctx.config

    def teardown(self) -> None:
        self.torn_down = True

    async def create_charge(self, order_id: str, amount: int, method: str) -> dict[str, Any]:
        return {}

    async def verify_callback(self, payload: dict[str, Any]) -> str:
        return "OK"


class _IncompatiblePlugin(_Gateway):
    key = "from_the_future"
    api_version = f"{int(CORE_PLUGIN_API_VERSION.split('.', 1)[0]) + 1}.0"


class _NotAPlugin:
    """Missing setup/teardown/version — fails the contract check."""

    key = "impostor"


class _ExplodingSetup(_Gateway):
    key = "exploding"

    def setup(self, ctx: PluginContext) -> None:
        raise RuntimeError("cấu hình sai")


class _SecondGateway(_Gateway):
    key = "another_gateway"


class _FakeEntryPoint:
    def __init__(self, name: str, target: type) -> None:
        self.name = name
        self._target = target

    def load(self) -> type:
        return self._target


def _install(monkeypatch: pytest.MonkeyPatch, **plugins: type) -> None:
    """Make ``entry_points(group=...)`` report exactly *plugins*."""
    eps = [_FakeEntryPoint(name, target) for name, target in plugins.items()]
    monkeypatch.setattr(loader_module, "entry_points", lambda group: eps)


def test_discover_lists_installed_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, vnpay=_Gateway, other=_SecondGateway)
    assert sorted(PluginLoader().discover()) == ["other", "vnpay"]


def test_nothing_loads_until_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Installing a plugin must not be the same as switching it on."""
    _install(monkeypatch, vnpay=_Gateway)
    loader = PluginLoader()
    loader.load_enabled({})
    assert loader.get("vnpay_fake") is None
    assert loader.registry.resolve(PaymentGateway) is None


def test_an_enabled_plugin_is_set_up_and_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, vnpay=_Gateway)
    loader = PluginLoader()
    loader.load_enabled({"vnpay": {"merchant": "BERA"}})

    plugin = loader.registry.resolve(PaymentGateway)
    assert plugin is not None
    assert plugin.key == "vnpay_fake"
    # Config reached the plugin — the whole point of the per-plugin config map.
    assert plugin.received_config == {"merchant": "BERA"}  # type: ignore[attr-defined]
    # A gateway must not be filed under an unrelated port.
    assert loader.registry.resolve(RegulatoryConnector) is None


def test_a_plugin_with_no_config_still_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, vnpay=_Gateway)
    loader = PluginLoader()
    loader.load_enabled({"vnpay": {}})
    assert loader.registry.resolve(PaymentGateway) is not None


# --- fail-fast ----------------------------------------------------------------


def test_enabling_a_plugin_that_is_not_installed_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The silent-no-op case the fail-fast change exists to kill."""
    _install(monkeypatch)
    with pytest.raises(PluginLoadError) as exc:
        PluginLoader().load_enabled({"vnpay": {}})
    assert "vnpay" in str(exc.value)


def test_an_incompatible_api_version_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, future=_IncompatiblePlugin)
    with pytest.raises(PluginLoadError, match="major"):
        PluginLoader().load_enabled({"future": {}})


def test_a_plugin_failing_the_contract_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, impostor=_NotAPlugin)
    with pytest.raises(PluginLoadError, match="contract"):
        PluginLoader().load_enabled({"impostor": {}})


def test_a_failing_setup_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, exploding=_ExplodingSetup)
    with pytest.raises(PluginLoadError, match="setup"):
        PluginLoader().load_enabled({"exploding": {}})


def test_two_gateways_enabled_at_once_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two providers for one port is a configuration error, not a race to register."""
    _install(monkeypatch, first=_Gateway, second=_SecondGateway)
    with pytest.raises(ProviderConflictError):
        PluginLoader().load_enabled({"first": {}, "second": {}})


def test_an_invalid_plugin_never_gets_to_run_its_own_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validation precedes activation: a rejected plugin's code must not execute."""
    ran: list[str] = []

    class _RecordingIncompatible(_IncompatiblePlugin):
        def setup(self, ctx: PluginContext) -> None:
            ran.append("setup")

    _install(monkeypatch, future=_RecordingIncompatible)
    with pytest.raises(PluginLoadError):
        PluginLoader().load_enabled({"future": {}})
    assert ran == []


# --- teardown -----------------------------------------------------------------


def test_teardown_clears_plugins_and_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, vnpay=_Gateway)
    loader = PluginLoader()
    loader.load_enabled({"vnpay": {}})
    plugin = loader.registry.resolve(PaymentGateway)

    loader.teardown_all()

    assert plugin.torn_down is True  # type: ignore[attr-defined]
    assert loader.get("vnpay_fake") is None
    assert loader.registry.resolve(PaymentGateway) is None


def test_one_failing_teardown_does_not_skip_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shutdown stays defensive — the opposite of load, and on purpose."""
    torn: list[str] = []

    class _BadTeardown(_Gateway):
        key = "bad"

        def teardown(self) -> None:
            raise RuntimeError("nổ lúc tắt")

    class _GoodConnector:
        key = "good"
        version = "0.1.0"
        api_version = CORE_PLUGIN_API_VERSION

        def setup(self, ctx: PluginContext) -> None: ...

        def teardown(self) -> None:
            torn.append("good")

        def map_event(self, event: dict[str, Any]) -> dict[str, Any]:
            return event

        async def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {}

    _install(monkeypatch, bad=_BadTeardown, good=_GoodConnector)
    loader = PluginLoader()
    loader.load_enabled({"bad": {}, "good": {}})

    loader.teardown_all()  # must not raise

    assert torn == ["good"]
