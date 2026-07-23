"""Clinical use-cases: check drug interactions (with an audited AI explanation) and
record the pharmacist's human-in-the-loop sign-off.

The safety verdict is deterministic — it comes from the domain engine over the
``drug_interactions`` reference table, never from the LLM. The injected
``LLMProvider`` (a mock in S5.5, see ``# BLOCKER: AI__API_KEY thật``) only produces an
advisory *explanation*; its confidence feeds the review guardrail but cannot clear a
serious finding. The service depends only on ports + the provider protocol; concrete
repositories and the unit of work are injected as factories at composition time.
"""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from uuid import UUID

from pharmacy_os.core.ai import LLMProvider, Message
from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, FeatureDisabledError, NotFoundError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.clinical.application.dto import (
    AiRecommendationOutput,
    AllergyAlertOutput,
    AllergyCheckResult,
    CheckAllergiesInput,
    CheckInteractionsInput,
    DrugInteractionOutput,
    InteractionCheckResult,
    SetTenantAiSettingsInput,
    TenantAiSettingsOutput,
)
from pharmacy_os.modules.clinical.domain import (
    AiRecommendation,
    AiRecommendationAlreadyAcceptedError,
    DrugInteraction,
    TenantAiSettings,
    find_allergy_alerts,
    find_interactions,
    requires_pharmacist_review,
)
from pharmacy_os.modules.clinical.domain.ports import (
    AiRecommendationRepository,
    DrugInteractionRepository,
    TenantAiSettingsRepository,
)

UowFactory = Callable[[], UnitOfWork]
InteractionRepoFactory = Callable[[UnitOfWork], DrugInteractionRepository]
RecommendationRepoFactory = Callable[[UnitOfWork, RequestContext], AiRecommendationRepository]
SettingsRepoFactory = Callable[[UnitOfWork, RequestContext], TenantAiSettingsRepository]

_SYSTEM_PROMPT = (
    "Bạn là trợ lý dược lâm sàng. Diễn giải ngắn gọn các tương tác thuốc đã được "
    "phát hiện. KHÔNG tự quyết định mức độ an toàn — mức độ đã do hệ thống xác định."
)


def _build_messages(ingredients: list[str], findings: list[DrugInteraction]) -> list[Message]:
    if findings:
        lines = "\n".join(
            f"- {f.ingredient_a} × {f.ingredient_b}: {f.severity.value} — {f.mechanism}"
            for f in findings
        )
        user = f"Hoạt chất: {', '.join(ingredients)}.\nTương tác đã phát hiện:\n{lines}"
    else:
        user = f"Hoạt chất: {', '.join(ingredients)}.\nKhông phát hiện tương tác đã biết."
    return [Message(role="system", content=_SYSTEM_PROMPT), Message(role="user", content=user)]


