"""Authentication use-cases: login, refresh/rotate, branch switch, logout, password.

Two rules drive the whole flow (docs/15 §4, duyệt 2026-07-23):

* **The branch is chosen here, never by the caller afterwards.** Permissions are
  resolved for one branch and signed into the access token, so a client that edits
  ``X-Branch-Id`` changes nothing.
* **Refresh is the revocation checkpoint.** Permissions are recomputed from the
  database on every rotation, so a role change takes effect within one access-token
  lifetime (60 minutes) rather than never.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)
from pharmacy_os.core.errors import ValidationError as AppValidationError
from pharmacy_os.core.security import JwtService, TokenPayload, hash_password, verify_password
from pharmacy_os.core.security.totp import (
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_code,
    totp_provisioning_uri,
    verify_totp,
)
from pharmacy_os.modules.iam.application.dto import (
    BranchOutput,
    ChangePasswordInput,
    LoginInput,
    ProfileOutput,
    SessionOutput,
    StepUpResult,
    TwoFactorActivationOutput,
    TwoFactorEnrollmentOutput,
    TwoFactorLoginInput,
    TwoFactorStatusOutput,
)
from pharmacy_os.modules.iam.application.errors import (
    BranchSelectionRequiredError,
    TwoFactorRequiredError,
)
from pharmacy_os.modules.iam.application.repositories import (
    IamRepositories,
    ReposFactory,
    UowFactory,
)
from pharmacy_os.modules.iam.domain import (
    CHALLENGE_TTL_MINUTES,
    BackupCode,
    Branch,
    IamError,
    RefreshSession,
    Role,
    RoleAssignment,
    TwoFactorChallenge,
    TwoFactorCodeReusedError,
    User,
    UserTwoFactor,
    accessible_branch_ids,
    requires_two_factor,
    resolve_permissions,
    validate_password_strength,
)

_REFRESH_TOKEN_BYTES = 48
_CHALLENGE_TOKEN_BYTES = 32

_TOTP_CODE = "totp"
_BACKUP_CODE = "backup"
"""Which factor satisfied a check — a spent backup code is audited separately,
because it usually means the authenticator device is gone."""


def hash_refresh_token(token: str) -> str:
    """SHA-256 of the opaque refresh secret.

    Plain SHA-256, not bcrypt: the token is 48 random bytes, so there is no
    low-entropy secret to slow a guesser down, and lookups happen by hash on every
    refresh — a deliberate KDF would make that a per-request cost for no gain.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


#: Two-factor login challenges are opaque secrets of the same shape and are hashed
#: the same way, for the same reason.
hash_challenge_token = hash_refresh_token


@dataclass(frozen=True, slots=True)
class _Access:
    """One read of everything that decides where and what a user may act."""

    assignments: list[RoleAssignment]
    branches: list[Branch]
    allowed_branch_ids: list[UUID]

    def branch(self, branch_id: UUID) -> Branch:
        return next(b for b in self.branches if b.id == branch_id)

    @property
    def allowed_branches(self) -> list[Branch]:
        allowed = set(self.allowed_branch_ids)
        return [b for b in self.branches if b.id in allowed]


