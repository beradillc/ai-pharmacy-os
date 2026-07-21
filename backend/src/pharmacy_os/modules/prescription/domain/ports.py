"""Prescription ports (implemented by infrastructure)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.prescription.domain.entities import Prescription


class PrescriptionRepository(Protocol):
    async def add(self, prescription: Prescription) -> None: ...

    async def update(self, prescription: Prescription) -> None: ...

    async def get(self, prescription_id: UUID) -> Prescription | None: ...
