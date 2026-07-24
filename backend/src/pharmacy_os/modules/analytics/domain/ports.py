"""Analytics ports.

Two kinds live here:

* **Cross-module sources/sinks** — Protocols analytics defines and the composition
  root implements as adapters over sales/inventory/procurement. Analytics never
  imports those modules; it only knows these shapes. Adapters read/write under a
  system identity (like every other cross-module reaction), so an analytics user
  needs only the ``analytics.*`` grants.
* **Own persistence** — :class:`ReorderSuggestionRepository` for analytics' own table.

All source methods take plain scope data (``tenant_id``/``branch_id``), never a
``RequestContext`` — authorisation is enforced at the analytics service boundary, and
the adapters supply their own system context downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.analytics.domain.entities import ReorderSuggestion, SuggestionStatus


@dataclass(frozen=True, slots=True)
class DrugSoldQty:
    """A drug's net sold quantity + revenue in a branch over the forecast window."""

    drug_id: UUID
    quantity_sold: Decimal
    revenue: Decimal


class SalesVelocitySource(Protocol):
    """Line-level sales, read for velocity + top sellers (adapter over sales)."""

    async def sold_quantity_by_drug(
        self, tenant_id: UUID, branch_id: UUID, *, date_from: date, date_to: date
    ) -> list[DrugSoldQty]: ...


class StockLevelSource(Protocol):
    """Current stock + near-expiry counts (adapter over inventory)."""

    async def on_hand_by_drug(self, tenant_id: UUID, branch_id: UUID) -> dict[UUID, Decimal]: ...

    async def count_near_expiry(
        self, tenant_id: UUID, branch_id: UUID, *, within_days: int
    ) -> int: ...


class SupplierSource(Protocol):
    """The drug→last-supplier lookup for materialising a draft PO (adapter over
    procurement). Returns ``None`` for a never-ordered drug."""

    async def last_supplier_for_drug(self, tenant_id: UUID, drug_id: UUID) -> UUID | None: ...


class DraftPoCountSource(Protocol):
    """Count of DRAFT POs awaiting approval, for the dashboard (adapter over
    procurement)."""

    async def count_draft_pos(self, tenant_id: UUID, branch_id: UUID) -> int: ...


class DraftPoSink(Protocol):
    """Create a single-line DRAFT purchase order from a suggestion (adapter over
    procurement). Returns the new PO's id. Price is left to the human to fill in on
    the draft, so a supplier quote isn't invented here."""

    async def create_draft_po(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        supplier_id: UUID,
        drug_id: UUID,
        quantity: Decimal,
    ) -> UUID: ...


class ReorderSuggestionRepository(Protocol):
    """Analytics' own persistence for :class:`ReorderSuggestion`."""

    async def add(self, suggestion: ReorderSuggestion) -> None: ...

    async def get(self, suggestion_id: UUID) -> ReorderSuggestion | None: ...

    async def update(self, suggestion: ReorderSuggestion) -> None: ...

    async def list_by_branch(
        self, tenant_id: UUID, branch_id: UUID, *, status: SuggestionStatus | None = None
    ) -> list[ReorderSuggestion]: ...

    async def count_by_status(
        self, tenant_id: UUID, branch_id: UUID, status: SuggestionStatus
    ) -> int: ...

    async def delete_recomputable_for_branch(self, tenant_id: UUID, branch_id: UUID) -> None:
        """Drop this branch's ``PENDING`` + ``INSUFFICIENT_DATA`` rows before a fresh
        run regenerates them. ``MATERIALIZED``/``DISMISSED`` are terminal — kept."""
        ...
