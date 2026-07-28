"""Plugin contract rules + provider-hook resolution (Sprint 8, docs/09).

The properties worth pinning are the ones that decide whether a plugin can quietly do
the wrong thing: an incompatible plugin must be refusable *before* it runs, and two
plugins must never silently contest one port.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import pytest

from pharmacy_os.core.plugins.hooks import HookRegistry, ProviderConflictError
from pharmacy_os.core.plugins.interfaces import (
    CORE_PLUGIN_API_VERSION,
    KNOWN_PORTS,
    PaymentCallbackError,
    PaymentGateway,
    Plugin,
    PluginContext,
    RegulatoryConnector,
    is_compatible_api_version,
)


class _FakeGateway:
    """A minimal, well-behaved ``PaymentGateway`` — no network, no state."""

    key = "fake_gateway"
    version = "0.1.0"
    api_version = CORE_PLUGIN_API_VERSION

    def __init__(self, key: str = "fake_gateway") -> None:
        self.key = key
        self.setup_calls = 0
        self.teardown_calls = 0

    def setup(self, ctx: PluginContext) -> None:
        self.setup_calls += 1

    def teardown(self) -> None:
        self.teardown_calls += 1

    async def create_charge(self, order_id: str, amount: int, method: str) -> dict[str, Any]:
        return {"order_id": order_id, "amount": amount, "method": method}

    async def verify_callback(self, payload: dict[str, Any]) -> str:
        if payload.get("bad_signature"):
            raise PaymentCallbackError("chữ ký không hợp lệ")
        return "OK"


class _FakeConnector:
    key = "fake_connector"
    version = "0.1.0"
    api_version = CORE_PLUGIN_API_VERSION

    def setup(self, ctx: PluginContext) -> None: ...

    def teardown(self) -> None: ...

    def map_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return event

    async def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ACK"}


# --- API version compatibility ------------------------------------------------


def test_same_api_version_is_compatible() -> None:
    assert is_compatible_api_version(CORE_PLUGIN_API_VERSION)


def test_a_newer_minor_is_still_compatible() -> None:
    """Minor bumps are additive by definition, so an older plugin keeps working."""
    core_major = CORE_PLUGIN_API_VERSION.split(".", 1)[0]
    assert is_compatible_api_version(f"{core_major}.999")


def test_a_different_major_is_refused() -> None:
    core_major = int(CORE_PLUGIN_API_VERSION.split(".", 1)[0])
    assert not is_compatible_api_version(f"{core_major + 1}.0")


@pytest.mark.parametrize("declared", ["", "abc", "x.0", ".", "v1.0"])
def test_a_malformed_api_version_is_refused_not_raised(declared: str) -> None:
    """Untrusted input from a plugin's own declaration: reject, never crash."""
    assert not is_compatible_api_version(declared)


# --- Protocol conformance -----------------------------------------------------


def test_a_conforming_plugin_satisfies_its_port_at_runtime() -> None:
    gateway = _FakeGateway()
    assert isinstance(gateway, Plugin)
    assert isinstance(gateway, PaymentGateway)


def test_a_gateway_is_not_mistaken_for_a_connector() -> None:
    """Ports must be distinguishable, otherwise the loader files plugins wrongly."""
    assert not isinstance(_FakeGateway(), RegulatoryConnector)
    assert not isinstance(_FakeConnector(), PaymentGateway)


def test_an_object_missing_contract_members_is_not_a_plugin() -> None:
    class NotAPlugin:
        key = "nope"

    assert not isinstance(NotAPlugin(), Plugin)


def test_known_ports_excludes_the_base_plugin_protocol() -> None:
    """Registering against ``Plugin`` would make every plugin contest one slot."""
    assert Plugin not in KNOWN_PORTS
    assert PaymentGateway in KNOWN_PORTS
    assert RegulatoryConnector in KNOWN_PORTS


# --- HookRegistry -------------------------------------------------------------


def test_resolving_an_unregistered_port_returns_none() -> None:
    """The default state of every deployment today — must not raise."""
    assert HookRegistry().resolve(PaymentGateway) is None


def test_a_registered_provider_is_resolved_back() -> None:
    registry = HookRegistry()
    gateway = _FakeGateway()
    registry.register_provider(PaymentGateway, gateway)
    assert registry.resolve(PaymentGateway) is gateway


