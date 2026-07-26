"""VNPAY's ``vnp_SecureHash``: HMAC-SHA512 over the sorted, form-encoded params.

Stdlib only (``hmac``/``hashlib``/``urllib.parse``), deliberately: this package may
not import ``pharmacy_os.core.security`` (docs/09 mục 6 — a plugin's only allowed
import from core is ``pharmacy_os.core.plugins``, the contract itself), and the
primitive is different anyway — a keyed MAC over form data for a specific gateway's
protocol, not the AEAD used for at-rest encryption.

VNPAY's own algorithm (not invented here): take every ``vnp_*`` parameter except
``vnp_SecureHash``/``vnp_SecureHashType``, sort by key, form-urlencode each value,
join as ``key=value&key=value...``, HMAC-SHA512 with the merchant's hash secret,
hex digest. The same function signs an outgoing charge request and verifies an
incoming callback — both are "does this exact param set match this exact hash".
"""

from __future__ import annotations

import hashlib
import hmac
from urllib.parse import quote_plus

_EXCLUDED = {"vnp_SecureHash", "vnp_SecureHashType"}


def _canonical_query(params: dict[str, str]) -> str:
    signable = {k: v for k, v in params.items() if k not in _EXCLUDED and v is not None}
    return "&".join(f"{k}={quote_plus(str(signable[k]))}" for k in sorted(signable))


def sign(params: dict[str, str], hash_secret: str) -> str:
    """The ``vnp_SecureHash`` value for *params*, to attach before redirecting."""
    query = _canonical_query(params)
    return hmac.new(hash_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha512).hexdigest()


def verify(params: dict[str, str], hash_secret: str) -> bool:
    """Whether ``params["vnp_SecureHash"]`` matches what *params* itself hashes to.

    Constant-time on purpose (:func:`hmac.compare_digest`) — a timing difference
    between "close" and "wrong" would leak how many leading bytes an attacker
    guessed correctly, turning forgery into a bytewise search instead of an
    infeasible one. Never compare the two hex strings with ``==``.
    """
    received = params.get("vnp_SecureHash")
    if not received:
        return False
    expected = sign(params, hash_secret)
    return hmac.compare_digest(received.lower(), expected.lower())
