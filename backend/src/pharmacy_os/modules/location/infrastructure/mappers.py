"""Chuyển đổi giữa ORM row và aggregate miền."""

from __future__ import annotations

from pharmacy_os.modules.location.domain import Location, LocationKind
from pharmacy_os.modules.location.infrastructure.models import LocationORM


def to_domain(row: LocationORM) -> Location:
    return Location(
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        kind=LocationKind(row.kind),
        code=row.code,
        path=row.path,
        name=row.name,
        parent_id=row.parent_id,
        is_active=row.is_active,
        pick_order=row.pick_order,
        id=row.id,
    )


def to_orm(loc: Location) -> LocationORM:
    return LocationORM(
        id=loc.id,
        tenant_id=loc.tenant_id,
        branch_id=loc.branch_id,
        parent_id=loc.parent_id,
        kind=loc.kind.value,
        code=loc.code,
        path=loc.path,
        name=loc.name,
        is_active=loc.is_active,
        pick_order=loc.pick_order,
    )
