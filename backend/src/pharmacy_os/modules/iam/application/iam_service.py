"""User/role administration use-cases, plus tenant bootstrap.

Every read and write is confined to the acting tenant: a row belonging to another
tenant is reported as *not found*, never as *forbidden*, so the endpoint cannot be
used to probe whether an id exists elsewhere in the deployment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pharmacy_os.core.audit import AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ConflictError, NotFoundError
from pharmacy_os.core.errors import ValidationError as AppValidationError
from pharmacy_os.core.security import hash_password, require_permission
from pharmacy_os.modules.iam.application.dto import (
    AssignRoleInput,
    BootstrapTenantInput,
    BootstrapTenantOutput,
    CreateUserInput,
    RoleAssignmentOutput,
    RoleOutput,
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
    ) -> None:
        self._uow_factory = uow_factory
        self._repos_factory = repos_factory
        self._audit = audit

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

        self._record(ctx, "user_created", "user", str(user.id))
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

        self._record(ctx, "user_activated" if active else "user_deactivated", "user", str(user.id))
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
        self._record(ctx, "password_reset", "user", str(user_id))

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

        self._record(ctx, "role_granted", "user_role", str(assignment.id))
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
        self._record(ctx, "role_revoked", "user_role", str(assignment_id))

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
            roles_created = await self._ensure_system_roles(repos)
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
            roles_created=roles_created,
        )

    async def _ensure_system_roles(self, repos: IamRepositories) -> int:
        """Insert any system role missing from the deployment; returns how many.

        Idempotent so the second tenant reuses the rows the first one created —
        system roles are shared (``tenant_id IS NULL``), not duplicated per tenant.
        """
        created = 0
        for spec in SYSTEM_ROLES:
            if await repos.roles.find_by_code(spec.code) is not None:
                continue
            await repos.roles.add(
                Role(
                    code=spec.code,
                    name=spec.name,
                    description=spec.description,
                    permissions=spec.permissions,
                )
            )
            created += 1
        return created

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

    def _record(self, ctx: RequestContext, action: str, entity_type: str, entity_id: str) -> None:
        self._audit.record(
            AuditEntry(
                actor_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )
