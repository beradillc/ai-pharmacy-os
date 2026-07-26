"""Database engine, declarative base and the Unit of Work."""

from pharmacy_os.core.db.base import Base
from pharmacy_os.core.db.encrypted_types import (
    EncryptedString,
    EncryptedText,
    active_cipher,
    configure_field_encryption,
    encryption_writes_enabled,
    reset_field_encryption,
)
from pharmacy_os.core.db.session import build_engine, build_sessionmaker
from pharmacy_os.core.db.uow import (
    OutboxSink,
    SqlAlchemyUnitOfWork,
    StagedEvent,
    UnitOfWork,
    UnitOfWorkFactory,
)

__all__ = [
    "Base",
    "EncryptedString",
    "EncryptedText",
    "active_cipher",
    "configure_field_encryption",
    "encryption_writes_enabled",
    "reset_field_encryption",
    "build_engine",
    "build_sessionmaker",
    "OutboxSink",
    "SqlAlchemyUnitOfWork",
    "StagedEvent",
    "UnitOfWork",
    "UnitOfWorkFactory",
]
