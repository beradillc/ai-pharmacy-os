from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.sales.domain import (
    EmptyOrderError,
    InvalidOrderStateError,
    InvalidReturnError,
    Payment,
    PaymentMethod,
    PrescriptionRequiredError,
    SaleLine,
    SalesOrder,
    SaleStatus,
    UnderpaidError,
    ensure_rx_for_etc,
)
from pharmacy_os.shared.value_objects import Money


def _order(**kw: object) -> SalesOrder:
    return SalesOrder(tenant_id=uuid4(), branch_id=uuid4(), client_uuid="c-1", **kw)  # type: ignore[arg-type]


def _line(price: str = "10000", qty: str = "2", *, rx: bool = False) -> SaleLine:
    return SaleLine(
        drug_id=uuid4(),
        quantity=Decimal(qty),
        unit_price=Money(Decimal(price)),
        requires_prescription=rx,
    )


def _pay(amount: str) -> Payment:
    return Payment(method=PaymentMethod.CASH, amount=Money(Decimal(amount)))


def test_subtotal_and_line_total() -> None:
    order = _order()
    order.add_line(_line(price="10000", qty="2"))
    order.add_line(_line(price="5000", qty="3"))
    assert order.subtotal == Money(Decimal("35000"))


def test_complete_happy_path_sets_status() -> None:
    order = _order()
    order.add_line(_line(price="10000", qty="2"))
    order.add_payment(_pay("20000"))
    order.complete()
    assert order.status is SaleStatus.COMPLETED


def test_complete_empty_order_rejected() -> None:
    order = _order()
    order.add_payment(_pay("0"))
    with pytest.raises(EmptyOrderError):
        order.complete()


def test_complete_underpaid_rejected() -> None:
    order = _order()
    order.add_line(_line(price="10000", qty="2"))
    order.add_payment(_pay("15000"))
    with pytest.raises(UnderpaidError):
        order.complete()


def test_overpayment_allowed() -> None:
    order = _order()
    order.add_line(_line(price="10000", qty="1"))
    order.add_payment(_pay("50000"))  # change given back at the till
    order.complete()
    assert order.status is SaleStatus.COMPLETED


def test_etc_without_prescription_blocked() -> None:
    order = _order()
    order.add_line(_line(rx=True))
    order.add_payment(_pay("20000"))
    with pytest.raises(PrescriptionRequiredError):
        order.complete()


def test_etc_with_prescription_ref_allowed() -> None:
    order = _order(prescription_ref=uuid4())
    order.add_line(_line(rx=True))
    order.add_payment(_pay("20000"))
    order.complete()
    assert order.status is SaleStatus.COMPLETED


def test_rule_helper_is_pure() -> None:
    ensure_rx_for_etc(False, None)  # OTC-only order: no-op
    ensure_rx_for_etc(True, uuid4())  # Rx supplied: no-op
    with pytest.raises(PrescriptionRequiredError):
        ensure_rx_for_etc(True, None)


def test_cannot_mutate_after_completion() -> None:
    order = _order()
    order.add_line(_line())
    order.add_payment(_pay("20000"))
    order.complete()
    with pytest.raises(InvalidOrderStateError):
        order.add_line(_line())
    with pytest.raises(InvalidOrderStateError):
        order.add_payment(_pay("1000"))


def test_cancel_draft_order_sets_status() -> None:
    order = _order()
    order.add_line(_line())
    order.cancel()
    assert order.status is SaleStatus.CANCELLED


def test_cancel_completed_order_rejected() -> None:
    order = _order()
    order.add_line(_line())
    order.add_payment(_pay("20000"))
    order.complete()
    with pytest.raises(InvalidOrderStateError):
        order.cancel()


def test_cannot_add_line_or_payment_after_cancel() -> None:
    order = _order()
    order.add_line(_line())
    order.cancel()
    with pytest.raises(InvalidOrderStateError):
        order.add_line(_line())
    with pytest.raises(InvalidOrderStateError):
        order.add_payment(_pay("1000"))


def test_zero_quantity_line_rejected() -> None:
    with pytest.raises(ValueError):
        SaleLine(drug_id=uuid4(), quantity=Decimal("0"), unit_price=Money(Decimal("1000")))


def test_payment_currency_mismatch_rejected() -> None:
    order = _order()
    with pytest.raises(InvalidOrderStateError):
        order.add_payment(Payment(method=PaymentMethod.CARD, amount=Money(Decimal("1000"), "USD")))


def test_partial_then_full_return_transitions_status() -> None:
    order = _order()
    line = _line(price="10000", qty="3")
    order.add_line(line)
    order.add_payment(_pay("30000"))
    order.complete()

    order.register_return(line.id, Decimal("1"))
    assert order.status is SaleStatus.PARTIALLY_RETURNED
    assert line.returnable_quantity == Decimal("2")

    order.register_return(line.id, Decimal("2"))
    assert order.status is SaleStatus.RETURNED


def test_return_more_than_sold_rejected() -> None:
    order = _order()
    line = _line(qty="2")
    order.add_line(line)
    order.add_payment(_pay("20000"))
    order.complete()
    with pytest.raises(InvalidReturnError):
        order.register_return(line.id, Decimal("3"))


def test_return_unknown_line_rejected() -> None:
    order = _order()
    order.add_line(_line())
    order.add_payment(_pay("20000"))
    order.complete()
    with pytest.raises(InvalidReturnError):
        order.register_return(uuid4(), Decimal("1"))


def test_return_before_completion_rejected() -> None:
    order = _order()
    line = _line()
    order.add_line(line)
    with pytest.raises(InvalidOrderStateError):
        order.register_return(line.id, Decimal("1"))


def test_sold_by_user_id_defaults_to_none() -> None:
    """An order built without a salesperson is legal — pre-column and offline-sync
    orders stay unattributed rather than being rejected (PROJECT_STATE §7ao)."""
    order = _order()
    assert order.sold_by_user_id is None


def test_sold_by_user_id_is_carried_through_completion() -> None:
    seller = uuid4()
    order = _order(sold_by_user_id=seller)
    order.add_line(_line(price="10000", qty="2"))
    order.add_payment(_pay("20000"))
    order.complete()
    assert order.status is SaleStatus.COMPLETED
    assert order.sold_by_user_id == seller
