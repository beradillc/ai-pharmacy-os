"""IAM data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
