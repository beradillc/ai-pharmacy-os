"""At-rest encryption seen from the database side (Sprint 8, mục 3/4).

The unit tests prove the cipher is correct; these prove it is actually *reached*. The
failure this suite exists to catch is the one that looks fine everywhere else: the
application round-trips a value perfectly while the column still holds plaintext,
because the encrypted type was never wired in. So every assertion here reads the raw
column with the cipher turned off and looks at what is really stored.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.db import (
    configure_field_encryption,
    reset_field_encryption,
)
from pharmacy_os.core.security.crypto import KEY_BYTES, FieldCipher, KeyRing
from pharmacy_os.modules.compliance.infrastructure.models import (
    ControlledLedgerEntryORM,
    DrugReturnRecordORM,
)
from pharmacy_os.modules.iam.infrastructure.models import TenantORM, UserORM, UserTwoFactorORM

_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"  # a realistic 32-char base32 TOTP secret


@pytest.fixture
def cipher_on() -> Iterator[FieldCipher]:
    cipher = FieldCipher(KeyRing(keys={1: b"\x07" * KEY_BYTES}, current_version=1))
    configure_field_encryption(cipher, write_enabled=True)
    yield cipher
    reset_field_encryption()


@pytest.fixture
def cipher_off() -> Iterator[None]:
    reset_field_encryption()
    yield
    reset_field_encryption()


async def _insert_secret(
    session_factory: async_sessionmaker[AsyncSession], secret: str
) -> tuple[object, object]:
    """Write one 2FA row through the ORM; return (user_id, row_id).

    Creates the tenant and user it hangs off: ``user_two_factor.user_id`` is a real
    foreign key and the test harness enables ``PRAGMA foreign_keys=ON`` so SQLite
    enforces it the way Postgres does.
    """
    tenant_id, user_id, row_id = uuid4(), uuid4(), uuid4()
    async with session_factory() as session:
        session.add(TenantORM(id=tenant_id, name="Nhà thuốc Thử", status="ACTIVE"))
        session.add(
            UserORM(
                id=user_id,
                tenant_id=tenant_id,
                email=f"{user_id}@bera.vn",
                password_hash="x" * 60,
                full_name="Người Thử",
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add(
            UserTwoFactorORM(
                id=row_id,
                user_id=user_id,
                tenant_id=tenant_id,
                secret=secret,
                status="ACTIVE",
            )
        )
        await session.commit()
    return user_id, row_id


async def _raw_secret(session_factory: async_sessionmaker[AsyncSession], row_id: object) -> str:
    """Read the column as the database really holds it, bypassing the encrypted type.

    ``literal_column`` carries no type, so SQLAlchemy performs no result processing and
    the ciphertext comes back untouched — while the ``id`` predicate still goes through
    the table's own UUID column so it binds correctly on both dialects.
    """
    table = UserTwoFactorORM.__table__
    async with session_factory() as session:
        result = await session.execute(
            select(literal_column("secret")).select_from(table).where(table.c.id == row_id)
        )
        return str(result.scalar_one())


async def test_the_secret_is_ciphertext_in_the_column(
    session_factory: async_sessionmaker[AsyncSession], cipher_on: FieldCipher
) -> None:
    """The claim worth proving: a database dump does not contain the secret."""
    _, row_id = await _insert_secret(session_factory, _SECRET)

    stored = await _raw_secret(session_factory, row_id)

    assert _SECRET not in stored
    assert stored.startswith("v1:")
    assert cipher_on.decrypt(stored) == _SECRET


async def test_the_application_still_reads_the_plaintext_back(
    session_factory: async_sessionmaker[AsyncSession], cipher_on: FieldCipher
) -> None:
    _, row_id = await _insert_secret(session_factory, _SECRET)

    async with session_factory() as session:
        row = (
            await session.execute(select(UserTwoFactorORM).where(UserTwoFactorORM.id == row_id))
        ).scalar_one()
        assert row.secret == _SECRET


async def test_two_rows_with_the_same_secret_store_different_ciphertext(
    session_factory: async_sessionmaker[AsyncSession], cipher_on: FieldCipher
) -> None:
    """Otherwise a dump would reveal which accounts share a secret."""
    _, first = await _insert_secret(session_factory, _SECRET)
    _, second = await _insert_secret(session_factory, _SECRET)

    assert await _raw_secret(session_factory, first) != await _raw_secret(session_factory, second)


async def test_with_encryption_off_the_column_holds_plaintext(
    session_factory: async_sessionmaker[AsyncSession], cipher_off: None
) -> None:
    """Backward compatibility: a deployment that never turns the flag on is unchanged."""
    _, row_id = await _insert_secret(session_factory, _SECRET)

    assert await _raw_secret(session_factory, row_id) == _SECRET


async def test_plaintext_written_before_the_backfill_is_still_readable(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The property that makes a live backfill possible: after switching encryption on,
    rows written earlier must keep reading correctly rather than raising."""
    reset_field_encryption()
    _, row_id = await _insert_secret(session_factory, _SECRET)  # legacy plaintext row

    cipher = FieldCipher(KeyRing(keys={1: b"\x07" * KEY_BYTES}, current_version=1))
    configure_field_encryption(cipher, write_enabled=True)
    try:
        async with session_factory() as session:
            row = (
                await session.execute(select(UserTwoFactorORM).where(UserTwoFactorORM.id == row_id))
            ).scalar_one()
            assert row.secret == _SECRET
    finally:
        reset_field_encryption()


