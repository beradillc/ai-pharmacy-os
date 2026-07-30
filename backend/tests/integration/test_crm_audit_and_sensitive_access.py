"""Health-data access control and its audit trail, verified against the database.

Every test drives the real use-case and then reads ``audit_logs`` back — the point
is not to check that the service *calls* the logger, but that a row exists. A call
site removed by a future refactor fails here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import PermissionDeniedError, ValidationError
from pharmacy_os.modules.catalog.domain import ActiveIngredient
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyActiveIngredientRepository
from pharmacy_os.modules.crm.application import (
    AddAllergyInput,
    AddConditionInput,
    CreateCustomerInput,
    CrmService,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.domain import ANONYMISED_NAME, AllergySeverity, ConsentPurpose


@pytest.fixture
async def audit_repo(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[SqlAlchemyAuditLogRepository]:
    async with session_factory() as session:
        yield SqlAlchemyAuditLogRepository(session)


async def _ingredient(session_factory: async_sessionmaker[AsyncSession]) -> ActiveIngredient:
    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        ingredient = ActiveIngredient(name="Penicillin")
        await repo.add(ingredient)
        await session.commit()
    return ingredient


def _ctx_with(ctx: RequestContext, *permissions: str) -> RequestContext:
    return RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(permissions),
        client_ip="203.0.113.9",
    )


async def _consented_customer(
    crm_service: CrmService, ctx: RequestContext, name: str = "Nguyễn Văn A"
) -> UUID:
    out = await crm_service.create_customer(
        CreateCustomerInput(full_name=name, phone="0900000000"), ctx
    )
    await crm_service.record_consent(
        out.id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=True, terms_version="v1"),
        ctx,
    )
    return out.id


async def _actions(repo: SqlAlchemyAuditLogRepository, tenant_id: UUID) -> list[AuditAction]:
    return [e.action for e in await repo.list(tenant_id, limit=200)]


# --- consent decisions are recorded -----------------------------------------


async def test_granting_and_revoking_consent_are_both_audited(
    crm_service: CrmService, ctx: RequestContext, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.record_consent(
        customer_id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=False, terms_version="v1"),
        ctx,
    )

    actions = await _actions(audit_repo, ctx.tenant_id)
    assert actions.count(AuditAction.CONSENT_GRANTED) == 1
    assert actions.count(AuditAction.CONSENT_REVOKED) == 1

    granted = next(
        e for e in await audit_repo.list(ctx.tenant_id) if e.action is AuditAction.CONSENT_GRANTED
    )
    assert granted.target_type == "customer"
    assert granted.target_id == str(customer_id)
    assert granted.context["purpose"] == "HEALTH"
    assert granted.context["terms_version"] == "v1"


async def test_writing_health_data_is_audited(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)

    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE),
        ctx,
    )
    await crm_service.add_condition(customer_id, AddConditionInput(condition_code="E11"), ctx)

    writes = [
        e
        for e in await audit_repo.list(ctx.tenant_id)
        if e.action is AuditAction.CUSTOMER_SENSITIVE_WRITE
    ]
    assert {w.context["field"] for w in writes} == {"allergy", "condition"}


async def test_reading_a_file_with_health_data_is_audited(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )

    out = await crm_service.get_customer(customer_id, ctx)
    assert len(out.allergies) == 1

    reads = [
        e
        for e in await audit_repo.list(ctx.tenant_id)
        if e.action is AuditAction.CUSTOMER_SENSITIVE_READ
    ]
    assert len(reads) == 1
    assert reads[0].target_id == str(customer_id)
    assert reads[0].context["branch_id"] == str(ctx.branch_id)
    # The service-level fixture has no client IP; the API layer fills it, and the
    # key is simply absent rather than stored as a null (see AuditEntry.with_context).
    assert "client_ip" not in reads[0].context


# --- the split: crm.read sees the person, not the diagnoses -----------------


async def test_a_caller_without_sensitive_read_gets_the_basics_not_a_403(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A cashier attaching a customer to a sale is doing something legitimate."""
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )

    cashier = _ctx_with(ctx, "crm.read")
    out = await crm_service.get_customer(customer_id, cashier)

    assert out.full_name == "Nguyễn Văn A"
    # Thu ngân thấy TÊN và ba số cuối — đủ để đối chiếu đúng người ở quầy, không đủ để
    # chép số ra ngoài. Số đầy đủ đi qua `reveal_phone()` và để lại vết (31/07).
    assert out.phone == "*000"
    assert out.allergies == []
    assert out.conditions == []
    assert out.history == []


