"""Pydantic request/response schemas for iam."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.iam.application.dto import (
    AssignRoleInput,
    BranchOutput,
    ChangePasswordInput,
    CreateUserInput,
    LoginInput,
    RoleAssignmentOutput,
    RoleOutput,
    SessionOutput,
    UserOutput,
)
from pharmacy_os.modules.iam.domain import MIN_PASSWORD_LENGTH

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
"""A deliberately loose shape check, not RFC 5322 validation: pydantic's ``EmailStr``
would pull in the ``email-validator`` dependency to reject addresses that a delivery
attempt would reject anyway, and iam never sends mail."""


class LoginRequest(BaseModel):
    # 320 = độ rộng cột ``users.email``: dài hơn thì không tài khoản nào khớp được,
    # chặn sớm cho đỡ một vòng truy vấn. Không chặn ``password`` (xem CreateUserRequest).
    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)
    password: str
    branch_id: UUID | None = None
    """Omit when the account reaches a single branch; required otherwise (the
    server answers 400 with the list of branches to choose from)."""

    def to_input(self) -> LoginInput:
        return LoginInput(email=self.email, password=self.password, branch_id=self.branch_id)


class RefreshRequest(BaseModel):
    refresh_token: str


class SwitchBranchRequest(BaseModel):
    """Switching branch *is* a rotation: permissions must be re-derived for the new
    branch, so the refresh token is what gets exchanged, not the access token.
    """

    refresh_token: str
    branch_id: UUID


class BranchResponse(BaseModel):
    id: UUID
    code: str
    name: str

    @classmethod
    def of(cls, out: BranchOutput) -> BranchResponse:
        return cls(id=out.id, code=out.code, name=out.name)


class SessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_id: UUID
    tenant_id: UUID
    branch_id: UUID
    permissions: list[str]
    must_change_password: bool
    accessible_branches: list[BranchResponse]

    @classmethod
    def of(cls, out: SessionOutput) -> SessionResponse:
        return cls(
            access_token=out.access_token,
            refresh_token=out.refresh_token,
            token_type=out.token_type,
            expires_in=out.expires_in,
            user_id=out.user_id,
            tenant_id=out.tenant_id,
            branch_id=out.branch_id,
            permissions=out.permissions,
            must_change_password=out.must_change_password,
            accessible_branches=[BranchResponse.of(b) for b in out.accessible_branches],
        )


class MeResponse(BaseModel):
    """Who the bearer token says you are, and what it lets you do."""

    user_id: UUID
    tenant_id: UUID
    branch_id: UUID
    permissions: list[str]


class CreateUserRequest(BaseModel):
    # max_length khớp đúng độ rộng cột — không chặn ở đây thì Postgres ném
    # StringDataRightTruncationError và client nhận 500 thay vì 422 (PROJECT_STATE §7aq).
    # ``password`` KHÔNG chặn trên: nó chỉ đi vào bcrypt (ra 60 ký tự cố định), không
    # xuống cột nào — chặn ở đây chỉ tổ khoá cửa người đặt mật khẩu rất dài.
    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)
    full_name: str = Field(min_length=1, max_length=255)

    def to_input(self) -> CreateUserInput:
        return CreateUserInput(email=self.email, password=self.password, full_name=self.full_name)


class SetUserActiveRequest(BaseModel):
    active: bool


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)

    def to_input(self) -> ChangePasswordInput:
        return ChangePasswordInput(
            current_password=self.current_password, new_password=self.new_password
        )


class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    status: str
    must_change_password: bool
    last_login_at: datetime | None
    locked_until: datetime | None

    @classmethod
    def of(cls, out: UserOutput) -> UserResponse:
        return cls(
            id=out.id,
            tenant_id=out.tenant_id,
            email=out.email,
            full_name=out.full_name,
            status=out.status,
            must_change_password=out.must_change_password,
            last_login_at=out.last_login_at,
            locked_until=out.locked_until,
        )


class RoleResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]

    @classmethod
    def of(cls, out: RoleOutput) -> RoleResponse:
        return cls(
            id=out.id,
            code=out.code,
            name=out.name,
            description=out.description,
            is_system=out.is_system,
            permissions=out.permissions,
        )


class AssignRoleRequest(BaseModel):
    role_id: UUID
    branch_id: UUID | None = None
    """``null`` grants the role across every branch of the tenant (cấp chuỗi,
    Luật 44/2024 Điều 17a); a concrete id scopes it to one pharmacy."""

    def to_input(self) -> AssignRoleInput:
        return AssignRoleInput(role_id=self.role_id, branch_id=self.branch_id)


class RoleAssignmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    role_code: str
    branch_id: UUID | None
    granted_by: UUID | None
    granted_at: datetime

    @classmethod
    def of(cls, out: RoleAssignmentOutput) -> RoleAssignmentResponse:
        return cls(
            id=out.id,
            user_id=out.user_id,
            role_id=out.role_id,
            role_code=out.role_code,
            branch_id=out.branch_id,
            granted_by=out.granted_by,
            granted_at=out.granted_at,
        )
