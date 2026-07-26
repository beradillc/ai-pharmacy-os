from __future__ import annotations

from uuid import uuid4

import pytest
from pharmacy_os.core.plugins.interfaces import (
    CORE_PLUGIN_API_VERSION,
    PaymentCallbackError,
    PaymentGateway,
    Plugin,
    PluginContext,
)
from pydantic import ValidationError

from payment_vnpay.plugin import VNPayPlugin
from payment_vnpay.signature import sign

_CONFIG = {
    "tmn_code": "DEMO01",
    "hash_secret": "test-hash-secret-do-not-use-in-prod",
    "return_url": "https://pharmacy.example/return",
}


def _plugin() -> VNPayPlugin:
    plugin = VNPayPlugin()
    plugin.setup(PluginContext(config=dict(_CONFIG)))
    return plugin


def test_satisfies_the_plugin_and_payment_gateway_contracts() -> None:
    plugin = _plugin()
    assert isinstance(plugin, Plugin)
    assert isinstance(plugin, PaymentGateway)
    assert plugin.api_version == CORE_PLUGIN_API_VERSION


def test_setup_rejects_missing_required_config() -> None:
    plugin = VNPayPlugin()
    with pytest.raises(ValidationError):
        plugin.setup(PluginContext(config={"tmn_code": "DEMO01"}))  # no hash_secret/return_url


async def test_create_charge_returns_a_signed_url_carrying_the_order_id() -> None:
    plugin = _plugin()
    order_id = str(uuid4())
    charge = await plugin.create_charge(order_id, 2_000_000, "vnpay")
    assert order_id in charge["payment_url"]
    assert "vnp_SecureHash=" in charge["payment_url"]
    assert charge["vnp_TxnRef"] == order_id


async def test_verify_callback_accepts_a_correctly_signed_payload() -> None:
    plugin = _plugin()
    order_id = str(uuid4())
    payload = {
        "vnp_TxnRef": order_id,
        "vnp_ResponseCode": "00",
        "vnp_Amount": "2000000",
        "vnp_TransactionNo": "vnpay-txn-1",
    }
    payload["vnp_SecureHash"] = sign(payload, _CONFIG["hash_secret"])

    result = await plugin.verify_callback(payload)

    assert result == order_id


async def test_verify_callback_rejects_a_forged_signature() -> None:
    plugin = _plugin()
    payload = {
        "vnp_TxnRef": str(uuid4()),
        "vnp_ResponseCode": "00",
        "vnp_SecureHash": "0" * 128,
    }
    with pytest.raises(PaymentCallbackError):
        await plugin.verify_callback(payload)


async def test_verify_callback_rejects_a_tampered_amount_even_with_a_once_valid_hash() -> None:
    plugin = _plugin()
    payload = {
        "vnp_TxnRef": str(uuid4()),
        "vnp_ResponseCode": "00",
        "vnp_Amount": "2000000",
    }
    payload["vnp_SecureHash"] = sign(payload, _CONFIG["hash_secret"])
    payload["vnp_Amount"] = "1"  # attacker edits the amount after signing

    with pytest.raises(PaymentCallbackError):
        await plugin.verify_callback(payload)


async def test_verify_callback_rejects_missing_txn_ref() -> None:
    plugin = _plugin()
    payload = {"vnp_ResponseCode": "00"}
    payload["vnp_SecureHash"] = sign(payload, _CONFIG["hash_secret"])
    with pytest.raises(PaymentCallbackError):
        await plugin.verify_callback(payload)


async def test_teardown_clears_config_so_calls_after_fail_loud() -> None:
    plugin = _plugin()
    plugin.teardown()
    with pytest.raises(RuntimeError):
        await plugin.create_charge("x", 1, "vnpay")