async def test_a_ciphertext_column_survives_the_declared_width(
    session_factory: async_sessionmaker[AsyncSession], cipher_on: FieldCipher
) -> None:
    """Guards the sizing mistake §7ap/§7aq were about: SQLite ignores varchar limits,
    so only an explicit length check catches a column that is too narrow for Postgres."""
    _, row_id = await _insert_secret(session_factory, _SECRET)

    stored = await _raw_secret(session_factory, row_id)
    declared = UserTwoFactorORM.__table__.c.secret.type.length
    assert len(stored) <= declared, f"ciphertext {len(stored)} vượt cột {declared}"


# --- compliance PII -----------------------------------------------------------
#
# The sharpest data in the system: a patient's name and address against a
# controlled-substance purchase (PL XIX), and the returner's **national ID number**
# (PL XVIII). A dump containing these is a reportable personal-data breach, not an
# inconvenience.


async def _raw_column(
    session_factory: async_sessionmaker[AsyncSession], table: object, column: str, row_id: object
) -> str:
    async with session_factory() as session:
        result = await session.execute(
            select(literal_column(column)).select_from(table).where(table.c.id == row_id)  # type: ignore[attr-defined]
        )
        return str(result.scalar_one())


async def test_a_patients_name_and_address_are_ciphertext_in_the_ledger(
    session_factory: async_sessionmaker[AsyncSession], cipher_on: FieldCipher
) -> None:
    row_id = uuid4()
    async with session_factory() as session:
        session.add(
            ControlledLedgerEntryORM(
                id=row_id,
                tenant_id=uuid4(),
                branch_id=uuid4(),
                drug_id=uuid4(),
                category="HUONG_THAN",
                direction="XUAT",
                quantity=Decimal("2"),
                lot_no="L2026",
                expiry_date=date(2028, 1, 1),
                transaction_at=datetime(2026, 7, 26, 10, 0, tzinfo=UTC),
                source_or_destination="Nhà thuốc Bera",
                document_no="PXK-001",
                customer_name="Nguyễn Thị Hoà",
                customer_address="12 Lê Lợi, Quận 1",
            )
        )
        await session.commit()

    table = ControlledLedgerEntryORM.__table__
    name = await _raw_column(session_factory, table, "customer_name", row_id)
    address = await _raw_column(session_factory, table, "customer_address", row_id)

    assert "Nguyễn Thị Hoà" not in name
    assert "Lê Lợi" not in address
    assert cipher_on.decrypt(name) == "Nguyễn Thị Hoà"
    assert cipher_on.decrypt(address) == "12 Lê Lợi, Quận 1"


async def test_the_returners_national_id_is_ciphertext(
    session_factory: async_sessionmaker[AsyncSession], cipher_on: FieldCipher
) -> None:
    """The single most sensitive identifier the system stores."""
    row_id = uuid4()
    async with session_factory() as session:
        session.add(
            DrugReturnRecordORM(
                id=row_id,
                tenant_id=uuid4(),
                branch_id=uuid4(),
                returner_name="Trần Văn B",
                returner_address="5 Nguyễn Huệ",
                returner_id_number="079201001234",
                returner_id_issuer="Công an TP.HCM",
                returner_id_issued_at=date(2020, 5, 1),
                returner_is_patient=True,
                receiving_pharmacist_name="DS. Lê Thị C",
                handover_at=datetime(2026, 7, 26, 9, 0, tzinfo=UTC),
                handover_location="Quầy thuốc",
            )
        )
        await session.commit()

    table = DrugReturnRecordORM.__table__
    id_number = await _raw_column(session_factory, table, "returner_id_number", row_id)

    assert "079201001234" not in id_number
    assert cipher_on.decrypt(id_number) == "079201001234"


