"""Reference data + idempotent seeding for catalog lookups.

ATC = Anatomical Therapeutic Chemical classification (WHO). This is a small
starter set; a full import job is a later concern.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.modules.catalog.infrastructure import AtcCodeORM

# (code, name, level)
ATC_CODES: list[tuple[str, str, int]] = [
    ("N02BE01", "Paracetamol", 5),
    ("M01AE01", "Ibuprofen", 5),
    ("J01CA04", "Amoxicillin", 5),
    ("J01CR02", "Amoxicillin và chất ức chế beta-lactamase", 5),
    ("A02BC01", "Omeprazole", 5),
    ("A10BA02", "Metformin", 5),
    ("C09AA05", "Ramipril", 5),
    ("R05CB01", "Acetylcysteine", 5),
    ("R06AE07", "Cetirizine", 5),
    ("B01AC06", "Acetylsalicylic acid (Aspirin)", 5),
]


async def seed_atc_codes(session: AsyncSession) -> int:
    """Insert any missing ATC codes. Returns the number inserted."""
    existing = set((await session.execute(select(AtcCodeORM.code))).scalars().all())
    inserted = 0
    for code, name, level in ATC_CODES:
        if code in existing:
            continue
        session.add(AtcCodeORM(code=code, name=name, level=level))
        inserted += 1
    await session.flush()
    return inserted