class ClinicalService:
    def __init__(
        self,
        uow_factory: UowFactory,
        interaction_repo_factory: InteractionRepoFactory,
        recommendation_repo_factory: RecommendationRepoFactory,
        settings_repo_factory: SettingsRepoFactory,
        llm: LLMProvider,
        *,
        min_confidence: float,
        model: str | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._interaction_repo_factory = interaction_repo_factory
        self._recommendation_repo_factory = recommendation_repo_factory
        self._settings_repo_factory = settings_repo_factory
        self._llm = llm
        self._min_confidence = min_confidence
        self._model = model
        self._audit = audit

    async def check_interactions(
        self, data: CheckInteractionsInput, ctx: RequestContext
    ) -> InteractionCheckResult:
        """Deterministically find drug interactions, then audit an AI explanation.

        The findings come from the domain engine (:func:`find_interactions`) over the
        reference table — the LLM call only explains. Every check writes one immutable
        :class:`AiRecommendation`; :attr:`requires_review` is the guardrail verdict
        (docs/12 mục 6): a serious finding or low model confidence demands a pharmacist.
        Gated by the caller tenant's :class:`TenantAiSettings` (SaaS: each tenant opts
        in independently) — an unconfigured tenant defaults to OFF (fail-safe).
        """
        require_permission(ctx, "clinical.check")
        await self._ensure_ai_enabled(ctx)

        async with self._uow_factory() as uow:
            interaction_repo = self._interaction_repo_factory(uow)
            known = await interaction_repo.find_for_ingredients(data.ingredients)
            findings = find_interactions(data.ingredients, known)

            messages = _build_messages(data.ingredients, findings)
            result = self._llm.complete(messages, model=self._model)
            confidence = result.confidence if result.confidence is not None else 0.0
            requires_review = requires_pharmacist_review(
                findings, confidence, min_confidence=self._min_confidence
            )
            prompt_hash = sha256("\n".join(m.content for m in messages).encode("utf-8")).hexdigest()
            # Cite the reference rows that produced the findings (the mock LLM has no RAG).
            sources = tuple(sorted({f.source for f in findings}))

            recommendation = AiRecommendation(
                tenant_id=ctx.tenant_id,
                context_type=data.context_type,
                context_id=data.context_id,
                model=result.model,
                prompt_hash=prompt_hash,
                confidence=confidence,
                requires_review=requires_review,
                output=result.content,
                sources=sources,
            )
            repo = self._recommendation_repo_factory(uow, ctx)
            await repo.add(recommendation)
            await uow.commit()

        await self._record(
            ctx, AuditAction.CLINICAL_INTERACTION_CHECKED, "ai_recommendation", recommendation.id
        )
        return InteractionCheckResult(
            findings=[DrugInteractionOutput.of(f) for f in findings],
            recommendation=AiRecommendationOutput.of(recommendation),
        )

    async def check_allergies(
        self, data: CheckAllergiesInput, ctx: RequestContext
    ) -> AllergyCheckResult:
        """Match a dispensed basket's ingredients against the customer's allergies.

        Deterministic and non-AI — a set-membership match on ``ingredient_id``. Unlike
        :meth:`check_interactions` this is **not** gated by :class:`TenantAiSettings` and
        writes no audit record: allergy safety is a baseline check that runs for every
        tenant, and there is no model output to persist. Returns the alerts for the
        caller to surface (the cross-module handler logs them, warn-only).
        """
        require_permission(ctx, "clinical.check")
        alerts = find_allergy_alerts(
            [(b.ingredient_id, b.name) for b in data.basket], data.allergy_severities
        )
        return AllergyCheckResult(
            alerts=[
                AllergyAlertOutput(
                    ingredient_id=a.ingredient_id,
                    ingredient_name=a.ingredient_name,
                    severity=a.severity,
                )
                for a in alerts
            ]
        )

    async def get_recommendation(
        self, recommendation_id: UUID, ctx: RequestContext
    ) -> AiRecommendationOutput:
        """Return one recommendation by id (tenant-scoped); 404 if not found."""
        require_permission(ctx, "clinical.check")
        async with self._uow_factory() as uow:
            repo = self._recommendation_repo_factory(uow, ctx)
            rec = await repo.get(recommendation_id)
        if rec is None:
            raise NotFoundError(f"Không tìm thấy khuyến nghị AI {recommendation_id}")
        return AiRecommendationOutput.of(rec)

    async def accept_recommendation(
        self, recommendation_id: UUID, ctx: RequestContext
    ) -> AiRecommendationOutput:
        """Pharmacist signs off on a recommendation (human-in-the-loop, docs/12 mục 6).

        404 if unknown; 409 if it was already accepted (accepting twice is a conflict).
        """
        require_permission(ctx, "clinical.accept")
        async with self._uow_factory() as uow:
            repo = self._recommendation_repo_factory(uow, ctx)
            rec = await repo.get(recommendation_id)
            if rec is None:
                raise NotFoundError(f"Không tìm thấy khuyến nghị AI {recommendation_id}")
            try:
                rec.accept(ctx.user_id)
            except AiRecommendationAlreadyAcceptedError as exc:
                raise ConflictError(str(exc)) from exc
            await repo.update(rec)
            await uow.commit()
        await self._record(
            ctx, AuditAction.CLINICAL_RECOMMENDATION_ACCEPTED, "ai_recommendation", rec.id
        )
        return AiRecommendationOutput.of(rec)

    async def get_tenant_ai_settings(self, ctx: RequestContext) -> TenantAiSettingsOutput:
        """Return the caller tenant's AI flags; unconfigured reads back as OFF (fail-safe),
        not 404 — there is always a well-defined answer to "is AI on for this tenant?".
        """
        require_permission(ctx, "clinical.settings.read")
        async with self._uow_factory() as uow:
            repo = self._settings_repo_factory(uow, ctx)
            settings = await repo.get(ctx.tenant_id)
        if settings is None:
            settings = TenantAiSettings(tenant_id=ctx.tenant_id, enable_clinical_ai=False)
        return TenantAiSettingsOutput.of(settings)

    async def set_tenant_ai_settings(
        self, data: SetTenantAiSettingsInput, ctx: RequestContext
    ) -> TenantAiSettingsOutput:
        """Create/update the caller tenant's AI flags (upsert)."""
        require_permission(ctx, "clinical.settings.write")
        async with self._uow_factory() as uow:
            repo = self._settings_repo_factory(uow, ctx)
            existing = await repo.get(ctx.tenant_id)
            settings = TenantAiSettings(
                tenant_id=ctx.tenant_id,
                enable_clinical_ai=data.enable_clinical_ai,
            )
            if existing is not None:
                settings.id = existing.id
            await repo.upsert(settings)
            await uow.commit()
        return TenantAiSettingsOutput.of(settings)

    async def _ensure_ai_enabled(self, ctx: RequestContext) -> None:
        async with self._uow_factory() as uow:
            repo = self._settings_repo_factory(uow, ctx)
            settings = await repo.get(ctx.tenant_id)
        if settings is None or not settings.enable_clinical_ai:
            raise FeatureDisabledError(
                f"Tính năng AI lâm sàng chưa được bật cho tenant {ctx.tenant_id}"
            )

    async def _record(
        self, ctx: RequestContext, action: AuditAction, target_type: str, target_id: UUID
    ) -> None:
        """Append one audit row — metadata only, never the AI output/findings content."""
        if self._audit is None:
            return
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )
