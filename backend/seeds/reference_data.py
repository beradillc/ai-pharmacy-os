"""Reference data + idempotent seeding for catalog lookups.

ATC = Anatomical Therapeutic Chemical classification (WHO). This is a small
starter set; a full import job is a later concern.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.modules.catalog.infrastructure import AtcCodeORM
from pharmacy_os.modules.clinical.domain import DrugInteraction, InteractionSeverity
from pharmacy_os.modules.clinical.infrastructure import DrugInteractionORM
from pharmacy_os.modules.clinical.infrastructure.mappers import interaction_to_orm
from pharmacy_os.modules.compliance.infrastructure import ControlledSubstanceORM
from seeds.tt18_controlled_substances import CONTROLLED_SUBSTANCES_TT18

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


# ---------------------------------------------------------------------------
# Danh mục dược chất kiểm soát đặc biệt — TT 18/2026 PL I/II/III + ngưỡng PL IV/V/VI.
# Khác 2 khối trên: đây là dữ liệu PHÁP LÝ chính thức, không phải tập mẫu.
# Dữ liệu nằm ở seeds/tt18_controlled_substances.py (sinh tự động từ văn bản gốc).
# ---------------------------------------------------------------------------


def _to_decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


async def seed_controlled_substances(session: AsyncSession) -> tuple[int, int]:
    """Đồng bộ danh mục TT18 vào ``controlled_substances``. Trả về (thêm mới, cập nhật).

    **Có nhánh cập nhật, không chỉ insert** (kỷ luật 7 trong CLAUDE.md): danh mục pháp lý
    có sửa đổi — thêm chất, đổi ngưỡng nồng độ. Deployment cũ đã có sẵn dòng cho chất đó
    thì phải được ghi đè theo văn bản mới, nếu chỉ insert-nếu-thiếu thì bản nâng cấp sẽ
    giữ nguyên ngưỡng cũ và phân loại sai thuốc.
    """
    rows = {
        row.name_intl: row
        for row in (await session.execute(select(ControlledSubstanceORM))).scalars().all()
    }
    created = updated = 0
    for (
        name_intl,
        common_name,
        scientific_name,
        appendix,
        limit_per_unit_mg,
        limit_concentration_pct,
        limit_note,
        effective_from,
    ) in CONTROLLED_SUBSTANCES_TT18:
        wanted = {
            "common_name": common_name,
            "scientific_name": scientific_name,
            "appendix": appendix,
            "limit_per_unit_mg": _to_decimal(limit_per_unit_mg),
            "limit_concentration_pct": _to_decimal(limit_concentration_pct),
            "limit_note": limit_note,
            "effective_from": (
                None if effective_from is None else date.fromisoformat(effective_from)
            ),
        }
        existing = rows.get(name_intl)
        if existing is None:
            session.add(ControlledSubstanceORM(name_intl=name_intl, **wanted))
            created += 1
            continue
        changed = [k for k, v in wanted.items() if getattr(existing, k) != v]
        if changed:
            for key in changed:
                setattr(existing, key, wanted[key])
            updated += 1
    await session.flush()
    return created, updated
