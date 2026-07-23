"""Pure access-resolution and credential policy rules.

The two-level role model (docs/15_IAM_DESIGN.md §5 Q4) lives here, framework-free
and DB-free, so it can be unit-tested without a session:

* a :class:`RoleAssignment` with ``branch_id is None`` applies **chain-wide** —
  every branch of the tenant (Luật 44/2024 Điều 17a, người chịu trách nhiệm
  chuyên môn cấp chuỗi);
* a :class:`RoleAssignment` with a concrete ``branch_id`` applies to that single
  pharmacy only (Điều 17a, cấp nhà thuốc).

A request's permission set is the **union** of every role matching the branch the
actor is operating in. The branch itself is never taken from a client header — it
is chosen at login against :func:`accessible_branch_ids` and then travels inside
the signed token (docs/15 §0 F1).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING
from uuid import UUID

from pharmacy_os.modules.iam.domain.exceptions import WeakPasswordError

if TYPE_CHECKING:  # entities imports the constants below — annotations-only avoids the cycle
    from pharmacy_os.modules.iam.domain.entities import Role, RoleAssignment

MIN_PASSWORD_LENGTH = 10
"""Length-only policy (NIST SP 800-63B style): no composition rules, which push
users towards predictable substitutions. Duyệt 2026-07-23 (docs/15 §6 D11)."""

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


def validate_password_strength(plain: str) -> None:
    """Raise :class:`WeakPasswordError` unless *plain* satisfies the policy."""
    if len(plain) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự")


def assignments_for_branch(
    assignments: Iterable[RoleAssignment], branch_id: UUID
) -> list[RoleAssignment]:
    """Assignments in effect while operating in *branch_id* (chain-wide included)."""
    return [a for a in assignments if a.branch_id is None or a.branch_id == branch_id]


def resolve_permissions(
    assignments: Iterable[RoleAssignment],
    roles: Mapping[UUID, Role],
    branch_id: UUID,
) -> frozenset[str]:
    """Union of the permissions granted by every role applying in *branch_id*.

    Assignments naming a role absent from *roles* are ignored rather than raising:
    a role deleted underneath an assignment must not lock the user out of the
    permissions their other roles still grant.
    """
    granted: set[str] = set()
    for assignment in assignments_for_branch(assignments, branch_id):
        role = roles.get(assignment.role_id)
        if role is not None:
            granted |= role.permissions
    return frozenset(granted)


def accessible_branch_ids(
    assignments: Iterable[RoleAssignment], tenant_branch_ids: Iterable[UUID]
) -> list[UUID]:
    """Branches the actor may operate in, in the order *tenant_branch_ids* gives.

    One chain-wide assignment opens every active branch of the tenant; otherwise
    only the explicitly assigned ones. Order is preserved (rather than returning a
    set) so ``/auth/login`` can present a stable list to the client.
    """
    materialised = list(assignments)
    if any(a.branch_id is None for a in materialised):
        return list(tenant_branch_ids)
    scoped = {a.branch_id for a in materialised if a.branch_id is not None}
    return [b for b in tenant_branch_ids if b in scoped]


def is_branch_accessible(
    assignments: Iterable[RoleAssignment], tenant_branch_ids: Iterable[UUID], branch_id: UUID
) -> bool:
    """Whether *branch_id* is both a branch of this tenant and open to the actor."""
    return branch_id in accessible_branch_ids(assignments, tenant_branch_ids)
