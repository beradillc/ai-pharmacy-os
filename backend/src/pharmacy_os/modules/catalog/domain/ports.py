"""Catalog persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.catalog.domain.entities import ActiveIngredient, Drug


class DrugRepository(Protocol):
    async def add(self, drug: Drug) -> None: ...

    async def get(self, drug_id: UUID) -> Drug | None: ...

    async def by_barcode(self, barcode: str) -> Drug | None: ...

    async def list(
        self,
        *,
        search: str | None = None,
        ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Drug]:
        """Drugs of the tenant, by name.

        ``search`` matches a **substring of the name, case-insensitively**, or an
        **exact barcode** — the two ways a person at a counter identifies a box:
        they type part of what is printed on it, or they scan it.

        ``ids`` restricts to a known set. That is what lets a screen holding a page
        of stock/sale rows label them with one request instead of one per row; an
        empty sequence means "no ids asked for" and yields no rows, which is
        different from ``None`` ("no id filter").
        """
        ...

    async def names_by_ids(self, drug_ids: Sequence[UUID]) -> dict[UUID, str]:
        """Name-only projection for many ids in one query. Ids the tenant can't see are
        simply absent from the result — callers decide what to show for a missing name,
        because a drug deleted after a report was computed is not an error."""
        ...


class ActiveIngredientRepository(Protocol):
    """Read/seed access to the global ``active_ingredients`` reference table (not tenant-scoped)."""

    async def add(self, ingredient: ActiveIngredient) -> None: ...

    async def get(self, ingredient_id: UUID) -> ActiveIngredient | None: ...

    async def find_by_name(self, name: str) -> ActiveIngredient | None: ...

    async def list(self) -> list[ActiveIngredient]: ...