class AuthService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repos_factory: ReposFactory,
        jwt_service: JwtService,
        audit: AuditLogger,
        *,
        access_ttl_minutes: int,
        refresh_ttl_days: int,
        two_factor_enforced: bool = False,
        two_factor_issuer: str = "AI Pharmacy OS",
    ) -> None:
        self._uow_factory = uow_factory
        self._repos_factory = repos_factory
        self._jwt = jwt_service
        self._audit = audit
        self._access_ttl_minutes = access_ttl_minutes
        self._refresh_ttl_days = refresh_ttl_days
        self._two_factor_enforced = two_factor_enforced
        self._two_factor_issuer = two_factor_issuer

    # -- use-cases -----------------------------------------------------------

    async def login(self, data: LoginInput) -> SessionOutput:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await repos.users.find_by_email(data.email)
            if user is None:
                # Same error as a wrong password: the endpoint must not tell an
                # attacker which addresses are registered.
                raise UnauthenticatedError("Email hoặc mật khẩu không đúng")

            self._ensure_can_authenticate(user, now)

            if not verify_password(data.password, user.password_hash):
                locked = user.register_failed_login(now)
                await repos.users.update(user)
                await uow.commit()
                # Two separate facts: the attempt, and the lock it may have caused.
                # Emitting only the lock would lose the four attempts before it.
                await self._record(user, AuditAction.LOGIN_FAILED, data.client_ip)
                if locked:
                    await self._record(user, AuditAction.ACCOUNT_LOCKED, data.client_ip)
                raise UnauthenticatedError("Email hoặc mật khẩu không đúng")

            access = await self._load_access(repos, user)
            # Branch selection stays ahead of the 2FA gate so a user who works in
            # several outlets still gets the picker on the first call, exactly as
            # before. Nothing authenticating is handed out here — only the names of
            # the tenant's own branches, which was already the case.
            branch = self._choose_branch(access, data.branch_id)
            permissions = resolve_permissions(
                access.assignments, await self._roles_by_id(repos, user), branch.id
            )

            two_factor = await repos.two_factor.find_for_user(user.id)
            if two_factor is not None and two_factor.is_active:
                # The password was right, so clear the lockout counter — but withhold
                # ``last_login_at``: the login is not finished until the second factor
                # lands, and the timestamp is read as "this account was used".
                user.failed_login_count = 0
                user.locked_until = None
                await repos.users.update(user)
                challenge_token = await self._open_challenge(repos, user, branch.id, now)
                await uow.commit()
                raise TwoFactorRequiredError(
                    "Nhập mã xác thực hai lớp để hoàn tất đăng nhập",
                    extra={"challenge_token": challenge_token},
                )

            user.register_successful_login(now)
            await repos.users.update(user)
            output, _ = await self._issue(repos, user, branch, permissions, access, now)
            await uow.commit()

        await self._record(user, AuditAction.LOGIN_SUCCESS, data.client_ip, branch_id=branch.id)
        return output

    async def complete_two_factor_login(self, data: TwoFactorLoginInput) -> SessionOutput:
        """Step 2: exchange a challenge plus a valid code for a real session.

        Accepts either a TOTP code or one of the backup codes — a user whose phone is
        dead must still be able to work, and forcing them through an administrator for
        every shift would guarantee the feature gets switched off.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            challenge = await repos.challenges.find_by_hash(
                hash_challenge_token(data.challenge_token)
            )
            if challenge is None or not challenge.is_usable(now):
                raise UnauthenticatedError("Phiên xác thực hai lớp không hợp lệ hoặc đã hết hạn")

            user = await repos.users.get(challenge.user_id)
            if user is None:
                raise UnauthenticatedError("Phiên xác thực hai lớp không hợp lệ hoặc đã hết hạn")
            self._ensure_can_authenticate(user, now)

            config = await repos.two_factor.find_for_user(user.id)
            if config is None or not config.is_active:
                # 2FA was turned off (or admin-reset) between the two steps. Refuse
                # rather than waving the login through: this challenge was minted
                # under different rules.
                raise UnauthenticatedError("Phiên xác thực hai lớp không hợp lệ hoặc đã hết hạn")

            verified = await self._consume_second_factor(repos, config, data.code, now)
            if verified is None:
                exhausted = challenge.register_failure()
                if exhausted:
                    # Burn the challenge, not the account: the attacker must go back
                    # and present the password again, which is what makes guessing
                    # six digits impractical.
                    challenge.consume(now)
                await repos.challenges.update(challenge)
                await uow.commit()
                await self._record(
                    user,
                    AuditAction.TWO_FACTOR_FAILED,
                    data.client_ip,
                    branch_id=challenge.branch_id,
                )
                raise UnauthenticatedError("Mã xác thực không đúng")

            challenge.consume(now)
            await repos.challenges.update(challenge)
            await repos.challenges.delete_expired(now)

            access = await self._load_access(repos, user)
            branch = self._choose_branch(access, challenge.branch_id)
            permissions = resolve_permissions(
                access.assignments, await self._roles_by_id(repos, user), branch.id
            )
            user.register_successful_login(now)
            await repos.users.update(user)
            output, _ = await self._issue(repos, user, branch, permissions, access, now)
            await uow.commit()

        if verified == _BACKUP_CODE:
            await self._record(
                user, AuditAction.TWO_FACTOR_BACKUP_CODE_USED, data.client_ip, branch_id=branch.id
            )
        await self._record(user, AuditAction.LOGIN_SUCCESS, data.client_ip, branch_id=branch.id)
        return output

    async def refresh(self, refresh_token: str, *, branch_id: UUID | None = None) -> SessionOutput:
        """Rotate a refresh token, optionally re-scoping the session to *branch_id*.

        ``/auth/switch-branch`` is this same operation with a branch named — moving
        between branches must re-derive permissions from the database, which is
        exactly what a rotation already does.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            session = await repos.sessions.find_by_hash(hash_refresh_token(refresh_token))
            if session is None:
                raise UnauthenticatedError("Refresh token không hợp lệ hoặc đã hết hạn")

            if session.is_revoked:
                # The legitimate client already exchanged this token, so whoever
                # presented it again holds a copy: drop every session of that user,
                # not merely this one.
                await repos.sessions.revoke_all_for_user(session.user_id, now)
                await uow.commit()
                await self._audit.record(
                    AuditEntry(
                        actor_user_id=session.user_id,
                        tenant_id=session.tenant_id,
                        action=AuditAction.TOKEN_REPLAY_DETECTED,
                        target_type="refresh_token",
                        target_id=str(session.id),
                        context={"branch_id": str(session.branch_id)},
                    )
                )
                raise UnauthenticatedError("Phiên đăng nhập đã bị thu hồi, vui lòng đăng nhập lại")

            if session.is_expired(now):
                raise UnauthenticatedError("Refresh token không hợp lệ hoặc đã hết hạn")

            user = await repos.users.get(session.user_id)
            if user is None:
                raise UnauthenticatedError("Refresh token không hợp lệ hoặc đã hết hạn")
            self._ensure_can_authenticate(user, now)

            access = await self._load_access(repos, user)
            branch = self._choose_branch(access, branch_id or session.branch_id)
            permissions = resolve_permissions(
                access.assignments, await self._roles_by_id(repos, user), branch.id
            )

            output, issued = await self._issue(repos, user, branch, permissions, access, now)
            session.revoke(now, replaced_by=issued.id)
            await repos.sessions.update(session)
            await repos.sessions.delete_expired(now)
            await uow.commit()
        return output

    async def logout(self, refresh_token: str) -> None:
        """Revoke one session. Unknown tokens succeed silently — a logout endpoint
        must not double as a token-validity oracle.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            session = await repos.sessions.find_by_hash(hash_refresh_token(refresh_token))
            if session is None or session.is_revoked:
                return
            session.revoke(now)
            await repos.sessions.update(session)
            await uow.commit()

    async def change_password(self, ctx: RequestContext, data: ChangePasswordInput) -> None:
        """Change one's own password and drop every live session, including this one.

        No permission code guards it: the actor proves ownership with the current
        password. An admin resetting *someone else's* password is a separate
        use-case on ``IamService``.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await repos.users.get(ctx.user_id)
            if user is None or user.tenant_id != ctx.tenant_id:
                raise NotFoundError("Không tìm thấy người dùng")
            if not verify_password(data.current_password, user.password_hash):
                raise UnauthenticatedError("Mật khẩu hiện tại không đúng")
            try:
                validate_password_strength(data.new_password)
            except IamError as exc:
                raise AppValidationError(str(exc)) from exc

            user.change_password(hash_password(data.new_password))
            await repos.users.update(user)
            await repos.sessions.revoke_all_for_user(user.id, now)
            await uow.commit()
        await self._record(user, AuditAction.PASSWORD_CHANGED, None, branch_id=ctx.branch_id)

    async def verify_own_password(self, ctx: RequestContext, plain_password: str) -> bool:
        """Xác minh mật khẩu hiện tại của người đang đăng nhập — đọc-only, không mutate.

        Dùng cho re-auth trước hành vi nhạy cảm ở module khác (VD ``compliance`` ký sổ điện
        tử, docs/13 mục C.5) qua cross-module read-port (``SigningReauthProvider``, wiring tại
        ``api/v1/cross_module.py``) — không đổi mật khẩu, không revoke session, không tự audit
        (nơi gọi tự ghi audit hành vi thật, ghi thêm ở đây là trùng lặp). Cùng logic xác minh
        bước đầu của :meth:`change_password`, tách riêng vì mục đích khác hẳn.
        """
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await repos.users.get(ctx.user_id)
        if user is None or user.tenant_id != ctx.tenant_id:
            return False
        return verify_password(plain_password, user.password_hash)

    # -- two-factor use-cases ------------------------------------------------

    async def enroll_two_factor(self, ctx: RequestContext) -> TwoFactorEnrollmentOutput:
        """Issue a TOTP secret for one's own account, awaiting confirmation.

        Guarded by nothing but having a session: a user hardening their own login is
        never something to hold behind a permission. Available whether or not
        enforcement is on, so an account can opt in ahead of the rollout.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._own_user(repos, ctx)
            existing = await repos.two_factor.find_for_user(user.id)
            if existing is not None and existing.is_active:
                raise ConflictError(
                    "Xác thực hai lớp đã bật — hãy tắt trước khi đăng ký lại thiết bị mới"
                )
            if existing is not None:
                # A previous, unconfirmed attempt: replace it outright. Keeping the old
                # secret alive would leave two valid enrolments for one account.
                await repos.two_factor.delete_for_user(user.id)

            config = UserTwoFactor(
                user_id=user.id,
                tenant_id=user.tenant_id,
                secret=generate_totp_secret(),
                created_at=now,
            )
            await repos.two_factor.add(config)
            await uow.commit()

        await self._record(
            user, AuditAction.TWO_FACTOR_ENROLLED, ctx.client_ip, branch_id=ctx.branch_id
        )
        return TwoFactorEnrollmentOutput(
            secret=config.secret,
            provisioning_uri=totp_provisioning_uri(
                config.secret, account_name=user.email, issuer=self._two_factor_issuer
            ),
        )

    async def activate_two_factor(
        self, ctx: RequestContext, code: str
    ) -> TwoFactorActivationOutput:
        """Prove the secret was stored correctly, then switch it on.

        Demanding one working code first is what stops a failed QR scan from locking
        the user out at their next login.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._own_user(repos, ctx)
            config = await repos.two_factor.find_for_user(user.id)
            if config is None:
                raise NotFoundError("Chưa đăng ký xác thực hai lớp")
            if config.is_active:
                raise ConflictError("Xác thực hai lớp đã được kích hoạt trước đó")

            timestep = verify_totp(config.secret, code, at=now)
            if timestep is None:
                raise UnauthenticatedError("Mã xác thực không đúng")

            config.activate(now, timestep)
            await repos.two_factor.update(config)

            plain_codes = generate_backup_codes()
            await repos.backup_codes.replace_all(
                config.id,
                [
                    BackupCode(two_factor_id=config.id, code_hash=hash_backup_code(c))
                    for c in plain_codes
                ],
            )
            await uow.commit()

        await self._record(
            user, AuditAction.TWO_FACTOR_ACTIVATED, ctx.client_ip, branch_id=ctx.branch_id
        )
        return TwoFactorActivationOutput(backup_codes=plain_codes)

    async def disable_two_factor(self, ctx: RequestContext, password: str, code: str) -> None:
        """Turn one's own second factor off, proving **both** factors first.

        Requiring the current code as well as the password is the point: if a password
        alone could disable 2FA, an attacker holding the password would simply switch
        it off and walk in. A backup code is accepted in its place, for the user whose
        device died.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._own_user(repos, ctx)
            if not verify_password(password, user.password_hash):
                raise UnauthenticatedError("Mật khẩu hiện tại không đúng")
            config = await repos.two_factor.find_for_user(user.id)
            if config is None:
                raise NotFoundError("Chưa đăng ký xác thực hai lớp")
            # An unconfirmed (PENDING) enrolment has no code to prove, so it can be
            # dropped on the password alone — there is nothing protecting it yet.
            if (
                config.is_active
                and await self._consume_second_factor(repos, config, code, now) is None
            ):
                raise UnauthenticatedError("Mã xác thực không đúng")

            await repos.two_factor.delete_for_user(user.id)
            await uow.commit()

        await self._record(
            user, AuditAction.TWO_FACTOR_DISABLED, ctx.client_ip, branch_id=ctx.branch_id
        )

    async def profile(self, ctx: RequestContext) -> ProfileOutput:
        """Hồ sơ của chính người gọi (M-03).

        ``/auth/me`` trước nay chỉ trả **định danh và quyền** — đủ cho máy, không đủ cho
        người: màn *Tài khoản của tôi* cần tên và email, mà hai thứ đó chỉ lấy được qua
        ``GET /users`` (đòi ``iam.user.read``, thu ngân không có). Đọc tên của **chính
        mình** không phải là quản lý nhân sự, nên không gác thêm quyền nào.
        """
        async with self._uow_factory() as uow:
            user = await self._own_user(self._repos_factory(uow), ctx)
        return ProfileOutput(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            last_login_at=user.last_login_at,
            must_change_password=user.must_change_password,
        )

    async def two_factor_status(self, ctx: RequestContext) -> TwoFactorStatusOutput:
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._own_user(repos, ctx)
            config = await repos.two_factor.find_for_user(user.id)
            unused = 0
            if config is not None:
                unused = sum(
                    1 for c in await repos.backup_codes.list_for(config.id) if not c.is_used
                )
        active = config is not None and config.is_active
        return TwoFactorStatusOutput(
            enrolled=config is not None,
            active=active,
            must_enroll=self._must_enroll(ctx.permissions, active),
            unused_backup_codes=unused,
        )

    async def verify_step_up(
        self, ctx: RequestContext, password: str, totp_code: str | None
    ) -> StepUpResult:
        """Re-authenticate immediately before a sensitive act (read-only, no mutation).

        This is the guard in front of signing the controlled-substance ledger — the one
        binding, irreversible act in the system (TT18 Điều 15.1.d, PROJECT_STATE §7aw).
        Password-only re-auth was never enough there: an unattended terminal at the
        counter is exactly the situation the password prompt was meant to cover, and a
        password can be watched over a shoulder.

        Consumes the TOTP time step on success, so the same code cannot sign twice.
        """
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await repos.users.get(ctx.user_id)
            if user is None or user.tenant_id != ctx.tenant_id:
                return StepUpResult.BAD_PASSWORD
            if not verify_password(password, user.password_hash):
                return StepUpResult.BAD_PASSWORD

            config = await repos.two_factor.find_for_user(user.id)
            if config is None or not config.is_active:
                # No second factor configured. Refuse only when enforcement is on *and*
                # this actor is in scope — otherwise the behaviour is what it was
                # before 2FA existed, which is what keeps the rollout non-breaking.
                if self._must_enroll(ctx.permissions, active=False):
                    return StepUpResult.ENROLLMENT_REQUIRED
                return StepUpResult.OK

            if not totp_code:
                return StepUpResult.CODE_REQUIRED
            used = await self._consume_second_factor(repos, config, totp_code, now)
            if used is None:
                await uow.commit()
                await self._record(
                    user, AuditAction.TWO_FACTOR_FAILED, ctx.client_ip, branch_id=ctx.branch_id
                )
                return StepUpResult.BAD_CODE
            await uow.commit()

        if used == _BACKUP_CODE:
            await self._record(
                user,
                AuditAction.TWO_FACTOR_BACKUP_CODE_USED,
                ctx.client_ip,
                branch_id=ctx.branch_id,
            )
        return StepUpResult.OK

    async def reset_two_factor_for_user(self, user: User, ctx: RequestContext) -> None:
        """Administrator-side recovery: clear another account's 2FA entirely.

        Called by ``IamService`` (which owns the ``iam.user.write`` check and the
        tenant validation) — the storage lives here, so the deletion does too.
        """
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            await repos.two_factor.delete_for_user(user.id)
            await uow.commit()
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.TWO_FACTOR_RESET,
                target_type="user",
                target_id=str(user.id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )

    # -- helpers -------------------------------------------------------------

    async def _own_user(self, repos: IamRepositories, ctx: RequestContext) -> User:
        user = await repos.users.get(ctx.user_id)
        if user is None or user.tenant_id != ctx.tenant_id:
            raise NotFoundError("Không tìm thấy người dùng")
        return user

    def _must_enroll(self, permissions: frozenset[str], active: bool) -> bool:
        return self._two_factor_enforced and not active and requires_two_factor(permissions)

    async def _open_challenge(
        self, repos: IamRepositories, user: User, branch_id: UUID, now: datetime
    ) -> str:
        token = secrets.token_urlsafe(_CHALLENGE_TOKEN_BYTES)
        await repos.challenges.add(
            TwoFactorChallenge(
                user_id=user.id,
                tenant_id=user.tenant_id,
                branch_id=branch_id,
                token_hash=hash_challenge_token(token),
                created_at=now,
                expires_at=now + timedelta(minutes=CHALLENGE_TTL_MINUTES),
            )
        )
        return token

    async def _consume_second_factor(
        self, repos: IamRepositories, config: UserTwoFactor, code: str, now: datetime
    ) -> str | None:
        """Spend a TOTP code or a backup code; ``None`` means neither matched.

        TOTP first because it is the common path; backup codes are the exception and
        checking them first would burn one on every typo in a normal code.
        """
        timestep = verify_totp(config.secret, code, at=now)
        if timestep is not None:
            try:
                config.register_use(timestep)
            except TwoFactorCodeReusedError:
                # Correct digits, already-spent step: treat as a failure, because
                # accepting it is exactly the replay this watermark exists to stop.
                return None
            await repos.two_factor.update(config)
            return _TOTP_CODE

        wanted = hash_backup_code(code)
        for stored in await repos.backup_codes.list_for(config.id):
            if stored.is_used or not hmac.compare_digest(stored.code_hash, wanted):
                continue
            stored.use(now)
            await repos.backup_codes.update(stored)
            return _BACKUP_CODE
        return None

    def _ensure_can_authenticate(self, user: User, now: datetime) -> None:
        try:
            user.ensure_can_authenticate(now)
        except IamError as exc:
            # 401, not 403: the credentials cannot be used at all right now. The
            # message names the reason (locked / disabled) because a user who cannot
            # get in needs to know whether to wait or to call an admin.
            raise UnauthenticatedError(str(exc)) from exc

    async def _load_access(self, repos: IamRepositories, user: User) -> _Access:
        assignments = await repos.assignments.list_for_user(user.id)
        branches = await repos.branches.list_active(user.tenant_id)
        return _Access(
            assignments=assignments,
            branches=branches,
            allowed_branch_ids=accessible_branch_ids(assignments, [b.id for b in branches]),
        )

    def _choose_branch(self, access: _Access, requested: UUID | None) -> Branch:
        if not access.allowed_branch_ids:
            raise PermissionDeniedError("Tài khoản chưa được gán vai trò ở chi nhánh nào")
        if requested is not None:
            if requested not in access.allowed_branch_ids:
                raise PermissionDeniedError("Không có quyền làm việc tại chi nhánh này")
            return access.branch(requested)
        if len(access.allowed_branch_ids) == 1:
            return access.branch(access.allowed_branch_ids[0])
        raise BranchSelectionRequiredError(
            "Tài khoản làm việc ở nhiều chi nhánh, vui lòng chọn chi nhánh",
            extra={
                "branches": [
                    {"id": str(b.id), "code": b.code, "name": b.name}
                    for b in access.allowed_branches
                ]
            },
        )

    async def _roles_by_id(self, repos: IamRepositories, user: User) -> dict[UUID, Role]:
        roles = await repos.roles.list_available(user.tenant_id)
        return {role.id: role for role in roles}

    async def _issue(
        self,
        repos: IamRepositories,
        user: User,
        branch: Branch,
        permissions: frozenset[str],
        access: _Access,
        now: datetime,
    ) -> tuple[SessionOutput, RefreshSession]:
        config = await repos.two_factor.find_for_user(user.id)
        must_enroll = self._must_enroll(permissions, active=config is not None and config.is_active)
        access_token = self._jwt.issue(
            TokenPayload(
                user_id=user.id,
                tenant_id=user.tenant_id,
                permissions=permissions,
                branch_id=branch.id,
            )
        )
        refresh_token = secrets.token_urlsafe(_REFRESH_TOKEN_BYTES)
        session = RefreshSession(
            user_id=user.id,
            tenant_id=user.tenant_id,
            branch_id=branch.id,
            token_hash=hash_refresh_token(refresh_token),
            issued_at=now,
            expires_at=now + timedelta(days=self._refresh_ttl_days),
        )
        await repos.sessions.add(session)

        output = SessionOutput(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._access_ttl_minutes * 60,
            user_id=user.id,
            tenant_id=user.tenant_id,
            branch_id=branch.id,
            permissions=sorted(permissions),
            must_change_password=user.must_change_password,
            accessible_branches=[BranchOutput.of(b) for b in access.allowed_branches],
            must_enroll_two_factor=must_enroll,
        )
        return output, session

    async def _record(
        self,
        user: User,
        action: AuditAction,
        client_ip: str | None,
        *,
        branch_id: UUID | None = None,
    ) -> None:
        await self._audit.record(
            AuditEntry(
                actor_user_id=user.id,
                tenant_id=user.tenant_id,
                action=action,
                target_type="user",
                target_id=str(user.id),
            ).with_context(
                client_ip=client_ip,
                branch_id=str(branch_id) if branch_id is not None else None,
            )
        )
