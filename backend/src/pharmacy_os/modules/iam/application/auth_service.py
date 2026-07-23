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
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, PermissionDeniedError, UnauthenticatedError
from pharmacy_os.core.errors import ValidationError as AppValidationError
from pharmacy_os.core.security import JwtService, TokenPayload, hash_password, verify_password
from pharmacy_os.modules.iam.application.dto import (
    BranchOutput,
    ChangePasswordInput,
    LoginInput,
    SessionOutput,
)
from pharmacy_os.modules.iam.application.errors import BranchSelectionRequiredError
from pharmacy_os.modules.iam.application.repositories import (
    IamRepositories,
    ReposFactory,
    UowFactory,
)
from pharmacy_os.modules.iam.domain import (
    Branch,
    IamError,
    RefreshSession,
    Role,
    RoleAssignment,
    User,
    accessible_branch_ids,
    resolve_permissions,
    validate_password_strength,
)

_REFRESH_TOKEN_BYTES = 48


def hash_refresh_token(token: str) -> str:
    """SHA-256 of the opaque refresh secret.

    Plain SHA-256, not bcrypt: the token is 48 random bytes, so there is no
    low-entropy secret to slow a guesser down, and lookups happen by hash on every
    refresh — a deliberate KDF would make that a per-request cost for no gain.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    ) -> None:
        self._uow_factory = uow_factory
        self._repos_factory = repos_factory
        self._jwt = jwt_service
        self._audit = audit
        self._access_ttl_minutes = access_ttl_minutes
        self._refresh_ttl_days = refresh_ttl_days

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
            branch = self._choose_branch(access, data.branch_id)
            permissions = resolve_permissions(
                access.assignments, await self._roles_by_id(repos, user), branch.id
            )

            user.register_successful_login(now)
            await repos.users.update(user)
            output, _ = await self._issue(repos, user, branch, permissions, access, now)
            await uow.commit()

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

    # -- helpers -------------------------------------------------------------

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
