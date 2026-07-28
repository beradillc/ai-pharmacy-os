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
    TwoFactorActivationOutput,
    TwoFactorEnrollmentOutput,
    TwoFactorLoginInput,
    TwoFactorStatusOutput,
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
    must_enroll_two_factor: bool = False
    """Enforcement is on and this account holds a sensitive permission but has no
    active second factor. A prompt, not a barrier — the session is fully usable; only
    signing the ledger is refused until enrolment."""

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
            must_enroll_two_factor=out.must_enroll_two_factor,
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


class StepUpFields(BaseModel):
    """Xác thực lại ngay trước một thao tác nhạy cảm (audit B-05).

    Vì sao là **thân yêu cầu** chứ không phải header: mật khẩu không được nằm trong
    header — header hay bị ghi lại nguyên văn ở proxy và log truy cập, đúng chỗ mà
    `APP__DEBUG` (audit B-03) vừa bị siết vì lý do y hệt.
    """

    current_password: str = Field(min_length=1)
    totp_code: str | None = Field(
        default=None,
        min_length=6,
        max_length=32,
        description="Mã xác thực hai lớp hoặc mã dự phòng; bắt buộc nếu tài khoản đã bật 2FA",
    )
    """Bắt buộc khi tài khoản người GỌI đang bật 2FA. Không phải mã của người bị thao
    tác — step-up chứng minh *ai đang bấm*, không chứng minh gì về nạn nhân.

    Cùng ràng buộc độ dài với ``SignLedgerBookRequest.totp_code``: cả hai nhận TOTP lẫn
    mã dự phòng, và người đọc mã trên giấy không phải chọn đúng ô."""


class ResetPasswordRequest(StepUpFields):
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class ResetTwoFactorRequest(StepUpFields):
    """Không có trường nào ngoài step-up — thân yêu cầu tồn tại chỉ để mang nó."""


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


# --- two-factor authentication ------------------------------------------------

_TOTP_OR_BACKUP = Field(
    min_length=6,
    max_length=32,
    description="Mã 6 chữ số từ ứng dụng xác thực, hoặc một mã dự phòng",
)
"""One field for both kinds of code on purpose: the service tries TOTP first and falls
back to a backup code, so the client does not have to know (or tell us) which it holds
— a user reading a code off a piece of paper should not need to pick the right box."""


class TwoFactorEnrollResponse(BaseModel):
    """The one and only time the secret leaves the server.

    Both fields carry the same secret: ``secret`` for manual entry when a camera is
    unavailable, ``provisioning_uri`` for the client to render as a QR code. Nothing
    is active until a working code is posted to ``/auth/2fa/activate``.
    """

    secret: str
    provisioning_uri: str

    @classmethod
    def of(cls, out: TwoFactorEnrollmentOutput) -> TwoFactorEnrollResponse:
        return cls(secret=out.secret, provisioning_uri=out.provisioning_uri)


class TwoFactorCodeRequest(BaseModel):
    code: str = _TOTP_OR_BACKUP


class TwoFactorActivateResponse(BaseModel):
    """Backup codes, shown exactly once — only their hashes are stored, so this
    response cannot be reproduced. Losing them means an administrator reset (or the
    server-side break-glass command), not a re-read."""

    backup_codes: list[str]

    @classmethod
    def of(cls, out: TwoFactorActivationOutput) -> TwoFactorActivateResponse:
        return cls(backup_codes=out.backup_codes)


class TwoFactorDisableRequest(BaseModel):
    """Both factors are required to switch the second one off.

    Password alone would mean a stolen password is enough to remove the very control
    that protects against a stolen password.
    """

    current_password: str
    code: str = _TOTP_OR_BACKUP


class TwoFactorStatusResponse(BaseModel):
    enrolled: bool
    active: bool
    must_enroll: bool
    unused_backup_codes: int

    @classmethod
    def of(cls, out: TwoFactorStatusOutput) -> TwoFactorStatusResponse:
        return cls(
            enrolled=out.enrolled,
            active=out.active,
            must_enroll=out.must_enroll,
            unused_backup_codes=out.unused_backup_codes,
        )


class TwoFactorLoginRequest(BaseModel):
    """Step 2 of a two-factor login: the challenge handed out by ``/auth/login``
    (as the ``challenge_token`` member of its 401 body) plus a code."""

    challenge_token: str
    code: str = _TOTP_OR_BACKUP

    def to_input(self) -> TwoFactorLoginInput:
        return TwoFactorLoginInput(challenge_token=self.challenge_token, code=self.code)
