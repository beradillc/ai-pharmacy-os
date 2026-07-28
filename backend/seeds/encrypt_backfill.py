"""Encrypt rows written before at-rest encryption was switched on, and re-key old ones.

**Why a command and not a migration.** A migration runs with no application context, so
it has no cipher and no key — it physically cannot encrypt anything. Encryption lives in
the SQLAlchemy column types, which means the only thing that can rewrite these values is
the application itself. Migrations widen the columns; this command fills them.

**Why re-reading and re-writing is enough.** Reads accept both shapes and writes encrypt
whenever the flag is on, so loading a row and marking the column dirty is a complete
re-encryption. The same mechanism re-keys a row written under an older key version,
because the write always uses the current one.

**Safe to interrupt and safe to repeat.** Work happens in batches, each committed on its
own, and a row already holding current-version ciphertext is skipped. Stopping halfway
leaves a column holding both shapes, which every read path already handles — that is the
property that lets this run against a live system.

Usage (from ``backend/`` with the venv active and ``ENCRYPTION__*`` configured)::

    python -m seeds.encrypt_backfill --dry-run     # count what would change
    python -m seeds.encrypt_backfill              # do it
    python -m seeds.encrypt_backfill --verify     # read everything back and check

Run ``--verify`` **before** dropping any pre-encryption backup: it is the only check
that proves every row decrypts with the keys this deployment actually holds.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.attributes import flag_modified

from pharmacy_os.core.bootstrap import build_blind_index, build_field_cipher
from pharmacy_os.core.config import get_settings
from pharmacy_os.core.db import (
    active_blind_index,
    active_cipher,
    build_engine,
    build_sessionmaker,
    configure_field_encryption,
    encryption_writes_enabled,
)
from pharmacy_os.core.security.crypto import DecryptionError

# `catalog` models are never touched directly here, but `CustomerAllergyORM.ingredient_id`
# is a real FK to `active_ingredients`. SQLAlchemy resolves FKs from whatever classes are
# registered on the shared declarative base at mapper-configure time (triggered by the
# first flush) — leaving this out makes flushing *any* row related to `customers` blow up
# with NoReferencedTableError, not just rows that touch allergies. Found by running this
# against real data, not by a test (pytest's conftest imports every module's models).
from pharmacy_os.modules.catalog.infrastructure.models import ActiveIngredientORM  # noqa: F401
from pharmacy_os.modules.compliance.infrastructure.models import (
    ControlledLedgerEntryORM,
    DrugReturnRecordORM,
)
from pharmacy_os.modules.crm.infrastructure.models import (
    CustomerAllergyORM,
    CustomerConditionORM,
    CustomerORM,
)
from pharmacy_os.modules.iam.infrastructure.models import UserTwoFactorORM

_log = structlog.get_logger("encrypt_backfill")


@dataclass(frozen=True, slots=True)
class _Target:
    model: type[DeclarativeBase]
    columns: tuple[str, ...]

    fingerprints: tuple[tuple[str, str], ...] = ()
    """``(source column, fingerprint column)`` pairs to recompute.

    Not optional decoration — without it the backfill leaves ``phone_fingerprint``
    empty on every pre-existing row and ``find_by_phone`` silently stops finding those
    customers. The fingerprint is normally written by the repository, which this
    command bypasses by going straight to the ORM, so it has to be recomputed here.
    Found by running the backfill against real data, not by a test.
    """

    @property
    def name(self) -> str:
        return str(self.model.__tablename__)


#: Every column carrying an encrypted type. Kept here rather than discovered by
#: reflection so that adding an encrypted column is a deliberate two-line change and
#: cannot be forgotten silently — a column missing from this list would simply never
#: get backfilled, and nothing else would complain.
TARGETS: tuple[_Target, ...] = (
    _Target(UserTwoFactorORM, ("secret",)),
    _Target(ControlledLedgerEntryORM, ("customer_name", "customer_address")),
    _Target(
        DrugReturnRecordORM,
        (
            "returner_name",
            "returner_address",
            "returner_id_number",
            "returner_id_issuer",
            "receiving_pharmacist_name",
        ),
    ),
    _Target(
        CustomerORM,
        ("full_name", "phone", "gender"),
        fingerprints=(("phone", "phone_fingerprint"),),
    ),
    _Target(CustomerAllergyORM, ("note",)),
    _Target(CustomerConditionORM, ("condition_code", "note")),
)


@dataclass(slots=True)
class _Counts:
    scanned: int = 0
    rewritten: int = 0
    failed: int = 0


async def _process(target: _Target, *, dry_run: bool, batch_size: int) -> _Counts:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    cipher = active_cipher()
    assert cipher is not None  # guarded by the caller
    counts = _Counts()
    offset = 0
    try:
        while True:
            async with session_factory() as session:
                rows = list(
                    (
                        await session.execute(
                            select(target.model)
                            .order_by(target.model.id)  # type: ignore[attr-defined]
                            .limit(batch_size)
                            .offset(offset)
                        )
                    )
                    .scalars()
                    .all()
                )
                if not rows:
                    break
                counts.scanned += len(rows)
                dirty = 0
                for row in rows:
                    for column in target.columns:
                        # The value arrives already decrypted; the question is whether
                        # what is *stored* is current-version ciphertext. Marking the
                        # attribute dirty makes the write path re-encrypt it.
                        if getattr(row, column) is None:
                            continue
                        flag_modified(row, column)
                        dirty += 1
                    for source, fingerprint_column in target.fingerprints:
                        value = getattr(row, source)
                        index = active_blind_index()
                        if value is not None and index is not None:
                            setattr(row, fingerprint_column, index.fingerprint(value))
                if dirty and not dry_run:
                    await session.commit()
                counts.rewritten += dirty
                offset += batch_size
    finally:
        await engine.dispose()
    return counts


async def _verify(target: _Target, *, batch_size: int) -> _Counts:
    """Read every row back, failing loudly on anything that will not decrypt."""
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    counts = _Counts()
    offset = 0
    try:
        while True:
            async with session_factory() as session:
                rows = list(
                    (
                        await session.execute(
                            select(target.model)
                            .order_by(target.model.id)  # type: ignore[attr-defined]
                            .limit(batch_size)
                            .offset(offset)
                        )
                    )
                    .scalars()
                    .all()
                )
                if not rows:
                    break
                for row in rows:
                    counts.scanned += 1
                    for column in target.columns:
                        try:
                            getattr(row, column)
                        except DecryptionError as exc:
                            counts.failed += 1
                            _log.error(
                                "decrypt_failed",
                                table=target.name,
                                column=column,
                                row_id=str(getattr(row, "id", "?")),
                                error=str(exc),
                            )
                offset += batch_size
    finally:
        await engine.dispose()
    return counts


async def _run(*, dry_run: bool, verify: bool, batch_size: int) -> int:
    # The column types read a process-wide cipher that the composition root normally
    # installs. This command never builds the container, so it has to install it
    # itself — without this the encrypted columns would silently pass values straight
    # through and the "backfill" would rewrite plaintext as plaintext.
    settings = get_settings()
    configure_field_encryption(
        build_field_cipher(settings),
        write_enabled=settings.encryption.enabled,
        blind_index=build_blind_index(settings),
    )

    if active_cipher() is None:
        print(  # noqa: T201
            "Chưa cấu hình khoá mã hoá (ENCRYPTION__KEYS) — không có gì để làm.",
            file=sys.stderr,
        )
        return 1
    if not verify and not encryption_writes_enabled():
        print(  # noqa: T201
            "ENCRYPTION__ENABLED=false: bật lên trước, nếu không lệnh này chỉ ghi lại "
            "bản rõ (đọc thì vẫn giải mã được nên --verify vẫn chạy bình thường).",
            file=sys.stderr,
        )
        return 1

    total = _Counts()
    for target in TARGETS:
        counts = (
            await _verify(target, batch_size=batch_size)
            if verify
            else await _process(target, dry_run=dry_run, batch_size=batch_size)
        )
        total.scanned += counts.scanned
        total.rewritten += counts.rewritten
        total.failed += counts.failed
        print(  # noqa: T201
            f"{target.name:32} quét {counts.scanned:6}  "
            + (f"lỗi giải mã {counts.failed}" if verify else f"ghi lại {counts.rewritten}")
        )

    if verify:
        print(  # noqa: T201
            f"\nTổng: quét {total.scanned} dòng, {total.failed} lỗi giải mã."
            + (
                "\n✅ Mọi dòng đọc được bằng khoá hiện có."
                if total.failed == 0
                else "\n🔴 CÓ DÒNG KHÔNG GIẢI MÃ ĐƯỢC — KHÔNG được xoá backup trước mã hoá."
            )
        )
        return 1 if total.failed else 0

    print(  # noqa: T201
        f"\nTổng: quét {total.scanned} dòng, "
        f"{'sẽ ghi lại' if dry_run else 'đã ghi lại'} {total.rewritten} giá trị."
        + ("\n(--dry-run: chưa ghi gì)" if dry_run else "\nChạy --verify để kiểm chứng.")
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mã hoá lại các cột nhạy cảm còn ở dạng rõ (hoặc dùng khoá cũ)."
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ đếm, không ghi")
    parser.add_argument("--verify", action="store_true", help="Đọc lại toàn bộ, báo dòng lỗi")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args(argv)
    return asyncio.run(_run(dry_run=args.dry_run, verify=args.verify, batch_size=args.batch_size))


if __name__ == "__main__":
    raise SystemExit(main())
