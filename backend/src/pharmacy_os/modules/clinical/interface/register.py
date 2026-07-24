"""Compose the clinical module: build its service (over the kernel LLM port) and router."""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.ai import LLMProvider
from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.modules.clinical.application import ClinicalService
from pharmacy_os.modules.clinical.infrastructure import (
    SqlAlchemyAiRecommendationRepository,
    SqlAlchemyDrugInteractionRepository,
    SqlAlchemyTenantAiSettingsRepository,
)
from pharmacy_os.modules.clinical.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    settings = container.resolve(Settings)
    # The LLM only explains; the review threshold comes from config (docs/12 mục 6).
    # Whether AI runs at all is a per-tenant flag (TenantAiSettings), not config.
    llm = container.resolve(LLMProvider)  # type: ignore[type-abstract]

    uow_factory = container.resolve(UnitOfWorkFactory)

    def interaction_repo_factory(uow: UnitOfWork) -> SqlAlchemyDrugInteractionRepository:
        return SqlAlchemyDrugInteractionRepository(uow.session)

    def recommendation_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyAiRecommendationRepository:
        return SqlAlchemyAiRecommendationRepository(uow.session, ctx)

    def settings_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyTenantAiSettingsRepository:
        return SqlAlchemyTenantAiSettingsRepository(uow.session, ctx)

    service = ClinicalService(
        uow_factory,
        interaction_repo_factory,
        recommendation_repo_factory,
        settings_repo_factory,
        llm,
        min_confidence=settings.ai.min_confidence,
        audit=container.resolve(AuditLogger),
    )
    container.register_instance(ClinicalService, service)
    return build_router(get_context)
