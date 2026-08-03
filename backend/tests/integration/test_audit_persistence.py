"""Every audit call site IAM makes must land a real row in ``audit_logs``.

The point of this suite is that it does **not** trust the code to be calling the
logger in the right places: each test drives the real use-case and then reads the
table back. A call that was removed, or one that never fired, fails here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pyotp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, AuditEntry, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import UnauthenticatedError
from pharmacy_os.modules.iam.application import (
    AssignRoleInput,
    AuthService,
    BootstrapTenantInput,
    ChangePasswordInput,
    CreateUserInput,
    IamService,
    LoginInput,
    StepUpResult,
)
from pharmacy_os.modules.iam.domain import CASHIER

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "MatKhauAdmin2026"
STAFF_EMAIL = "thu-ngan@bera.vn"
STAFF_PASSWORD = "MatKhauNhanVien26"


@pytest.fixture
async def audit_repo(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[SqlAlchemyAuditLogRepository]:
    async with session_factory() as session:
        yield SqlAlchemyAuditLogRepository(session)


async def _bootstrap(iam_service: IamService) -> UUID:
    out = await iam_service.bootstrap_tenant(
        BootstrapTenantInput(
            tenant_name="Nhà thuốc Bera",
            branch_code="HQ",
            branch_name="Chi nhánh chính",
            admin_email=ADMIN_EMAIL,
            admin_full_name="Nguyễn Quản Trị",
            admin_password=ADMIN_PASSWORD,
        )
    )
    return out.tenant_id


async def _admin_ctx(iam_service: IamService, auth_service: AuthService) -> RequestContext:
    await _bootstrap(iam_service)
    session = await auth_service.login(
        LoginInput(email=ADMIN_EMAIL, password=ADMIN_PASSWORD, client_ip="10.0.0.7")
    )
    return RequestContext(
        tenant_id=session.tenant_id,
        branch_id=session.branch_id,
        user_id=session.user_id,
        permissions=frozenset(session.permissions),
        client_ip="10.0.0.7",
    )


async def _actions(repo: SqlAlchemyAuditLogRepository, tenant_id: UUID) -> list[AuditAction]:
    return [e.action for e in await repo.list(tenant_id, limit=200)]


# --- one test per action IAM emits ------------------------------------------


async def test_login_success_is_persisted_with_ip_and_branch(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    tenant_id = await _bootstrap(iam_service)
    session = await auth_service.login(
        LoginInput(email=ADMIN_EMAIL, password=ADMIN_PASSWORD, client_ip="203.0.113.9")
    )

    entries = await audit_repo.list(tenant_id)
    logged_in = [e for e in entries if e.action is AuditAction.LOGIN_SUCCESS]
    assert len(logged_in) == 1
    entry = logged_in[0]
    assert entry.actor_user_id == session.user_id
    assert entry.target_type == "user"
    assert entry.context == {"client_ip": "203.0.113.9", "branch_id": str(session.branch_id)}
    assert entry.occurred_at.tzinfo is not None


async def test_failed_login_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    tenant_id = await _bootstrap(iam_service)
    with pytest.raises(UnauthenticatedError):
        await auth_service.login(
            LoginInput(email=ADMIN_EMAIL, password="SaiMatKhau123", client_ip="203.0.113.9")
        )

    entries = [e for e in await audit_repo.list(tenant_id) if e.action is AuditAction.LOGIN_FAILED]
    assert len(entries) == 1
    assert entries[0].context["client_ip"] == "203.0.113.9"


async def test_lockout_records_both_the_attempt_and_the_lock(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    """Five attempts must leave five LOGIN_FAILED rows plus one ACCOUNT_LOCKED —
    collapsing them would erase the four tries that led to the lock."""
    tenant_id = await _bootstrap(iam_service)
    for _ in range(5):
        with pytest.raises(UnauthenticatedError):
            await auth_service.login(LoginInput(email=ADMIN_EMAIL, password="SaiMatKhau123"))

    actions = await _actions(audit_repo, tenant_id)
    assert actions.count(AuditAction.LOGIN_FAILED) == 5
    assert actions.count(AuditAction.ACCOUNT_LOCKED) == 1


async def test_user_created_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    user = await iam_service.create_user(
        CreateUserInput(email=STAFF_EMAIL, password=STAFF_PASSWORD, full_name="Thu Ngân"), ctx
    )

    entries = [
        e for e in await audit_repo.list(ctx.tenant_id) if e.action is AuditAction.USER_CREATED
    ]
    assert len(entries) == 1
    assert entries[0].target_id == str(user.id)
    assert entries[0].actor_user_id == ctx.user_id
    assert entries[0].context["client_ip"] == "10.0.0.7"


async def test_user_deactivated_and_reactivated_are_separate_rows(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    user = await iam_service.create_user(
        CreateUserInput(email=STAFF_EMAIL, password=STAFF_PASSWORD, full_name="Thu Ngân"), ctx
    )
    await iam_service.set_user_active(user.id, active=False, ctx=ctx)
    await iam_service.set_user_active(user.id, active=True, ctx=ctx)

    actions = await _actions(audit_repo, ctx.tenant_id)
    assert actions.count(AuditAction.USER_DEACTIVATED) == 1
    assert actions.count(AuditAction.USER_ACTIVATED) == 1


async def test_role_granted_and_revoked_are_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    roles = {r.code: r for r in await iam_service.list_roles(ctx)}
    user = await iam_service.create_user(
        CreateUserInput(email=STAFF_EMAIL, password=STAFF_PASSWORD, full_name="Thu Ngân"), ctx
    )
    grant = await iam_service.assign_role(
        user.id, AssignRoleInput(role_id=roles[CASHIER].id, branch_id=ctx.branch_id), ctx
    )
    await iam_service.revoke_role(user.id, grant.id, ctx)

    entries = await audit_repo.list(ctx.tenant_id)
    granted = [e for e in entries if e.action is AuditAction.ROLE_GRANTED]
    revoked = [e for e in entries if e.action is AuditAction.ROLE_REVOKED]
    assert len(granted) == len(revoked) == 1
    assert granted[0].target_type == "user_role" == revoked[0].target_type
    assert granted[0].target_id == revoked[0].target_id == str(grant.id)


async def test_password_changed_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    ctx = await _admin_ctx(iam_service, auth_service)
    await auth_service.change_password(
        ctx, ChangePasswordInput(current_password=ADMIN_PASSWORD, new_password="MatKhauMoi2026")
    )

    entries = [
        e for e in await audit_repo.list(ctx.tenant_id) if e.action is AuditAction.PASSWORD_CHANGED
    ]
    assert len(entries) == 1
    assert entries[0].actor_user_id == ctx.user_id


async def test_admin_password_reset_is_a_distinct_action(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    """An admin resetting somebody else's password is a privileged act and must not
    be indistinguishable from a user changing their own."""
    ctx = await _admin_ctx(iam_service, auth_service)
    user = await iam_service.create_user(
        CreateUserInput(email=STAFF_EMAIL, password=STAFF_PASSWORD, full_name="Thu Ngân"), ctx
    )
    await iam_service.reset_password(user.id, "MatKhauTamThoi26", ctx)

    entries = [
        e for e in await audit_repo.list(ctx.tenant_id) if e.action is AuditAction.PASSWORD_RESET
    ]
    assert len(entries) == 1
    assert entries[0].actor_user_id == ctx.user_id  # the admin, not the target
    assert entries[0].target_id == str(user.id)


async def test_token_replay_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    tenant_id = await _bootstrap(iam_service)
    first = await auth_service.login(LoginInput(email=ADMIN_EMAIL, password=ADMIN_PASSWORD))
    await auth_service.refresh(first.refresh_token)
    with pytest.raises(UnauthenticatedError):
        await auth_service.refresh(first.refresh_token)

    entries = [
        e for e in await audit_repo.list(tenant_id) if e.action is AuditAction.TOKEN_REPLAY_DETECTED
    ]
    assert len(entries) == 1
    assert entries[0].target_type == "refresh_token"


#: Customer-data, prescription, compliance, sales, inventory, procurement,
#: clinical and catalog actions belong to their own feature's persistence suite
#: (test_crm_privacy_api_e2e.py, test_prescription_flow.py, test_compliance_flow.py,
#: test_sales_flow.py, test_sales_vnpay_flow.py, test_inventory_flow.py,
#: test_procurement_flow.py, test_clinical_flow.py, test_catalog_repo.py); listing
#: them here keeps the net below honest about what this file does *not* prove.
_COVERED_ELSEWHERE = {
    AuditAction.CUSTOMER_SENSITIVE_READ,
    AuditAction.CUSTOMER_SENSITIVE_AUTO_CHECK,
    AuditAction.CUSTOMER_SENSITIVE_WRITE,
    AuditAction.CUSTOMER_MEDICATION_HISTORY_RECORDED,
    AuditAction.CONSENT_GRANTED,
    AuditAction.CONSENT_REVOKED,
    AuditAction.CUSTOMER_ERASED,
    AuditAction.PRESCRIPTION_CREATED,
    AuditAction.PRESCRIPTION_APPROVED,
    AuditAction.PRESCRIPTION_REJECTED,
    AuditAction.PRESCRIPTION_DISPENSED,
    AuditAction.CONTROLLED_LEDGER_ENTRY_RECORDED,
    AuditAction.TENANT_COMPLIANCE_CONFIG_SET,
    AuditAction.PERIODIC_REPORT_EXPORTED,
    AuditAction.DRUG_RETURN_RECORDED,
    AuditAction.LEDGER_DAILY_CLOSURE_EXPORTED,
    AuditAction.LEDGER_BOOK_SIGNED,
    AuditAction.SALE_COMPLETED,
    AuditAction.SALES_ALLERGY_WARNING_OVERRIDDEN,
    AuditAction.SALE_VNPAY_INITIATED,
    AuditAction.SALE_VNPAY_CANCELLED,
    AuditAction.INVENTORY_STOCK_RECEIVED,
    AuditAction.INVENTORY_STOCK_DISPENSED,
    AuditAction.PROCUREMENT_PO_ORDERED,
    AuditAction.PROCUREMENT_GRN_CONFIRMED,
    AuditAction.CLINICAL_INTERACTION_CHECKED,
    AuditAction.CLINICAL_RECOMMENDATION_ACCEPTED,
    AuditAction.CATALOG_DRUG_CREATED,
    # Có test bền vững riêng: tests/integration/test_catalog_replace_ingredients.py
    # ::test_ghi_vet_audit_kem_so_luong_TRUOC_va_SAU (đọc thẳng AuditLogORM).
    AuditAction.CATALOG_DRUG_INGREDIENTS_REPLACED,
    # Có test bền vững riêng: tests/integration/test_catalog_set_price.py
    # ::test_doi_gia_ghi_mot_dong_audit (đọc thẳng AuditLogORM).
    AuditAction.CATALOG_DRUG_PRICE_CHANGED,
    # Có test riêng: tests/integration/test_sales_price_override.py
    AuditAction.SALE_PRICE_OVERRIDE,
    # Có test riêng: tests/integration/test_rx_image_e2e.py
    AuditAction.RX_IMAGE_ATTACHED,
    AuditAction.RX_IMAGE_VIEWED,
    # Có test riêng: tests/integration/test_crm_phone_masking.py (đường mở lộ số).
    AuditAction.CUSTOMER_PHONE_REVEALED,
    # Có test riêng: tests/integration/test_uy_quyen_quan_tri_flow.py
    # ::test_cap_va_thu_hoi_deu_de_lai_vet_voi_ly_do — đọc thẳng AuditLogORM và khẳng định
    # cả nội dung ``context`` (có ``ly_do``, có ``so_quyen``, KHÔNG có danh sách mã quyền).
    AuditAction.ADMIN_DELEGATION_GRANTED,
    AuditAction.ADMIN_DELEGATION_REVOKED,
    AuditAction.SALE_RETURN_REGISTERED,
    AuditAction.INVENTORY_RECONCILIATION_RESOLVED,
    # Có test riêng: tests/integration/test_inventory_location_e2e.py
    AuditAction.INVENTORY_PUT_AWAY,
    AuditAction.INVENTORY_COUNT_APPROVED,
    AuditAction.INVENTORY_COUNT_REJECTED,
    # Có test riêng: tests/integration/test_location_e2e.py
    AuditAction.LOCATION_CREATED,
    AuditAction.LOCATION_CHANGED,
    AuditAction.ANALYTICS_REORDER_RUN,
    AuditAction.ANALYTICS_SUGGESTION_MATERIALIZED,
    AuditAction.ANALYTICS_SUGGESTION_DISMISSED,
    AuditAction.ANALYTICS_SUGGESTION_UNDONE,
    AuditAction.ENCRYPTION_KEY_ROTATED,
}


async def test_every_action_emitted_by_iam_reaches_the_table() -> None:
    """Sanity net: the actions the tests above assert on cover every iam action.

    Anything added to :class:`AuditAction` without a persistence test shows up here
    rather than being noticed months later during an inspection.
    """
    covered = {
        AuditAction.LOGIN_SUCCESS,
        AuditAction.LOGIN_FAILED,
        AuditAction.ACCOUNT_LOCKED,
        AuditAction.USER_CREATED,
        AuditAction.USER_ACTIVATED,
        AuditAction.USER_DEACTIVATED,
        AuditAction.ROLE_GRANTED,
        AuditAction.ROLE_REVOKED,
        AuditAction.PASSWORD_CHANGED,
        AuditAction.PASSWORD_RESET,
        AuditAction.TOKEN_REPLAY_DETECTED,
        AuditAction.TWO_FACTOR_ENROLLED,
        AuditAction.TWO_FACTOR_ACTIVATED,
        AuditAction.TWO_FACTOR_DISABLED,
        AuditAction.TWO_FACTOR_RESET,
        AuditAction.TWO_FACTOR_FAILED,
        AuditAction.TWO_FACTOR_BACKUP_CODE_USED,
    }
    assert covered == set(AuditAction) - _COVERED_ELSEWHERE


# --- two-factor: every transition of a second factor is answerable ------------
#
# Each of these drives the real use-case and reads the table back, like the rest of
# this file. Worth the coverage because every one of them either raises or lowers the
# protection standing between a leaked password and a binding ledger signature.


def _totp_now(secret: str, *, skew_seconds: int = 0) -> str:
    """A valid code for *secret*.

    ``skew_seconds`` moves to a neighbouring time step, which the replay watermark
    forces after a code has already been spent: ``UserTwoFactor.register_use`` refuses
    any step at or below the last one used, so re-reading "now" straight after
    activation would be rejected as a replay (correctly).
    """
    return str(pyotp.TOTP(secret).at(datetime.now(UTC) + timedelta(seconds=skew_seconds)))


async def _enrolled_admin(
    iam_service: IamService, auth_service: AuthService
) -> tuple[RequestContext, str, list[str]]:
    """An admin with 2FA switched on; returns its context, TOTP secret and backup codes."""
    ctx = await _admin_ctx(iam_service, auth_service)
    enrolment = await auth_service.enroll_two_factor(ctx)
    activation = await auth_service.activate_two_factor(ctx, _totp_now(enrolment.secret))
    return ctx, enrolment.secret, activation.backup_codes


async def test_two_factor_enrolment_and_activation_are_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    ctx, _, _ = await _enrolled_admin(iam_service, auth_service)

    actions = await _actions(audit_repo, ctx.tenant_id)
    assert AuditAction.TWO_FACTOR_ENROLLED in actions
    assert AuditAction.TWO_FACTOR_ACTIVATED in actions


async def test_the_secret_is_never_written_to_the_audit_trail(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    """The trail records *that* the factor changed, never the credential itself."""
    ctx, secret, backup_codes = await _enrolled_admin(iam_service, auth_service)

    entries = await audit_repo.list(ctx.tenant_id, limit=200)
    blob = "".join(str(e.context) for e in entries)
    assert secret not in blob
    for code in backup_codes:
        assert code not in blob


async def test_a_wrong_code_at_step_up_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    """A burst of these on one account is the signature of somebody who already has
    the password and is guessing the six digits."""
    ctx, _, _ = await _enrolled_admin(iam_service, auth_service)

    result = await auth_service.verify_step_up(ctx, ADMIN_PASSWORD, "000000")

    assert result is StepUpResult.BAD_CODE
    assert AuditAction.TWO_FACTOR_FAILED in await _actions(audit_repo, ctx.tenant_id)


async def test_spending_a_backup_code_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    """Its own action because it usually means the authenticator is gone — and
    because ten of them is a finite supply somebody should be watching."""
    ctx, _, backup_codes = await _enrolled_admin(iam_service, auth_service)

    result = await auth_service.verify_step_up(ctx, ADMIN_PASSWORD, backup_codes[0])

    assert result is StepUpResult.OK
    assert AuditAction.TWO_FACTOR_BACKUP_CODE_USED in await _actions(audit_repo, ctx.tenant_id)


async def test_disabling_ones_own_two_factor_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    ctx, secret, _ = await _enrolled_admin(iam_service, auth_service)

    await auth_service.disable_two_factor(ctx, ADMIN_PASSWORD, _totp_now(secret, skew_seconds=30))

    assert AuditAction.TWO_FACTOR_DISABLED in await _actions(audit_repo, ctx.tenant_id)


async def test_an_admin_resetting_someone_elses_two_factor_is_persisted(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    """Separate from DISABLED for the reason PASSWORD_RESET is separate from
    PASSWORD_CHANGED: one person lowering another's defences is a privileged act and
    must be answerable on its own."""
    ctx = await _admin_ctx(iam_service, auth_service)
    staff = await iam_service.create_user(
        CreateUserInput(email=STAFF_EMAIL, password=STAFF_PASSWORD, full_name="Nhân Viên"), ctx
    )

    await iam_service.reset_two_factor(staff.id, ctx)

    entries = await audit_repo.list(ctx.tenant_id, limit=200)
    reset = [e for e in entries if e.action is AuditAction.TWO_FACTOR_RESET]
    assert len(reset) == 1
    # The subject is the user who lost their factor; the actor is the admin.
    assert reset[0].target_id == str(staff.id)
    assert reset[0].actor_user_id == ctx.user_id


# --- the trail's own properties ---------------------------------------------


async def test_entries_are_scoped_to_their_tenant(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    tenant_a = await _bootstrap(iam_service)
    await auth_service.login(LoginInput(email=ADMIN_EMAIL, password=ADMIN_PASSWORD))
    other = await iam_service.bootstrap_tenant(
        BootstrapTenantInput(
            tenant_name="Nhà thuốc Khác",
            branch_code="HQ",
            branch_name="CN",
            admin_email="admin@khac.vn",
            admin_full_name="Khác",
            admin_password=ADMIN_PASSWORD,
        )
    )
    await auth_service.login(LoginInput(email="admin@khac.vn", password=ADMIN_PASSWORD))

    assert all(e.tenant_id == tenant_a for e in await audit_repo.list(tenant_a))
    assert len(await audit_repo.list(other.tenant_id)) == 1


async def test_repository_exposes_no_way_to_change_history() -> None:
    """Append-only enforced structurally, not by convention."""
    for forbidden in ("update", "delete", "remove", "save", "merge"):
        assert not hasattr(SqlAlchemyAuditLogRepository, forbidden)


async def test_listing_is_newest_first_and_pages(
    session_factory: async_sessionmaker[AsyncSession],
    audit_repo: SqlAlchemyAuditLogRepository,
) -> None:
    tenant_id = uuid4()
    base = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        for minute in range(5):
            await repo.add(
                AuditEntry(
                    tenant_id=tenant_id,
                    action=AuditAction.LOGIN_SUCCESS,
                    target_type="user",
                    occurred_at=base + timedelta(minutes=minute),
                )
            )
        await session.commit()

    newest = await audit_repo.list(tenant_id, limit=2)
    assert [e.occurred_at for e in newest] == [
        base + timedelta(minutes=4),
        base + timedelta(minutes=3),
    ]
    assert len(await audit_repo.list(tenant_id, limit=2, offset=4)) == 1
    assert await audit_repo.count(tenant_id) == 5


async def test_filters_narrow_by_time_actor_and_action(
    session_factory: async_sessionmaker[AsyncSession],
    audit_repo: SqlAlchemyAuditLogRepository,
) -> None:
    tenant_id, actor = uuid4(), uuid4()
    base = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)
    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        await repo.add(
            AuditEntry(
                tenant_id=tenant_id,
                action=AuditAction.LOGIN_SUCCESS,
                target_type="user",
                actor_user_id=actor,
                occurred_at=base,
            )
        )
        await repo.add(
            AuditEntry(
                tenant_id=tenant_id,
                action=AuditAction.ROLE_GRANTED,
                target_type="user_role",
                actor_user_id=uuid4(),
                occurred_at=base + timedelta(hours=2),
            )
        )
        await session.commit()

    assert len(await audit_repo.list(tenant_id, actor_user_id=actor)) == 1
    assert len(await audit_repo.list(tenant_id, action=AuditAction.ROLE_GRANTED)) == 1
    assert len(await audit_repo.list(tenant_id, occurred_to=base + timedelta(hours=1))) == 1
    assert len(await audit_repo.list(tenant_id, occurred_from=base + timedelta(hours=1))) == 1
    assert await audit_repo.count(tenant_id, action=AuditAction.LOGIN_SUCCESS) == 1


async def test_context_never_carries_a_password_or_token(
    iam_service: IamService, auth_service: AuthService, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    """Metadata only — the trail must not become a second store of the secrets and
    personal data it exists to protect (NĐ 356/2025 Điều 4.2)."""
    tenant_id = await _bootstrap(iam_service)
    session = await auth_service.login(
        LoginInput(email=ADMIN_EMAIL, password=ADMIN_PASSWORD, client_ip="203.0.113.9")
    )
    with pytest.raises(UnauthenticatedError):
        await auth_service.login(LoginInput(email=ADMIN_EMAIL, password="SaiMatKhau123"))

    for entry in await audit_repo.list(tenant_id):
        blob = repr(entry.context)
        assert ADMIN_PASSWORD not in blob
        assert "SaiMatKhau123" not in blob
        assert session.refresh_token not in blob
        assert session.access_token not in blob
        assert set(entry.context) <= {"client_ip", "branch_id"}
