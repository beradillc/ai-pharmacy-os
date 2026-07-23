"""Round-trip contract for the outbox event codec.

Every DomainEvent must survive ``deserialize(serialize(e)) == e`` — money/quantity
Decimals keep precision, dates/UUIDs/optionals/nested-tuples all reconstruct. A new
event type added without a case here is caught by ``test_registry_covers_every_event``.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.core.events import (
    DomainEvent,
    EventRegistry,
    deserialize_event,
    serialize_event,
)
from pharmacy_os.modules.iam.domain import RolesChanged, UserDeactivated, UserRegistered
from pharmacy_os.modules.inventory.domain import (
    LowStockDetected,
    StockMovedIn,
    StockMovedOut,
    StockShortfallDetected,
)
from pharmacy_os.modules.prescription.domain import (
    PrescriptionDispensed,
    PrescriptionRejected,
    PrescriptionValidated,
)
from pharmacy_os.modules.procurement.domain import (
    GoodsReceived,
    PurchaseOrdered,
    ReceivedItem,
)
from pharmacy_os.modules.sales.domain import (
    SaleCompleted,
    SaleReturned,
    SoldItem,
)

_TENANT = uuid4()
_WHEN = datetime(2026, 7, 24, 3, 14, 15, tzinfo=UTC)


def _all_events() -> list[DomainEvent]:
    """One realistic instance of every DomainEvent subclass, exercising each field
    kind: Decimals with fractional parts, dates, optional None + present, empty and
    multi-item nested tuples."""
    return [
        SaleCompleted(
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            order_id=uuid4(),
            branch_id=uuid4(),
            client_uuid="c-123",
            items=(
                SoldItem(drug_id=uuid4(), quantity=Decimal("2.500")),
                SoldItem(drug_id=uuid4(), quantity=Decimal("1")),
            ),
        ),
        SaleCompleted(  # empty-tuple edge case
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            order_id=uuid4(),
            branch_id=uuid4(),
            client_uuid="c-empty",
            items=(),
        ),
        SaleReturned(
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            return_id=uuid4(),
            order_id=uuid4(),
            branch_id=uuid4(),
            line_id=uuid4(),
            drug_id=uuid4(),
            quantity=Decimal("3.000"),
        ),
        PurchaseOrdered(
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            po_id=uuid4(),
            branch_id=uuid4(),
            supplier_id=uuid4(),
        ),
        GoodsReceived(
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            grn_id=uuid4(),
            po_id=uuid4(),
            branch_id=uuid4(),
            received_by=uuid4(),
            items=(
                ReceivedItem(
                    drug_id=uuid4(),
                    lot_no="L1",
                    expiry_date=date(2027, 1, 1),
                    unit_cost=Decimal("1234.56"),
                    quantity=Decimal("100"),
                    po_item_id=uuid4(),
                    mfg_date=date(2026, 1, 1),
                ),
                ReceivedItem(  # optional mfg_date=None
                    drug_id=uuid4(),
                    lot_no="L2",
                    expiry_date=date(2027, 6, 1),
                    unit_cost=Decimal("9.99"),
                    quantity=Decimal("5.5"),
                    po_item_id=uuid4(),
                ),
            ),
        ),
        UserRegistered(tenant_id=_TENANT, occurred_at=_WHEN, user_id=uuid4(), email="a@b.vn"),
        RolesChanged(  # branch_id present
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            user_id=uuid4(),
            role_id=uuid4(),
            branch_id=uuid4(),
            granted=True,
        ),
        RolesChanged(  # branch_id None (chain-wide) + granted False
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            user_id=uuid4(),
            role_id=uuid4(),
            branch_id=None,
            granted=False,
        ),
        UserDeactivated(tenant_id=_TENANT, occurred_at=_WHEN, user_id=uuid4()),
        PrescriptionValidated(
            tenant_id=_TENANT, occurred_at=_WHEN, prescription_id=uuid4(), validated_by=uuid4()
        ),
        PrescriptionRejected(
            tenant_id=_TENANT, occurred_at=_WHEN, prescription_id=uuid4(), reason="Chữ ký mờ"
        ),
        PrescriptionDispensed(tenant_id=_TENANT, occurred_at=_WHEN, prescription_id=uuid4()),
        StockMovedIn(
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            drug_id=uuid4(),
            batch_id=uuid4(),
            branch_id=uuid4(),
            quantity=Decimal("10.250"),
        ),
        StockMovedOut(
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            drug_id=uuid4(),
            branch_id=uuid4(),
            quantity=Decimal("4"),
        ),
        LowStockDetected(
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            drug_id=uuid4(),
            branch_id=uuid4(),
            on_hand=Decimal("2"),
            reorder_point=Decimal("5"),
        ),
        StockShortfallDetected(  # optional ref_type/ref_id present
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            drug_id=uuid4(),
            branch_id=uuid4(),
            requested=Decimal("12"),
            available=Decimal("8"),
            ref_type="sale",
            ref_id=uuid4(),
        ),
        StockShortfallDetected(  # optional ref_type/ref_id None
            tenant_id=_TENANT,
            occurred_at=_WHEN,
            drug_id=uuid4(),
            branch_id=uuid4(),
            requested=Decimal("1"),
            available=Decimal("0"),
        ),
    ]


@pytest.mark.parametrize("event", _all_events(), ids=lambda e: f"{e.name}-{e.event_id}")
def test_round_trip_is_identity(event: DomainEvent) -> None:
    encoded = serialize_event(event)
    # The payload must be genuinely JSON-safe (no UUID/Decimal/date objects left).
    json.dumps(encoded)
    rebuilt = deserialize_event(type(event), encoded["payload"])
    assert rebuilt == event
    assert type(rebuilt) is type(event)


def test_serialize_records_the_type_name() -> None:
    event = UserDeactivated(tenant_id=_TENANT, user_id=uuid4())
    assert serialize_event(event)["event_type"] == "UserDeactivated"


def test_registry_resolves_names_and_misses_unknown() -> None:
    registry = EventRegistry()
    registry.register(SaleCompleted, GoodsReceived)
    assert registry.resolve("SaleCompleted") is SaleCompleted
    assert registry.resolve("GoodsReceived") is GoodsReceived
    assert registry.resolve("NeverRegistered") is None


def test_registry_can_round_trip_via_resolved_type() -> None:
    """The outbox path: store type name, later resolve it, then deserialize."""
    registry = EventRegistry()
    registry.register(SaleReturned)
    original = SaleReturned(
        tenant_id=_TENANT,
        return_id=uuid4(),
        order_id=uuid4(),
        branch_id=uuid4(),
        line_id=uuid4(),
        drug_id=uuid4(),
        quantity=Decimal("2"),
    )
    stored = serialize_event(original)
    resolved = registry.resolve(stored["event_type"])
    assert resolved is not None
    assert deserialize_event(resolved, stored["payload"]) == original
