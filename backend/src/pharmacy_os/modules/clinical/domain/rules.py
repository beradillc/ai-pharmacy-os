"""Clinical domain rules — the deterministic interaction engine + output guardrail.

Pure functions, framework-free and LLM-free: the safety-critical decision (which
ingredient pairs interact, and how seriously) is computed here from reference data,
never delegated to the model (docs/12 mục 1, 6).
"""

from __future__ import annotations

from collections.abc import Iterable

from pharmacy_os.modules.clinical.domain.entities import (
    DrugInteraction,
    InteractionSeverity,
    normalize_ingredient,
)

# Most-serious first — the rank used to order findings.
_SEVERITY_ORDER: tuple[InteractionSeverity, ...] = (
    InteractionSeverity.CONTRAINDICATED,
    InteractionSeverity.MAJOR,
    InteractionSeverity.MODERATE,
    InteractionSeverity.MINOR,
)
_SEVERITY_RANK: dict[InteractionSeverity, int] = {
    sev: rank for rank, sev in enumerate(_SEVERITY_ORDER)
}

# Findings at or above this severity always demand a pharmacist's review,
# independent of the LLM's confidence.
_REVIEW_FORCING_SEVERITIES = frozenset(
    {InteractionSeverity.CONTRAINDICATED, InteractionSeverity.MAJOR}
)


def find_interactions(
    ingredients: Iterable[str], known: Iterable[DrugInteraction]
) -> list[DrugInteraction]:
    """Return the known interactions whose *both* ingredients are in ``ingredients``.

    Deterministic and order-independent (ingredient keys are normalized). Results are
    ranked most-serious first; ties keep a stable ingredient ordering.
    """
    present = {normalize_ingredient(name) for name in ingredients}
    found = [
        interaction
        for interaction in known
        if interaction.ingredient_a in present and interaction.ingredient_b in present
    ]
    found.sort(key=lambda i: (_SEVERITY_RANK[i.severity], i.ingredient_a, i.ingredient_b))
    return found


def requires_pharmacist_review(
    findings: Iterable[DrugInteraction], confidence: float, *, min_confidence: float
) -> bool:
    """Output-guardrail verdict (docs/12 mục 6).

    Review is required when any finding is serious (CONTRAINDICATED/MAJOR) or the
    model's confidence is below ``min_confidence`` — either way the result is not to
    be treated as cleared without a human sign-off.
    """
    if any(f.severity in _REVIEW_FORCING_SEVERITIES for f in findings):
        return True
    return confidence < min_confidence
