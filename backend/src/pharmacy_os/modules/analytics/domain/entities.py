"""Analytics domain entities: the :class:`ReorderSuggestion` aggregate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


def _now() -> datetime:
    return datetime.now(UTC)


class SuggestionStatus(StrEnum):
    """Lifecycle of a reorder suggestion.

    * ``PENDING`` — projected stock is at/below the reorder point; awaits a human.
    * ``INSUFFICIENT_DATA`` — the drug sold, but too little in the window to forecast
      it honestly (see :data:`rules.MIN_SALES_FOR_FORECAST`); shown as "chưa đủ dữ
      liệu", never turned into a purchase order (GĐ: don't fabricate a demand number).
    * ``MATERIALIZED`` — a human turned it into a DRAFT purchase order (``po_id`` set).
    * ``DISMISSED`` — a human decided not to act on it.

    ``PENDING`` and ``INSUFFICIENT_DATA`` are *recomputed* each reorder run (cleared
    and regenerated); ``MATERIALIZED`` and ``DISMISSED`` are terminal history the run
    leaves untouched.
    """

    PENDING = "PENDING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    MATERIALIZED = "MATERIALIZED"
    DISMISSED = "DISMISSED"


@dataclass(slots=True)
class ReorderSuggestion:
    """One drug×branch reorder suggestion produced by a run (aggregate root).

    A snapshot: the velocity/reorder-point/on-hand it was computed from are stored so
    the number a human sees is explainable and doesn't silently shift under them
    between runs. ``supplier_id`` is the drug's last known supplier (``None`` when the
    drug was never ordered — the suggestion then can't be materialised, surfaced as
    "chưa có NCC", PROJECT_STATE §7am Q3)."""

    tenant_id: UUID
    branch_id: UUID
    drug_id: UUID
    avg_daily_velocity: Decimal
    reorder_point: Decimal
    on_hand_at_calc: Decimal
    suggested_qty: Decimal
    status: SuggestionStatus = SuggestionStatus.PENDING
    supplier_id: UUID | None = None
    po_id: UUID | None = None
    calculated_at: datetime = field(default_factory=_now)
    id: UUID = field(default_factory=uuid4)

    @property
    def can_materialize(self) -> bool:
        """True only if it's actionable *and* has a supplier to send the draft to."""
        return self.status is SuggestionStatus.PENDING and self.supplier_id is not None

    def mark_materialized(self, po_id: UUID) -> None:
        self.status = SuggestionStatus.MATERIALIZED
        self.po_id = po_id

    def mark_undone(self) -> None:
        """Undo a materialisation: back to PENDING, no PO attached.

        Deliberately returns to ``PENDING`` rather than to a new "UNDONE" state — the
        suggestion is once again a thing the pharmacist may act on, which is exactly
        what PENDING means. A separate state would only add a case every screen has to
        handle to say the same thing.
        """
        self.status = SuggestionStatus.PENDING
        self.po_id = None

    def mark_dismissed(self) -> None:
        self.status = SuggestionStatus.DISMISSED
