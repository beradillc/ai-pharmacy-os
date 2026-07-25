"""Two-factor authentication for high-trust accounts (ROADMAP Sprint 8).

The motivating risk is narrow and real: ``compliance.ledger.sign`` lets three roles
put a **legally binding** electronic signature on the controlled-substance ledger
(TT 18/2026/TT-BYT Điều 15.1.d, PROJECT_STATE §7aw). Signing already demands the
user's password again, but password-only re-auth means *one leaked password is
enough to forge that signature*. This module adds the second factor that closes it.

Entities only — the TOTP maths lives in ``core.security.totp`` and is applied by the
application layer, the same split :class:`~.entities.User` documents for
``password_hash``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.iam.domain.exceptions import (
    TwoFactorCodeReusedError,
    TwoFactorNotPendingError,
)

TWO_FACTOR_PERMISSIONS: frozenset[str] = frozenset(
    {
        # The urgent gap: forging a binding ledger signature (TT18 Điều 15.1.d).
        "compliance.ledger.sign",
        # Privilege escalation. Whoever can grant themselves a role, or rewrite what a
        # role contains, can hand themselves ``compliance.ledger.sign`` — so guarding
        # only the signing permission would be a paper wall.
        "iam.role.assign",
        "iam.role.write",
    }
)
"""Permissions whose holders are in scope for enforced 2FA.

Deliberately a **rule over permissions**, not a hand-written list of role codes. The
schema already allows tenant-owned roles (``roles.tenant_id IS NOT NULL``, docs/15 §5
Q5); the day those are switched on, a tenant role granted ``compliance.ledger.sign``
falls into scope automatically. A copied list would silently miss it — precisely the
failure mode of PROJECT_STATE §7l, where a new permission never reached an existing
deployment while all tests stayed green.

Today this resolves to exactly ``chain_pharmacist`` / ``branch_pharmacist`` /
``system_admin``. ``crm.erase`` was considered and left out: irreversible, but its
risk is *destruction* rather than *forged identity*, and it is already chain-only.
"""


def requires_two_factor(permissions: frozenset[str]) -> bool:
    """Whether an actor holding *permissions* is in scope for enforced 2FA."""
    return not permissions.isdisjoint(TWO_FACTOR_PERMISSIONS)


class TwoFactorStatus(StrEnum):
    """Lifecycle of one user's TOTP configuration.

    "Disabled" is the **absence of a row**, not a member: a user who never enrolled
    and a user who turned 2FA off are the same state, and keeping a dead row around
    would leave a stale secret in the database for no benefit.
    """

    PENDING = "PENDING"
    """Secret issued, not yet proven. Has **no effect on login** — see
    :meth:`UserTwoFactor.is_active`."""

    ACTIVE = "ACTIVE"
    """Confirmed with a real code; now required at login and for step-up."""


@dataclass(slots=True)
class UserTwoFactor:
    """One user's TOTP configuration.

    ``secret`` is stored as the raw base32 string.

    # TODO(sprint8-1b): mã hóa at-rest cột ``secret``.
    Left in cleartext on purpose, not by omission: this codebase has no key
    management at all (no KMS, no envelope keys, no rotation), so encrypting with a
    key drawn from ``SECURITY__JWT_SECRET`` — same file, same host, same read
    permissions as the database credentials — would buy a feeling of safety rather
    than safety. The generic "mã hóa at-rest" work is the sibling Sprint 8 #1b task
    and will cover this column. Damage if the database alone leaks: 2FA degrades to
    one factor, because both login and signing still require the password as well —
    a leak does not become account takeover.
    """

    user_id: UUID
    tenant_id: UUID
    secret: str
    status: TwoFactorStatus = TwoFactorStatus.PENDING
    confirmed_at: datetime | None = None
    last_used_timestep: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)

    @property
    def is_active(self) -> bool:
        return self.status is TwoFactorStatus.ACTIVE

    def activate(self, now: datetime, timestep: int) -> None:
        """Promote a proven secret to ``ACTIVE``.

        Requiring one correct code before activation is what stops a user whose QR
        scan silently failed from locking themselves out at the next login.
        """
        if self.status is not TwoFactorStatus.PENDING:
            raise TwoFactorNotPendingError("Xác thực hai lớp đã được kích hoạt trước đó")
        self.status = TwoFactorStatus.ACTIVE
        self.confirmed_at = now
        self.last_used_timestep = timestep

    def register_use(self, timestep: int) -> None:
        """Consume a verified code, refusing any step already spent.

        A TOTP code stays valid for its whole 30-second step (plus the drift window),
        so without this an observed code can simply be typed in again. Storing the
        highest step used makes each code strictly single-use.
        """
        if self.last_used_timestep is not None and timestep <= self.last_used_timestep:
            raise TwoFactorCodeReusedError("Mã xác thực này đã được dùng, chờ mã kế tiếp")
        self.last_used_timestep = timestep


@dataclass(slots=True)
class BackupCode:
    """One single-use recovery code, kept as a hash.

    Used rows are **marked, never deleted**: which code was spent and when is part of
    the account's security history, and an empty table cannot distinguish "never had
    any" from "burned all ten".
    """

    two_factor_id: UUID
    code_hash: str
    used_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def use(self, now: datetime) -> None:
        self.used_at = now


MAX_CHALLENGE_ATTEMPTS = 5
"""Guesses allowed against one login challenge before it is destroyed.

A TOTP code is six digits. Without a cap, an attacker holding the password simply
enumerates 10^6 and 2FA buys nothing. Five wrong answers costs a legitimate
fat-fingered user one extra password entry.

This is a limit **bound to the challenge state machine**, not the IP/endpoint rate
limiting that the sibling Sprint 8 #1b task will build on Redis — they do not
overlap.
"""

CHALLENGE_TTL_MINUTES = 5


@dataclass(slots=True)
class TwoFactorChallenge:
    """A half-finished login: password accepted, second factor still owed.

    Stored server-side as a hash of an opaque token — the same shape as
    :class:`~.entities.RefreshSession`, and for a sharper reason than symmetry. The
    obvious alternative, a short-lived JWT, is unsafe here: ``api.deps.get_context``
    accepts any token ``JwtService`` can decode, so a challenge JWT would authenticate
    as its user (with no permissions) — and ``POST /auth/change-password`` requires no
    permission at all, only the current password, which whoever reached this point has
    just supplied. That path would let a stolen password change the password *without*
    ever passing 2FA. An opaque row is not decodable by ``JwtService``, and adds
    single-use and attempt-counting that a stateless token cannot express.
    """

    user_id: UUID
    tenant_id: UUID
    token_hash: str
    expires_at: datetime
    branch_id: UUID | None = None
    """The branch the client asked for at step 1, carried through so the second step
    resolves permissions for the same branch (or re-raises the picker when unset)."""

    attempts: int = 0
    consumed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def is_usable(self, now: datetime) -> bool:
        return not self.is_consumed and not self.is_expired(now)

    def register_failure(self) -> bool:
        """Count a wrong code; return whether that exhausted the challenge."""
        self.attempts += 1
        return self.attempts >= MAX_CHALLENGE_ATTEMPTS

    def consume(self, now: datetime) -> None:
        self.consumed_at = now
