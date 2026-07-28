"""Pydantic request/response schemas for the analytics HTTP API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from pharmacy_os.modules.analytics.application import (
    DashboardOutput,
    MaterializeOutput,
    ReorderRunSummary,
    SuggestionOutput,
    TopDrug,
)


class ReorderRunResponse(BaseModel):
    branch_id: UUID
    drugs_evaluated: int
    suggested: int
    insufficient_data: int

    @classmethod
    def of(cls, s: ReorderRunSummary) -> ReorderRunResponse:
        return cls(
            branch_id=s.branch_id,
            drugs_evaluated=s.drugs_evaluated,
            suggested=s.suggested,
            insufficient_data=s.insufficient_data,
        )


class SuggestionResponse(BaseModel):
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
    #: ``null`` when the drug can no longer be resolved — the UI shows the id then,
    #: rather than the row vanishing.
    drug_name: str | None

    @classmethod
    def of(cls, s: SuggestionOutput) -> SuggestionResponse:
        return cls(
            id=s.id,
            drug_id=s.drug_id,
            drug_name=s.drug_name,
            avg_daily_velocity=s.avg_daily_velocity,
            reorder_point=s.reorder_point,
            on_hand_at_calc=s.on_hand_at_calc,
            suggested_qty=s.suggested_qty,
            status=s.status,
            supplier_id=s.supplier_id,
            po_id=s.po_id,
            can_materialize=s.can_materialize,
            calculated_at=s.calculated_at,
        )


class MaterializeResponse(BaseModel):
    suggestion_id: UUID
    po_id: UUID

    @classmethod
    def of(cls, s: MaterializeOutput) -> MaterializeResponse:
        return cls(suggestion_id=s.suggestion_id, po_id=s.po_id)


class TopDrugResponse(BaseModel):
    drug_id: UUID
    quantity_sold: Decimal
    revenue: Decimal
    #: See :attr:`SuggestionResponse.drug_name`.
    drug_name: str | None

    @classmethod
    def of(cls, t: TopDrug) -> TopDrugResponse:
        return cls(
            drug_id=t.drug_id,
            quantity_sold=t.quantity_sold,
            revenue=t.revenue,
            drug_name=t.drug_name,
        )


class DashboardResponse(BaseModel):
    branch_id: UUID
    date_from: date
    date_to: date
    revenue_total: Decimal
    top_drugs: list[TopDrugResponse]
    near_expiry_count: int
    low_stock_count: int
    draft_po_count: int

    @classmethod
    def of(cls, d: DashboardOutput) -> DashboardResponse:
        return cls(
            branch_id=d.branch_id,
            date_from=d.date_from,
            date_to=d.date_to,
            revenue_total=d.revenue_total,
            top_drugs=[TopDrugResponse.of(t) for t in d.top_drugs],
            near_expiry_count=d.near_expiry_count,
            low_stock_count=d.low_stock_count,
            draft_po_count=d.draft_po_count,
        )
