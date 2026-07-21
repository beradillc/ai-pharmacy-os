"""Compliance read-ports (implemented by infrastructure / composition root).

``compliance`` never imports catalog/inventory/sales/prescription directly — the adapter
lives at the composition root (``api/v1/cross_module.py``), same pattern as
``sales.DrugInfoProvider`` / ``CatalogDrugInfoProvider``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DrugMasterFacts:
    """Catalog facts compliance needs to build a ``NationalDrugRecord`` (docs/13 mục B)."""

    registration_no: str | None
    base_unit: str


class DrugMasterProvider(Protocol):
    """Read-port for catalog facts (docs/13 mục B mapping `so_dang_ky`/`don_vi_dong_goi_nn`).

    Returns ``None`` when the drug is unknown to catalog.
    """

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugMasterFacts | None: ...
