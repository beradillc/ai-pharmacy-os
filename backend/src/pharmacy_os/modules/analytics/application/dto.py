"""Analytics data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.analytics.domain import ReorderSuggestion


@dataclass(slots=True)
class SuggestionOutput:
    id: UUID
    drug_id: UUID
    avg_daily_velocity: Decimal
    reorder_point: Decimal
    on_hand_at_calc: Decimal
    suggested_qty: Decimal
    status: str
    supplier_id: UUID | None
    po_id: UUID | None
    can_materialize: bool
    calculated_at: datetime
    #: Display label resolved from catalog. ``None`` means "not resolvable" (drug gone),
    #: never "not looked up" — the service always attempts the lookup.
    drug_name: str | None = None
    #: Display label for :attr:`supplier_id`. ``None`` both when there is no supplier yet
    #: ("chưa có NCC") and when the id no longer resolves — the UI tells them apart by
    #: looking at ``supplier_id`` itself.
    supplier_name: str | None = None

    @classmethod
    def of(
        cls,
        s: ReorderSuggestion,
        *,
        drug_name: str | None = None,
        supplier_name: str | None = None,
    ) -> SuggestionOutput:
        return cls(
            id=s.id,
            drug_id=s.drug_id,
            avg_daily_velocity=s.avg_daily_velocity,
            reorder_point=s.reorder_point,
            on_hand_at_calc=s.on_hand_at_calc,
            suggested_qty=s.suggested_qty,
            status=s.status.value,
            supplier_id=s.supplier_id,
            po_id=s.po_id,
            can_materialize=s.can_materialize,
            calculated_at=s.calculated_at,
            drug_name=drug_name,
            supplier_name=supplier_name,
        )


@dataclass(slots=True)
class ReorderRunSummary:
    """Outcome of one reorder run — the counts a caller shows after "tính lại"."""

    branch_id: UUID
    drugs_evaluated: int
    suggested: int
    insufficient_data: int


@dataclass(slots=True)
class TopDrug:
    drug_id: UUID
    quantity_sold: Decimal
    revenue: Decimal
    #: See :attr:`SuggestionOutput.drug_name`.
    drug_name: str | None = None


@dataclass(slots=True)
class DashboardOutput:
    """The analytics dashboard's first-screen tiles (PROJECT_STATE §7am)."""

    branch_id: UUID
    date_from: date
    date_to: date
    revenue_total: Decimal
    top_drugs: list[TopDrug]
    near_expiry_count: int
    low_stock_count: int
    draft_po_count: int


@dataclass(slots=True)
class MaterializeOutput:
    suggestion_id: UUID
    po_id: UUID
    #: The order number to print — "PO-0412", not the UUID (docs/19 khe hở G-2).
    po_code: str
