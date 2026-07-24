"""Pure reorder maths (``evaluate_reorder``) + suggestion aggregate transitions."""

from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.analytics.domain import (
    ReorderOutcome,
    ReorderPolicy,
    ReorderSuggestion,
    SuggestionStatus,
    evaluate_reorder,
)

# 90-day window, 7-day lead, 3-day safety → reorder covers 10 days of demand.
_POLICY = ReorderPolicy(window_days=90, lead_time_days=7, safety_stock_days=3)


def _eval(quantity_sold: str, on_hand: str) -> object:
    return evaluate_reorder(
        quantity_sold=Decimal(quantity_sold), on_hand=Decimal(on_hand), policy=_POLICY
    )


def test_velocity_is_window_average() -> None:
    ev = _eval("90", "0")  # 90 sold / 90 days = 1.0/day
    assert ev.avg_daily_velocity == Decimal("1.0000")
    assert ev.reorder_point == Decimal("10.00")  # 1.0 × (7+3)


def test_needs_reorder_when_on_hand_at_or_below_point() -> None:
    ev = _eval("90", "4")  # point 10, on-hand 4 → reorder
    assert ev.outcome is ReorderOutcome.NEEDS_REORDER
    # order-up-to = 2×10 = 20; suggested = ceil(20 − 4) = 16
    assert ev.suggested_qty == Decimal("16")


def test_healthy_when_on_hand_above_point() -> None:
    ev = _eval("90", "50")  # well above point 10
    assert ev.outcome is ReorderOutcome.HEALTHY
    assert ev.suggested_qty == Decimal("0")


def test_exactly_at_point_reorders() -> None:
    ev = _eval("90", "10")  # on-hand == reorder point → reorder
    assert ev.outcome is ReorderOutcome.NEEDS_REORDER
    # order-up-to = 20; suggested = ceil(20 − 10) = 10
    assert ev.suggested_qty == Decimal("10")


def test_tiny_deficit_floors_suggested_to_one() -> None:
    # qty 3 (≥ threshold) → velocity 0.0333, point 0.33; on-hand at point → reorder,
    # up-to 0.66, raw 0.33 → ceil 1 (never suggest a fractional/zero order).
    ev = _eval("3", "0.33")
    assert ev.outcome is ReorderOutcome.NEEDS_REORDER
    assert ev.suggested_qty == Decimal("1")


def test_insufficient_data_below_threshold() -> None:
    ev = _eval("2", "0")  # < MIN_SALES_FOR_FORECAST (3)
    assert ev.outcome is ReorderOutcome.INSUFFICIENT_DATA
    assert ev.suggested_qty == Decimal("0")
    assert ev.avg_daily_velocity == Decimal("0.0222")  # still reported


def test_suggested_qty_rounds_up_to_whole_units() -> None:
    ev = _eval("45", "1")  # velocity 0.5, point 5.00, up-to 10, 10−1=9
    assert ev.outcome is ReorderOutcome.NEEDS_REORDER
    assert ev.suggested_qty == Decimal("9")


@pytest.mark.parametrize("bad", [dict(window_days=0), dict(lead_time_days=-1)])
def test_policy_rejects_bad_config(bad: dict[str, int]) -> None:
    kwargs = {"window_days": 90, "lead_time_days": 7, "safety_stock_days": 3, **bad}
    with pytest.raises(ValueError):
        ReorderPolicy(**kwargs)


def _suggestion() -> ReorderSuggestion:
    return ReorderSuggestion(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        drug_id=uuid4(),
        avg_daily_velocity=Decimal("1"),
        reorder_point=Decimal("10"),
        on_hand_at_calc=Decimal("4"),
        suggested_qty=Decimal("16"),
        supplier_id=uuid4(),
    )


def test_can_materialize_needs_pending_and_supplier() -> None:
    s = _suggestion()
    assert s.can_materialize is True
    s.supplier_id = None
    assert s.can_materialize is False


def test_mark_materialized_sets_po_and_status() -> None:
    s = _suggestion()
    po = uuid4()
    s.mark_materialized(po)
    assert s.status is SuggestionStatus.MATERIALIZED
    assert s.po_id == po
    assert s.can_materialize is False


def test_dismiss_blocks_materialize() -> None:
    s = _suggestion()
    s.mark_dismissed()
    assert s.status is SuggestionStatus.DISMISSED
    assert s.can_materialize is False
