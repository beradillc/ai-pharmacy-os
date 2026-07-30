from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from pharmacy_os.modules.catalog.domain import ActiveIngredient
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyActiveIngredientRepository
from pharmacy_os.modules.crm.application import (
    AddAllergyInput,
    AddConditionInput,
    CreateCustomerInput,
    CrmService,
    MedicationHistoryItemInput,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.domain import (
    AllergySeverity,
    ConsentPurpose,
    MedicationHistorySource,
)


async def _grant_health_consent(
    service: CrmService, customer_id: UUID, ctx: RequestContext
) -> None:
    """Health data cannot be recorded without consent (Luật 91/2025 Điều 26.1)."""
    await service.record_consent(
        customer_id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=True, terms_version="v1"),
        ctx,
    )


async def _seed_ingredient(
    session_factory: async_sessionmaker[AsyncSession], name: str = "Penicillin"
) -> ActiveIngredient:
    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        ingredient = ActiveIngredient(name=name)
        await repo.add(ingredient)
        await session.commit()
    return ingredient


async def test_create_and_get_customer(crm_service: CrmService, ctx: RequestContext) -> None:
    created = await crm_service.create_customer(
        CreateCustomerInput(full_name="Nguyễn Văn A", phone="0900000000"), ctx
    )
    assert created.allergies == []

    fetched = await crm_service.get_customer(created.id, ctx)
    assert fetched.full_name == "Nguyễn Văn A"
    # Đổi có chủ ý 31/07: mọi đường đọc trả số ĐÃ CHE. Số đầy đủ chỉ ra qua
    # `reveal_phone()` (quyền `crm.pii.reveal`, cấp chuỗi, có ghi vết).
    assert fetched.phone == "*000"


async def test_tenant_isolation(crm_service: CrmService, ctx: RequestContext) -> None:
    created = await crm_service.create_customer(CreateCustomerInput(full_name="X"), ctx)
    other = RequestContext(
        tenant_id=uuid4(),
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=ctx.permissions,
    )
    with pytest.raises(NotFoundError):
        await crm_service.get_customer(created.id, other)


async def test_permission_enforced(crm_service: CrmService, ctx: RequestContext) -> None:
    no_perm = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(),
    )
    with pytest.raises(PermissionDeniedError):
        await crm_service.create_customer(CreateCustomerInput(full_name="Y"), no_perm)


async def test_get_unknown_customer_404(crm_service: CrmService, ctx: RequestContext) -> None:
    with pytest.raises(NotFoundError):
        await crm_service.get_customer(uuid4(), ctx)


async def test_add_allergy_round_trips(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _seed_ingredient(session_factory)
    created = await crm_service.create_customer(CreateCustomerInput(full_name="Z"), ctx)
    await _grant_health_consent(crm_service, created.id, ctx)

    updated = await crm_service.add_allergy(
        created.id,
        AddAllergyInput(
            ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE, note="Sốc phản vệ"
        ),
        ctx,
    )
    assert len(updated.allergies) == 1
    assert updated.allergies[0].ingredient_id == ingredient.id
    assert updated.allergies[0].severity == "SEVERE"

    fetched = await crm_service.get_customer(created.id, ctx)
    assert len(fetched.allergies) == 1
    assert fetched.allergies[0].note == "Sốc phản vệ"


async def test_duplicate_allergy_rejected(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _seed_ingredient(session_factory)
    created = await crm_service.create_customer(CreateCustomerInput(full_name="W"), ctx)
    await _grant_health_consent(crm_service, created.id, ctx)
    await crm_service.add_allergy(
        created.id, AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD), ctx
    )
    with pytest.raises(ValidationError):
        await crm_service.add_allergy(
            created.id,
            AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE),
            ctx,
        )


