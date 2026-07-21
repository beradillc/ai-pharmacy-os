"""Sales use-cases: completing an (offline-originated) sale, idempotently.

The service depends only on ports; the concrete repository and unit of work are
injected as factories at composition time (see the module ``register``).

Offline-first idempotency: a sale carries a client-generated ``client_uuid``. If
a sync retries a sale already recorded, :meth:`complete_sale` returns the stored
result **without** re-processing — so no duplicate order and no duplicate
``SaleCompleted`` (which would otherwise double-dispense stock).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.sales.application.dto import CreateSaleInput, SaleOutput
from pharmacy_os.modules.sales.domain import (
    Payment,
    SaleCompleted,
    SaleLine,
    SalesError,
    SalesOrder,
    SoldItem,
)
from pharmacy_os.modules.sales.domain.ports import SalesRepository
from pharmacy_os.shared.value_objects import Money

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], SalesRepository]


class SalesService:
    def __init__(self, uow_factory: UowFactory, repo_factory: RepoFactory) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory

    async def complete_sale(self, data: CreateSaleInput, ctx: RequestContext) -> SaleOutput:
        """Record and finalise a sale for the caller's tenant/branch.

        Idempotent on ``data.client_uuid``: a repeated sync returns the existing
        order untouched. On a fresh sale, runs the domain rules (Rx + full
        payment) and emits :class:`SaleCompleted` after commit. Raises
        :class:`ValidationError` on a domain rule violation.
        """
        require_permission(ctx, "sales.create")

        order = SalesOrder(
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            client_uuid=data.client_uuid,
            currency=data.currency,
            prescription_ref=data.prescription_ref,
        )
        try:
            for line in data.lines:
                order.add_line(
                    SaleLine(
                        drug_id=line.drug_id,
                        quantity=line.quantity,
                        unit_price=Money(line.unit_price, data.currency),
                        requires_prescription=line.requires_prescription,
                    )
                )
            for payment in data.payments:
                order.add_payment(
                    Payment(method=payment.method, amount=Money(payment.amount, data.currency))
                )
            order.complete()
        except SalesError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            existing = await repo.by_client_uuid(data.client_uuid)
            if existing is not None:
                return SaleOutput.of(existing)  # idempotent replay — do not re-emit

            await repo.add(order)
            uow.collect(
                SaleCompleted(
                    tenant_id=ctx.tenant_id,
                    order_id=order.id,
                    branch_id=ctx.branch_id,
                    client_uuid=order.client_uuid,
                    items=tuple(
                        SoldItem(drug_id=line.drug_id, quantity=line.quantity)
                        for line in order.lines
                    ),
                )
            )
            try:
                await uow.commit()
            except Exception as exc:  # unique(tenant, client_uuid) race → treat as replay
                await uow.rollback()
                replay = await self._by_client_uuid(data.client_uuid, ctx)
                if replay is not None:
                    return replay
                raise ConflictError("Không thể ghi nhận đơn bán") from exc

        return SaleOutput.of(order)

    async def get_sale(self, order_id: UUID, ctx: RequestContext) -> SaleOutput:
        """Return one sale by id, scoped to the tenant; 404 if not found."""
        require_permission(ctx, "sales.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            order = await repo.get(order_id)
        if order is None:
            raise NotFoundError(f"Không tìm thấy đơn bán {order_id}")
        return SaleOutput.of(order)

    async def _by_client_uuid(self, client_uuid: str, ctx: RequestContext) -> SaleOutput | None:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            order = await repo.by_client_uuid(client_uuid)
        return SaleOutput.of(order) if order is not None else None
