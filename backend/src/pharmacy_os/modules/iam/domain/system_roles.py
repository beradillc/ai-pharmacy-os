"""The five seeded system roles and their permission sets (docs/15 §5 Q5, duyệt 2026-07-23).

Code is the single source of truth: :mod:`seeds.bootstrap_tenant` materialises these
rows, so a deployment never carries hand-edited role data. Roles are named after real
pharmacy job titles rather than permission groups because the pharmacy owner is the
one assigning them — and because Luật 44/2024 Điều 17a already names the two
professional roles (cấp chuỗi vs cấp nhà thuốc), so following the statute keeps the
mapping defensible in an inspection.

``ALL_PERMISSIONS`` is the audited list of every code passed to
``core.security.rbac.require_permission`` across the eight business modules (38 as of
2026-07-23, incl. ``sales.return``, ``inventory.reconcile``), plus the six ``iam.*`` codes this
module introduces. It intentionally includes the six ``compliance.*`` codes that
``api/deps.py._DEV_PERMISSIONS`` was missing (docs/15 §0 F3).
"""

from __future__ import annotations

from dataclasses import dataclass

CATALOG_PERMISSIONS = frozenset({"catalog.read", "catalog.create"})
INVENTORY_PERMISSIONS = frozenset(
    {"inventory.read", "inventory.receive", "inventory.dispense", "inventory.reconcile"}
)
SALES_PERMISSIONS = frozenset({"sales.read", "sales.create", "sales.return"})
RX_PERMISSIONS = frozenset({"rx.read", "rx.create", "rx.approve", "rx.dispense"})
CLINICAL_PERMISSIONS = frozenset(
    {"clinical.check", "clinical.accept", "clinical.settings.read", "clinical.settings.write"}
)
CRM_PERMISSIONS = frozenset(
    {
        "crm.create",
        "crm.read",
        "crm.write",
        # Recording a consent decision is not the same authority as reading the data
        # it unlocks: counter staff take the decision at the till, but must not be
        # able to read what it authorises (Luật 91/2025 Điều 9 · NĐ356 Điều 4.2).
        "crm.consent.manage",
        # Reading and writing the health data itself is a separate authority from
        # touching the customer record (NĐ356 Điều 4.2).
        "crm.sensitive.read",
        "crm.sensitive.write",
        # Erasure is destructive and irreversible; kept away from branch staff.
        "crm.erase",
    }
)
COMPLIANCE_PERMISSIONS = frozenset(
    {
        "compliance.config.read",
        "compliance.config.write",
        "compliance.ledger.read",
        "compliance.ledger.write",
        "compliance.sync.read",
        "compliance.sync.push",
    }
)
PROCUREMENT_PERMISSIONS = frozenset(
    {
        "procurement.supplier.read",
        "procurement.supplier.create",
        "procurement.po.read",
        "procurement.po.create",
        "procurement.po.write",
        "procurement.grn.read",
        "procurement.grn.create",
        "procurement.grn.confirm",
    }
)
AUDIT_PERMISSIONS = frozenset({"audit.read"})
PRIVACY_PERMISSIONS = frozenset({"privacy.dpia.read"})
"""Reading the processing record: the input to a tenant's DPIA filing, so it belongs
with whoever answers to the regulator, not with counter staff."""

"""Reading the trail is itself privileged: it names who touched patient data."""

IAM_PERMISSIONS = frozenset(
    {
        "iam.user.read",
        "iam.user.create",
        "iam.user.write",
        "iam.role.read",
        "iam.role.write",
        "iam.role.assign",
    }
)

ALL_PERMISSIONS: frozenset[str] = (
    CATALOG_PERMISSIONS
    | INVENTORY_PERMISSIONS
    | SALES_PERMISSIONS
    | RX_PERMISSIONS
    | CLINICAL_PERMISSIONS
    | CRM_PERMISSIONS
    | COMPLIANCE_PERMISSIONS
    | PROCUREMENT_PERMISSIONS
    | IAM_PERMISSIONS
    | AUDIT_PERMISSIONS
    | PRIVACY_PERMISSIONS
)

SYSTEM_ADMIN = "system_admin"
CHAIN_PHARMACIST = "chain_pharmacist"
BRANCH_PHARMACIST = "branch_pharmacist"
CASHIER = "cashier"
WAREHOUSE = "warehouse"


@dataclass(frozen=True, slots=True)
class SystemRoleSpec:
    """A seedable role definition. ``chain_level`` documents the intended scope —
    it is guidance for whoever assigns the role, not an enforced constraint: the
    scope of a grant is decided per :class:`RoleAssignment` (branch_id NULL or not).
    """

    code: str
    name: str
    description: str
    permissions: frozenset[str]
    chain_level: bool


