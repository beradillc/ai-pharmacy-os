"""Clinical domain: deterministic drug-interaction engine + AI recommendation audit.

Framework-free and LLM-free. See docs/12_AI_INTEGRATION.md.
"""

from pharmacy_os.modules.clinical.domain.entities import (
    AiContextType,
    AiRecommendation,
    AllergyAlert,
    DrugInteraction,
    InteractionSeverity,
    TenantAiSettings,
    normalize_ingredient,
)
from pharmacy_os.modules.clinical.domain.exceptions import (
    AiRecommendationAlreadyAcceptedError,
    ClinicalError,
    InvalidConfidenceError,
    InvalidInteractionError,
)
from pharmacy_os.modules.clinical.domain.ports import (
    AiRecommendationRepository,
    DrugInteractionRepository,
    TenantAiSettingsRepository,
)
from pharmacy_os.modules.clinical.domain.rules import (
    find_allergy_alerts,
    find_interactions,
    requires_pharmacist_review,
)

__all__ = [
    "AiContextType",
    "AiRecommendation",
    "AllergyAlert",
    "DrugInteraction",
    "InteractionSeverity",
    "TenantAiSettings",
    "normalize_ingredient",
    "AiRecommendationAlreadyAcceptedError",
    "ClinicalError",
    "InvalidConfidenceError",
    "InvalidInteractionError",
    "AiRecommendationRepository",
    "DrugInteractionRepository",
    "TenantAiSettingsRepository",
    "find_allergy_alerts",
    "find_interactions",
    "requires_pharmacist_review",
]
