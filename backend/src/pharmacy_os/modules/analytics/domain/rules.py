"""Reorder maths — pure, framework-free, the heart of analytics v1.

Forecast = 90-day moving average (PROJECT_STATE §7am): no ML. The reorder point is
``velocity × (lead_time + safety_stock)`` days of demand; when on-hand is at/below it,
we suggest ordering back up to :data:`ORDER_UP_TO_FACTOR` × the reorder point.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from enum import StrEnum

#: Below this many units sold in the whole window, the velocity is too thin to
#: forecast honestly — we refuse to invent a demand number (GĐ, PROJECT_STATE §7am).
#: A v1 heuristic, deliberately conservative; tune when more history exists.
MIN_SALES_FOR_FORECAST: Decimal = Decimal("3")

#: Order-up-to level as a multiple of the reorder point. Ordering only *to* the
#: reorder point would re-trigger immediately; 2× buys one more lead+safety cycle of
#: cover. A v1 heuristic (no separate review-period config — Chain kept config to
#: lead_time + safety_stock only, §7am Q2).
ORDER_UP_TO_FACTOR: Decimal = Decimal("2")


class ReorderOutcome(StrEnum):
    """What the maths says about one drug — mapped to a persisted status by the
    service (``NEEDS_REORDER`` → PENDING, ``INSUFFICIENT_DATA`` → same, ``HEALTHY`` →
    not persisted)."""

    NEEDS_REORDER = "NEEDS_REORDER"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    HEALTHY = "HEALTHY"


@dataclass(frozen=True, slots=True)
class ReorderPolicy:
    """The per-tenant knobs of the reorder maths (defaults live in the service;
    per-tenant override is deferred to v2, §7am Q2)."""

    window_days: int
    lead_time_days: int
    safety_stock_days: int

    def __post_init__(self) -> None:
        if self.window_days <= 0:
            raise ValueError("window_days phải > 0")
        if self.lead_time_days < 0 or self.safety_stock_days < 0:
            raise ValueError("lead_time_days/safety_stock_days không được âm")


@dataclass(frozen=True, slots=True)
class ReorderEvaluation:
    """Result of :func:`evaluate_reorder` for one drug."""

    outcome: ReorderOutcome
    avg_daily_velocity: Decimal
    reorder_point: Decimal
    suggested_qty: Decimal


def evaluate_reorder(
    *,
    quantity_sold: Decimal,
    on_hand: Decimal,
    policy: ReorderPolicy,
) -> ReorderEvaluation:
    """Evaluate one drug's reorder need from its window sales and current stock.

    * ``quantity_sold`` below :data:`MIN_SALES_FOR_FORECAST` → ``INSUFFICIENT_DATA``
      (velocity reported for transparency, but no order quantity).
    * on-hand above the reorder point → ``HEALTHY`` (no action).
    * otherwise → ``NEEDS_REORDER`` with a whole-unit ``suggested_qty`` (rounded up,
      always ≥ 1) to reach the order-up-to level.
    """
    velocity = (quantity_sold / Decimal(policy.window_days)).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    if quantity_sold < MIN_SALES_FOR_FORECAST:
        return ReorderEvaluation(
            outcome=ReorderOutcome.INSUFFICIENT_DATA,
            avg_daily_velocity=velocity,
            reorder_point=Decimal("0"),
            suggested_qty=Decimal("0"),
        )

    reorder_point = (velocity * Decimal(policy.lead_time_days + policy.safety_stock_days)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if on_hand > reorder_point:
        return ReorderEvaluation(
            outcome=ReorderOutcome.HEALTHY,
            avg_daily_velocity=velocity,
            reorder_point=reorder_point,
            suggested_qty=Decimal("0"),
        )

    order_up_to = reorder_point * ORDER_UP_TO_FACTOR
    raw_qty = order_up_to - on_hand
    suggested = raw_qty.quantize(Decimal("1"), rounding=ROUND_CEILING)
    if suggested < 1:
        suggested = Decimal("1")  # at/below reorder point always means order ≥ 1
    return ReorderEvaluation(
        outcome=ReorderOutcome.NEEDS_REORDER,
        avg_daily_velocity=velocity,
        reorder_point=reorder_point,
        suggested_qty=suggested,
    )