#: Chain-level professional: everything a branch pharmacist may do, plus the
#: business-wide switches (drug master, AI toggle, compliance config) and read
#: access to the user list. Cannot create users or edit roles — that stays with
#: ``system_admin`` so a single professional account cannot silently widen itself.
_CHAIN_PHARMACIST_PERMISSIONS = (
    CATALOG_PERMISSIONS
    | INVENTORY_PERMISSIONS
    | SALES_PERMISSIONS
    | RX_PERMISSIONS
    | CLINICAL_PERMISSIONS
    | CRM_PERMISSIONS
    | COMPLIANCE_PERMISSIONS
    | PROCUREMENT_PERMISSIONS
    | AUDIT_PERMISSIONS
    | PRIVACY_PERMISSIONS
    | {"iam.user.read", "iam.role.read"}
)

#: Branch-level professional. Excludes the chain-wide switches: ``catalog.create``
#: (drug master stays consistent across the chain), ``clinical.settings.write`` and
#: ``compliance.config.write`` (business-level decisions), and
#: ``procurement.supplier.create``.
_BRANCH_PHARMACIST_PERMISSIONS = (
    (CATALOG_PERMISSIONS - {"catalog.create"})
    | INVENTORY_PERMISSIONS
    | SALES_PERMISSIONS
    | RX_PERMISSIONS
    | (CLINICAL_PERMISSIONS - {"clinical.settings.write"})
    # Erasure is irreversible and answers a legal request, not a clinical need:
    # it stays with the chain, like the other business-level switches.
    | (CRM_PERMISSIONS - {"crm.erase"})
    | (COMPLIANCE_PERMISSIONS - {"compliance.config.write"})
    | (PROCUREMENT_PERMISSIONS - {"procurement.supplier.create"})
)

#: Counter staff. No ``rx.approve``/``rx.dispense``: validating and handing over a
#: prescription-only medicine is a pharmacist act (Luật Dược Điều 6.5.h) — a legal
#: constraint, not a configuration preference. ``crm.read``/``crm.create`` and
#: ``crm.consent.manage`` are granted (docs/15 §7n Q4, hồ sơ sức khỏe KH Bước 4):
#: taking a consent decision at the till is a distinct authority from reading what
#: it unlocks, so cashier can see the person and record consent but never
#: ``crm.sensitive.read``/``crm.sensitive.write``/``crm.erase`` — those stay
#: pharmacist-only, split by NĐ356 Điều 4.2 and GPP TT02/2018 I-1a.III.4.a.
_CASHIER_PERMISSIONS = (
    {"catalog.read", "inventory.read", "inventory.dispense"}
    | SALES_PERMISSIONS
    | {"rx.read"}
    | {"crm.read", "crm.create", "crm.consent.manage"}
)

#: Stock/purchasing staff: goods in, no selling, no patient data at all. Gets
#: ``inventory.reconcile`` too — GRN lot collisions/failures are exactly the
#: discrepancies this role's own goods-receipt work produces.
_WAREHOUSE_PERMISSIONS = {
    "catalog.read",
    "inventory.read",
    "inventory.receive",
    "inventory.reconcile",
} | PROCUREMENT_PERMISSIONS

SYSTEM_ROLES: tuple[SystemRoleSpec, ...] = (
    SystemRoleSpec(
        code=SYSTEM_ADMIN,
        name="Quản trị hệ thống",
        description="Toàn quyền kỹ thuật trên tenant, gồm quản lý người dùng và vai trò.",
        permissions=ALL_PERMISSIONS,
        chain_level=True,
    ),
    SystemRoleSpec(
        code=CHAIN_PHARMACIST,
        name="Người chịu trách nhiệm chuyên môn cấp chuỗi",
        description=(
            "Dược sĩ phụ trách chuyên môn toàn chuỗi (Luật 44/2024 Điều 17a): nghiệp vụ "
            "toàn hệ thống + cấu hình cấp doanh nghiệp, không sửa được người dùng/vai trò."
        ),
        permissions=frozenset(_CHAIN_PHARMACIST_PERMISSIONS),
        chain_level=True,
    ),
    SystemRoleSpec(
        code=BRANCH_PHARMACIST,
        name="Dược sĩ phụ trách nhà thuốc",
        description=(
            "Dược sĩ phụ trách chuyên môn một nhà thuốc (Luật 44/2024 Điều 17a, GPP "
            "TT02/2018): bán, duyệt và cấp phát thuốc kê đơn tại chi nhánh được gán."
        ),
        permissions=frozenset(_BRANCH_PHARMACIST_PERMISSIONS),
        chain_level=False,
    ),
    SystemRoleSpec(
        code=CASHIER,
        name="Nhân viên bán thuốc / thu ngân",
        description=(
            "Bán hàng tại quầy. Không duyệt/cấp phát thuốc kê đơn và không truy cập "
            "hồ sơ bệnh của khách hàng."
        ),
        permissions=frozenset(_CASHIER_PERMISSIONS),
        chain_level=False,
    ),
    SystemRoleSpec(
        code=WAREHOUSE,
        name="Thủ kho / nhân viên nhập hàng",
        description="Nhà cung cấp, đơn mua, nhập kho. Không bán hàng, không dữ liệu bệnh nhân.",
        permissions=frozenset(_WAREHOUSE_PERMISSIONS),
        chain_level=False,
    ),
)

SYSTEM_ROLES_BY_CODE: dict[str, SystemRoleSpec] = {spec.code: spec for spec in SYSTEM_ROLES}