async def test_compliance_pii_reads_back_as_plaintext_through_the_orm(
    session_factory: async_sessionmaker[AsyncSession], cipher_on: FieldCipher
) -> None:
    """Encryption must be invisible above the storage boundary, or every rule that
    reads these values would have to know about ciphertext."""
    row_id = uuid4()
    async with session_factory() as session:
        session.add(
            DrugReturnRecordORM(
                id=row_id,
                tenant_id=uuid4(),
                branch_id=uuid4(),
                returner_name="Trần Văn B",
                returner_address="5 Nguyễn Huệ",
                returner_id_number="079201001234",
                returner_id_issuer="Công an TP.HCM",
                returner_id_issued_at=date(2020, 5, 1),
                returner_is_patient=True,
                receiving_pharmacist_name="DS. Lê Thị C",
                handover_at=datetime(2026, 7, 26, 9, 0, tzinfo=UTC),
                handover_location="Quầy thuốc",
            )
        )
        await session.commit()

    async with session_factory() as session:
        row = (
            await session.execute(
                select(DrugReturnRecordORM).where(DrugReturnRecordORM.id == row_id)
            )
        ).scalar_one()
        assert row.returner_name == "Trần Văn B"
        assert row.returner_id_number == "079201001234"
        assert row.receiving_pharmacist_name == "DS. Lê Thị C"


@pytest.fixture(autouse=True)
async def _isolate_cipher() -> AsyncIterator[None]:
    """The cipher is process-wide state; never let one test leak into the next."""
    yield
    reset_field_encryption()


# --- CRM: encryption must not break the lookup it sits on top of ---------------


async def _customer_repo(
    session_factory: async_sessionmaker[AsyncSession], tenant_id: object
) -> object:
    from pharmacy_os.core.context import RequestContext
    from pharmacy_os.modules.crm.infrastructure.repository import SqlAlchemyCustomerRepository

    session = session_factory()
    ctx = RequestContext(
        tenant_id=tenant_id, branch_id=uuid4(), user_id=uuid4(), permissions=frozenset()
    )
    return SqlAlchemyCustomerRepository(session, ctx), session


async def test_find_by_phone_still_works_against_an_encrypted_column(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The point of the blind index. A randomised ciphertext differs on every write, so
    without a fingerprint ``WHERE phone = ?`` could never match and the pharmacy would
    lose customer lookup entirely."""
    from pharmacy_os.core.security.crypto import BlindIndex
    from pharmacy_os.modules.crm.domain import Customer

    cipher = FieldCipher(KeyRing(keys={1: b"\x07" * KEY_BYTES}, current_version=1))
    configure_field_encryption(
        cipher, write_enabled=True, blind_index=BlindIndex(b"\x09" * KEY_BYTES)
    )
    try:
        tenant_id = uuid4()
        repo, session = await _customer_repo(session_factory, tenant_id)
        async with session:
            await repo.add(Customer(full_name="Trần Thị D", phone="0912345678"))
            await session.commit()

            found = await repo.find_by_phone("0912345678")
            assert found is not None
            assert found.phone == "0912345678"

            # Typed with spaces — normalisation must still find the same customer.
            assert (await repo.find_by_phone("0912 345 678")) is not None
            assert (await repo.find_by_phone("0900000000")) is None
    finally:
        reset_field_encryption()


async def test_the_phone_is_ciphertext_but_the_fingerprint_is_searchable(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from pharmacy_os.core.security.crypto import BlindIndex
    from pharmacy_os.modules.crm.domain import Customer
    from pharmacy_os.modules.crm.infrastructure.models import CustomerORM

    cipher = FieldCipher(KeyRing(keys={1: b"\x07" * KEY_BYTES}, current_version=1))
    configure_field_encryption(
        cipher, write_enabled=True, blind_index=BlindIndex(b"\x09" * KEY_BYTES)
    )
    try:
        tenant_id = uuid4()
        customer = Customer(full_name="Trần Thị D", phone="0912345678")
        repo, session = await _customer_repo(session_factory, tenant_id)
        async with session:
            await repo.add(customer)
            await session.commit()

        table = CustomerORM.__table__
        stored_phone = await _raw_column(session_factory, table, "phone", customer.id)
        fingerprint = await _raw_column(session_factory, table, "phone_fingerprint", customer.id)

        assert "0912345678" not in stored_phone
        assert cipher.decrypt(stored_phone) == "0912345678"
        # The fingerprint is searchable but must not be the number itself.
        assert "0912345678" not in fingerprint
        assert len(fingerprint) == 64
    finally:
        reset_field_encryption()


async def test_find_by_phone_works_with_encryption_off(
    session_factory: async_sessionmaker[AsyncSession], cipher_off: None
) -> None:
    """Backward compatibility: a deployment that never enables encryption is unchanged,
    and the lookup falls back to comparing the column directly."""
    from pharmacy_os.modules.crm.domain import Customer

    tenant_id = uuid4()
    repo, session = await _customer_repo(session_factory, tenant_id)
    async with session:
        await repo.add(Customer(full_name="Trần Thị D", phone="0912345678"))
        await session.commit()
        assert (await repo.find_by_phone("0912345678")) is not None
