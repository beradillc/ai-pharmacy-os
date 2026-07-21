"""Clinical domain: deterministic drug-interaction engine + AI recommendation audit.

Framework-free and LLM-free. See docs/12_AI_INTEGRATION.md.
"""

from pharmacy_os.modules.clinical.domain.entities import (
    AiContextType,
    AiRecommendation,
    DrugInteraction,
    InteractionSeverity,
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
)
from pharmacy_os.modules.clinical.domain.rules import (
    find_interactions,
    requires_pharmacist_review,
)

__all__ = [
    "AiContextType",
    "AiRecommendation",
    "DrugInteraction",
    "InteractionSeverity",
    "normalize_ingredient",
    "AiRecommendationAlreadyAcceptedError",
    "ClinicalError",
    "InvalidConfidenceError",
    "InvalidInteractionError",
    "AiRecommendationRepository",
    "DrugInteractionRepository",
    "find_interactions",
    "requires_pharmacist_review",
]
