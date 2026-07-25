"""IAM service-level flows against a real database session.

Covers the three things the design (docs/15) treats as load-bearing: the branch is
decided server-side, refresh is the revocation checkpoint, and a replayed refresh
token takes the whole session family down with it.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)
from pharmacy_os.core.errors import ValidationError as AppValidationError
from pharmacy_os.core.security import JwtService
from pharmacy_os.modules.iam.application import (
    AssignRoleInput,
    AuthService,
    BootstrapTenantInput,
    BranchSelectionRequiredError,
    ChangePasswordInput,
    CreateUserInput,
    IamService,
    LoginInput,
    SessionOutput,
    SystemRoleSyncOutput,
)
from pharmacy_os.modules.iam.domain import (
    BRANCH_PHARMACIST,
    CASHIER,
    SYSTEM_ADMIN,
    SYSTEM_ROLES,
    SYSTEM_ROLES_BY_CODE,
    Role,
)

ADMIN_PASSWORD = "MatKhauAdmin2026"
STAFF_PASSWORD = "MatKhauNhanVien26"


def _bootstrap_input(**kwargs: str) -> BootstrapTenantInput:
    data: dict[str, str] = {
        "tenant_name": "Nhà thuốc Bera",
        "branch_code": "HQ",
        "branch_name": "Chi nhánh chính",
        "admin_email": "admin@bera.vn",
        "admin_full_name": "Nguyễn Quản Trị",
        "admin_password": ADMIN_PASSWORD,
    }
    data.update(kwargs)
    return BootstrapTenantInput(**data)  # type: ignore[arg-type]


async def _admin_ctx(iam_service: IamService, auth_service: AuthService) -> RequestContext:
    """Bootstrap a tenant and return a context built from a real login."""
    await iam_service.bootstrap_tenant(_bootstrap_input())
    session = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    return _ctx_of(session)


def _ctx_of(session: SessionOutput) -> RequestContext:
    return RequestContext(
        tenant_id=session.tenant_id,
        branch_id=session.branch_id,
        user_id=session.user_id,
        permissions=frozenset(session.permissions),
    )


# --- bootstrap --------------------------------------------------------------


async def test_bootstrap_creates_tenant_branch_roles_and_admin(iam_service: IamService) -> None:
    out = await iam_service.bootstrap_tenant(_bootstrap_input())
    assert out.roles_created == len(SYSTEM_ROLES)
    assert out.tenant_id and out.branch_id and out.admin_user_id


async def test_bootstrap_reuses_system_roles_for_a_second_tenant(iam_service: IamService) -> None:
    """System roles are shared (tenant_id IS NULL), not duplicated per tenant."""
    await iam_service.bootstrap_tenant(_bootstrap_input())
    second = await iam_service.bootstrap_tenant(
        _bootstrap_input(tenant_name="Nhà thuốc Hai", admin_email="admin@hai.vn")
    )
    assert second.roles_created == 0


async def test_bootstrap_refuses_a_duplicate_email(iam_service: IamService) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    with pytest.raises(ConflictError):
        await iam_service.bootstrap_tenant(_bootstrap_input(tenant_name="Khác"))


async def test_bootstrap_refuses_a_weak_admin_password(iam_service: IamService) -> None:
    with pytest.raises(AppValidationError):
        await iam_service.bootstrap_tenant(_bootstrap_input(admin_password="ngan"))


# --- login ------------------------------------------------------------------


async def test_admin_can_log_in_and_receives_every_permission(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    session = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))

    assert session.access_token and session.refresh_token
    assert session.must_change_password is True  # bootstrap forces a change
    assert "iam.user.create" in session.permissions
    assert "sales.create" in session.permissions
    assert [b.code for b in session.accessible_branches] == ["HQ"]


async def test_login_is_case_insensitive_on_email(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    session = await auth_service.login(LoginInput(email="ADMIN@Bera.VN", password=ADMIN_PASSWORD))
    assert session.user_id


async def test_access_token_carries_the_branch(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """The signed branch is what closes the X-Branch-Id hole (docs/15 §0 F1)."""
    await iam_service.bootstrap_tenant(_bootstrap_input())
    session = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))

    payload = JwtService("test-secret").decode(session.access_token)
    assert payload.branch_id == session.branch_id
    assert payload.tenant_id == session.tenant_id


async def test_unknown_email_and_wrong_password_are_indistinguishable(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    with pytest.raises(UnauthenticatedError) as unknown:
        await auth_service.login(LoginInput(email="khong-ton-tai@bera.vn", password="Sai"))
    with pytest.raises(UnauthenticatedError) as wrong:
        await auth_service.login(LoginInput(email="admin@bera.vn", password="SaiMatKhau123"))
    assert str(unknown.value) == str(wrong.value)


async def test_five_wrong_passwords_lock_the_account(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    for _ in range(5):
        with pytest.raises(UnauthenticatedError):
            await auth_service.login(LoginInput(email="admin@bera.vn", password="SaiMatKhau123"))

    # Even the correct password is refused while the lock holds.
    with pytest.raises(UnauthenticatedError, match="tạm khóa"):
        await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))


async def test_deactivated_user_cannot_log_in(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    user = await iam_service.create_user(
        CreateUserInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD, full_name="Thu Ngân"),
        ctx,
    )
    await iam_service.set_user_active(user.id, active=False, ctx=ctx)

    with pytest.raises(UnauthenticatedError, match="vô hiệu hóa"):
        await auth_service.login(LoginInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD))


async def test_user_without_any_role_cannot_log_in(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """No assignment means no branch to act in — refused rather than given a blank session."""
    ctx = await _admin_ctx(iam_service, auth_service)
    await iam_service.create_user(
        CreateUserInput(email="chua-phan-quyen@bera.vn", password=STAFF_PASSWORD, full_name="X"),
        ctx,
    )
    with pytest.raises(PermissionDeniedError, match="chưa được gán vai trò"):
        await auth_service.login(
            LoginInput(email="chua-phan-quyen@bera.vn", password=STAFF_PASSWORD)
        )


# --- two-level roles across branches ----------------------------------------


async def test_branch_scoped_role_grants_only_that_branch(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    cashier = await iam_service.create_user(
        CreateUserInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD, full_name="Thu Ngân"),
        ctx,
    )
    await iam_service.assign_role(
        cashier.id, AssignRoleInput(role_id=roles[CASHIER].id, branch_id=ctx.branch_id), ctx
    )

    session = await auth_service.login(
        LoginInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD)
    )
    assert session.branch_id == ctx.branch_id
    assert "sales.create" in session.permissions
    # The legal constraints the seeded role encodes must survive the round trip.
    assert "rx.dispense" not in session.permissions
    assert "crm.create" in session.permissions
    assert "crm.sensitive.read" not in session.permissions


async def test_login_at_a_branch_the_user_is_not_assigned_to_is_refused(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await _admin_ctx(iam_service, auth_service)
    with pytest.raises(PermissionDeniedError, match="chi nhánh"):
        await auth_service.login(
            LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD, branch_id=uuid4())
        )


async def test_multi_branch_user_must_name_a_branch(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """A chain-wide admin reaches every branch, so login cannot pick for them."""
    out = await iam_service.bootstrap_tenant(_bootstrap_input())
    ctx = _ctx_of(
        await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    )
    second = await _add_branch(iam_service, ctx, code="CN2", name="Chi nhánh 2")

    with pytest.raises(BranchSelectionRequiredError) as exc:
        await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    branches = exc.value.extra["branches"]
    assert isinstance(branches, list)
    assert {b["code"] for b in branches} == {"HQ", "CN2"}

    # Naming one works, and the chain-wide role applies there too.
    session = await auth_service.login(
        LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD, branch_id=second)
    )
    assert session.branch_id == second
    assert session.branch_id != out.branch_id
    assert "sales.create" in session.permissions


async def _add_branch(iam_service: IamService, ctx: RequestContext, *, code: str, name: str):  # type: ignore[no-untyped-def]
    """Create an extra branch directly through the repositories.

    There is no "create branch" use-case yet (chain management is out of scope,
    docs/15 §1); this stands one up so the two-branch behaviour can be exercised.
    """
    from pharmacy_os.modules.iam.domain import Branch

    branch = Branch(tenant_id=ctx.tenant_id, code=code, name=name)
    async with iam_service._uow_factory() as uow:  # noqa: SLF001 - test-only shortcut
        await iam_service._repos_factory(uow).branches.add(branch)  # noqa: SLF001
        await uow.commit()
    return branch.id


# --- refresh, rotation and reuse detection ----------------------------------


async def test_refresh_rotates_the_token_and_keeps_the_branch(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    first = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    second = await auth_service.refresh(first.refresh_token)

    assert second.refresh_token != first.refresh_token
    assert second.branch_id == first.branch_id

    # The old token is now spent.
    with pytest.raises(UnauthenticatedError):
        await auth_service.refresh(first.refresh_token)


async def test_replaying_a_rotated_token_revokes_the_whole_family(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    first = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    second = await auth_service.refresh(first.refresh_token)

    with pytest.raises(UnauthenticatedError, match="thu hồi"):
        await auth_service.refresh(first.refresh_token)

    # The live token the legitimate client holds is revoked too — theft is assumed.
    with pytest.raises(UnauthenticatedError):
        await auth_service.refresh(second.refresh_token)


async def test_refresh_recomputes_permissions_from_the_database(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """Refresh is the revocation checkpoint: a revoked role must not survive it."""
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    pharmacist = await iam_service.create_user(
        CreateUserInput(email="duoc-si@bera.vn", password=STAFF_PASSWORD, full_name="Dược Sĩ"),
        ctx,
    )
    grant = await iam_service.assign_role(
        pharmacist.id,
        AssignRoleInput(role_id=roles[BRANCH_PHARMACIST].id, branch_id=ctx.branch_id),
        ctx,
    )
    session = await auth_service.login(LoginInput(email="duoc-si@bera.vn", password=STAFF_PASSWORD))
    assert "rx.dispense" in session.permissions

    await iam_service.revoke_role(pharmacist.id, grant.id, ctx)
    with pytest.raises(PermissionDeniedError):
        # No roles left at all, so there is no branch to refresh into either.
        await auth_service.refresh(session.refresh_token)


async def test_switching_branch_reissues_the_token_for_the_new_branch(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    ctx = _ctx_of(
        await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    )
    second_branch = await _add_branch(iam_service, ctx, code="CN2", name="Chi nhánh 2")
    session = await auth_service.login(
        LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD, branch_id=ctx.branch_id)
    )

    switched = await auth_service.refresh(session.refresh_token, branch_id=second_branch)
    assert switched.branch_id == second_branch
    assert JwtService("test-secret").decode(switched.access_token).branch_id == second_branch


async def test_logout_revokes_the_session(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    session = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    await auth_service.logout(session.refresh_token)

    with pytest.raises(UnauthenticatedError):
        await auth_service.refresh(session.refresh_token)


async def test_logout_of_an_unknown_token_is_silent(auth_service: AuthService) -> None:
    await auth_service.logout("khong-ton-tai")


async def test_deactivating_a_user_kills_their_live_sessions(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    staff = await iam_service.create_user(
        CreateUserInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD, full_name="Thu Ngân"),
        ctx,
    )
    await iam_service.assign_role(
        staff.id, AssignRoleInput(role_id=roles[CASHIER].id, branch_id=ctx.branch_id), ctx
    )
    session = await auth_service.login(
        LoginInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD)
    )

    await iam_service.set_user_active(staff.id, active=False, ctx=ctx)
    with pytest.raises(UnauthenticatedError):
        await auth_service.refresh(session.refresh_token)


# --- password change --------------------------------------------------------


async def test_changing_password_clears_the_flag_and_revokes_sessions(
    iam_service: IamService, auth_service: AuthService
) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    session = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    ctx = _ctx_of(session)

    await auth_service.change_password(
        ctx, ChangePasswordInput(current_password=ADMIN_PASSWORD, new_password="MatKhauMoi2026")
    )
    with pytest.raises(UnauthenticatedError):
        await auth_service.refresh(session.refresh_token)

    fresh = await auth_service.login(LoginInput(email="admin@bera.vn", password="MatKhauMoi2026"))
    assert fresh.must_change_password is False


async def test_changing_password_requires_the_current_one(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    with pytest.raises(UnauthenticatedError):
        await auth_service.change_password(
            ctx, ChangePasswordInput(current_password="SaiRoi123456", new_password="MatKhauMoi2026")
        )


async def test_new_password_must_satisfy_the_policy(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    with pytest.raises(AppValidationError):
        await auth_service.change_password(
            ctx, ChangePasswordInput(current_password=ADMIN_PASSWORD, new_password="ngan")
        )


# --- reauth for cross-module signing (compliance ký sổ, docs/13 mục C.5) ---


async def test_verify_own_password_true_for_the_correct_password(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    assert await auth_service.verify_own_password(ctx, ADMIN_PASSWORD) is True


async def test_verify_own_password_false_for_a_wrong_password(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    assert await auth_service.verify_own_password(ctx, "SaiRoi123456") is False


async def test_verify_own_password_does_not_mutate_or_revoke_sessions(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """Read-only: unlike ``change_password``, a wrong attempt must not touch the session."""
    await iam_service.bootstrap_tenant(_bootstrap_input())
    session = await auth_service.login(LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD))
    ctx = _ctx_of(session)
    assert await auth_service.verify_own_password(ctx, "SaiRoi123456") is False
    # the same refresh token must still work — nothing was revoked by the failed attempt
    await auth_service.refresh(session.refresh_token)


# --- administration guards --------------------------------------------------


async def test_creating_a_user_requires_the_permission(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    weak = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset({"sales.create"}),
    )
    with pytest.raises(PermissionDeniedError):
        await iam_service.create_user(
            CreateUserInput(email="x@bera.vn", password=STAFF_PASSWORD, full_name="X"), weak
        )


async def test_a_users_of_another_tenant_is_reported_as_not_found(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """Tenant isolation answers 404, not 403 — no probing for ids elsewhere."""
    ctx = await _admin_ctx(iam_service, auth_service)
    other = await iam_service.bootstrap_tenant(
        _bootstrap_input(tenant_name="Nhà thuốc Khác", admin_email="admin@khac.vn")
    )
    with pytest.raises(NotFoundError):
        await iam_service.get_user(other.admin_user_id, ctx)


async def test_duplicate_role_grant_is_rejected(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    staff = await iam_service.create_user(
        CreateUserInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD, full_name="Thu Ngân"),
        ctx,
    )
    await iam_service.assign_role(staff.id, AssignRoleInput(role_id=roles[CASHIER].id), ctx)
    with pytest.raises(ConflictError):
        await iam_service.assign_role(staff.id, AssignRoleInput(role_id=roles[CASHIER].id), ctx)


async def test_the_same_role_may_be_granted_chain_wide_and_per_branch(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """The two partial unique indexes must not collide with each other."""
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    staff = await iam_service.create_user(
        CreateUserInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD, full_name="Thu Ngân"),
        ctx,
    )
    await iam_service.assign_role(staff.id, AssignRoleInput(role_id=roles[CASHIER].id), ctx)
    await iam_service.assign_role(
        staff.id, AssignRoleInput(role_id=roles[CASHIER].id, branch_id=ctx.branch_id), ctx
    )
    assert len(await iam_service.list_assignments(staff.id, ctx)) == 2


async def test_assigning_an_unknown_branch_is_rejected(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    staff = await iam_service.create_user(
        CreateUserInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD, full_name="Thu Ngân"),
        ctx,
    )
    with pytest.raises(NotFoundError):
        await iam_service.assign_role(
            staff.id, AssignRoleInput(role_id=roles[CASHIER].id, branch_id=uuid4()), ctx
        )


async def test_admin_reset_forces_a_password_change_and_revokes_sessions(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    staff = await iam_service.create_user(
        CreateUserInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD, full_name="Thu Ngân"),
        ctx,
    )
    await iam_service.assign_role(
        staff.id, AssignRoleInput(role_id=roles[CASHIER].id, branch_id=ctx.branch_id), ctx
    )
    session = await auth_service.login(
        LoginInput(email="thu-ngan@bera.vn", password=STAFF_PASSWORD)
    )

    await iam_service.reset_password(staff.id, "MatKhauTamThoi26", ctx)
    with pytest.raises(UnauthenticatedError):
        await auth_service.refresh(session.refresh_token)

    fresh = await auth_service.login(
        LoginInput(email="thu-ngan@bera.vn", password="MatKhauTamThoi26")
    )
    assert fresh.must_change_password is True


async def test_seeded_roles_are_listed_for_a_fresh_tenant(
    iam_service: IamService, auth_service: AuthService
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    codes = {r.code for r in await iam_service.list_roles(ctx)}
    assert codes == {spec.code for spec in SYSTEM_ROLES}
    assert SYSTEM_ADMIN in codes


# --- system-role drift on upgrade -------------------------------------------


async def test_sync_system_roles_updates_a_role_that_drifted(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """A permission added to the code catalogue must reach an existing deployment.

    Regression for a real bug: seeding was insert-only, so a database provisioned by
    an earlier release kept its old permission set forever and the new endpoint
    answered 403 to an admin. Found by running the CLI against a live database, not
    by the suite — which always started empty and therefore always took the insert
    path.
    """
    ctx = await _admin_ctx(iam_service, auth_service)
    admin_role = next(r for r in await iam_service.list_roles(ctx) if r.code == SYSTEM_ADMIN)

    # Simulate the older release: strip a permission straight through the repository.
    async with iam_service._uow_factory() as uow:  # noqa: SLF001 - test-only shortcut
        repos = iam_service._repos_factory(uow)  # noqa: SLF001
        stale = await repos.roles.get(admin_role.id)
        assert stale is not None
        await repos.roles.update(
            Role(
                id=stale.id,
                code=stale.code,
                name=stale.name,
                description=stale.description,
                permissions=frozenset(stale.permissions - {"audit.read"}),
            )
        )
        await uow.commit()

    drifted = next(r for r in await iam_service.list_roles(ctx) if r.code == SYSTEM_ADMIN)
    assert "audit.read" not in drifted.permissions

    result = await iam_service.sync_system_roles()
    assert (result.created, result.updated) == (0, 1)

    refreshed = next(r for r in await iam_service.list_roles(ctx) if r.code == SYSTEM_ADMIN)
    assert "audit.read" in refreshed.permissions
    assert set(refreshed.permissions) == set(SYSTEM_ROLES_BY_CODE[SYSTEM_ADMIN].permissions)


async def test_sync_system_roles_is_idempotent(iam_service: IamService) -> None:
    await iam_service.bootstrap_tenant(_bootstrap_input())
    assert await iam_service.sync_system_roles() == SystemRoleSyncOutput(created=0, updated=0)


async def test_sync_system_roles_seeds_an_empty_deployment(iam_service: IamService) -> None:
    result = await iam_service.sync_system_roles()
    assert (result.created, result.updated) == (len(SYSTEM_ROLES), 0)


async def test_sync_leaves_tenant_owned_roles_alone(
    iam_service: IamService, auth_service: AuthService
) -> None:
    """Only ``tenant_id IS NULL`` rows are code-owned."""
    ctx = await _admin_ctx(iam_service, auth_service)
    custom = Role(
        code="vai_tro_rieng",
        name="Vai trò riêng của nhà thuốc",
        tenant_id=ctx.tenant_id,
        permissions=frozenset({"sales.read"}),
    )
    async with iam_service._uow_factory() as uow:  # noqa: SLF001 - test-only shortcut
        await iam_service._repos_factory(uow).roles.add(custom)  # noqa: SLF001
        await uow.commit()

    await iam_service.sync_system_roles()

    kept = next(r for r in await iam_service.list_roles(ctx) if r.code == "vai_tro_rieng")
    assert kept.permissions == ["sales.read"]
