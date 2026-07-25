"""TOTP (RFC 6238) and backup-code primitives.

Sits beside :mod:`pharmacy_os.core.security.password` and for the same reason: the
``iam`` domain entities stay framework- and crypto-library-free, so the actual code
generation lives here and the **application** layer applies it (exactly the split
``User`` already documents for ``password_hash``).

Built on ``pyotp`` rather than hand-rolled HMAC. TOTP is short enough to write from
the RFC, but "short enough to write" is not "short enough to get right" — an
off-by-one in the time step or a non-constant-time compare is invisible in tests and
fatal in production. ``pyotp`` is the standard implementation, gives the
``otpauth://`` provisioning URI for free, and every authenticator app on the market
is tested against it.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime

import pyotp

TOTP_DIGITS = 6
TOTP_INTERVAL_SECONDS = 30

TOTP_VALID_WINDOW = 1
"""Accept the neighbouring time step on each side (±30s).

Phone clocks drift and people finish typing after the step rolls over. Zero window
produces "correct code rejected" support tickets; a wider one multiplies the guess
space a brute-forcer gets per attempt for no usability gain.
"""

BACKUP_CODE_COUNT = 10
_BACKUP_CODE_BYTES = 8
"""64 bits per backup code — unguessable, and short enough to read off paper."""

_BACKUP_GROUP = 4


def generate_totp_secret() -> str:
    """A fresh base32 secret (160 bits), the format every authenticator app expects."""
    return str(pyotp.random_base32())


def totp_provisioning_uri(secret: str, *, account_name: str, issuer: str) -> str:
    """The ``otpauth://`` URI a client turns into a QR code.

    The server deliberately does **not** render the QR image: that would pull an
    imaging dependency into the backend to produce something every frontend and
    mobile toolkit already draws from this string.
    """
    return str(
        pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL_SECONDS).provisioning_uri(
            name=account_name, issuer_name=issuer
        )
    )


def timestep_at(moment: datetime) -> int:
    """The RFC 6238 counter for *moment* — the unit replay protection is tracked in."""
    return int(moment.timestamp()) // TOTP_INTERVAL_SECONDS


def verify_totp(
    secret: str,
    code: str,
    *,
    at: datetime,
    valid_window: int = TOTP_VALID_WINDOW,
) -> int | None:
    """Return the **time step that matched**, or ``None`` when *code* is wrong.

    Returning the step rather than a bool is what makes replay protection possible:
    the caller stores it and refuses anything at or below it next time, so a code
    observed over someone's shoulder cannot be re-used inside its own 30-second life
    (see ``UserTwoFactor.register_use``).
    """
    candidate = code.strip().replace(" ", "")
    if len(candidate) != TOTP_DIGITS or not candidate.isdigit():
        return None

    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL_SECONDS)
    current = timestep_at(at)
    for offset in range(-valid_window, valid_window + 1):
        step = current + offset
        try:
            expected = str(totp.generate_otp(step))
        except Exception:  # noqa: BLE001 — malformed/corrupt base32 secret
            return None
        # Constant-time: a timing oracle on the first differing digit would cut the
        # search space from 10^6 to 6x10.
        if hmac.compare_digest(expected, candidate):
            return step
    return None


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> list[str]:
    """Fresh single-use recovery codes, formatted ``XXXX-XXXX-XXXX-XXXX``."""
    return [
        _format_backup_code(secrets.token_hex(_BACKUP_CODE_BYTES).upper()) for _ in range(count)
    ]


def _format_backup_code(raw: str) -> str:
    return "-".join(raw[i : i + _BACKUP_GROUP] for i in range(0, len(raw), _BACKUP_GROUP))


def normalize_backup_code(code: str) -> str:
    """Strip the cosmetic formatting so ``abcd-ef01`` and ``ABCDEF01`` are one code."""
    return code.strip().replace("-", "").replace(" ", "").upper()


def hash_backup_code(code: str) -> str:
    """SHA-256 of the normalised code.

    Plain SHA-256, not bcrypt — the same reasoning ``hash_refresh_token`` already
    records: the code is 64 random bits, so there is no low-entropy secret for a KDF
    to slow a guesser down on, and a deliberate work factor would only be a cost
    paid on every verification.
    """
    return hashlib.sha256(normalize_backup_code(code).encode("utf-8")).hexdigest()