async def test_a_read_without_sensitive_access_is_not_audited_as_one(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Auditing a read that returned nothing sensitive would inflate the trail with
    events that never happened."""
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )

    await crm_service.get_customer(customer_id, _ctx_with(ctx, "crm.read"))

    assert AuditAction.CUSTOMER_SENSITIVE_READ not in await _actions(audit_repo, ctx.tenant_id)


async def test_writing_health_data_needs_the_sensitive_permission(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    cashier = _ctx_with(ctx, "crm.read", "crm.write", "crm.create")

    with pytest.raises(PermissionDeniedError):
        await crm_service.add_allergy(
            customer_id,
            AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
            cashier,
        )
    with pytest.raises(PermissionDeniedError):
        await crm_service.add_condition(
            customer_id, AddConditionInput(condition_code="E11"), cashier
        )


async def test_the_customer_list_never_carries_health_data(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Even for a pharmacist: a page of fifty files is not a lookup."""
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )

    listed = await crm_service.list_customers(ctx)
    assert listed and all(c.allergies == [] for c in listed)


# --- consent is a lawful basis, not just a checkbox -------------------------


async def test_permission_alone_does_not_open_a_file_without_consent(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Luật 91/2025 Điều 26.1 — no consent, no lawful basis, permission or not."""
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )

    await crm_service.record_consent(
        customer_id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=False, terms_version="v1"),
        ctx,
    )
    out = await crm_service.get_customer(customer_id, ctx)

    assert out.health_data_allowed is False
    assert out.allergies == []


async def test_writing_health_data_after_revocation_is_refused(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.record_consent(
        customer_id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=False, terms_version="v1"),
        ctx,
    )

    with pytest.raises(ValidationError, match="chưa đồng ý"):
        await crm_service.add_allergy(
            customer_id,
            AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
            ctx,
        )


# --- the automated safety check (duyệt Q3) ----------------------------------


async def test_the_safety_check_reads_allergies_without_the_sensitive_permission(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """An allergy warning must not stop firing for the staff least able to spot the
    problem unaided."""
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE),
        ctx,
    )

    cashier = _ctx_with(ctx, "crm.read")
    severities = await crm_service.allergy_severities_for_safety_check(customer_id, cashier)
    assert severities == {ingredient.id: "SEVERE"}


async def test_the_safety_check_is_audited_under_its_own_action(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Machine reads must stay distinguishable from a person opening the file."""
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )

    await crm_service.allergy_severities_for_safety_check(customer_id, ctx)

    actions = await _actions(audit_repo, ctx.tenant_id)
    assert actions.count(AuditAction.CUSTOMER_SENSITIVE_AUTO_CHECK) == 1
    assert AuditAction.CUSTOMER_SENSITIVE_READ not in actions


async def test_the_safety_check_returns_nothing_without_consent(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )
    await crm_service.record_consent(
        customer_id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=False, terms_version="v1"),
        ctx,
    )

    assert await crm_service.allergy_severities_for_safety_check(customer_id, ctx) == {}
    # Nothing was read, so nothing is claimed to have been.
    actions = await _actions(audit_repo, ctx.tenant_id)
    assert AuditAction.CUSTOMER_SENSITIVE_AUTO_CHECK not in actions


# --- the trail never becomes a second copy of the data ----------------------


async def test_audit_context_carries_no_health_values(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE, note="Sốc"),
        ctx,
    )
    await crm_service.add_condition(
        customer_id, AddConditionInput(condition_code="E11", note="Tiểu đường"), ctx
    )
    await crm_service.get_customer(customer_id, ctx)

    for entry in await audit_repo.list(ctx.tenant_id):
        blob = repr(entry.context)
        assert "Sốc" not in blob
        assert "Tiểu đường" not in blob
        assert "E11" not in blob
        assert str(ingredient.id) not in blob
        assert set(entry.context) <= {
            "client_ip",
            "branch_id",
            "field",
            "purpose",
            "terms_version",
        }


