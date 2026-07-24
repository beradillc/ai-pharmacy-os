"""Sales ports (implemented by infrastructure / composition root)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.sales.domain.entities import SalesOrder


@dataclass(frozen=True, slots=True)
class OrderRevenueRow:
    """One completed order's revenue facts, as read for the Sprint 7 revenue report.

    Deliberately order-level, not line-level: the report groups by period/branch, and
    an order-level ``subtotal`` (summed in SQL from its lines) is all that grouping
    needs. ``created_at`` doubles as the completion timestamp — ``complete_sale``
    builds and completes an order in the same call, so there is no separate
    "completed_at" to read (see ``SalesOrder.complete``).
    """

    order_id: UUID
    branch_id: UUID
    currency: str
    created_at: datetime
    subtotal: Decimal
    sold_by_user_id: UUID | None = None
    """Who completed the sale, or ``None`` for an order recorded before the column
    existed — see :attr:`SalesOrder.sold_by_user_id`. Defaulted so a repository (or
    a test double) that does not care about the salesperson dimension keeps
    building rows unchanged."""


@dataclass(frozen=True, slots=True)
class DrugSalesAggRow:
    """Net quantity a drug sold in one branch over a window, plus its net revenue.

    Line-level aggregation (group by ``drug_id``/``branch_id``), unlike
    :class:`OrderRevenueRow` which is order-level — this is what the analytics module
    reads to model demand velocity and rank top sellers (PROJECT_STATE §7am, Q1).

    ``quantity_sold`` is **net of returns** (``quantity - returned_quantity`` summed):
    a returned item was not consumed, so counting it would over-state demand and lead
    analytics to over-order. This deliberately differs from the revenue report, which
    counts gross at sale time (recognised revenue, PROJECT_STATE §7an) — different
    purpose, different convention, both documented. ``revenue`` is likewise net.
    Rows whose net quantity is ``0`` (fully returned) are dropped by the query.
    """

    drug_id: UUID
    branch_id: UUID
    quantity_sold: Decimal
    revenue: Decimal


class SalesRepository(Protocol):
    async def add(self, order: SalesOrder) -> None: ...

    async def update(self, order: SalesOrder) -> None: ...

    async def get(self, order_id: UUID) -> SalesOrder | None: ...

    async def by_client_uuid(self, client_uuid: str) -> SalesOrder | None: ...

    async def completed_in_range(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        sold_by_user_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
        limit: int,
        offset: int,
    ) -> list[OrderRevenueRow]:
        """Page of completed orders (any post-``DRAFT`` status) in ``[created_from,
        created_to)``, optionally narrowed to one branch and/or one salesperson,
        oldest first — the report service buckets these into periods in Python (no
        ``date_trunc``: the project keeps queries portable across Postgres/SQLite,
        see ``models.py``).

        ``sold_by_user_id`` filters to the orders that user completed; ``None``
        means "every salesperson", **not** "orders with no salesperson" — the
        unattributed pre-column orders stay in the unfiltered total and cannot be
        isolated on their own."""
        ...

    async def aggregate_sold_by_drug(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
    ) -> list[DrugSalesAggRow]:
        """Net quantity + revenue sold per ``(drug_id, branch_id)`` over
        ``[created_from, created_to)``, across completed (post-``DRAFT``) orders,
        optionally narrowed to one branch.

        Grouped in SQL — the result is bounded by the number of distinct drugs (a
        pharmacy's catalogue), not by order volume, so a plain list is returned (no
        paging, unlike :meth:`completed_in_range` which the report streams). Fully
        returned lines net to ``0`` and are excluded (see :class:`DrugSalesAggRow`)."""
        ...


@dataclass(frozen=True, slots=True)
class DrugInfo:
    """The authoritative dispensing facts sales needs about a drug.

    ``name``/``unit`` default to empty when the caller only cares about the Rx
    rule (e.g. tests) — a receipt renderer treats an empty ``name`` as "unknown
    drug" and falls back to the raw id.
    """

    drug_id: UUID
    requires_prescription: bool
    name: str = ""
    unit: str = ""


class DrugInfoProvider(Protocol):
    """Read-port for catalog facts, so sales never imports the catalog module.

    Implemented at the composition root (adapter over ``CatalogService``).
    Returns ``None`` when the drug is unknown to catalog.
    """

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None: ...


@dataclass(frozen=True, slots=True)
class PrescriptionInfo:
    """The authoritative Rx facts sales needs to authorise a prescription sale.

    ``status`` is the prescription's raw status *value* (e.g. ``"VALIDATED"``);
    sales owns the accept-list of sale-authorising states in its domain rules, so
    it never imports the prescription module's status enum.
    """

    prescription_id: UUID
    status: str


class PrescriptionInfoProvider(Protocol):
    """Read-port for prescription facts, so sales never imports the prescription module.

    Implemented at the composition root (adapter over ``PrescriptionService``).
    Returns ``None`` when the prescription is unknown to the caller's tenant.
    """

    async def get(self, prescription_id: UUID, tenant_id: UUID) -> PrescriptionInfo | None: ...
