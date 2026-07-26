"""At-rest encryption primitives (Sprint 8, mục 3/4).

The properties pinned here are the ones whose failure would be silent: a nonce reused,
a tampered ciphertext accepted, a rotation that strands old rows, or a blind index that
matches the wrong record. Each of those looks fine in a smoke test and is fatal in
production.
"""

from __future__ import annotations

import base64

import pytest

from pharmacy_os.core.security.crypto import (
    KEY_BYTES,
    BlindIndex,
    DecryptionError,
    FieldCipher,
    KeyRing,
    decode_key,
    encode_key,
    generate_key,
    normalize_for_index,
)

_K1 = b"\x01" * KEY_BYTES
_K2 = b"\x02" * KEY_BYTES


def _cipher(current: int = 1, keys: dict[int, bytes] | None = None) -> FieldCipher:
    return FieldCipher(KeyRing(keys=keys or {1: _K1}, current_version=current))


# --- keys ---------------------------------------------------------------------


def test_generated_keys_are_256_bit_and_distinct() -> None:
    a, b = generate_key(), generate_key()
    assert len(a) == len(b) == KEY_BYTES
    assert a != b


def test_a_key_round_trips_through_base64() -> None:
    key = generate_key()
    assert decode_key(encode_key(key)) == key


@pytest.mark.parametrize("bad", ["", "not-base64!!", base64.b64encode(b"short").decode()])
def test_a_malformed_or_wrong_length_key_is_refused(bad: str) -> None:
    """Caught at load time, not at the first failed decryption months later."""
    with pytest.raises(ValueError):
        decode_key(bad)


def test_a_keyring_without_its_current_version_is_refused() -> None:
    with pytest.raises(ValueError, match="current_version"):
        KeyRing(keys={1: _K1}, current_version=2)


def test_an_empty_keyring_is_refused() -> None:
    with pytest.raises(ValueError):
        KeyRing(keys={}, current_version=1)


# --- encrypt / decrypt --------------------------------------------------------


def test_a_value_round_trips() -> None:
    cipher = _cipher()
    assert cipher.decrypt(cipher.encrypt("0912345678")) == "0912345678"


@pytest.mark.parametrize(
    "plaintext",
    ["", "Nguyễn Thị Hoà", "dị ứng penicillin — nổi mề đay", "a" * 5000, "line1\nline2"],
)
def test_round_trip_survives_unicode_empty_long_and_newlines(plaintext: str) -> None:
    """Vietnamese diacritics and free-text notes are the actual payload here."""
    cipher = _cipher()
    assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext


def test_the_same_value_encrypts_differently_every_time() -> None:
    """A fresh nonce per write. Without this, equal ciphertexts would reveal which
    customers share a phone number straight from a dump."""
    cipher = _cipher()
    assert cipher.encrypt("0912345678") != cipher.encrypt("0912345678")


def test_the_ciphertext_does_not_contain_the_plaintext() -> None:
    cipher = _cipher()
    assert "0912345678" not in cipher.encrypt("0912345678")


def test_a_tampered_ciphertext_is_rejected_not_decrypted() -> None:
    """GCM authenticates: flipping a byte must fail loudly, never return garbage a
    caller might trust."""
    cipher = _cipher()
    stored = cipher.encrypt("0912345678")
    version, blob = stored.split(":", 1)
    raw = bytearray(base64.b64decode(blob))
    raw[-1] ^= 0x01
    tampered = f"{version}:{base64.b64encode(bytes(raw)).decode()}"

    with pytest.raises(DecryptionError):
        cipher.decrypt(tampered)


def test_the_wrong_key_cannot_decrypt() -> None:
    stored = _cipher().encrypt("bí mật")
    other = FieldCipher(KeyRing(keys={1: _K2}, current_version=1))
    with pytest.raises(DecryptionError):
        other.decrypt(stored)


def test_plaintext_left_over_from_before_the_backfill_is_reported_clearly() -> None:
    """During a backfill a column holds both shapes; the untagged one must be
    recognisable rather than crashing obscurely."""
    cipher = _cipher()
    assert cipher.is_encrypted("0912345678") is False
    assert cipher.is_encrypted(cipher.encrypt("0912345678")) is True
    with pytest.raises(DecryptionError, match="chưa mã hoá"):
        cipher.decrypt("0912345678")


# --- rotation -----------------------------------------------------------------


def test_a_new_key_version_still_reads_old_ciphertexts() -> None:
    """The property that makes rotation possible without a big-bang re-encryption."""
    old = _cipher(current=1, keys={1: _K1})
    stored_v1 = old.encrypt("0912345678")

    rotated = _cipher(current=2, keys={1: _K1, 2: _K2})
    assert rotated.decrypt(stored_v1) == "0912345678"
    assert rotated.encrypt("x").startswith("v2:")


def test_rotation_is_detectable_so_a_sweep_can_find_old_rows() -> None:
    old = _cipher(current=1, keys={1: _K1})
    stored_v1 = old.encrypt("0912345678")
    rotated = _cipher(current=2, keys={1: _K1, 2: _K2})

    assert rotated.needs_rotation(stored_v1) is True
    assert rotated.needs_rotation(rotated.encrypt("x")) is False


def test_a_missing_old_key_fails_loudly_naming_the_version() -> None:
    """Dropping a key version while rows still reference it is data loss; the error
    has to say which version is missing so it is recoverable by restoring that key."""
    stored_v1 = _cipher(current=1, keys={1: _K1}).encrypt("0912345678")
    only_v2 = FieldCipher(KeyRing(keys={2: _K2}, current_version=2))

    with pytest.raises(DecryptionError, match="v1"):
        only_v2.decrypt(stored_v1)


# --- blind index --------------------------------------------------------------


def test_the_same_value_gives_the_same_fingerprint() -> None:
    """Equality lookup survives encryption — the entire reason this exists."""
    index = BlindIndex(_K1)
    assert index.fingerprint("0912345678") == index.fingerprint("0912345678")


def test_different_values_give_different_fingerprints() -> None:
    index = BlindIndex(_K1)
    assert index.fingerprint("0912345678") != index.fingerprint("0912345679")


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("0912 345 678", "0912345678"),
        ("0912-345-678", "0912345678"),
        (" 0912345678 ", "0912345678"),
        ("Nguyễn Thị Hoà", "nguyễn thị hoà"),
    ],
)
def test_formatting_differences_still_match(typed: str, stored: str) -> None:
    """A staff member typing a phone with spaces must find the same customer."""
    index = BlindIndex(_K1)
    assert index.fingerprint(typed) == index.fingerprint(stored)


def test_a_different_index_key_gives_a_different_fingerprint() -> None:
    """Fingerprints are not portable between deployments, and a leaked database
    without the index key cannot be matched against a guessed value."""
    assert BlindIndex(_K1).fingerprint("0912345678") != BlindIndex(_K2).fingerprint("0912345678")


def test_the_fingerprint_does_not_contain_the_value() -> None:
    assert "0912345678" not in BlindIndex(_K1).fingerprint("0912345678")


def test_a_short_index_key_is_refused() -> None:
    with pytest.raises(ValueError):
        BlindIndex(b"too-short")


def test_normalisation_folds_case_and_punctuation() -> None:
    assert normalize_for_index("  Nguyễn-Thị Hoà  ") == normalize_for_index("nguyễnthịhoà")
