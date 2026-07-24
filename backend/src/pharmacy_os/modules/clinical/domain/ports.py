"""Clinical persistence ports (implemented by infrastructure).

The LLM seam is the kernel port ``pharmacy_os.core.ai.LLMProvider`` — used by the
application layer for *explanation only*, never here in the domain, which stays pure
and deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.clinical.domain.entities import (
    AiContextType,
    AiRecommendation,
    DrugInteraction,
    TenantAiSettings,
)


class DrugInteractionRepository(Protocol):
    """Read/seed access to the ``drug_interactions`` reference table (global, not tenant-scoped)."""

    async def add(self, interaction: DrugInteraction) -> None: ...

    async def find_for_ingredients(self, ingredients: Sequence[str]) -> list[DrugInteraction]:
        """Known interactions where *both* ingredients are within ``ingredients``."""
        ...


class AiRecommendationRepository(Protocol):
    """Persistence port for :class:`AiRecommendation` (tenant-scoped, immutable audit)."""

    async def add(self, recommendation: AiRecommendation) -> None: ...

    async def get(self, recommendation_id: UUID) -> AiRecommendation | None: ...

    async def find_for_context(
        self, context_type: AiContextType, context_id: UUID
    ) -> AiRecommendation | None:
        """The recommendation already recorded for a business action, if any.

        The idempotency key of an automatic check: a redelivered event must not add a
        second compliance record for the same sale/prescription. Returns the earliest
        one when several exist (a manual re-check via the API is still allowed and
        leaves the original in place).
        """
        ...

    async def update(self, recommendation: AiRecommendation) -> None: ...


class TenantAiSettingsRepository(Protocol):
    """Persistence port for :class:`TenantAiSettings` (one row per tenant)."""

    async def get(self, tenant_id: UUID) -> TenantAiSettings | None: ...

    async def upsert(self, settings: TenantAiSettings) -> None: ...
