"""IAM domain rules: entity invariants, lockout, and the two-level role resolution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pharmacy_os.modules.iam.domain import (
    ALL_PERMISSIONS,
    BRANCH_PHARMACIST,
    CASHIER,
    CHAIN_PHARMACIST,
    LOCKOUT_MINUTES,
    MAX_FAILED_LOGINS,
    MIN_PASSWORD_LENGTH,
    SYSTEM_ADMIN,
    SYSTEM_ROLES,
    SYSTEM_ROLES_BY_CODE,
    WAREHOUSE,
    ActivationStatus,
    Branch,
    InvalidRoleError,
    InvalidTenantError,
    InvalidUserError,
    RefreshSession,
    Role,
    RoleAssignment,
    Tenant,
    User,
    UserInactiveError,
    UserLockedError,
    WeakPasswordError,
    accessible_branch_ids,
    is_branch_accessible,
    resolve_permissions,
    validate_password_strength,
)

NOW = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)


def _user(**kwargs: object) -> User:
    defaults: dict[str, object] = {
        "tenant_id": uuid4(),
        "email": "duocsi@nhathuoc.vn",
        "password_hash": "hashed",
        "full_name": "Nguyễn Văn A",
    }
    defaults.update(kwargs)
    return User(**defaults)  # type: ignore[arg-type]


# --- entity invariants ------------------------------------------------------


def test_user_email_is_normalised_to_lowercase() -> None:
    assert _user(email="  DuocSi@NhaThuoc.VN ").email == "duocsi@nhathuoc.vn"


@pytest.mark.parametrize("email", ["khong-co-a-cong", ""])
def test_user_rejects_malformed_email(email: str) -> None:
    with pytest.raises(InvalidUserError):
        _user(email=email)


def test_user_rejects_blank_full_name() -> None:
    with pytest.raises(InvalidUserError):
        _user(full_name="   ")


def test_tenant_and_branch_reject_blank_names() -> None:
    with pytest.raises(InvalidTenantError):
        Tenant(name="  ")
    with pytest.raises(InvalidTenantError):
        Branch(tenant_id=uuid4(), code="", name="Chi nhánh 1")
    with pytest.raises(InvalidTenantError):
        Branch(tenant_id=uuid4(), code="HQ", name=" ")


def test_role_requires_code_and_name() -> None:
    with pytest.raises(InvalidRoleError):
        Role(code=" ", name="Thu ngân")
    with pytest.raises(InvalidRoleError):
        Role(code="cashier", name="")


def test_system_role_is_marked_by_absent_tenant() -> None:
    assert Role(code="cashier", name="Thu ngân").is_system is True
    assert Role(code="custom", name="Riêng", tenant_id=uuid4()).is_system is False


# --- authentication guards --------------------------------------------------


def test_inactive_user_cannot_authenticate() -> None:
    user = _user(status=ActivationStatus.INACTIVE)
    with pytest.raises(UserInactiveError):
        user.ensure_can_authenticate(NOW)


def test_locked_user_cannot_authenticate_until_lock_expires() -> None:
    user = _user(locked_until=NOW + timedelta(minutes=5))
    with pytest.raises(UserLockedError):
        user.ensure_can_authenticate(NOW)
    # Past the lock window the account is usable again without an admin unlocking it.
    user.ensure_can_authenticate(NOW + timedelta(minutes=6))


def test_failed_logins_lock_the_account_on_the_configured_attempt() -> None:
    user = _user()
    for _ in range(MAX_FAILED_LOGINS - 1):
        assert user.register_failed_login(NOW) is False
    assert user.is_locked(NOW) is False

    assert user.register_failed_login(NOW) is True
    assert user.locked_until == NOW + timedelta(minutes=LOCKOUT_MINUTES)
    # Counter resets with the lock so the next window starts clean.
    assert user.failed_login_count == 0


def test_successful_login_clears_lock_and_counter() -> None:
    user = _user(failed_login_count=3, locked_until=NOW - timedelta(minutes=1))
    user.register_successful_login(NOW)
    assert (user.failed_login_count, user.locked_until, user.last_login_at) == (0, None, NOW)


def test_change_password_clears_forced_change_flag() -> None:
    user = _user(must_change_password=True)
    user.change_password("new-hash")
    assert (user.password_hash, user.must_change_password) == ("new-hash", False)


def test_deactivate_then_activate_resets_lockout_state() -> None:
    user = _user(failed_login_count=4, locked_until=NOW + timedelta(minutes=5))
    user.deactivate()
    assert user.is_active is False
    user.activate()
    assert (user.is_active, user.failed_login_count, user.locked_until) == (True, 0, None)


@pytest.mark.parametrize("plain", ["", "ngan", "a" * (MIN_PASSWORD_LENGTH - 1)])
def test_password_policy_rejects_short_passwords(plain: str) -> None:
    with pytest.raises(WeakPasswordError):
        validate_password_strength(plain)


def test_password_policy_accepts_minimum_length() -> None:
    validate_password_strength("a" * MIN_PASSWORD_LENGTH)


# --- two-level role resolution (docs/15 §5 Q4) ------------------------------


def test_chain_wide_assignment_applies_to_every_branch() -> None:
    tenant_id, branch_a, branch_b = uuid4(), uuid4(), uuid4()
    role = Role(code=CHAIN_PHARMACIST, name="Chuỗi", permissions=frozenset({"rx.approve"}))
    assignment = RoleAssignment(user_id=uuid4(), tenant_id=tenant_id, role_id=role.id)

    assert assignment.is_chain_wide is True
    roles = {role.id: role}
    assert resolve_permissions([assignment], roles, branch_a) == frozenset({"rx.approve"})
    assert resolve_permissions([assignment], roles, branch_b) == frozenset({"rx.approve"})
    assert accessible_branch_ids([assignment], [branch_a, branch_b]) == [branch_a, branch_b]


def test_branch_assignment_does_not_leak_to_another_branch() -> None:
    tenant_id, branch_a, branch_b = uuid4(), uuid4(), uuid4()
    role = Role(code=BRANCH_PHARMACIST, name="Chi nhánh", permissions=frozenset({"rx.dispense"}))
    assignment = RoleAssignment(
        user_id=uuid4(), tenant_id=tenant_id, role_id=role.id, branch_id=branch_a
    )
    roles = {role.id: role}

    assert resolve_permissions([assignment], roles, branch_a) == frozenset({"rx.dispense"})
    assert resolve_permissions([assignment], roles, branch_b) == frozenset()
    assert accessible_branch_ids([assignment], [branch_a, branch_b]) == [branch_a]
    assert is_branch_accessible([assignment], [branch_a, branch_b], branch_b) is False


def test_permissions_are_the_union_of_chain_and_branch_roles() -> None:
    tenant_id, branch_a = uuid4(), uuid4()
    chain_role = Role(code="chain", name="Chuỗi", permissions=frozenset({"catalog.create"}))
    branch_role = Role(code="branch", name="Chi nhánh", permissions=frozenset({"sales.create"}))
    user_id = uuid4()
    assignments = [
        RoleAssignment(user_id=user_id, tenant_id=tenant_id, role_id=chain_role.id),
        RoleAssignment(
            user_id=user_id, tenant_id=tenant_id, role_id=branch_role.id, branch_id=branch_a
        ),
    ]

    resolved = resolve_permissions(
        assignments, {chain_role.id: chain_role, branch_role.id: branch_role}, branch_a
    )
    assert resolved == frozenset({"catalog.create", "sales.create"})


def test_assignment_to_a_missing_role_is_ignored_not_fatal() -> None:
    """A deleted role must not cost the user the permissions their other roles give."""
    tenant_id, branch_a = uuid4(), uuid4()
    live_role = Role(code="live", name="Còn", permissions=frozenset({"sales.read"}))
    user_id = uuid4()
    assignments = [
        RoleAssignment(user_id=user_id, tenant_id=tenant_id, role_id=live_role.id),
        RoleAssignment(user_id=user_id, tenant_id=tenant_id, role_id=uuid4()),
    ]

    assert resolve_permissions(assignments, {live_role.id: live_role}, branch_a) == frozenset(
        {"sales.read"}
    )


def test_branch_of_another_tenant_is_never_accessible() -> None:
    """The branch list is the tenant's own; a foreign id can't be smuggled in."""
    tenant_id, branch_a, foreign_branch = uuid4(), uuid4(), uuid4()
    assignment = RoleAssignment(user_id=uuid4(), tenant_id=tenant_id, role_id=uuid4())
    assert is_branch_accessible([assignment], [branch_a], foreign_branch) is False


def test_user_without_assignments_reaches_no_branch() -> None:
    assert accessible_branch_ids([], [uuid4(), uuid4()]) == []


# --- refresh sessions -------------------------------------------------------


def _session(**kwargs: object) -> RefreshSession:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "tenant_id": uuid4(),
        "branch_id": uuid4(),
        "token_hash": "hash",
        "expires_at": NOW + timedelta(days=30),
    }
    defaults.update(kwargs)
    return RefreshSession(**defaults)  # type: ignore[arg-type]


def test_fresh_session_is_usable() -> None:
    assert _session().is_usable(NOW) is True


def test_expired_session_is_not_usable() -> None:
    session = _session(expires_at=NOW - timedelta(seconds=1))
    assert (session.is_expired(NOW), session.is_usable(NOW)) == (True, False)


def test_revoked_session_is_not_usable_and_keeps_first_revocation_time() -> None:
    session = _session()
    replacement = uuid4()
    session.revoke(NOW, replaced_by=replacement)
    assert (session.is_revoked, session.is_usable(NOW)) == (True, False)
    assert (session.revoked_at, session.replaced_by) == (NOW, replacement)

    # Re-revoking (e.g. the family-wide sweep after a replay) must not rewrite history.
    session.revoke(NOW + timedelta(hours=1))
    assert (session.revoked_at, session.replaced_by) == (NOW, replacement)


# --- seeded system roles (docs/15 §5 Q5) ------------------------------------


def test_five_system_roles_are_defined() -> None:
    codes = [spec.code for spec in SYSTEM_ROLES]
    assert codes == [SYSTEM_ADMIN, CHAIN_PHARMACIST, BRANCH_PHARMACIST, CASHIER, WAREHOUSE]


def test_every_seeded_permission_is_a_known_permission() -> None:
    for spec in SYSTEM_ROLES:
        assert spec.permissions <= ALL_PERMISSIONS, spec.code


def test_admin_holds_every_permission_and_is_the_only_role_that_does() -> None:
    assert SYSTEM_ROLES_BY_CODE[SYSTEM_ADMIN].permissions == ALL_PERMISSIONS
    others = [s for s in SYSTEM_ROLES if s.code != SYSTEM_ADMIN]
    assert all(spec.permissions < ALL_PERMISSIONS for spec in others)


def test_cashier_cannot_approve_or_dispense_prescriptions() -> None:
    """Luật Dược Điều 6.5.h — a pharmacist act, not a configuration preference."""
    cashier = SYSTEM_ROLES_BY_CODE[CASHIER].permissions
    assert {"rx.approve", "rx.dispense"} & cashier == set()
    assert "rx.read" in cashier


def test_cashier_has_no_customer_data_access() -> None:
    """NĐ356 Điều 4.2 / GPP TT02 I-1a.III.4.a — crm.read still exposes allergies."""
    assert not any(p.startswith("crm.") for p in SYSTEM_ROLES_BY_CODE[CASHIER].permissions)


def test_warehouse_touches_no_patient_or_sales_data() -> None:
    warehouse = SYSTEM_ROLES_BY_CODE[WAREHOUSE].permissions
    assert not any(p.startswith(("crm.", "rx.", "sales.", "clinical.")) for p in warehouse)


def test_branch_pharmacist_lacks_chain_level_switches() -> None:
    branch = SYSTEM_ROLES_BY_CODE[BRANCH_PHARMACIST].permissions
    chain = SYSTEM_ROLES_BY_CODE[CHAIN_PHARMACIST].permissions
    assert {
        "catalog.create",
        "clinical.settings.write",
        "compliance.config.write",
    } & branch == set()
    assert branch < chain


def test_only_admin_may_manage_users_and_roles() -> None:
    for spec in SYSTEM_ROLES:
        if spec.code == SYSTEM_ADMIN:
            continue
        assert {"iam.user.create", "iam.user.write", "iam.role.write", "iam.role.assign"} & (
            spec.permissions
        ) == set()
