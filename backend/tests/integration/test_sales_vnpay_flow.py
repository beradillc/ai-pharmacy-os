"""VNPAY payment-gateway flow (Sprint 8 mục 4/4): initiate → webhook confirm.

Uses a fake :class:`PaymentGateway` (no real plugin package, no network) wired
through the same :class:`HookRegistry` the composition root uses in production —
what these tests pin is the ``sales`` orchestration around the gateway contract,
not VNPAY's own HMAC (that lives in the ``payment_vnpay`` package and is verified
against the real sandbox separately, see PROJECT_STATE).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import ConflictError, ValidationError
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.core.plugins import (
    CORE_PLUGIN_API_VERSION,
    HookRegistry,
    PaymentCallbackError,
    PaymentGateway,
    PluginContext,
)
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    SaleLineInput,
    SalesService,
    VnpayConfirmOutcome,
)
from pharmacy_os.modules.sales.domain import SaleCompleted, SaleStatus
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository


class _FakeVnpayGateway:
    """Stands in for the real ``payment_vnpay`` plugin: no network, deterministic.

    ``verify_callback`` treats ``payload["sig"] == "valid"`` as a passing signature
    check and returns ``payload["vnp_TxnRef"]`` — mirroring the real contract's
    split (signature-only here; response-code interpretation stays in ``sales``).
    """

    key = "fake_vnpay"
    version = "0.0.0"
    api_version = CORE_PLUGIN_API_VERSION

    def setup(self, ctx: PluginContext) -> None: ...

    def teardown(self) -> None: ...

    async def create_charge(self, order_id: str, amount: int, method: str) -> dict[str, Any]:
        return {"payment_url": f"https://sandbox.example/pay?ref={order_id}&amount={amount}"}

    async def verify_callback(self, payload: dict[str, Any]) -> str:
        if payload.get("sig") != "valid":
            raise PaymentCallbackError("chữ ký không hợp lệ")
        return str(payload["vnp_TxnRef"])


@pytest.fixture
def hook_registry() -> HookRegistry:
    registry = HookRegistry()
    registry.register_provider(PaymentGateway, _FakeVnpayGateway())
    return registry


@pytest.fixture
def vnpay_sales_service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    hook_registry: HookRegistry,
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        audit=AuditLogger(session_factory),
        hook_registry=hook_registry,
    )


def _sale(client_uuid: str = "vnp-1") -> CreateSaleInput:
    return CreateSaleInput(
        client_uuid=client_uuid,
        lines=[SaleLineInput(drug_id=uuid4(), quantity=Decimal("2"), unit_price=Decimal("10000"))],
    )


def _ipn(
    order_id: object, *, amount_cents: int = 2_000_000, response_code: str = "00"
) -> dict[str, str]:
    return {
        "sig": "valid",
        "vnp_TxnRef": str(order_id),
        "vnp_ResponseCode": response_code,
        "vnp_TransactionNo": "vnpay-txn-1",
        "vnp_Amount": str(amount_cents),
    }


async def test_initiate_persists_draft_and_returns_payment_url(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await vnpay_sales_service.initiate_vnpay_payment(_sale(), ctx)
    assert "ref=" in out.payment_url

    fetched = await vnpay_sales_service.get_sale(out.order_id, ctx)
    assert fetched.status == SaleStatus.DRAFT.value


async def test_initiate_without_gateway_configured_is_rejected(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    service = SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        hook_registry=HookRegistry(),  # nothing registered
    )
    with pytest.raises(ValidationError):
        await service.initiate_vnpay_payment(_sale(), ctx)


async def test_confirm_completes_order_and_emits_sale_completed(
    vnpay_sales_service: SalesService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    seen: list[SaleCompleted] = []

    async def record(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        seen.append(event)

    event_bus.subscribe(SaleCompleted, record)

    out = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-2"), ctx)
    outcome = await vnpay_sales_service.confirm_vnpay_callback(_ipn(out.order_id))

    assert outcome is VnpayConfirmOutcome.CONFIRMED
    fetched = await vnpay_sales_service.get_sale(out.order_id, ctx)
    assert fetched.status == SaleStatus.COMPLETED.value
    assert fetched.paid_total == Decimal("20000.00")
    assert len(seen) == 1


async def test_duplicate_ipn_is_idempotent(
    vnpay_sales_service: SalesService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    seen: list[SaleCompleted] = []

    async def record(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        seen.append(event)

    event_bus.subscribe(SaleCompleted, record)

    out = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-3"), ctx)
    first = await vnpay_sales_service.confirm_vnpay_callback(_ipn(out.order_id))
    second = await vnpay_sales_service.confirm_vnpay_callback(_ipn(out.order_id))

    assert first is VnpayConfirmOutcome.CONFIRMED
    assert second is VnpayConfirmOutcome.ALREADY_CONFIRMED
    assert len(seen) == 1  # not dispensed twice

    fetched = await vnpay_sales_service.get_sale(out.order_id, ctx)
    assert fetched.paid_total == Decimal("20000.00")  # not doubled


async def test_bad_signature_leaves_order_untouched(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-4"), ctx)
    payload = _ipn(out.order_id)
    payload["sig"] = "forged"

    outcome = await vnpay_sales_service.confirm_vnpay_callback(payload)

    assert outcome is VnpayConfirmOutcome.INVALID_SIGNATURE
    fetched = await vnpay_sales_service.get_sale(out.order_id, ctx)
    assert fetched.status == SaleStatus.DRAFT.value


async def test_amount_mismatch_is_rejected_even_with_valid_signature(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-5"), ctx)

    outcome = await vnpay_sales_service.confirm_vnpay_callback(_ipn(out.order_id, amount_cents=1))

    assert outcome is VnpayConfirmOutcome.AMOUNT_MISMATCH
    fetched = await vnpay_sales_service.get_sale(out.order_id, ctx)
    assert fetched.status == SaleStatus.DRAFT.value


async def test_non_numeric_amount_is_rejected_not_500(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    """A signature only proves the message came from the gateway, not that its
    fields parse. Must degrade to AMOUNT_MISMATCH, never raise past this call."""
    out = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-5b"), ctx)
    payload = _ipn(out.order_id)
    payload["vnp_Amount"] = "not-a-number"

    outcome = await vnpay_sales_service.confirm_vnpay_callback(payload)

    assert outcome is VnpayConfirmOutcome.AMOUNT_MISMATCH
    fetched = await vnpay_sales_service.get_sale(out.order_id, ctx)
    assert fetched.status == SaleStatus.DRAFT.value


async def test_gateway_failure_cancels_the_pending_order(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-6"), ctx)

    outcome = await vnpay_sales_service.confirm_vnpay_callback(
        _ipn(out.order_id, response_code="24")  # VNPAY: khách huỷ giao dịch
    )

    assert outcome is VnpayConfirmOutcome.CANCELLED_RECORDED
    fetched = await vnpay_sales_service.get_sale(out.order_id, ctx)
    assert fetched.status == SaleStatus.CANCELLED.value


async def test_callback_for_unknown_order_is_rejected_safely(
    vnpay_sales_service: SalesService,
) -> None:
    outcome = await vnpay_sales_service.confirm_vnpay_callback(_ipn(uuid4()))
    assert outcome is VnpayConfirmOutcome.ORDER_NOT_FOUND


async def test_reinitiate_on_existing_draft_reuses_the_same_order(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    first = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-7"), ctx)
    second = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-7"), ctx)
    assert first.order_id == second.order_id


async def test_reinitiate_on_completed_order_is_rejected(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    out = await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-8"), ctx)
    await vnpay_sales_service.confirm_vnpay_callback(_ipn(out.order_id))

    with pytest.raises(ConflictError):
        await vnpay_sales_service.initiate_vnpay_payment(_sale("vnp-8"), ctx)


async def test_initiate_rejects_client_supplied_payments(
    vnpay_sales_service: SalesService, ctx: RequestContext
) -> None:
    from pharmacy_os.modules.sales.application import PaymentInput
    from pharmacy_os.modules.sales.domain import PaymentMethod

    data = _sale("vnp-9")
    data.payments = [PaymentInput(method=PaymentMethod.CASH, amount=Decimal("20000"))]
    with pytest.raises(ValidationError):
        await vnpay_sales_service.initiate_vnpay_payment(data, ctx)
