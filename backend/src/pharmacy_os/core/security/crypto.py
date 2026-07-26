"""At-rest field encryption and blind indexes (Sprint 8, mục 3/4).

**What this protects against, and what it does not.** Field encryption defends the
threat this project actually has: a database dump walking out. ``pg_dump`` files are
made routinely (the full-auto safety net requires one before every migration) and a
copied dump is plaintext no matter how the disk is encrypted. Disk/volume encryption
covers a *different* threat — a stolen physical disk — and is an operations concern,
not this module's. Neither stops somebody who owns the application host: the key lives
there. The honest claim is "a leaked dump or database credential is no longer enough",
not "the data is safe".

**Versioned keys rather than per-record envelope.** Every ciphertext is tagged with the
key version that produced it (``v1:…``), and the registry can hold several versions at
once. Rotation is therefore: add a new version, point ``current`` at it, and old rows
keep decrypting untouched — no downtime, no big-bang re-encryption, and a sweep can
re-encrypt lazily afterwards. A per-record envelope (a DEK per row, wrapped by a KEK)
buys the ability to re-key without touching ciphertexts, which matters at a scale this
system does not have, and costs a DEK column plus an unwrap on every read. Versioned
keys give the same operational property — rotate without rewriting everything — for a
fraction of the moving parts.

**AES-256-GCM** because it authenticates as well as encrypts: a tampered ciphertext
fails loudly instead of decrypting to garbage that some caller then trusts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import unicodedata
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32
"""AES-256. Anything shorter is rejected at construction rather than silently accepted."""

_NONCE_BYTES = 12
"""96 bits, the size AES-GCM is specified for. Fresh per encryption, never reused: a
repeated (key, nonce) pair in GCM leaks the XOR of the plaintexts *and* the
authentication key, which is a total break rather than a weakening."""

_VERSION_RE = re.compile(r"^v(\d+):(.+)$", re.DOTALL)


class DecryptionError(Exception):
    """A ciphertext could not be decrypted — wrong key, unknown version, or tampering.

    Deliberately not silently degraded to ``None``: a caller that cannot read a
    patient's data must fail visibly, because the alternative is quietly showing an
    empty allergy list to a pharmacist who is about to dispense.
    """


def generate_key() -> bytes:
    """A fresh 256-bit key. Operators run this once per version and store the result
    outside the repository — see ``docs/10_CONFIG.md``."""
    return secrets.token_bytes(KEY_BYTES)


def encode_key(key: bytes) -> str:
    """Key as base64 for putting in an environment variable."""
    return base64.b64encode(key).decode("ascii")


def decode_key(encoded: str) -> bytes:
    """Parse a base64 key, refusing anything that is not exactly 256 bits.

    Refusing early matters: a truncated or mistyped key would otherwise surface as a
    decryption failure long after the data was written with it.
    """
    try:
        key = base64.b64decode(encoded, validate=True)
    except Exception as exc:  # noqa: BLE001 — operator input, not a bug
        raise ValueError("Khoá mã hoá không phải base64 hợp lệ") from exc
    if len(key) != KEY_BYTES:
        raise ValueError(f"Khoá mã hoá phải đúng {KEY_BYTES} byte (256 bit), đang có {len(key)}")
    return key


@dataclass(frozen=True, slots=True)
class KeyRing:
    """The encryption keys this deployment knows about, and which one writes.

    Holding several versions is what makes rotation non-disruptive: reads consult the
    version tag on each ciphertext, writes always use ``current_version``.
    """

    keys: dict[int, bytes]
    current_version: int

    def __post_init__(self) -> None:
        if not self.keys:
            raise ValueError("KeyRing rỗng — không có khoá nào để mã hoá/giải mã")
        if self.current_version not in self.keys:
            raise ValueError(
                f"current_version={self.current_version} không có trong danh sách khoá "
                f"{sorted(self.keys)}"
            )
        for version, key in self.keys.items():
            if len(key) != KEY_BYTES:
                raise ValueError(f"Khoá v{version} phải đúng {KEY_BYTES} byte")


class FieldCipher:
    """Encrypts and decrypts individual field values.

    Values are handled as text in and text out; the stored form is
    ``v{version}:{base64(nonce || ciphertext || tag)}``, which is safe for a
    ``varchar``/``Text`` column and carries everything a later read needs except the
    key itself.
    """

    def __init__(self, key_ring: KeyRing) -> None:
        self._ring = key_ring

    def encrypt(self, plaintext: str) -> str:
        """Encrypt with the current key version, tagging the result with it."""
        nonce = secrets.token_bytes(_NONCE_BYTES)
        aes = AESGCM(self._ring.keys[self._ring.current_version])
        blob = nonce + aes.encrypt(nonce, plaintext.encode("utf-8"), None)
        return f"v{self._ring.current_version}:{base64.b64encode(blob).decode('ascii')}"

    def decrypt(self, stored: str) -> str:
        """Decrypt a value produced by :meth:`encrypt`, whichever version wrote it."""
        match = _VERSION_RE.match(stored)
        if match is None:
            raise DecryptionError(
                "Giá trị không đúng định dạng 'v<version>:<base64>' — "
                "có thể là dữ liệu chưa mã hoá còn sót"
            )
        version = int(match.group(1))
        key = self._ring.keys.get(version)
        if key is None:
            raise DecryptionError(
                f"Không có khoá v{version} — deployment này thiếu khoá cũ, "
                f"đang có {sorted(self._ring.keys)}"
            )
        try:
            blob = base64.b64decode(match.group(2), validate=True)
            nonce, payload = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
            return AESGCM(key).decrypt(nonce, payload, None).decode("utf-8")
        except InvalidTag as exc:
            # GCM's whole point: this is tampering or the wrong key, never "close enough".
            raise DecryptionError(
                f"Giải mã thất bại với khoá v{version} — dữ liệu bị sửa?"
            ) from exc
        except Exception as exc:  # noqa: BLE001 — malformed stored value
            raise DecryptionError(f"Giá trị mã hoá hỏng: {exc!r}") from exc

    def is_encrypted(self, stored: str) -> bool:
        """Whether *stored* already carries a version tag.

        Needed during a backfill, when a column legitimately holds both shapes at once.
        """
        return _VERSION_RE.match(stored) is not None

    def needs_rotation(self, stored: str) -> bool:
        """Whether *stored* was written by an older key than the current one."""
        match = _VERSION_RE.match(stored)
        return match is not None and int(match.group(1)) != self._ring.current_version


class BlindIndex:
    """A deterministic, searchable fingerprint of a value that is stored encrypted.

    Exists because encryption destroys equality: ``customers.phone`` is looked up
    directly (``find_by_phone``), and a randomised ciphertext differs on every write,
    so ``WHERE phone = ?`` would never match. The fingerprint is indexable and lets that
    query keep working against encrypted data.

    **Uses its own key, never the encryption key.** Reusing one key for two purposes is
    the classic way a weakness in one becomes a break in the other.

    **What it gives up, stated plainly:** equal values produce equal fingerprints, so
    somebody holding the database can tell *that* two customers share a phone number —
    just not what it is. For a low-cardinality field a determined attacker with the
    index key could also confirm a guess. That is a real and accepted trade for keeping
    exact-match lookup; it is why this is applied only to fields that must be searched,
    not to everything.
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != KEY_BYTES:
            raise ValueError(f"Khoá blind index phải đúng {KEY_BYTES} byte")
        self._key = key

    def fingerprint(self, value: str) -> str:
        """A stable hex fingerprint of *value*, normalised first.

        Normalisation is what makes the lookup behave the way a human expects: a phone
        typed ``0912 345 678`` must find the customer stored as ``0912345678``.
        """
        return hmac.new(
            self._key, normalize_for_index(value).encode("utf-8"), hashlib.sha256
        ).hexdigest()


def normalize_for_index(value: str) -> str:
    """Fold away the differences that should not create a different fingerprint.

    Unicode NFKC, case-folded, and stripped of spaces/punctuation — so formatting a
    phone number differently, or capitalising a name differently, still matches.
    """
    folded = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in folded if ch.isalnum())
