"""Mapping between the analytics ORM row and its domain entity."""

from __future__ import annotations

from pharmacy_os.modules.analytics.domain import ReorderSuggestion, SuggestionStatus
from pharmacy_os.modules.analytics.infrastructure.models import ReorderSuggestionORM


def to_domain(row: ReorderSuggestionORM) -> ReorderSuggestion:
    return ReorderSuggestion(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        drug_id=row.drug_id,
        avg_daily_velocity=row.avg_daily_velocity,
        reorder_point=row.reorder_point,
        on_hand_at_calc=row.on_hand_at_calc,
        suggested_qty=row.suggested_qty,
        status=SuggestionStatus(row.status),
        supplier_id=row.supplier_id,
        po_id=row.po_id,
        calculated_at=row.calculated_at,
    )


def to_orm(suggestion: ReorderSuggestion) -> ReorderSuggestionORM:
    return ReorderSuggestionORM(
        id=suggestion.id,
        tenant_id=suggestion.tenant_id,
        branch_id=suggestion.branch_id,
        drug_id=suggestion.drug_id,
        avg_daily_velocity=suggestion.avg_daily_velocity,
        reorder_point=suggestion.reorder_point,
        on_hand_at_calc=suggestion.on_hand_at_calc,
        suggested_qty=suggestion.suggested_qty,
        status=suggestion.status.value,
        supplier_id=suggestion.supplier_id,
        po_id=suggestion.po_id,
        calculated_at=suggestion.calculated_at,
    )
