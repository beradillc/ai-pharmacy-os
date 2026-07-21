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
    """The authoritative dispensing facts sales needs about a drug."""

    drug_id: UUID
    requires_prescription: bool


class DrugInfoProvider(Protocol):
    """Read-port for catalog facts, so sales never imports the catalog module.

    Implemented at the composition root (adapter over ``CatalogService``).
    Returns ``None`` when the drug is unknown to catalog.
    """

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None: ...
