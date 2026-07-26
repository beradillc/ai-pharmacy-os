"""SQLAlchemy column types that encrypt on write and decrypt on read.

**Why a column type rather than threading a cipher through the repositories.**
Encryption belongs at the storage boundary: it is not a business rule, and the domain
entities must keep holding plaintext or every rule that reads them would have to know
about ciphertext. Repositories and mappers in this project are pure translation
functions built per request by factories that never see ``Settings``; passing a cipher
into each of them would touch dozens of call sites for one cross-cutting concern. A
``TypeDecorator`` puts the concern exactly where the value crosses into the database
and nowhere else.

**The cost, stated honestly:** the cipher has to be reachable from inside the type,
which means process-wide state (:func:`configure_field_encryption`). That is the usual
shape for this pattern, but it is global state, so it is set once at startup and reset
explicitly in tests.

**Reads always accept both shapes.** A value without a version tag is returned as-is
rather than raising. That is what makes a live backfill possible: while it runs, a
column legitimately holds plaintext and ciphertext at the same time, and reads must not
care which row they landed on. Writes encrypt only when encryption is switched on, so
turning the flag off stops new ciphertext without stranding what is already stored.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from pharmacy_os.core.security.crypto import FieldCipher

_cipher: FieldCipher | None = None
_write_enabled = False


def configure_field_encryption(cipher: FieldCipher | None, *, write_enabled: bool) -> None:
    """Install the process-wide cipher used by the column types below.

    Called once from the composition root. ``cipher`` may be supplied with
    ``write_enabled=False`` — the useful state during a backfill's early phase, where
    the application can already *read* ciphertext but is not yet producing it.
    """
    global _cipher, _write_enabled  # noqa: PLW0603 — deliberate process-wide state
    _cipher = cipher
    _write_enabled = write_enabled and cipher is not None


def reset_field_encryption() -> None:
    """Drop the configured cipher — for tests, so one case cannot leak into the next."""
    configure_field_encryption(None, write_enabled=False)


def active_cipher() -> FieldCipher | None:
    """The configured cipher, if any. Exposed for the backfill command."""
    return _cipher


def encryption_writes_enabled() -> bool:
    return _write_enabled


def _encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    if not _write_enabled or _cipher is None:
        return value
    return _cipher.encrypt(value)


def _decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    if _cipher is None:
        # No key configured: hand back whatever is stored. Ciphertext will look like
        # gibberish to the caller, which is the correct outcome — better a visibly
        # wrong value than a crash that takes the whole deployment down when somebody
        # forgets a key, and the fail-fast in Settings already refuses that combination
        # for any deployment that writes ciphertext.
        return value
    return _cipher.decrypt(value) if _cipher.is_encrypted(value) else value


class EncryptedString(TypeDecorator[str]):
    """A ``varchar`` whose contents are encrypted at rest.

    Size the column for **ciphertext**, not plaintext: the stored form is
    ``v{n}:base64(nonce||ct||tag)``, roughly ``4/3 × (28 + len(utf8))`` plus the tag —
    a 32-character secret becomes ~83 characters. Under-sizing shows up as a Postgres
    ``StringDataRightTruncation`` (a 500) that SQLite will not reproduce, exactly the
    class of bug PROJECT_STATE §7ap/§7aq were about.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return _encrypt(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> str | None:  # noqa: ANN401
        return _decrypt(value)


class EncryptedText(TypeDecorator[str]):
    """``Text`` counterpart of :class:`EncryptedString` — no length to get wrong."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return _encrypt(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> str | None:  # noqa: ANN401
        return _decrypt(value)
