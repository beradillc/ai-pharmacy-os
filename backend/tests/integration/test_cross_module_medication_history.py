"""wire_medication_history: fold a named customer's dispensed drugs into CRM history.

Cross-module reaction declared at the composition root, separate from the warn-only
safety checks (this one writes to crm). Fires on ``SaleCompleted`` (reads the sale for
its customer_id — the event contract is unchanged) and ``PrescriptionDispensed`` (reads
the prescription). Consent-gated and idempotent, both enforced by the crm use-case.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.api.v1.cross_module import wire_medication_history
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus, InMemoryEventBus
from pharmacy_os.modules.crm.application import (
    CreateCustomerInput,
    CrmService,
    CustomerOutput,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.domain import ConsentPurpose
from pharmacy_os.modules.crm.infrastructure import CustomerMedicationHistoryORM
from pharmacy_os.modules.prescription.application import (
    CreatePrescriptionInput,
    PrescriptionItemInput,
    PrescriptionService,
)
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import PaymentMethod, SaleCompleted, SoldItem


@pytest.fixture
def medhist_container(
    event_bus: InMemoryEventBus,
    crm_service: CrmService,
    sales_service: SalesService,
    prescription_service: PrescriptionService,
) -> Container:
    container = Container()
    container.register_instance(EventBus, event_bus)  # type: ignore[type-abstract]
    container.register_instance(CrmService, crm_service)
    container.register_instance(SalesService, sales_service)
    container.register_instance(PrescriptionService, prescription_service)
    wire_medication_history(container)
    return container


async def _consenting_customer(crm_service: CrmService, ctx: RequestContext) -> CustomerOutput:
    customer = await crm_service.create_customer(CreateCustomerInput(full_name="KH Test"), ctx)
    await crm_service.record_consent(
        customer.id,
        RecordConsentInput(purpose=ConsentPurpose.HEALTH, granted=True, terms_version="v1"),
        ctx,
    )
    return customer


def _sale_input(customer_id: UUID, order_id: UUID, drug_ids: list[UUID]) -> CreateSaleInput:
    return CreateSaleInput(
        client_uuid=str(order_id),
        customer_id=customer_id,
        lines=[
            SaleLineInput(drug_id=d, quantity=Decimal("2"), unit_price=Decimal("1000"))
            for d in drug_ids
        ],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("2000") * len(drug_ids))],
    )


async def test_completed_sale_records_history_for_a_consenting_customer(
    medhist_container: Container,
    crm_service: CrmService,
    sales_service: SalesService,
    ctx: RequestContext,
) -> None:
    customer = await _consenting_customer(crm_service, ctx)
    drug_a, drug_b = uuid4(), uuid4()

    await sales_service.complete_sale(
        _sale_input(customer.id, uuid4(), [drug_a, drug_b]),
        ctx,
    )

    fetched = await crm_service.get_customer(customer.id, ctx)
    assert {h.drug_id for h in fetched.history} == {drug_a, drug_b}
    assert all(h.source == "SALE" for h in fetched.history)


async def _history_count(
    session_factory: async_sessionmaker[AsyncSession], customer_id: UUID
) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(func.count())
            .select_from(CustomerMedicationHistoryORM)
            .where(CustomerMedicationHistoryORM.customer_id == customer_id)
        )
        return int(result.scalar_one())


async def test_completed_sale_records_nothing_without_consent(
    medhist_container: Container,
    crm_service: CrmService,
    sales_service: SalesService,
    session_factory: async_sessionmaker[AsyncSession],
    ctx: RequestContext,
) -> None:
    customer = await crm_service.create_customer(CreateCustomerInput(full_name="Chưa đồng ý"), ctx)

    await sales_service.complete_sale(
        _sale_input(customer.id, uuid4(), [uuid4()]),
        ctx,
    )

    # Checked at the table, not via get_customer (which hides history without consent
    # anyway) — proves nothing was actually written.
    assert await _history_count(session_factory, customer.id) == 0


async def test_walk_in_sale_records_no_history(
    medhist_container: Container,
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    # A synthetic SaleCompleted whose order was never persisted → handler 404s and
    # skips. (A real walk-in sale simply has customer_id None; either way, no history.)
    await event_bus.publish(
        SaleCompleted(
            tenant_id=ctx.tenant_id,
            order_id=uuid4(),
            branch_id=ctx.branch_id,
            client_uuid=str(uuid4()),
            items=(SoldItem(drug_id=uuid4(), quantity=Decimal("1")),),
        )
    )  # must not raise


async def test_completed_sale_is_idempotent_on_replay(
    medhist_container: Container,
    event_bus: InMemoryEventBus,
    crm_service: CrmService,
    sales_service: SalesService,
    ctx: RequestContext,
) -> None:
    customer = await _consenting_customer(crm_service, ctx)
    drug = uuid4()
    order_id = uuid4()

    out = await sales_service.complete_sale(
        _sale_input(customer.id, order_id, [drug]),
        ctx,
    )
    # Re-publish the same SaleCompleted (as a duplicate delivery would) — the sale
    # exists, so the handler runs again, but the crm use-case skips the second fold.
    await event_bus.publish(
        SaleCompleted(
            tenant_id=ctx.tenant_id,
            order_id=out.id,
            branch_id=ctx.branch_id,
            client_uuid=out.client_uuid,
            items=(SoldItem(drug_id=drug, quantity=Decimal("2")),),
        )
    )

    fetched = await crm_service.get_customer(customer.id, ctx)
    assert len(fetched.history) == 1  # not 2


async def test_dispensed_prescription_records_history(
    medhist_container: Container,
    crm_service: CrmService,
    prescription_service: PrescriptionService,
    ctx: RequestContext,
) -> None:
    customer = await _consenting_customer(crm_service, ctx)
    drug = uuid4()

    rx = await prescription_service.create_prescription(
        CreatePrescriptionInput(
            customer_id=customer.id,
            doctor_name="BS. Test",
            items=[
                PrescriptionItemInput(
                    drug_id=drug, quantity=Decimal("3"), dose="1", frequency="1", duration="1"
                )
            ],
        ),
        ctx,
    )
    await prescription_service.validate_prescription(rx.id, ctx)
    await prescription_service.dispense_prescription(rx.id, ctx)

    fetched = await crm_service.get_customer(customer.id, ctx)
    assert len(fetched.history) == 1
    assert fetched.history[0].drug_id == drug
    assert fetched.history[0].source == "PRESCRIPTION"
    assert fetched.history[0].ref_id == rx.id
