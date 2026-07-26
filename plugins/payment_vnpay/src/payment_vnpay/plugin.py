"""``VNPayPlugin``: implements ``pharmacy_os.core.plugins.interfaces.PaymentGateway``.

The only import from the host app anywhere in this package is
``pharmacy_os.core.plugins`` — the contract itself (docs/09 mục 6, enforced by the
``payment-vnpay-*`` import-linter contracts in the host's ``.importlinter``). No
``pharmacy_os.modules``, no ``pharmacy_os.core.security``/``core.db``/etc.: this
plugin knows nothing about orders, tenants, or the database, and cannot — the
``sales`` module (which does) is what calls it, never the reverse.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus

from pharmacy_os.core.plugins.interfaces import (
    CORE_PLUGIN_API_VERSION,
    PaymentCallbackError,
    PluginContext,
)

from payment_vnpay.config import VnpayConfig
from payment_vnpay.signature import sign, verify

__version__ = "0.1.0"


class VNPayPlugin:
    key = "vnpay"
    version = __version__
    api_version = CORE_PLUGIN_API_VERSION

    def __init__(self) -> None:
        self._config: VnpayConfig | None = None

    def setup(self, ctx: PluginContext) -> None:
        # Pydantic raises on a missing/malformed field; PluginLoader turns that
        # into a startup-time PluginLoadError. Never caught here — a config error
        # must stop the app, not be swallowed into "gateway not configured".
        self._config = VnpayConfig.model_validate(ctx.config)

    def teardown(self) -> None:
        self._config = None

    async def create_charge(self, order_id: str, amount: int, method: str) -> dict[str, Any]:
        """Build the VNPAY redirect URL. No network call: VNPAY's redirect-based
        flow needs nothing from their servers to start a payment, only a correctly
        signed URL — the customer's browser does the rest. ``async def`` regardless,
        matching the contract (docs/09 mục 4): a future gateway that does need a
        network round-trip here changes nothing at the call site.
        """
        config = self._require_config()
        now = datetime.now(UTC)
        params = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": config.tmn_code,
            "vnp_Amount": str(amount),
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": order_id,
            "vnp_OrderInfo": f"Thanh toan don hang {order_id}",
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": config.return_url,
            "vnp_IpAddr": "127.0.0.1",
            "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
        }
        secure_hash = sign(params, config.hash_secret)
        query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(params.items()))
        payment_url = f"{config.base_url}?{query}&vnp_SecureHash={secure_hash}"
        return {"payment_url": payment_url, "vnp_TxnRef": order_id}

    async def verify_callback(self, payload: dict[str, Any]) -> str:
        """Authenticate one IPN callback; return the order id it names.

        Only checks the signature — never interprets ``vnp_ResponseCode`` (that is
        a business decision for ``sales``, which this package is forbidden from
        importing). Raises :class:`PaymentCallbackError` on anything that cannot
        be trusted: missing fields or a signature that does not match.
        """
        config = self._require_config()
        txn_ref = payload.get("vnp_TxnRef")
        secure_hash = payload.get("vnp_SecureHash")
        if not txn_ref or not secure_hash:
            raise PaymentCallbackError(
                "callback thiếu vnp_TxnRef hoặc vnp_SecureHash — không xác thực được"
            )
        string_payload = {k: str(v) for k, v in payload.items()}
        if not verify(string_payload, config.hash_secret):
            raise PaymentCallbackError("chữ ký vnp_SecureHash không khớp")
        return str(txn_ref)

    def _require_config(self) -> VnpayConfig:
        if self._config is None:
            # PluginLoader always calls setup() before anything can reach here —
            # this is an invariant violation, not a normal runtime outcome.
            raise RuntimeError("VNPayPlugin dùng trước khi setup() — lỗi vòng đời plugin")
        return self._config