def test_two_plugins_claiming_one_port_is_refused() -> None:
    registry = HookRegistry()
    registry.register_provider(PaymentGateway, _FakeGateway("first"))
    with pytest.raises(ProviderConflictError) as exc:
        registry.register_provider(PaymentGateway, _FakeGateway("second"))
    # The message must name both, or an operator cannot tell which to switch off.
    assert "first" in str(exc.value)
    assert "second" in str(exc.value)


def test_registering_the_same_plugin_twice_is_harmless() -> None:
    registry = HookRegistry()
    gateway = _FakeGateway()
    registry.register_provider(PaymentGateway, gateway)
    registry.register_provider(PaymentGateway, gateway)
    assert registry.resolve(PaymentGateway) is gateway


def test_distinct_ports_do_not_collide() -> None:
    registry = HookRegistry()
    gateway, connector = _FakeGateway(), _FakeConnector()
    registry.register_provider(PaymentGateway, gateway)
    registry.register_provider(RegulatoryConnector, connector)
    assert registry.resolve(PaymentGateway) is gateway
    assert registry.resolve(RegulatoryConnector) is connector


def test_clear_drops_registrations() -> None:
    registry = HookRegistry()
    registry.register_provider(PaymentGateway, _FakeGateway())
    registry.clear()
    assert registry.resolve(PaymentGateway) is None


async def test_gateway_hooks_are_awaitable() -> None:
    """Guards the async decision: a sync hook here would stall the event loop and
    could not be timed out (design mục 3)."""
    gateway = _FakeGateway()
    charge = await gateway.create_charge("order-1", 50_000, "CARD")
    assert charge["amount"] == 50_000
    assert await gateway.verify_callback({}) == "OK"


async def test_bad_callback_raises_the_shared_gateway_agnostic_error() -> None:
    """A caller in ``sales`` catches this one type regardless of which gateway is
    active — it cannot import anything plugin-specific (mục 4/4 `payment_vnpay`)."""
    with pytest.raises(PaymentCallbackError):
        await _FakeGateway().verify_callback({"bad_signature": True})


# --- A-06: trần thời gian gọi plugin là THẬT, không chỉ là docstring ----------


async def test_gateway_call_that_hangs_is_cut_off_by_the_timeout() -> None:
    """Kiểm toán A-06: docstring hứa timeout, repo không có ``asyncio.wait_for`` nào.

    🔴 **Đo THỜI GIAN TRÔI, không chỉ bắt ``TimeoutError``.** Bản đầu của test này chỉ
    ``pytest.raises(TimeoutError)`` — và khi tôi cố ý gỡ trần thời gian ra để kiểm
    (kỷ luật #14), nó **treo vô hạn** thay vì đỏ. Một test treo còn tệ hơn test đỏ: nó
    làm nghẽn cả bộ test mà không nói vì sao.

    Thêm một guard riêng của test ở 2 giây thì lại sinh vấn đề khác — ``TimeoutError``
    của guard đó cũng lọt qua ``pytest.raises``, tức test sẽ **xanh vì lý do sai**. Nên
    thứ được khẳng định ở đây là **thời gian trôi**: nếu trần của sản phẩm cắt thì lời
    gọi kết thúc trong mili giây; nếu chính guard của test cắt thì nó mất 2 giây, và
    khẳng định dưới đây đỏ.
    """
    import asyncio
    import time

    from pharmacy_os.modules.sales.application.service import SalesService

    never = asyncio.Event()

    async def hangs() -> str:
        await never.wait()
        return "không bao giờ tới đây"

    service = SalesService.__new__(SalesService)  # không cần CSDL cho phép thử này
    service._gateway_timeout = 0.05  # type: ignore[attr-defined]

    started = time.monotonic()
    with suppress(TimeoutError):
        await asyncio.wait_for(
            service._with_gateway_timeout(hangs()),  # type: ignore[attr-defined]
            timeout=2.0,  # guard của TEST, không phải của sản phẩm
        )
    elapsed = time.monotonic() - started

    assert elapsed < 1.0, (
        f"lời gọi mất {elapsed:.2f}s — trần của SẢN PHẨM không cắt, chính guard của test cắt"
    )


async def test_gateway_call_within_the_budget_passes_through_untouched() -> None:
    """Mặt ngược lại: cổng phải MỞ được. Một trần chỉ biết cắt thì không phải trần."""
    from pharmacy_os.modules.sales.application.service import SalesService

    async def quick() -> str:
        return "xong"

    service = SalesService.__new__(SalesService)
    service._gateway_timeout = 5.0  # type: ignore[attr-defined]

    assert await service._with_gateway_timeout(quick()) == "xong"  # type: ignore[attr-defined]
