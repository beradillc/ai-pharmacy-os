"""Location domain: sơ đồ kho (Kho → Khu → Kệ → Ô). Framework-free."""

from pharmacy_os.modules.location.domain.entities import (
    MAX_CODE_LENGTH,
    PATH_SEPARATOR,
    Location,
    LocationKind,
    normalize_code,
)
from pharmacy_os.modules.location.domain.exceptions import (
    DuplicateLocationCodeError,
    InvalidLocationCodeError,
    InvalidLocationNestingError,
    LocationError,
    LocationHasChildrenError,
)
from pharmacy_os.modules.location.domain.ports import LocationRepository

__all__ = [
    "MAX_CODE_LENGTH",
    "PATH_SEPARATOR",
    "Location",
    "LocationKind",
    "normalize_code",
    "DuplicateLocationCodeError",
    "InvalidLocationCodeError",
    "InvalidLocationNestingError",
    "LocationError",
    "LocationHasChildrenError",
    "LocationRepository",
]
