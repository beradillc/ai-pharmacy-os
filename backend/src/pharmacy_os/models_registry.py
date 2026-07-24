"""Import-side-effect aggregator: registers every ORM model on Base.metadata.

Lives at the package root (not in ``core``) so it may import business modules
without violating the kernel's "core knows no modules" contract. Alembic and
the integration test harness import this to see the full schema.
"""

from __future__ import annotations

import pharmacy_os.core.audit.models  # noqa: F401
import pharmacy_os.core.outbox.models  # noqa: F401
import pharmacy_os.modules.analytics.infrastructure.models  # noqa: F401
import pharmacy_os.modules.catalog.infrastructure.models  # noqa: F401
import pharmacy_os.modules.clinical.infrastructure.models  # noqa: F401
import pharmacy_os.modules.compliance.infrastructure.models  # noqa: F401
import pharmacy_os.modules.crm.infrastructure.models  # noqa: F401
import pharmacy_os.modules.iam.infrastructure.models  # noqa: F401
import pharmacy_os.modules.inventory.infrastructure.models  # noqa: F401
import pharmacy_os.modules.prescription.infrastructure.models  # noqa: F401
import pharmacy_os.modules.procurement.infrastructure.models  # noqa: F401
import pharmacy_os.modules.sales.infrastructure.models  # noqa: F401
from pharmacy_os.core.db.base import Base

__all__ = ["Base"]
