"""IAM domain events (docs/08_MODULES.md §2.1).

Published for traceability; no module subscribes to them today. They exist so a
future reaction (e.g. persisting to the ``audit_logs`` table, nợ Sprint 7) can be
wired at the composition root without touching this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pharmacy_os.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    """A new user account was created inside a tenant."""

    user_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class RolesChanged(DomainEvent):
    """A role was granted to or revoked from a user.

    ``branch_id is None`` on a grant means the role applies chain-wide.
    """

    user_id: UUID
    role_id: UUID
    branch_id: UUID | None
    granted: bool


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(DomainEvent):
    """A user was disabled; their live sessions are revoked with it."""

    user_id: UUID
