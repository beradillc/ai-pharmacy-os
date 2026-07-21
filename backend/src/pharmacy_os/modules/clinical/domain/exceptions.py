"""Clinical domain exceptions (pure — no framework)."""

from __future__ import annotations


class ClinicalError(Exception):
    """Base for clinical domain rule violations."""


class InvalidInteractionError(ClinicalError):
    """Raised when a :class:`DrugInteraction` is malformed (empty/self-paired ingredient)."""


class InvalidConfidenceError(ClinicalError):
    """Raised when an :class:`AiRecommendation` confidence is outside [0, 1]."""


class AiRecommendationAlreadyAcceptedError(ClinicalError):
    """Raised when accepting an :class:`AiRecommendation` that a pharmacist already accepted."""
