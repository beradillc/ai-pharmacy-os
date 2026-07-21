"""Reference data + idempotent seeding for catalog lookups.

ATC = Anatomical Therapeutic Chemical classification (WHO). This is a small
starter set; a full import job is a later concern.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.modules.catalog.infrastructure import AtcCodeORM
from pharmacy_os.modules.clinical.domain import DrugInteraction, InteractionSeverity
from pharmacy_os.modules.clinical.infrastructure import DrugInteractionORM
from pharmacy_os.modules.clinical.infrastructure.mappers import interaction_to_orm

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


# ---------------------------------------------------------------------------
# Drug–drug interactions (SAMPLE / PLACEHOLDER — see source string below).
#
# These are well-known pairs used only so the interaction engine has data to
# exercise end-to-end. They are NOT an authoritative clinical source and must be
# replaced before any real clinical use:
#   # BLOCKER: nguồn tri thức dược thật + bản quyền — cần bảng tương tác chính
#   thức (nguồn được cấp phép) thay cho tập mẫu này.
# Keyed by active ingredient (docs/03 drug_interactions), independent of the ATC
# seed above; the DrugInteraction entity canonicalizes each pair (normalized +
# sorted) so ordering here does not matter.
# ---------------------------------------------------------------------------
_SAMPLE_SOURCE = "SAMPLE — không phải nguồn dược chính thức (S5.5 placeholder)"

# (ingredient_a, ingredient_b, severity, mechanism, management)
DRUG_INTERACTIONS: list[tuple[str, str, InteractionSeverity, str, str]] = [
    (
        "Warfarin",
        "Acetylsalicylic acid",
        InteractionSeverity.MAJOR,
        "Cộng hợp tác dụng chống đông + ức chế tiểu cầu → tăng nguy cơ chảy máu.",
        "Tránh phối hợp nếu không có chỉ định; theo dõi INR và dấu hiệu xuất huyết.",
    ),
    (
        "Clopidogrel",
        "Omeprazole",
        InteractionSeverity.MAJOR,
        "Omeprazole ức chế CYP2C19, giảm hoạt hóa clopidogrel → giảm chống kết tập.",
        "Ưu tiên PPI ít ức chế CYP2C19 (pantoprazole) hoặc tách thời điểm dùng.",
    ),
    (
        "Ramipril",
        "Ibuprofen",
        InteractionSeverity.MODERATE,
        "NSAID giảm tác dụng hạ áp của ACE-inhibitor và tăng nguy cơ suy thận cấp.",
        "Hạn chế dùng kéo dài; theo dõi huyết áp và chức năng thận.",
    ),
    (
        "Acetylsalicylic acid",
        "Ibuprofen",
        InteractionSeverity.MODERATE,
        "Ibuprofen cạnh tranh gắn COX-1, làm giảm tác dụng chống kết tập của aspirin liều thấp.",
        "Uống aspirin trước ibuprofen ≥ 2 giờ, hoặc cân nhắc thuốc thay thế.",
    ),
    (
        "Metformin",
        "Cimetidine",
        InteractionSeverity.MINOR,
        "Cimetidine giảm thải trừ metformin qua ống thận → tăng nồng độ metformin.",
        "Theo dõi đường huyết; thường không cần chỉnh liều.",
    ),
]


async def seed_drug_interactions(session: AsyncSession) -> int:
    """Insert any missing SAMPLE drug interactions. Returns the number inserted.

    Idempotent by the canonical (ingredient_a, ingredient_b) pair — re-running never
    duplicates a row.
    """
    existing = {
        (a, b)
        for a, b in (
            await session.execute(
                select(DrugInteractionORM.ingredient_a, DrugInteractionORM.ingredient_b)
            )
        ).all()
    }
    inserted = 0
    for ingredient_a, ingredient_b, severity, mechanism, management in DRUG_INTERACTIONS:
        interaction = DrugInteraction(
            ingredient_a=ingredient_a,
            ingredient_b=ingredient_b,
            severity=severity,
            mechanism=mechanism,
            management=management,
            source=_SAMPLE_SOURCE,
        )
        key = (interaction.ingredient_a, interaction.ingredient_b)
        if key in existing:
            continue
        session.add(interaction_to_orm(interaction))
        existing.add(key)
        inserted += 1
    await session.flush()
    return inserted
