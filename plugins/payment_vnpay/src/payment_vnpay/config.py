"""Config schema for the ``vnpay`` entry in ``PLUGINS__CONFIG`` (docs/09/10).

Validated by :class:`VNPayPlugin.setup` — a bad/missing field raises here, which
``PluginLoader`` turns into a startup-time ``PluginLoadError`` (fail-fast, docs/09
mục 6): a merchant code or hash secret typo must stop the app from starting, not
surface the first time a cashier presses "pay".
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class VnpayConfig(BaseModel):
    tmn_code: str = Field(min_length=1)
    """VNPAY's merchant code (``vnp_TmnCode``) — issued once per merchant account,
    not secret, but wrong is a same-class failure as a wrong secret: nothing works."""

    hash_secret: str = Field(min_length=1)
    """TUYỆT ĐỐI KHÔNG commit, không ghi log — signs every request and callback.
    A leaked hash secret lets anyone forge a "payment succeeded" callback for any
    amount, same severity class as the at-rest encryption keys (docs/09 §3,
    PLUGINS__CONFIG env-var only)."""

    base_url: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    """VNPAY's payment page. Sandbox by default — a deployment must deliberately
    point this at the production endpoint, never the other way around."""

    return_url: str = Field(min_length=1)
    """Where VNPAY redirects the customer's browser after paying (``vnp_ReturnUrl``).
    Display-only: this is the customer's *browser* returning, not proof of payment
    — the IPN callback is the only source of truth, matching :meth:`verify_callback`
    never trusting anything the confirm flow did not independently authenticate."""
