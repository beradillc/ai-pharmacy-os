"""Catalog persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.catalog.domain.entities import ActiveIngredient, Drug


class DrugRepository(Protocol):
    async def add(self, drug: Drug) -> None: ...

    async def get(self, drug_id: UUID) -> Drug | None: ...

    async def by_barcode(self, barcode: str) -> Drug | None: ...

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Drug]: ...


class ActiveIngredientRepository(Protocol):
    """Read/seed access to the global ``active_ingredients`` reference table (not tenant-scoped)."""

    async def add(self, ingredient: ActiveIngredient) -> None: ...

    async def get(self, ingredient_id: UUID) -> ActiveIngredient | None: ...

    async def find_by_name(self, name: str) -> ActiveIngredient | None: ...

    async def list(self) -> list[ActiveIngredient]: ...
