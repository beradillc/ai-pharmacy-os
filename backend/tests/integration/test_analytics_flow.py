"""Analytics service flow: reorder run → list → materialize/dismiss → dashboard.

The cross-module sources/sink are faked (unit-of-analytics, not of the adapters —
those are covered by their own module tests); the suggestion repository is the real
SQLAlchemy one against the test DB, so the run/persist/regenerate cycle is exercised
end to end.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.analytics.application import AnalyticsService
from pharmacy_os.modules.analytics.domain import DrugSoldQty, SuggestionStatus
from pharmacy_os.modules.analytics.infrastructure.repository import (
    SqlAlchemyReorderSuggestionRepository,
)

_TENANT = uuid4()
_BRANCH = uuid4()


def _ctx(*perms: str) -> RequestContext:
    return RequestContext(
        tenant_id=_TENANT, branch_id=_BRANCH, user_id=uuid4(), permissions=frozenset(perms)
    )


class _FakeSales:
    def __init__(self, rows: list[DrugSoldQty]) -> None:
        self.rows = rows

    async def sold_quantity_by_drug(
        self, tenant_id: UUID, branch_id: UUID, *, date_from: date, date_to: date
    ) -> list[DrugSoldQty]:
        return self.rows


class _FakeStock:
    def __init__(self, on_hand: dict[UUID, Decimal], near_expiry: int = 0) -> None:
        self.on_hand = on_hand
        self.near_expiry = near_expiry

    async def on_hand_by_drug(self, tenant_id: UUID, branch_id: UUID) -> dict[UUID, Decimal]:
        return self.on_hand

    async def count_near_expiry(self, tenant_id: UUID, branch_id: UUID, *, within_days: int) -> int:
        return self.near_expiry


class _FakeSupplier:
    def __init__(self, mapping: dict[UUID, UUID]) -> None:
        self.mapping = mapping

    async def last_supplier_for_drug(self, tenant_id: UUID, drug_id: UUID) -> UUID | None:
        return self.mapping.get(drug_id)


class _FakeDraftPoCount:
    def __init__(self, count: int = 0) -> None:
        self.count = count

    async def count_draft_pos(self, tenant_id: UUID, branch_id: UUID) -> int:
        return self.count


class _FakeDraftPoSink:
    def __init__(self) -> None:
        self.created: list[tuple[UUID, UUID, Decimal]] = []

    async def create_draft_po(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        supplier_id: UUID,
        drug_id: UUID,
        quantity: Decimal,
    ) -> UUID:
        po_id = uuid4()
        self.created.append((supplier_id, drug_id, quantity))
        return po_id


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    *,
    sales: _FakeSales,
    stock: _FakeStock,
    supplier: _FakeSupplier | None = None,
    draft_count: _FakeDraftPoCount | None = None,
    sink: _FakeDraftPoSink | None = None,
) -> AnalyticsService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return AnalyticsService(
        uow_factory,
        lambda uow, c: SqlAlchemyReorderSuggestionRepository(uow.session, c),
        sales,
        stock,
        supplier or _FakeSupplier({}),
        draft_count or _FakeDraftPoCount(),
        sink or _FakeDraftPoSink(),
        AuditLogger(session_factory),
    )


async def test_run_reorder_generates_pending_and_insufficient(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    low, healthy, thin = uuid4(), uuid4(), uuid4()
    sales = _FakeSales(
        [
            DrugSoldQty(low, Decimal("90"), Decimal("900000")),  # velocity 1, point 10
            DrugSoldQty(healthy, Decimal("90"), Decimal("900000")),
            DrugSoldQty(thin, Decimal("2"), Decimal("20000")),  # < threshold
        ]
    )
    stock = _FakeStock({low: Decimal("4"), healthy: Decimal("500"), thin: Decimal("0")})
    supplier = _FakeSupplier({low: uuid4()})
    svc = _service(session_factory, event_bus, sales=sales, stock=stock, supplier=supplier)

    summary = await svc.run_reorder(_ctx("analytics.reorder.run"))
    assert summary.drugs_evaluated == 3
    assert summary.suggested == 1  # only `low`
    assert summary.insufficient_data == 1  # `thin`

    read = _ctx("analytics.read")
    pending = await svc.list_suggestions(read, status=SuggestionStatus.PENDING)
    assert [s.drug_id for s in pending] == [low]
    assert pending[0].can_materialize is True
    assert pending[0].suggested_qty == Decimal("16")


async def test_run_is_idempotent_regenerates_not_appends(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    drug = uuid4()
    sales = _FakeSales([DrugSoldQty(drug, Decimal("90"), Decimal("900000"))])
    stock = _FakeStock({drug: Decimal("4")})
    svc = _service(
        session_factory,
        event_bus,
        sales=sales,
        stock=stock,
        supplier=_FakeSupplier({drug: uuid4()}),
    )
    run = _ctx("analytics.reorder.run")
    await svc.run_reorder(run)
    await svc.run_reorder(run)  # second run must not double up

    pending = await svc.list_suggestions(_ctx("analytics.read"), status=SuggestionStatus.PENDING)
    assert len(pending) == 1


async def test_materialize_creates_draft_po_and_marks(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    drug, supplier_id = uuid4(), uuid4()
    sales = _FakeSales([DrugSoldQty(drug, Decimal("90"), Decimal("900000"))])
    stock = _FakeStock({drug: Decimal("4")})
    sink = _FakeDraftPoSink()
    svc = _service(
        session_factory,
        event_bus,
        sales=sales,
        stock=stock,
        supplier=_FakeSupplier({drug: supplier_id}),
        sink=sink,
    )
    run = _ctx("analytics.reorder.run")
    await svc.run_reorder(run)
    sug = (await svc.list_suggestions(_ctx("analytics.read")))[0]

    out = await svc.materialize(sug.id, run)
    assert sink.created == [(supplier_id, drug, Decimal("16"))]
    assert out.po_id is not None

    materialized = await svc.list_suggestions(
        _ctx("analytics.read"), status=SuggestionStatus.MATERIALIZED
    )
    assert materialized[0].po_id == out.po_id
    with pytest.raises(ConflictError):  # already materialized
        await svc.materialize(sug.id, run)


async def test_materialize_blocked_without_supplier(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    drug = uuid4()
    sales = _FakeSales([DrugSoldQty(drug, Decimal("90"), Decimal("900000"))])
    stock = _FakeStock({drug: Decimal("4")})
    svc = _service(session_factory, event_bus, sales=sales, stock=stock, supplier=_FakeSupplier({}))
    run = _ctx("analytics.reorder.run")
    await svc.run_reorder(run)
    sug = (await svc.list_suggestions(_ctx("analytics.read")))[0]
    assert sug.can_materialize is False  # PENDING but no supplier
    with pytest.raises(ConflictError):
        await svc.materialize(sug.id, run)


async def test_dismiss_then_run_keeps_dismissed(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    drug = uuid4()
    sales = _FakeSales([DrugSoldQty(drug, Decimal("90"), Decimal("900000"))])
    stock = _FakeStock({drug: Decimal("4")})
    svc = _service(
        session_factory,
        event_bus,
        sales=sales,
        stock=stock,
        supplier=_FakeSupplier({drug: uuid4()}),
    )
    run = _ctx("analytics.reorder.run")
    await svc.run_reorder(run)
    sug = (await svc.list_suggestions(_ctx("analytics.read")))[0]
    await svc.dismiss(sug.id, run)

    await svc.run_reorder(run)  # regeneration must not resurrect a dismissed one
    statuses = {s.status for s in await svc.list_suggestions(_ctx("analytics.read"))}
    assert SuggestionStatus.DISMISSED.value in statuses
    assert SuggestionStatus.PENDING.value in statuses  # a fresh PENDING for the same drug


async def test_dashboard_tiles(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    d1, d2 = uuid4(), uuid4()
    sales = _FakeSales(
        [
            DrugSoldQty(d1, Decimal("30"), Decimal("300000")),
            DrugSoldQty(d2, Decimal("90"), Decimal("120000")),
        ]
    )
    stock = _FakeStock({d1: Decimal("2")}, near_expiry=4)
    svc = _service(
        session_factory,
        event_bus,
        sales=sales,
        stock=stock,
        supplier=_FakeSupplier({d1: uuid4(), d2: uuid4()}),
        draft_count=_FakeDraftPoCount(5),
    )
    run = _ctx("analytics.reorder.run")
    await svc.run_reorder(run)

    today = date.today()
    dash = await svc.dashboard(
        _ctx("analytics.read"), date_from=today - timedelta(days=30), date_to=today
    )
    assert dash.revenue_total == Decimal("420000")
    assert dash.top_drugs[0].drug_id == d2  # highest quantity_sold (90 > 30)
    assert dash.near_expiry_count == 4
    assert dash.draft_po_count == 5
    assert dash.low_stock_count >= 1  # d1 is PENDING


async def test_permissions_enforced(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    svc = _service(session_factory, event_bus, sales=_FakeSales([]), stock=_FakeStock({}))
    from pharmacy_os.core.errors import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        await svc.run_reorder(_ctx("analytics.read"))  # needs reorder.run
    with pytest.raises(PermissionDeniedError):
        await svc.list_suggestions(_ctx())  # needs analytics.read


async def test_get_unknown_suggestion_raises(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> None:
    svc = _service(session_factory, event_bus, sales=_FakeSales([]), stock=_FakeStock({}))
    with pytest.raises(NotFoundError):
        await svc.materialize(uuid4(), _ctx("analytics.reorder.run"))
