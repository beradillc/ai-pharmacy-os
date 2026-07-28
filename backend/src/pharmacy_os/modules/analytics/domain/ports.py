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
the adapters supply their own system context downstream. The one **write** sink is the
exception in substance (it forwards the caller's identity/grants, see
:class:`DraftPoSink`) but not in shape: it too takes plain data, not a context object.
"""

from __future__ import annotations

from collections.abc import Sequence
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


class DrugNameSource(Protocol):
    """Drug id → display name, for screens humans read (adapter over catalog).

    Analytics computes on ``drug_id`` and never needs a name to decide anything — this
    exists purely so the dashboard and the reorder screen can print *"Paracetamol
    500mg"* instead of a UUID. Bulk by design: resolving names one row at a time turns
    a 7-row reorder screen into 8 round-trips (docs/19 khe hở **G-1**).

    Ids with no name are **omitted**, not raised: a drug removed after the numbers were
    computed must not blank out a whole dashboard.
    """

    async def names_for(self, tenant_id: UUID, drug_ids: Sequence[UUID]) -> dict[UUID, str]: ...


class SupplierSource(Protocol):
    """Everything analytics needs to know about suppliers (adapter over procurement):
    which one to order a drug from, and what to call it on screen."""

    async def last_supplier_for_drug(self, tenant_id: UUID, drug_id: UUID) -> UUID | None:
        """Supplier of the drug's most recent placed PO; ``None`` if never ordered."""
        ...

    async def names_for(self, tenant_id: UUID, supplier_ids: Sequence[UUID]) -> dict[UUID, str]:
        """Display labels, same contract as :meth:`DrugNameSource.names_for` — bulk,
        and missing ids omitted rather than raised."""
        ...


class DraftPoCountSource(Protocol):
    """Count of DRAFT POs awaiting approval, for the dashboard (adapter over
    procurement)."""

    async def count_draft_pos(self, tenant_id: UUID, branch_id: UUID) -> int: ...


@dataclass(frozen=True, slots=True)
class DraftPoCreated:
    """A newly created draft PO: its id, and the number a human reads out loud.

    Both, not just the id — the id addresses the order in the system, the code is what
    the toast prints and what a pharmacist tells the supplier on the phone
    (docs/19 khe hở G-2).
    """

    po_id: UUID
    code: str


class DraftPoSink(Protocol):
    """Create a single-line DRAFT purchase order from a suggestion (adapter over
    procurement). Returns the new PO's id. Price is left to the human to fill in on
    the draft, so a supplier quote isn't invented here.

    Unlike the read sources, this **write** carries the acting human's identity and
    grants rather than a system identity (design doc §6, Chain duyệt 2026-07-25): a
    draft PO must have someone answerable for it, and procurement gets to enforce its
    own ``procurement.po.create`` against the real caller — so an ``analytics.*`` grant
    alone can never mint purchase orders.
    """

    async def create_draft_po(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        actor_user_id: UUID,
        actor_permissions: frozenset[str],
        supplier_id: UUID,
        drug_id: UUID,
        quantity: Decimal,
    ) -> DraftPoCreated: ...

    async def cancel_draft_po(self, tenant_id: UUID, branch_id: UUID, *, po_id: UUID) -> None:
        """Cancel a draft this analytics flow created — the "hoàn tác" of docs/19 §5.

        🔴 **Read this before widening the signature.** Unlike :meth:`create_draft_po`,
        this one runs under the **system** identity holding ``procurement.po.write``:
        Chain's G-3 decision was to keep the undo inside the ``analytics.*`` grant
        rather than hand every reorder user write access to all purchase orders.
        Letting someone create a commitment they cannot retract is worse than not
        letting them create it — but the fix must not become a side door.

        Three things keep it from being one, and all three are load-bearing:

        1. ``po_id`` comes from the **stored suggestion**, never from the request — the
           service reads it off the record it just loaded and tenant-scoped.
        2. Procurement's own ``cancel`` refuses anything past ``DRAFT``, so an order
           already placed with a supplier cannot be cancelled through here.
        3. The suggestion must still be ``MATERIALIZED``, so one draft can be undone at
           most once through this path.
        """
        ...


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
