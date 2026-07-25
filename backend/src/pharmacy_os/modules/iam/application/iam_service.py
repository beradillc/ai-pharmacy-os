"""User/role administration use-cases, plus tenant bootstrap.

Every read and write is confined to the acting tenant: a row belonging to another
tenant is reported as *not found*, never as *forbidden*, so the endpoint cannot be
used to probe whether an id exists elsewhere in the deployment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ConflictError, NotFoundError
from pharmacy_os.core.errors import ValidationError as AppValidationError
from pharmacy_os.core.security import hash_password, require_permission
from pharmacy_os.modules.iam.application.auth_service import AuthService
from pharmacy_os.modules.iam.application.dto import (
    AssignRoleInput,
    BootstrapTenantInput,
    BootstrapTenantOutput,
    CreateUserInput,
    RoleAssignmentOutput,
    RoleOutput,
    SystemRoleSyncOutput,
    UserOutput,
)
from pharmacy_os.modules.iam.application.repositories import (
    IamRepositories,
    ReposFactory,
    UowFactory,
)
from pharmacy_os.modules.iam.domain import (
    SYSTEM_ADMIN,
    SYSTEM_ROLES,
    Branch,
    IamError,
    Role,
    RoleAssignment,
    RolesChanged,
    Tenant,
    User,
    UserDeactivated,
    UserRegistered,
    validate_password_strength,
)


class IamService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repos_factory: ReposFactory,
        audit: AuditLogger,
        auth: AuthService | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._repos_factory = repos_factory
        self._audit = audit
        self._auth = auth
        """``None`` only in contexts that never call :meth:`reset_two_factor` (e.g. a
        unit test standing up ``IamService`` alone) — composition root always injects
        it (``interface/register.py``). ``AuthService`` owns 2FA storage; this class
        owns the ``iam.user.write`` check and tenant validation in front of it, same
        split as the rest of this file's admin actions."""

    # -- users ---------------------------------------------------------------

    async def create_user(self, data: CreateUserInput, ctx: RequestContext) -> UserOutput:
        require_permission(ctx, "iam.user.create")
        try:
            validate_password_strength(data.password)
            user = User(
                tenant_id=ctx.tenant_id,
                email=data.email,
                password_hash=hash_password(data.password),
                full_name=data.full_name,
                # Created by an admin who therefore knows the password: force a
                # change so only the account holder ends up knowing it.
                must_change_password=True,
            )
        except IamError as exc:
            raise AppValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            if await repos.users.find_by_email(user.email) is not None:
                raise ConflictError("Email đã được sử dụng")
            await repos.users.add(user)
            uow.collect(UserRegistered(tenant_id=ctx.tenant_id, user_id=user.id, email=user.email))
            await uow.commit()

        await self._record(ctx, AuditAction.USER_CREATED, "user", str(user.id))
        return UserOutput.of(user)

    async def list_users(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> list[UserOutput]:
        require_permission(ctx, "iam.user.read")
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            users = await repos.users.list(ctx.tenant_id, limit=limit, offset=offset)
        return [UserOutput.of(u) for u in users]

    async def get_user(self, user_id: UUID, ctx: RequestContext) -> UserOutput:
        require_permission(ctx, "iam.user.read")
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._user_or_404(repos, user_id, ctx)
        return UserOutput.of(user)

    async def set_user_active(
        self, user_id: UUID, *, active: bool, ctx: RequestContext
    ) -> UserOutput:
        """Enable or disable an account; disabling also kills its live sessions.

        Rows are never deleted — dispensing records must keep resolving to an actor
        long after that pharmacist leaves.
        """
        require_permission(ctx, "iam.user.write")
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._user_or_404(repos, user_id, ctx)
            if active:
                user.activate()
            else:
                user.deactivate()
            await repos.users.update(user)
            if not active:
                await repos.sessions.revoke_all_for_user(user.id, now)
                uow.collect(UserDeactivated(tenant_id=ctx.tenant_id, user_id=user.id))
            await uow.commit()

        await self._record(
            ctx,
            AuditAction.USER_ACTIVATED if active else AuditAction.USER_DEACTIVATED,
            "user",
            str(user.id),
        )
        return UserOutput.of(user)

    async def reset_password(self, user_id: UUID, new_password: str, ctx: RequestContext) -> None:
        """Admin reset: sets a temporary password and revokes the user's sessions."""
        require_permission(ctx, "iam.user.write")
        now = datetime.now(UTC)
        try:
            validate_password_strength(new_password)
        except IamError as exc:
            raise AppValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._user_or_404(repos, user_id, ctx)
            user.change_password(hash_password(new_password))
            user.must_change_password = True
            await repos.users.update(user)
            await repos.sessions.revoke_all_for_user(user.id, now)
            await uow.commit()
        await self._record(ctx, AuditAction.PASSWORD_RESET, "user", str(user_id))

    async def reset_two_factor(self, user_id: UUID, ctx: RequestContext) -> None:
        """Admin recovery: clear a user's 2FA entirely (lost phone, lost backup codes).

        Guarded the same way as :meth:`reset_password` — ``iam.user.write``, tenant
        checked via :meth:`_user_or_404` — but deliberately does **not** revoke
        sessions or force a password change: this lowers a defence, it does not touch
        the credential, so an already-logged-in shift is not interrupted by it.
        """
        require_permission(ctx, "iam.user.write")
        assert self._auth is not None, "IamService built without AuthService"
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            user = await self._user_or_404(repos, user_id, ctx)
        await self._auth.reset_two_factor_for_user(user, ctx)

    # -- roles ---------------------------------------------------------------

    async def list_roles(self, ctx: RequestContext) -> list[RoleOutput]:
        require_permission(ctx, "iam.role.read")
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            roles = await repos.roles.list_available(ctx.tenant_id)
        return [RoleOutput.of(r) for r in roles]

    async def list_assignments(
        self, user_id: UUID, ctx: RequestContext
    ) -> list[RoleAssignmentOutput]:
        require_permission(ctx, "iam.user.read")
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            await self._user_or_404(repos, user_id, ctx)
            assignments = await repos.assignments.list_for_user(user_id)
            roles = {r.id: r for r in await repos.roles.list_available(ctx.tenant_id)}
        return [
            RoleAssignmentOutput.of(a, roles[a.role_id].code if a.role_id in roles else "?")
            for a in assignments
        ]

    async def assign_role(
        self, user_id: UUID, data: AssignRoleInput, ctx: RequestContext
    ) -> RoleAssignmentOutput:
        """Grant a role, chain-wide (``branch_id`` omitted) or for one branch."""
        require_permission(ctx, "iam.role.assign")
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            await self._user_or_404(repos, user_id, ctx)
            role = await self._role_or_404(repos, data.role_id, ctx)
            if data.branch_id is not None:
                await self._branch_or_404(repos, data.branch_id, ctx)

            existing = await repos.assignments.list_for_user(user_id)
            if any(a.role_id == role.id and a.branch_id == data.branch_id for a in existing):
                raise ConflictError("Vai trò này đã được gán ở phạm vi tương ứng")

            assignment = RoleAssignment(
                user_id=user_id,
                tenant_id=ctx.tenant_id,
                role_id=role.id,
                branch_id=data.branch_id,
                granted_by=ctx.user_id,
            )
            await repos.assignments.add(assignment)
            uow.collect(
                RolesChanged(
                    tenant_id=ctx.tenant_id,
                    user_id=user_id,
                    role_id=role.id,
                    branch_id=data.branch_id,
                    granted=True,
                )
            )
            await uow.commit()

        await self._record(ctx, AuditAction.ROLE_GRANTED, "user_role", str(assignment.id))
        return RoleAssignmentOutput.of(assignment, role.code)

    async def revoke_role(self, user_id: UUID, assignment_id: UUID, ctx: RequestContext) -> None:
        """Remove a grant.

        Live access tokens keep the old permissions until they expire (≤60 minutes,
        docs/15 D2); the next refresh recomputes them. Revoke the user's sessions via
        :meth:`set_user_active` when a change must bite immediately.
        """
        require_permission(ctx, "iam.role.assign")
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            assignment = await repos.assignments.get(assignment_id)
            if (
                assignment is None
                or assignment.user_id != user_id
                or assignment.tenant_id != ctx.tenant_id
            ):
                raise NotFoundError("Không tìm thấy phân quyền")
            await repos.assignments.delete(assignment_id)
            uow.collect(
                RolesChanged(
                    tenant_id=ctx.tenant_id,
                    user_id=user_id,
                    role_id=assignment.role_id,
                    branch_id=assignment.branch_id,
                    granted=False,
                )
            )
            await uow.commit()
        await self._record(ctx, AuditAction.ROLE_REVOKED, "user_role", str(assignment_id))

    # -- bootstrap -----------------------------------------------------------

    async def bootstrap_tenant(self, data: BootstrapTenantInput) -> BootstrapTenantOutput:
        """Stand up a tenant, its first branch, the system roles and an admin user.

        Deliberately context-free and permission-free: it runs before any user exists
        and is only reachable by someone who already holds the database credentials
        (``python -m seeds.bootstrap_tenant``). Exposing it over HTTP would create a
        public "make me an admin" path — rejected in docs/15 §5 Q2.
        """
        try:
            validate_password_strength(data.admin_password)
            tenant = Tenant(name=data.tenant_name)
            branch = Branch(tenant_id=tenant.id, code=data.branch_code, name=data.branch_name)
            admin = User(
                tenant_id=tenant.id,
                email=data.admin_email,
                password_hash=hash_password(data.admin_password),
                full_name=data.admin_full_name,
                must_change_password=True,
            )
        except IamError as exc:
            raise AppValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            if await repos.users.find_by_email(admin.email) is not None:
                raise ConflictError(f"Email {admin.email} đã tồn tại")

            await repos.tenants.add(tenant)
            await repos.branches.add(branch)
            roles = await self._sync_system_roles(repos)
            await repos.users.add(admin)

            admin_role = await repos.roles.find_by_code(SYSTEM_ADMIN)
            if admin_role is None:  # pragma: no cover - _ensure_system_roles just ran
                raise NotFoundError(f"Thiếu vai trò hệ thống {SYSTEM_ADMIN}")
            # Chain-wide: the first admin must be able to reach branches created later.
            await repos.assignments.add(
                RoleAssignment(user_id=admin.id, tenant_id=tenant.id, role_id=admin_role.id)
            )
            uow.collect(UserRegistered(tenant_id=tenant.id, user_id=admin.id, email=admin.email))
            await uow.commit()

        return BootstrapTenantOutput(
            tenant_id=tenant.id,
            branch_id=branch.id,
            admin_user_id=admin.id,
            roles_created=roles.created,
            roles_updated=roles.updated,
        )

    async def sync_system_roles(self) -> SystemRoleSyncOutput:
        """Bring the deployment's system roles in line with the code catalogue.

        Inserts what is missing **and updates what has drifted**. The update half is
        not optional: system roles are code-owned (``tenant_id IS NULL``), so a
        permission added to :data:`SYSTEM_ROLES` in a release reaches an
        already-provisioned deployment only if something rewrites the existing rows.
        Insert-only seeding silently left every upgraded install one permission short
        — found by running the real CLI against a database seeded by an earlier
        version, not by the test suite (which always starts empty).

        Idempotent, and safe to run on every deploy. Tenant-owned roles
        (``tenant_id IS NOT NULL``) are never touched.
        """
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            result = await self._sync_system_roles(repos)
            await uow.commit()
        return result

    async def _sync_system_roles(self, repos: IamRepositories) -> SystemRoleSyncOutput:
        created = updated = 0
        for spec in SYSTEM_ROLES:
            existing = await repos.roles.find_by_code(spec.code)
            if existing is None:
                await repos.roles.add(
                    Role(
                        code=spec.code,
                        name=spec.name,
                        description=spec.description,
                        permissions=spec.permissions,
                    )
                )
                created += 1
                continue
            if (
                existing.permissions == spec.permissions
                and existing.name == spec.name
                and existing.description == spec.description
            ):
                continue
            await repos.roles.update(
                Role(
                    id=existing.id,
                    code=existing.code,
                    name=spec.name,
                    description=spec.description,
                    permissions=spec.permissions,
                )
            )
            updated += 1
        return SystemRoleSyncOutput(created=created, updated=updated)

    # -- helpers -------------------------------------------------------------

    async def _user_or_404(
        self, repos: IamRepositories, user_id: UUID, ctx: RequestContext
    ) -> User:
        user = await repos.users.get(user_id)
        if user is None or user.tenant_id != ctx.tenant_id:
            raise NotFoundError("Không tìm thấy người dùng")
        return user

    async def _role_or_404(
        self, repos: IamRepositories, role_id: UUID, ctx: RequestContext
    ) -> Role:
        role = await repos.roles.get(role_id)
        if role is None or (role.tenant_id is not None and role.tenant_id != ctx.tenant_id):
            raise NotFoundError("Không tìm thấy vai trò")
        return role

    async def _branch_or_404(
        self, repos: IamRepositories, branch_id: UUID, ctx: RequestContext
    ) -> Branch:
        branch = await repos.branches.get(branch_id)
        if branch is None or branch.tenant_id != ctx.tenant_id:
            raise NotFoundError("Không tìm thấy chi nhánh")
        return branch

    async def _record(
        self, ctx: RequestContext, action: AuditAction, target_type: str, target_id: str
    ) -> None:
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )
