"""IAM aggregates: :class:`Tenant`, :class:`Branch`, :class:`User`, :class:`Role`,
:class:`RoleAssignment` and :class:`RefreshSession`.

``Tenant``/``Branch`` live here because docs/08_MODULES.md §2.1 makes "tenant/branch
context" this module's responsibility. They are deliberately **minimal** — an id, a
name and an activation flag — and carry no chain-pharmacy business (kho chuỗi, luân
chuyển thuốc theo Luật 44/2024 Điều 47a is explicitly out of scope, docs/15 §1).

Unlike every other module's tables these entities are *not* branch-scoped: a user
belongs to a tenant and reaches branches through :class:`RoleAssignment`. That is why
none of the ORM models use ``TenantScopedMixin`` (which forces ``branch_id NOT NULL``)
— see docs/15 §0 F5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.iam.domain.exceptions import (
    InvalidRoleError,
    InvalidTenantError,
    InvalidUserError,
    UserInactiveError,
    UserLockedError,
)
from pharmacy_os.modules.iam.domain.policy import LOCKOUT_MINUTES, MAX_FAILED_LOGINS


class ActivationStatus(StrEnum):
    """Shared lifecycle flag for tenants, branches and users.

    Deactivation is always reversible and never deletes rows — dispensing records
    must keep pointing at a resolvable actor long after that pharmacist leaves.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(slots=True)
class Tenant:
    """One pharmacy business (single shop or chain) — the isolation boundary."""

    name: str
    status: ActivationStatus = ActivationStatus.ACTIVE
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidTenantError("Tên tenant không được để trống")

    @property
    def is_active(self) -> bool:
        return self.status is ActivationStatus.ACTIVE


@dataclass(slots=True)
class Branch:
    """One pharmacy outlet inside a tenant (nhà thuốc trong chuỗi)."""

    tenant_id: UUID
    code: str
    name: str
    status: ActivationStatus = ActivationStatus.ACTIVE
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.code = self.code.strip()
        if not self.code:
            raise InvalidTenantError("Mã chi nhánh không được để trống")
        if not self.name.strip():
            raise InvalidTenantError("Tên chi nhánh không được để trống")

    @property
    def is_active(self) -> bool:
        return self.status is ActivationStatus.ACTIVE


@dataclass(slots=True)
class Role:
    """A named bundle of permission codes.

    ``tenant_id is None`` marks a **system role** shared by every tenant and seeded
    from code (docs/15 §5 Q5); a concrete ``tenant_id`` marks a tenant's own role.
    v1 ships system roles only — the tenant-role path exists in the schema so adding
    it later needs no migration of existing rows.

    ``permissions`` holds raw permission codes exactly as ``require_permission``
    receives them (e.g. ``sales.create``); there is no wildcard expansion, because
    ``core.security.rbac.require_permission`` does an exact membership test and is
    used by all eight business modules — widening it is not this module's call.
    """

    code: str
    name: str
    permissions: frozenset[str] = frozenset()
    description: str | None = None
    tenant_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.code = self.code.strip()
        if not self.code:
            raise InvalidRoleError("Mã vai trò không được để trống")
        if not self.name.strip():
            raise InvalidRoleError("Tên vai trò không được để trống")
        self.permissions = frozenset(self.permissions)

    @property
    def is_system(self) -> bool:
        return self.tenant_id is None


@dataclass(slots=True)
class RoleAssignment:
    """Grant of one :class:`Role` to one :class:`User`, at chain or branch level.

    ``branch_id is None`` = chain-wide (Luật 44/2024 Điều 17a, cấp chuỗi). Rotating
    a pharmacist between outlets (Điều 47a.1.đ) is revoking one row and granting
    another — ``granted_by``/``granted_at`` keep who did it, the audit log keeps why.
    """

    user_id: UUID
    tenant_id: UUID
    role_id: UUID
    branch_id: UUID | None = None
    granted_by: UUID | None = None
    granted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)

    @property
    def is_chain_wide(self) -> bool:
        return self.branch_id is None


@dataclass(slots=True)
class User:
    """A person who can sign in, owned by exactly one tenant.

    Holds only the ``password_hash`` — hashing lives in ``core.security.password``
    and is applied by the application layer, keeping this entity framework-free.
    """

    tenant_id: UUID
    email: str
    password_hash: str
    full_name: str
    status: ActivationStatus = ActivationStatus.ACTIVE
    must_change_password: bool = False
    failed_login_count: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.email = self.email.strip().lower()
        if "@" not in self.email:
            raise InvalidUserError("Email không hợp lệ")
        if not self.full_name.strip():
            raise InvalidUserError("Họ tên không được để trống")

    @property
    def is_active(self) -> bool:
        return self.status is ActivationStatus.ACTIVE

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > now

    def ensure_can_authenticate(self, now: datetime) -> None:
        """Raise unless the account is allowed to attempt a login right now.

        Checked *before* the password comparison so a locked account stays locked
        even when the correct password is supplied.
        """
        if not self.is_active:
            raise UserInactiveError("Tài khoản đã bị vô hiệu hóa")
        if self.is_locked(now):
            raise UserLockedError("Tài khoản đang tạm khóa do đăng nhập sai nhiều lần")

    def register_failed_login(
        self,
        now: datetime,
        *,
        max_attempts: int = MAX_FAILED_LOGINS,
        lockout_minutes: int = LOCKOUT_MINUTES,
    ) -> bool:
        """Count a wrong password; lock the account on the *max_attempts*-th one.

        Returns whether this attempt triggered the lock, so the caller can audit
        the lock as its own event.
        """
        self.failed_login_count += 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = now + timedelta(minutes=lockout_minutes)
            self.failed_login_count = 0
            return True
        return False

    def register_successful_login(self, now: datetime) -> None:
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = now

    def change_password(self, password_hash: str) -> None:
        """Set a new hash and clear the forced-change flag.

        Revoking the user's live refresh sessions is the application layer's job
        (it owns the session repository) — see ``AuthService.change_password``.
        """
        self.password_hash = password_hash
        self.must_change_password = False

    def deactivate(self) -> None:
        self.status = ActivationStatus.INACTIVE

    def activate(self) -> None:
        self.status = ActivationStatus.ACTIVE
        self.failed_login_count = 0
        self.locked_until = None


@dataclass(slots=True)
class RefreshSession:
    """One issued refresh token, stored as a hash so a DB leak yields no usable token.

    Rotation: every successful refresh revokes the presented row and records the
    replacement in ``replaced_by``. Presenting an already-revoked row therefore means
    the token was replayed — probable theft — which the application layer answers by
    revoking the user's whole session family (docs/15 §4).
    """

    user_id: UUID
    tenant_id: UUID
    branch_id: UUID
    token_hash: str
    expires_at: datetime
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    revoked_at: datetime | None = None
    replaced_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def is_usable(self, now: datetime) -> bool:
        return not self.is_revoked and not self.is_expired(now)

    def revoke(self, now: datetime, *, replaced_by: UUID | None = None) -> None:
        if self.revoked_at is None:
            self.revoked_at = now
        self.replaced_by = replaced_by if replaced_by is not None else self.replaced_by