async def test_entries_are_scoped_to_the_acting_tenant(
    crm_service: CrmService, ctx: RequestContext, audit_repo: SqlAlchemyAuditLogRepository
) -> None:
    await _consented_customer(crm_service, ctx)
    assert await audit_repo.count(uuid4()) == 0
    assert await audit_repo.count(ctx.tenant_id) >= 1


# --- data-subject rights (Luật 91/2025 Điều 13-14) ---------------------------


async def test_export_returns_everything_with_a_provenance_line(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE),
        ctx,
    )

    export = await crm_service.export_customer_data(customer_id, ctx)

    assert export.customer.full_name == "Nguyễn Văn A"
    assert len(export.customer.allergies) == 1
    assert len(export.customer.consents) == 1
    assert export.exported_by == ctx.user_id
    assert export.exported_at.tzinfo is not None


async def test_export_is_audited_as_a_sensitive_read(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
) -> None:
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.export_customer_data(customer_id, ctx)

    reads = [
        e
        for e in await audit_repo.list(ctx.tenant_id)
        if e.action is AuditAction.CUSTOMER_SENSITIVE_READ
    ]
    assert len(reads) == 1
    assert reads[0].context["reason"] == "export"


async def test_export_still_works_after_consent_is_withdrawn(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The right of access does not depend on consent to processing — and the person
    who withdrew is exactly the one likely to ask what is still held."""
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
        ctx,
    )
    await crm_service.record_consent(
        customer_id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=False, terms_version="v1"),
        ctx,
    )

    export = await crm_service.export_customer_data(customer_id, ctx)
    assert len(export.customer.allergies) == 1


async def test_export_needs_the_sensitive_permission(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    customer_id = await _consented_customer(crm_service, ctx)
    with pytest.raises(PermissionDeniedError):
        await crm_service.export_customer_data(customer_id, _ctx_with(ctx, "crm.read"))


async def test_anonymise_strips_identity_and_health_data_in_the_database(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE),
        ctx,
    )
    await crm_service.add_condition(customer_id, AddConditionInput(condition_code="E11"), ctx)

    await crm_service.anonymise_customer(customer_id, ctx)

    # Read back through a fresh query: the aggregate in memory being clean proves
    # nothing about the rows, and the id-diff update path is insert-only by default.
    reloaded = await crm_service.get_customer(customer_id, ctx)
    assert reloaded.full_name == ANONYMISED_NAME
    assert reloaded.phone is None
    assert reloaded.allergies == []
    assert reloaded.conditions == []
    assert reloaded.anonymised_at is not None


async def test_anonymise_is_audited_and_idempotent(
    crm_service: CrmService,
    ctx: RequestContext,
    audit_repo: SqlAlchemyAuditLogRepository,
) -> None:
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.anonymise_customer(customer_id, ctx)
    await crm_service.anonymise_customer(customer_id, ctx)

    actions = await _actions(audit_repo, ctx.tenant_id)
    # Second call changed nothing, so it claims nothing happened.
    assert actions.count(AuditAction.CUSTOMER_ERASED) == 1


async def test_anonymise_needs_the_erase_permission(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """Irreversible, so it is kept away from branch staff."""
    customer_id = await _consented_customer(crm_service, ctx)
    weak = _ctx_with(ctx, "crm.read", "crm.sensitive.read", "crm.sensitive.write")
    with pytest.raises(PermissionDeniedError):
        await crm_service.anonymise_customer(customer_id, weak)


async def test_the_safety_check_finds_nothing_after_anonymisation(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _ingredient(session_factory)
    customer_id = await _consented_customer(crm_service, ctx)
    await crm_service.add_allergy(
        customer_id,
        AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE),
        ctx,
    )
    await crm_service.anonymise_customer(customer_id, ctx)

    assert await crm_service.allergy_severities_for_safety_check(customer_id, ctx) == {}
