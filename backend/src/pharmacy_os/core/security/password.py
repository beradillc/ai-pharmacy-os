"""Password hashing (bcrypt).

Uses the ``bcrypt`` library directly. bcrypt operates on at most 72 bytes, so
inputs are truncated to that boundary (standard practice) before hashing.
"""

from __future__ import annotations

import bcrypt

_MAX_BCRYPT_BYTES = 72


def _prepare(plain: str) -> bytes:
    return plain.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_prepare(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("ascii"))
    except ValueError:
        return False
