"""Clinical domain entities: drug interactions and the AI recommendation audit record.

Interactions are keyed by **active ingredient** (docs/03 ERD ``drug_interactions``:
``ingredient_a``/``ingredient_b``), the pharmacologically correct level. Mapping a
sold/prescribed ``drug_id`` to its ingredients is a separate concern that depends on a
catalog ingredient model which does not exist yet:

    # BLOCKER: catalog has no active-ingredient model (active_ingredients /
    # drug_ingredients per docs/03 are unimplemented); drug→ingredient resolution
    # and any cross-module auto-check (sale/prescription) wait on it.

See docs/12_AI_INTEGRATION.md for the AI design and audit rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.clinical.domain.exceptions import (
    AiRecommendationAlreadyAcceptedError,
    InvalidConfidenceError,
    InvalidInteractionError,
)


def _now() -> datetime:
    return datetime.now(UTC)


def normalize_ingredient(value: str) -> str:
    """Canonical key for matching an active ingredient (case/space-insensitive)."""
    return value.strip().casefold()


class InteractionSeverity(StrEnum):
    """Severity of a drug–drug interaction (most → least serious for ranking)."""

    CONTRAINDICATED = "CONTRAINDICATED"  # tuyệt đối chống chỉ định
    MAJOR = "MAJOR"  # nghiêm trọng
    MODERATE = "MODERATE"  # trung bình
    MINOR = "MINOR"  # nhẹ


class AiContextType(StrEnum):
    """What business action an AI recommendation was produced for (docs/03 ai_recommendations)."""

    SALE = "SALE"
    RX = "RX"
    CHAT = "CHAT"


@dataclass(frozen=True, slots=True)
class DrugInteraction:
    """One known interaction between two active ingredients (reference data).

    The ingredient pair is unordered — stored normalized so lookup is
    direction-independent (``A×B`` == ``B×A``). ``source`` records where the fact
    came from; the seed data shipped in S5.5 is **sample/placeholder**, not an
    authoritative clinical source (see module ``# BLOCKER``).
    """

    ingredient_a: str
    ingredient_b: str
    severity: InteractionSeverity
    mechanism: str
    management: str
    source: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        a = normalize_ingredient(self.ingredient_a)
        b = normalize_ingredient(self.ingredient_b)
        if not a or not b:
            raise InvalidInteractionError("Tên hoạt chất không được để trống")
        if a == b:
            raise InvalidInteractionError("Tương tác cần hai hoạt chất khác nhau")
        # Canonicalize: store the pair sorted so (A,B) and (B,A) are one fact.
        lo, hi = sorted((a, b))
        object.__setattr__(self, "ingredient_a", lo)
        object.__setattr__(self, "ingredient_b", hi)


@dataclass(slots=True)
class AiRecommendation:
    """Immutable audit record of one AI decision-support call (docs/12 mục 7).

    Carries only audit metadata + the human-in-the-loop ``accepted_by`` state; the
    finding/source detail is serialized into ``output``/``sources`` (stored as jsonb
    by infrastructure). ``requires_review`` is the output-guardrail verdict: when set,
    the recommendation must not be treated as cleared until a pharmacist accepts it.
    """

    tenant_id: UUID
    context_type: AiContextType
    model: str
    prompt_hash: str
    confidence: float
    requires_review: bool
    output: str
    context_id: UUID | None = None
    sources: tuple[str, ...] = ()
    accepted_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise InvalidConfidenceError("confidence phải trong khoảng [0, 1]")

    def accept(self, user_id: UUID) -> None:
        """Pharmacist signs off on the recommendation (human-in-the-loop)."""
        if self.accepted_by is not None:
            raise AiRecommendationAlreadyAcceptedError(
                f"Khuyến nghị đã được {self.accepted_by} chấp nhận"
            )
        self.accepted_by = user_id
