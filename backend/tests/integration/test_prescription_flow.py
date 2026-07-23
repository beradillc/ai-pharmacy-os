from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.modules.prescription.application import (
    CreatePrescriptionInput,
    PrescriptionItemInput,
    PrescriptionService,
)
from pharmacy_os.modules.prescription.domain import (
    PrescriptionDispensed,
    PrescriptionRejected,
    PrescriptionStatus,
    PrescriptionValidated,
)


def _intake(**kw: object) -> CreatePrescriptionInput:
    kw.setdefault(
        "items",
        [
            PrescriptionItemInput(
                drug_id=uuid4(),
                quantity=Decimal("10"),
                dose="1 viên",
                frequency="2 lần/ngày",
                duration="5 ngày",
            )
        ],
    )
    return CreatePrescriptionInput(  # type: ignore[arg-type]
        customer_id=uuid4(),
        doctor_name="BS. Trần Thị B",
        **kw,
    )


async def test_create_prescription_persists_and_reads_back(
    prescription_service: PrescriptionService, ctx: RequestContext
) -> None:
    out = await prescription_service.create_prescription(_intake(), ctx)
    assert out.status == PrescriptionStatus.DRAFT.value
    assert len(out.items) == 1

    fetched = await prescription_service.get_prescription(out.id, ctx)
    assert fetched.id == out.id
    assert fetched.doctor_name == "BS. Trần Thị B"


async def test_validate_then_dispense_flow(
    prescription_service: PrescriptionService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    validated_events: list[PrescriptionValidated] = []
    dispensed_events: list[PrescriptionDispensed] = []

    async def on_validated(event: DomainEvent) -> None:
        assert isinstance(event, PrescriptionValidated)
        validated_events.append(event)

    async def on_dispensed(event: DomainEvent) -> None:
        assert isinstance(event, PrescriptionDispensed)
        dispensed_events.append(event)

    event_bus.subscribe(PrescriptionValidated, on_validated)
    event_bus.subscribe(PrescriptionDispensed, on_dispensed)

    created = await prescription_service.create_prescription(_intake(), ctx)
    validated = await prescription_service.validate_prescription(created.id, ctx)
    assert validated.status == PrescriptionStatus.VALIDATED.value
    assert validated.validated_by == ctx.user_id

    dispensed = await prescription_service.dispense_prescription(created.id, ctx)
    assert dispensed.status == PrescriptionStatus.DISPENSED.value

    assert len(validated_events) == 1
    assert validated_events[0].prescription_id == created.id
    assert len(dispensed_events) == 1
    assert dispensed_events[0].prescription_id == created.id


async def test_reject_from_draft(
    prescription_service: PrescriptionService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    rejected_events: list[PrescriptionRejected] = []

    async def on_rejected(event: DomainEvent) -> None:
        assert isinstance(event, PrescriptionRejected)
        rejected_events.append(event)

    event_bus.subscribe(PrescriptionRejected, on_rejected)

    created = await prescription_service.create_prescription(_intake(), ctx)
    out = await prescription_service.reject_prescription(created.id, "Chữ ký không rõ", ctx)

    assert out.status == PrescriptionStatus.REJECTED.value
    assert out.rejection_reason == "Chữ ký không rõ"
    assert len(rejected_events) == 1


async def test_dispense_without_validation_rejected(
    prescription_service: PrescriptionService, ctx: RequestContext
) -> None:
    created = await prescription_service.create_prescription(_intake(), ctx)
    with pytest.raises(ValidationError):
        await prescription_service.dispense_prescription(created.id, ctx)


async def test_validate_empty_prescription_rejected(
    prescription_service: PrescriptionService, ctx: RequestContext
) -> None:
    created = await prescription_service.create_prescription(_intake(items=[]), ctx)
    with pytest.raises(ValidationError):
        await prescription_service.validate_prescription(created.id, ctx)


async def test_get_unknown_prescription_raises(
    prescription_service: PrescriptionService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await prescription_service.get_prescription(uuid4(), ctx)


# --- audit trail: the fact an inspection asks about first --------------------


async def test_create_validate_dispense_each_leave_an_audit_row(
    prescription_service: PrescriptionService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call sites to be wired — reads the table back."""
    created = await prescription_service.create_prescription(_intake(), ctx)
    await prescription_service.validate_prescription(created.id, ctx)
    await prescription_service.dispense_prescription(created.id, ctx)

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        for action in (
            AuditAction.PRESCRIPTION_CREATED,
            AuditAction.PRESCRIPTION_APPROVED,
            AuditAction.PRESCRIPTION_DISPENSED,
        ):
            entries = await repo.list(ctx.tenant_id, action=action)
            matching = [e for e in entries if e.target_id == str(created.id)]
            assert len(matching) == 1, f"{action} không thấy trong audit_logs"
            assert matching[0].actor_user_id == ctx.user_id


async def test_reject_leaves_an_audit_row(
    prescription_service: PrescriptionService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    created = await prescription_service.create_prescription(_intake(), ctx)
    await prescription_service.reject_prescription(created.id, "Chữ ký không rõ", ctx)

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.PRESCRIPTION_REJECTED)
        matching = [e for e in entries if e.target_id == str(created.id)]
        assert len(matching) == 1
        # The rejection reason itself must not leak into the trail.
        assert "Chữ ký" not in str(matching[0].context)