async def test_add_allergy_unknown_customer_404(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _seed_ingredient(session_factory)
    with pytest.raises(NotFoundError):
        await crm_service.add_allergy(
            uuid4(),
            AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
            ctx,
        )


async def test_add_allergy_unknown_ingredient_404_not_500(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """FK violation (unknown ingredient_id) must surface as 404, not a raw
    IntegrityError/500 — see CrmService.add_allergy."""
    created = await crm_service.create_customer(CreateCustomerInput(full_name="T"), ctx)
    await _grant_health_consent(crm_service, created.id, ctx)
    with pytest.raises(NotFoundError):
        await crm_service.add_allergy(
            created.id,
            AddAllergyInput(ingredient_id=uuid4(), severity=AllergySeverity.MILD),
            ctx,
        )


async def test_add_condition_round_trips_and_rejects_duplicate(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    created = await crm_service.create_customer(CreateCustomerInput(full_name="V"), ctx)
    await _grant_health_consent(crm_service, created.id, ctx)
    updated = await crm_service.add_condition(
        created.id, AddConditionInput(condition_code="E11", note="Đái tháo đường type 2"), ctx
    )
    assert updated.conditions[0].condition_code == "E11"

    with pytest.raises(ValidationError):
        await crm_service.add_condition(created.id, AddConditionInput(condition_code="E11"), ctx)


async def test_list_customers_newest_first_not_alphabetical(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """🔴 Test này TỪNG khẳng định thứ tự bảng chữ cái. Nó đổi vì hợp đồng đổi.

    Chain quyết 2026-07-28: mã hoá ``full_name`` (migration ``0035``) và **chấp nhận bỏ**
    sắp xếp theo tên. Ciphertext sắp ngẫu nhiên, và blind index không cứu được —
    fingerprint giữ *đẳng thức*, không giữ *thứ tự*.

    Sửa test cho khớp quyết định, **không** nới quyết định cho khớp test. Khẳng định ở
    đây là thứ tự **mới nhất trước**, thứ tự duy nhất còn đúng ở tầng CSDL.
    """
    for name in ("Bình", "An", "Cường", "Dũng", "Em"):
        await crm_service.create_customer(CreateCustomerInput(full_name=name), ctx)

    # 🔴 KHÔNG khẳng định một thứ tự cứng ở đây. Bản đầu của test này làm vậy và
    # **đỏ vì lý do sai**: `created_at` do CSDL đặt bằng `now()`, mà cả năm dòng được
    # tạo trong cùng một giây nên chúng BẰNG NHAU — thứ tự thật do `id` (UUID ngẫu
    # nhiên) quyết định. Một test khẳng định thứ tự cứng ở đó là test tung đồng xu.
    #
    # Tính chất thật sự cần, và cũng là thứ phân trang dựa vào: **thứ tự TOÀN PHẦN và
    # ỔN ĐỊNH**. `ORDER BY created_at DESC, id` cho đúng điều đó kể cả khi mọi
    # `created_at` bằng nhau, vì `id` là duy nhất.
    first_call = await crm_service.list_customers(ctx)
    second_call = await crm_service.list_customers(ctx)

    assert [c.id for c in first_call] == [c.id for c in second_call], "thứ tự không ổn định"

    # Phân trang không được lặp hay bỏ sót dòng nào — hệ quả trực tiếp của thứ tự toàn phần.
    page_1 = await crm_service.list_customers(ctx, limit=2, offset=0)
    page_2 = await crm_service.list_customers(ctx, limit=2, offset=2)
    page_3 = await crm_service.list_customers(ctx, limit=2, offset=4)
    paged = [c.id for c in (*page_1, *page_2, *page_3)]

    assert len(paged) == 5
    assert len(set(paged)) == 5, "có dòng xuất hiện ở hai trang"
    assert paged == [c.id for c in first_call]


async def test_non_positive_weight_rejected(crm_service: CrmService, ctx: RequestContext) -> None:
    with pytest.raises(ValidationError):
        await crm_service.create_customer(
            CreateCustomerInput(full_name="U", weight_kg=Decimal("0")), ctx
        )


# --- medication history from events (system reaction) ------------------------


def _items() -> list[MedicationHistoryItemInput]:
    return [
        MedicationHistoryItemInput(drug_id=uuid4(), quantity=Decimal("2")),
        MedicationHistoryItemInput(drug_id=uuid4(), quantity=Decimal("1")),
    ]


async def test_record_medication_history_records_when_consented(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    created = await crm_service.create_customer(CreateCustomerInput(full_name="Hà"), ctx)
    await _grant_health_consent(crm_service, created.id, ctx)
    ref = uuid4()

    n = await crm_service.record_medication_history(
        created.id, _items(), MedicationHistorySource.SALE, ref, datetime.now(UTC), ctx
    )
    assert n == 2

    fetched = await crm_service.get_customer(created.id, ctx)
    assert len(fetched.history) == 2
    assert {h.ref_id for h in fetched.history} == {ref}
    assert all(h.source == MedicationHistorySource.SALE.value for h in fetched.history)

    # One machine-write audit row per call (not per drug), under its own action.
    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(
            ctx.tenant_id, action=AuditAction.CUSTOMER_MEDICATION_HISTORY_RECORDED
        )
        matching = [e for e in entries if e.target_id == str(created.id)]
        assert len(matching) == 1


async def test_record_medication_history_skips_without_consent(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """No HEALTH consent → nothing recorded, no error (Luật 91 Điều 26.1)."""
    created = await crm_service.create_customer(CreateCustomerInput(full_name="Nam"), ctx)

    n = await crm_service.record_medication_history(
        created.id, _items(), MedicationHistorySource.SALE, uuid4(), datetime.now(UTC), ctx
    )
    assert n == 0
    fetched = await crm_service.get_customer(created.id, ctx)
    assert fetched.history == []


async def test_record_medication_history_idempotent_on_ref(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    created = await crm_service.create_customer(CreateCustomerInput(full_name="Lan"), ctx)
    await _grant_health_consent(crm_service, created.id, ctx)
    ref = uuid4()
    items = _items()

    first = await crm_service.record_medication_history(
        created.id, items, MedicationHistorySource.SALE, ref, datetime.now(UTC), ctx
    )
    second = await crm_service.record_medication_history(
        created.id, items, MedicationHistorySource.SALE, ref, datetime.now(UTC), ctx
    )
    assert first == 2
    assert second == 0  # same ref → not folded in twice

    fetched = await crm_service.get_customer(created.id, ctx)
    assert len(fetched.history) == 2  # not 4


async def test_record_medication_history_unknown_customer_404(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await crm_service.record_medication_history(
            uuid4(), _items(), MedicationHistorySource.SALE, uuid4(), datetime.now(UTC), ctx
        )


# --- B-06: số CCCD phải mã hoá, và tên cột không được nói dối -----------------


async def test_national_id_is_stored_as_ciphertext_not_plaintext(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Kiểm toán B-06 chứng minh lỗi bằng cách đọc THẲNG CSDL, nên test cũng vậy —
    đi qua service rồi tự tin là đã mã hoá thì chỉ đang kiểm chính niềm tin đó.

    Test chạy trên SQLite với mã hoá TẮT, nên nó không khẳng định được "đã thành
    ciphertext" — khẳng định được là **giá trị đi trọn vòng qua đúng tên cột mới**.
    Bằng chứng ciphertext thật nằm ở lần chạy trên Postgres có bật khoá, ghi trong
    PROJECT_STATE.
    """
    created = await crm_service.create_customer(
        CreateCustomerInput(full_name="Người Có CCCD", national_id="079200001234"), ctx
    )

    fetched = await crm_service.get_customer(created.id, ctx)

    assert fetched.national_id == "079200001234"


async def test_anonymise_clears_the_national_id(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """Xoá theo yêu cầu (Luật 91/2025) phải cuốn theo cả số định danh — nếu không thì
    "đã xoá" chỉ đúng với những trường ai đó nhớ ra."""
    created = await crm_service.create_customer(
        CreateCustomerInput(full_name="Người Yêu Cầu Xoá", national_id="079200005678"), ctx
    )

    anonymised = await crm_service.anonymise_customer(created.id, ctx)

    assert anonymised.national_id is None
