"""IAM data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pharmacy_os.modules.iam.domain import Branch, Role, RoleAssignment, User


@dataclass(slots=True)
class LoginInput:
    email: str
    password: str
    branch_id: UUID | None = None
    """Omitted when the actor reaches exactly one branch; required otherwise."""

    client_ip: str | None = None
    """Filled by the API layer, never by the client — recorded on the audit entry so
    a burst of failed logins can be traced to an origin. Optional so service-level
    callers (tests, CLI) need not fake one."""


@dataclass(slots=True)
class BranchOutput:
    id: UUID
    code: str
    name: str

    @classmethod
    def of(cls, branch: Branch) -> BranchOutput:
        return cls(id=branch.id, code=branch.code, name=branch.name)


@dataclass(slots=True)
class SessionOutput:
    """A freshly issued token pair plus everything the client needs to render itself.

    ``refresh_token`` is the only time the opaque secret is ever visible — the server
    keeps just its hash.
    """

    access_token: str
    refresh_token: str
    expires_in: int
    user_id: UUID
    tenant_id: UUID
    branch_id: UUID
    permissions: list[str]
    must_change_password: bool
    accessible_branches: list[BranchOutput]
    token_type: str = "bearer"
    must_enroll_two_factor: bool = False
    """Enforcement is on, this account holds a sensitive permission, and it has no
    active second factor yet.

    A prompt, not a barrier — deliberately the same shape as ``must_change_password``.
    The session is fully usable; only signing the ledger is refused until enrolment,
    so turning enforcement on mid-shift never strands staff mid-transaction."""


@dataclass(slots=True)
class CreateUserInput:
    email: str
    password: str
    full_name: str


@dataclass(slots=True)
class UserOutput:
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    status: str
    must_change_password: bool
    last_login_at: datetime | None
    locked_until: datetime | None

    @classmethod
    def of(cls, user: User) -> UserOutput:
        return cls(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            full_name=user.full_name,
            status=user.status.value,
            must_change_password=user.must_change_password,
            last_login_at=user.last_login_at,
            locked_until=user.locked_until,
        )


@dataclass(slots=True)
class RoleOutput:
    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]

    @classmethod
    def of(cls, role: Role) -> RoleOutput:
        return cls(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=sorted(role.permissions),
        )


@dataclass(slots=True)
class AssignRoleInput:
    role_id: UUID
    branch_id: UUID | None = None
    """``None`` grants the role across every branch of the tenant (cấp chuỗi)."""


@dataclass(slots=True)
class RoleAssignmentOutput:
    id: UUID
    user_id: UUID
    role_id: UUID
    role_code: str
    branch_id: UUID | None
    granted_by: UUID | None
    granted_at: datetime

    @classmethod
    def of(cls, assignment: RoleAssignment, role_code: str) -> RoleAssignmentOutput:
        return cls(
            id=assignment.id,
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            role_code=role_code,
            branch_id=assignment.branch_id,
            granted_by=assignment.granted_by,
            granted_at=assignment.granted_at,
        )


@dataclass(slots=True)
class ChangePasswordInput:
    current_password: str
    new_password: str


class StepUpResult(StrEnum):
    """Outcome of a re-authentication in front of a sensitive act.

    Five outcomes rather than a bool because the caller must be able to answer the
    user differently: a wrong password and a missing code need different prompts, and
    "you must enrol first" is not a failure of the credentials supplied at all.
    """

    OK = "OK"
    BAD_PASSWORD = "BAD_PASSWORD"
    CODE_REQUIRED = "CODE_REQUIRED"
    """2FA is active on this account and no code was supplied."""

    BAD_CODE = "BAD_CODE"
    ENROLLMENT_REQUIRED = "ENROLLMENT_REQUIRED"
    """Enforcement is on and this actor is in scope, but has no active second factor."""


@dataclass(slots=True)
class TwoFactorEnrollmentOutput:
    """The one and only time the TOTP secret is handed back to the client.

    Both fields carry the same secret: ``secret`` for manual entry when a camera is
    unavailable, ``provisioning_uri`` for the QR code. Nothing is active yet — the
    user must return one working code to
    :meth:`~.auth_service.AuthService.activate_two_factor`.
    """

    secret: str
    provisioning_uri: str


@dataclass(slots=True)
class TwoFactorActivationOutput:
    """Backup codes, shown exactly once.

    Only their hashes are stored, so this response cannot be reproduced — if the user
    loses them, the way back is an administrator reset, not a re-read.
    """

    backup_codes: list[str]


@dataclass(slots=True)
class TwoFactorStatusOutput:
    enrolled: bool
    active: bool
    must_enroll: bool
    """The account holds a sensitive permission, enforcement is on, and it has not
    enrolled — the client should prompt."""

    unused_backup_codes: int


@dataclass(slots=True)
class ProfileOutput:
    """Hồ sơ của chính người đang đăng nhập — nguồn của màn *Tài khoản của tôi* (M-03).

    Chỉ dữ liệu **của bản thân**: không cần ``iam.user.read``, vì đọc tên của chính mình
    không phải là quản lý nhân sự. Không trả ``password_hash``, không trả trạng thái khoá
    của người khác, không trả gì vượt ra ngoài tài khoản gọi.
    """

    user_id: UUID
    email: str
    full_name: str
    last_login_at: datetime | None
    must_change_password: bool


@dataclass(slots=True)
class TwoFactorLoginInput:
    """Step 2 of a two-factor login.

    ``code`` accepts either a six-digit TOTP code or one of the backup codes; the
    service tries them in that order.
    """

    challenge_token: str
    code: str
    client_ip: str | None = None


@dataclass(slots=True)
class BootstrapTenantInput:
    """Everything ``seeds.bootstrap_tenant`` needs to stand a new tenant up."""

    tenant_name: str
    branch_code: str
    branch_name: str
    admin_email: str
    admin_full_name: str
    admin_password: str


@dataclass(slots=True)
class SystemRoleSyncOutput:
    """How many system roles the sync inserted and how many it brought up to date."""

    created: int
    updated: int


@dataclass(slots=True)
class BootstrapTenantOutput:
    tenant_id: UUID
    branch_id: UUID
    admin_user_id: UUID
    roles_created: int
    roles_updated: int
