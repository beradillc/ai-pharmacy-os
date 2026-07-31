"""Location DTO (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pharmacy_os.modules.location.domain import Location


@dataclass(slots=True)
class CreateLocationInput:
    kind: str
    code: str
    name: str | None = None
    #: ``None`` = tạo một KHO gốc. Khác ``None`` = tạo chỗ con dưới vị trí đó.
    parent_id: UUID | None = None
    pick_order: int = 0


@dataclass(slots=True)
class UpdateLocationInput:
    """Chỉ ba thứ đổi được. ``code`` và ``path`` bất biến — xem ``Location``."""

    name: str | None = None
    pick_order: int | None = None
    is_active: bool | None = None


@dataclass(slots=True)
class LocationOutput:
    id: UUID
    parent_id: UUID | None
    kind: str
    code: str
    path: str
    name: str | None
    is_active: bool
    pick_order: int

    @classmethod
    def of(cls, loc: Location) -> LocationOutput:
        return cls(
            id=loc.id,
            parent_id=loc.parent_id,
            kind=loc.kind.value,
            code=loc.code,
            path=loc.path,
            name=loc.name,
            is_active=loc.is_active,
            pick_order=loc.pick_order,
        )
