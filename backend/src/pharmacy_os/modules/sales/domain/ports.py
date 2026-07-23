"""Sales ports (implemented by infrastructure / composition root)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.sales.domain.entities import SalesOrder


class SalesRepository(Protocol):
    async def add(self, order: SalesOrder) -> None: ...

    async def get(self, order_id: UUID) -> SalesOrder | None: ...

    async def by_client_uuid(self, client_uuid: str) -> SalesOrder | None: ...


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
