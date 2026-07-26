from __future__ import annotations

from payment_vnpay.signature import sign, verify

_SECRET = "test-hash-secret-do-not-use-in-prod"


def _params() -> dict[str, str]:
    return {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": "DEMO01",
        "vnp_Amount": "2000000",
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": "order-123",
        "vnp_OrderInfo": "Thanh toan don hang order-123",
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": "https://pharmacy.example/return",
        "vnp_IpAddr": "127.0.0.1",
        "vnp_CreateDate": "20260726120000",
    }


def test_sign_is_deterministic_for_the_same_params() -> None:
    params = _params()
    assert sign(params, _SECRET) == sign(params, _SECRET)


def test_different_secret_yields_a_different_hash() -> None:
    params = _params()
    assert sign(params, _SECRET) != sign(params, "a-different-secret")


def test_sign_then_verify_round_trips() -> None:
    params = _params()
    params["vnp_SecureHash"] = sign(params, _SECRET)
    assert verify(params, _SECRET) is True


def test_verify_rejects_when_secure_hash_missing() -> None:
    assert verify(_params(), _SECRET) is False


def test_verify_rejects_a_tampered_amount() -> None:
    """The whole point: signing over the params means changing one after the fact
    invalidates the hash — this is what stops an attacker from replaying a
    genuine callback with the amount edited."""
    params = _params()
    params["vnp_SecureHash"] = sign(params, _SECRET)
    params["vnp_Amount"] = "1"
    assert verify(params, _SECRET) is False


def test_verify_rejects_a_tampered_hash() -> None:
    params = _params()
    real_hash = sign(params, _SECRET)
    params["vnp_SecureHash"] = real_hash[:-1] + ("0" if real_hash[-1] != "0" else "1")
    assert verify(params, _SECRET) is False


def test_verify_is_case_insensitive_on_the_hex_digest() -> None:
    """VNPAY's own SDKs are inconsistent about hex case; the comparison must not be."""
    params = _params()
    params["vnp_SecureHash"] = sign(params, _SECRET).upper()
    assert verify(params, _SECRET) is True


def test_secure_hash_and_type_fields_are_excluded_from_the_signed_payload() -> None:
    """Including them would make signing depend on the previous hash — circular."""
    params = _params()
    without_extra = sign(params, _SECRET)
    params["vnp_SecureHash"] = "irrelevant-placeholder"
    params["vnp_SecureHashType"] = "SHA512"
    assert sign(params, _SECRET) == without_extra
