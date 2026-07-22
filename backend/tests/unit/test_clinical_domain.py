"""Unit tests for the clinical domain: interaction engine, guardrail, audit record."""

from __future__ import annotations

from uuid import uuid4

import pytest

from pharmacy_os.modules.clinical.domain import (
    AiContextType,
    AiRecommendation,
    AiRecommendationAlreadyAcceptedError,
    DrugInteraction,
    InteractionSeverity,
    InvalidConfidenceError,
    InvalidInteractionError,
    TenantAiSettings,
    find_interactions,
    requires_pharmacist_review,
)


def _interaction(a: str, b: str, severity: InteractionSeverity) -> DrugInteraction:
    return DrugInteraction(
        ingredient_a=a,
        ingredient_b=b,
        severity=severity,
        mechanism="cơ chế mẫu",
        management="xử trí mẫu",
        source="SAMPLE",
    )


# --- DrugInteraction -------------------------------------------------------


def test_interaction_pair_is_canonical_and_order_independent() -> None:
    ab = _interaction("Warfarin", "Aspirin", InteractionSeverity.MAJOR)
    ba = _interaction("aspirin", "  WARFARIN ", InteractionSeverity.MAJOR)
    assert (ab.ingredient_a, ab.ingredient_b) == (ba.ingredient_a, ba.ingredient_b)


def test_self_paired_interaction_rejected() -> None:
    with pytest.raises(InvalidInteractionError):
        _interaction("Aspirin", "aspirin", InteractionSeverity.MINOR)


def test_empty_ingredient_rejected() -> None:
    with pytest.raises(InvalidInteractionError):
        _interaction("Aspirin", "   ", InteractionSeverity.MINOR)


# --- find_interactions -----------------------------------------------------


def test_finds_only_pairs_with_both_ingredients_present() -> None:
    known = [
        _interaction("warfarin", "aspirin", InteractionSeverity.MAJOR),
        _interaction("warfarin", "paracetamol", InteractionSeverity.MODERATE),
    ]
    # Only warfarin+aspirin are both in the basket.
    found = find_interactions(["Aspirin", "Warfarin", "vitamin c"], known)
    assert len(found) == 1
    assert {found[0].ingredient_a, found[0].ingredient_b} == {"warfarin", "aspirin"}


def test_findings_ranked_most_serious_first() -> None:
    known = [
        _interaction("a", "b", InteractionSeverity.MINOR),
        _interaction("a", "c", InteractionSeverity.CONTRAINDICATED),
        _interaction("b", "c", InteractionSeverity.MODERATE),
    ]
    found = find_interactions(["a", "b", "c"], known)
    assert [f.severity for f in found] == [
        InteractionSeverity.CONTRAINDICATED,
        InteractionSeverity.MODERATE,
        InteractionSeverity.MINOR,
    ]


def test_no_interactions_returns_empty() -> None:
    known = [_interaction("a", "b", InteractionSeverity.MAJOR)]
    assert find_interactions(["a", "x", "y"], known) == []


# --- requires_pharmacist_review (guardrail) --------------------------------


@pytest.mark.parametrize(
    "severity", [InteractionSeverity.CONTRAINDICATED, InteractionSeverity.MAJOR]
)
def test_serious_finding_forces_review_even_with_high_confidence(
    severity: InteractionSeverity,
) -> None:
    findings = [_interaction("a", "b", severity)]
    assert requires_pharmacist_review(findings, confidence=0.99, min_confidence=0.7) is True


def test_low_confidence_forces_review_without_serious_findings() -> None:
    findings = [_interaction("a", "b", InteractionSeverity.MINOR)]
    assert requires_pharmacist_review(findings, confidence=0.5, min_confidence=0.7) is True


def test_no_review_when_minor_and_confident() -> None:
    findings = [_interaction("a", "b", InteractionSeverity.MODERATE)]
    assert requires_pharmacist_review(findings, confidence=0.9, min_confidence=0.7) is False


# --- AiRecommendation (audit + human-in-the-loop) --------------------------


def _recommendation() -> AiRecommendation:
    return AiRecommendation(
        tenant_id=uuid4(),
        context_type=AiContextType.SALE,
        model="mock-llm",
        prompt_hash="sha256:abc",
        confidence=0.8,
        requires_review=True,
        output='{"warnings": []}',
    )


def test_confidence_out_of_range_rejected() -> None:
    with pytest.raises(InvalidConfidenceError):
        AiRecommendation(
            tenant_id=uuid4(),
            context_type=AiContextType.RX,
            model="mock-llm",
            prompt_hash="h",
            confidence=1.5,
            requires_review=False,
            output="{}",
        )


def test_accept_sets_pharmacist_and_blocks_double_accept() -> None:
    rec = _recommendation()
    assert rec.accepted_by is None
    pharmacist = uuid4()
    rec.accept(pharmacist)
    assert rec.accepted_by == pharmacist
    with pytest.raises(AiRecommendationAlreadyAcceptedError):
        rec.accept(uuid4())


# --- TenantAiSettings (per-tenant SaaS feature flag) ------------------------


def test_tenant_ai_settings_defaults_to_off() -> None:
    settings = TenantAiSettings(tenant_id=uuid4())
    assert settings.enable_clinical_ai is False


def test_tenant_ai_settings_can_be_enabled() -> None:
    settings = TenantAiSettings(tenant_id=uuid4(), enable_clinical_ai=True)
    assert settings.enable_clinical_ai is True
