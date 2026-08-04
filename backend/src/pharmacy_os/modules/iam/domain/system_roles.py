"""The five seeded system roles and their permission sets (docs/15 §5 Q5, duyệt 2026-07-23).

Code is the single source of truth: :mod:`seeds.bootstrap_tenant` materialises these
rows, so a deployment never carries hand-edited role data. Roles are named after real
pharmacy job titles rather than permission groups because the pharmacy owner is the
one assigning them — and because Luật 44/2024 Điều 17a already names the two
professional roles (cấp chuỗi vs cấp nhà thuốc), so following the statute keeps the
mapping defensible in an inspection.

``ALL_PERMISSIONS`` is the audited list of every code passed to
``core.security.rbac.require_permission`` across the eight business modules (39 as of
2026-07-25, incl. ``sales.return``, ``inventory.reconcile``, ``compliance.ledger.sign`` added
for TT18 bước 6 ký sổ điện tử), plus the six ``iam.*`` codes this module introduces and the two
kernel-audit codes (``audit.read`` query + ``audit.dashboard.read`` dashboard, the latter added
2026-07-24 for the Sprint 7 audit dashboard). It intentionally includes the ``compliance.*``
codes that ``api/deps.py._DEV_PERMISSIONS`` was missing (docs/15 §0 F3).
"""

from __future__ import annotations

from dataclasses import dataclass

#: ``catalog.update`` (2026-07-30) là quyền **sửa hồ sơ thuốc đã tạo** — cụ thể là danh
#: sách hoạt chất, đường duy nhất làm cảnh báo dị ứng ngừng kêu. Tách khỏi ``catalog.create``
#: vì hai việc khác nhau về hậu quả: tạo sai thì thuốc mới chưa ai bán, sửa sai thì mọi
#: cảnh báo đang chạy trên thuốc đó đổi hành vi ngay.
CATALOG_PERMISSIONS = frozenset({"catalog.read", "catalog.create", "catalog.update"})
INVENTORY_PERMISSIONS = frozenset(
    {"inventory.read", "inventory.receive", "inventory.dispense", "inventory.reconcile"}
)
SALES_PERMISSIONS = frozenset({"sales.read", "sales.create", "sales.return"})
#: Gross margin — revenue minus cost of goods (ROADMAP V3-7a, 2026-08-04). Split from
#: ``sales.read`` deliberately: ``sales.read`` already lets a cashier see *what sold*
#: (POS UI shows that today), but nothing today shows *how much it cost the pharmacy*
#: — a cashier or warehouse clerk seeing exact purchase cost/margin per sale is a
#: commercial-sensitivity escalation the reused-permission reasoning in V3-5/ADR-0005
#: does NOT cover (that reuse was justified because revenue export "is not more
#: sensitive than what the POS/inventory UI already shows"; profit margin is not
#: already shown anywhere). Chain-level only — see ``docs/adr/ADR-0006``.
PROFIT_PERMISSIONS = frozenset({"sales.profit.read"})
#: ``rx.image.read`` (2026-07-31, Chain duyệt khuyến nghị GĐ) tách khỏi ``rx.read`` vì ảnh
#: đơn thuốc mang **chẩn đoán** — đúng thứ ``crm.sensitive.read`` cố ý không cấp cho thu
#: ngân. Để chung sẽ mở một đường vòng qua ranh giới quyền đó: thu ngân không đọc được hồ
#: sơ sức khoẻ của khách, nhưng lại xem được ảnh ghi rõ bệnh của họ.
#: Gắn ảnh là việc của quầy (``rx.create``); đọc chẩn đoán thì không.
RX_PERMISSIONS = frozenset({"rx.read", "rx.create", "rx.approve", "rx.dispense", "rx.image.read"})

#: Quyền **PHẠM VI**, không phải quyền nội dung (2026-07-31, Chain giao mục Lưu trữ).
#:
#: Hai câu hỏi độc lập, cố ý tách:
#:   · ``rx.image.read``      — *được xem LOẠI dữ liệu gì*
#:   · ``archive.read.chain`` — *được xem của MẤY chi nhánh*
#:
#: Vì sao phải thêm chứ không mượn tạm một quyền cấp chuỗi sẵn có làm dấu hiệu:
#: ``RequestContext`` chỉ mang MỘT ``branch_id`` lấy từ JWT, không có cờ nào nói người này
#: thuộc cấp chuỗi — và ``SystemRoleSpec.chain_level`` tự khai trong docstring rằng nó là
#: ghi chú cho người gán vai, **không phải ràng buộc được cưỡng chế**. Mượn ``catalog.update``
#: hay ``crm.pii.reveal`` làm dấu hiệu phạm vi là ghép ngầm hai khái niệm không liên quan:
#: người sửa sau sẽ không đoán ra vì sao sửa quyền danh mục lại làm lộ ảnh đơn thuốc của
#: chi nhánh khác.
#:
#: Quyền này KHÔNG mở thêm loại dữ liệu nào — nó chỉ nới chiều chi nhánh cho những loại mà
#: người gọi vốn đã có quyền đọc.
ARCHIVE_PERMISSIONS = frozenset({"archive.read.chain"})

#: Sơ đồ kho (BERAS V2 Phase 1). Tách ĐỌC khỏi GHI vì hai việc khác hẳn nhau: ai đứng quầy
#: cũng cần biết thuốc nằm ở đâu, còn dựng lại sơ đồ kho là việc quản lý — một lần đổi sai
#: thứ tự lấy hàng làm cả kho đi sai đường.
LOCATION_PERMISSIONS = frozenset({"location.read", "location.write"})
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
        # Xem ĐẦY ĐỦ số điện thoại khách (Chain chốt 2026-07-31). Danh sách khách chỉ
        # trả ba số cuối; quyền này mở nốt phần còn lại, và chỉ cấp chuỗi mới có.
        # Tách khỏi ``crm.sensitive.read``: quyền đó là dữ liệu SỨC KHOẺ và cả dược sĩ
        # chi nhánh đều giữ — gộp vào thì "chỉ Chủ chuỗi xem được" thành sai ngay.
        "crm.pii.reveal",
    }
)
COMPLIANCE_PERMISSIONS = frozenset(
    {
        "compliance.config.read",
        "compliance.config.write",
        "compliance.ledger.read",
        "compliance.ledger.write",
        # Ký xác nhận điện tử sổ kiểm soát đặc biệt (TT18 Điều 15.1.d, hướng A — docs/13 mục
        # C.5). Tách khỏi ``.write``: chỉ "người chịu trách nhiệm chuyên môn về dược" (Luật
        # 44/2024 Điều 17a) ký được, không mở cho thu ngân/thủ kho dù họ ghi được sổ ở nhóm
        # quyền khác — nhưng ở đây, ai ghi được sổ (``.write``) thì cũng thuộc nhóm ký được,
        # nên cả hai role dược sĩ đều giữ cả 2 quyền như nhau (docs/features/tt18-kiem-soat-
        # dac-biet/02_DECISIONS_KY_SO.md, GĐ quyết dưới ủy quyền 2026-07-25).
        "compliance.ledger.sign",
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
AUDIT_DASHBOARD_PERMISSIONS = frozenset({"audit.dashboard.read"})
#: Analytics (Sprint 7, PROJECT_STATE §7am/§7ap): reading the dashboard/suggestions vs
#: running a reorder + turning a suggestion into a draft PO. A management surface —
#: granted to admin/chain/branch, never cashier/warehouse (Chain duyệt 2026-07-25).
ANALYTICS_PERMISSIONS = frozenset({"analytics.read", "analytics.reorder.run"})
"""The audit **dashboard** — a distinct authority from the raw ``audit.read`` query.

Split so a branch manager can be given the investigation/inspection lens over their
own tenant's trail without also holding the raw query permission (PROJECT_STATE §7ak,
duyệt GĐ full-auto 2026-07-24). The dashboard is itself a sensitive surface: the
trail names who read whose health record, so this is deliberately kept away from
counter/warehouse staff and granted only to the two professional roles + admin.
"""
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
        "iam.delegation.grant",
        "iam.delegation.read",
    }
)
"""``iam.delegation.grant`` là quyền **cấp** uỷ quyền quản trị có thời hạn (Chain chốt
2026-08-03), ``iam.delegation.read`` là quyền **đọc** sổ uỷ quyền.

🔴 Xem :data:`_SYSTEM_ADMIN_PERMISSIONS`: quyền *cấp* là quyền duy nhất bị giữ **ngoài**
vai quản trị hệ thống, và lý do nằm ở đó."""

ALL_PERMISSIONS: frozenset[str] = (
    CATALOG_PERMISSIONS
    | INVENTORY_PERMISSIONS
    | SALES_PERMISSIONS
    | PROFIT_PERMISSIONS
    | RX_PERMISSIONS
    | CLINICAL_PERMISSIONS
    | CRM_PERMISSIONS
    | COMPLIANCE_PERMISSIONS
    | PROCUREMENT_PERMISSIONS
    | IAM_PERMISSIONS
    | AUDIT_PERMISSIONS
    | AUDIT_DASHBOARD_PERMISSIONS
    | ARCHIVE_PERMISSIONS
    | LOCATION_PERMISSIONS
    | PRIVACY_PERMISSIONS
    | ANALYTICS_PERMISSIONS
)

_SYSTEM_ADMIN_PERMISSIONS = ALL_PERMISSIONS - {"iam.delegation.grant"}
"""🔴 **Quyền duy nhất vai quản trị hệ thống KHÔNG có** (Chain chốt 2026-08-03).

Cho tới bản này ``system_admin`` giữ đúng **56/56** quyền — đã kiểm bằng lệnh, không suy:
``sa.permissions == ALL_PERMISSIONS`` trả ``True``. Nếu ``iam.delegation.grant`` cứ thế đi
vào :data:`IAM_PERMISSIONS` thì tài khoản kỹ thuật **tự cấp được** quyền nghiệp vụ cho tài
khoản kỹ thuật — tức chính cơ chế uỷ quyền mất nghĩa ngay khi vừa dựng xong.

**Luật "không tự uỷ quyền cho chính mình" KHÔNG chặn được đường này**, và chỗ này đúng là
chỗ dễ tưởng nhầm là đã chặn: luật ấy chỉ so ``nguoi_cap_id != nguoi_nhan_id``, nên **hai**
tài khoản quản trị cấp chéo cho nhau là hợp lệ với mọi luật domain hiện có. Cùng một hình
dạng lỗi đã bắt được ở bước 2/5 (*"chủ chuỗi không có quyền ký nên ràng buộc tự chặn"* —
`grep` cho thấy chủ chuỗi **có**): *"ràng buộc A tự nhiên kéo theo tính chất B"* là một
**giả định**, không phải một suy luận.

Đây **không** phải phương án "cắt quyền" mà Chain đã bác. Chain bác việc cắt quyền **đọc
dữ liệu** của người bảo trì, vì làm việc mù thì họ mở ``psql`` — không vết. Ở đây không
quyền dữ liệu nào bị lấy đi: người bảo trì vẫn nhận đủ 25 quyền dữ liệu **qua uỷ quyền**.
Thứ bị lấy đi là quyền **tự ký giấy cho mình** — đúng điều kiện Chain đặt ra: *"chủ chuỗi
sẽ chịu trách nhiệm"*. Một người vừa cấp vừa dùng thì không còn ai chịu trách nhiệm.

Hệ quả vận hành phải nói thẳng: ở quầy một người, Chain cần **hai tài khoản** — một
``chain_pharmacist`` để cấp, một ``system_admin`` để dùng. Điều đó đã là hệ quả bắt buộc
của luật 1 trong :func:`~pharmacy_os.modules.iam.domain.delegation.tao_uy_quyen` từ bước
2/5, bản này không thêm ràng buộc mới nào cho Chain."""

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
    # Chủ chuỗi xem báo cáo lợi nhuận (ROADMAP V3-7a) — dược sĩ chi nhánh/thu ngân/thủ
    # kho không, xem ghi chú ở `PROFIT_PERMISSIONS`.
    | PROFIT_PERMISSIONS
    | RX_PERMISSIONS
    | CLINICAL_PERMISSIONS
    | CRM_PERMISSIONS
    | COMPLIANCE_PERMISSIONS
    | PROCUREMENT_PERMISSIONS
    | AUDIT_PERMISSIONS
    | AUDIT_DASHBOARD_PERMISSIONS
    # Chủ chuỗi xem Lưu trữ của TOÀN BỘ chi nhánh (Chain chốt 2026-07-31) — đây là vai duy
    # nhất ngoài quản trị hệ thống có quyền phạm vi này. Dược sĩ chi nhánh chỉ thấy chi
    # nhánh mình: xem ghi chú ở `ARCHIVE_PERMISSIONS`.
    | ARCHIVE_PERMISSIONS
    | LOCATION_PERMISSIONS
    | PRIVACY_PERMISSIONS
    | ANALYTICS_PERMISSIONS
    # Chủ chuỗi là người CẤP uỷ quyền quản trị và người đọc lại sổ ấy — xem
    # `_SYSTEM_ADMIN_PERMISSIONS` để biết vì sao quyền cấp không nằm ở vai quản trị.
    | {"iam.user.read", "iam.role.read", "iam.delegation.grant", "iam.delegation.read"}
)

#: Branch-level professional. Excludes the chain-wide switches: ``catalog.create`` and
#: ``catalog.update`` (drug master stays consistent across the chain — sửa hoạt chất ở một
#: chi nhánh sẽ đổi hành vi cảnh báo dị ứng của **toàn chuỗi**, đó là quyết định cấp chuỗi),
#: ``clinical.settings.write`` and ``compliance.config.write`` (business-level decisions),
#: and ``procurement.supplier.create``.
_BRANCH_PHARMACIST_PERMISSIONS = (
    (CATALOG_PERMISSIONS - {"catalog.create", "catalog.update"})
    # Dược sĩ chi nhánh dựng được sơ đồ kho CỦA CHI NHÁNH MÌNH: người xếp kho là người
    # biết kệ nào đối lưng kệ nào. Vị trí đã theo chi nhánh nên không có đường nào chạm
    # sang cơ sở khác.
    | LOCATION_PERMISSIONS
    | INVENTORY_PERMISSIONS
    | SALES_PERMISSIONS
    | RX_PERMISSIONS
    | (CLINICAL_PERMISSIONS - {"clinical.settings.write"})
    # Erasure is irreversible and answers a legal request, not a clinical need:
    # it stays with the chain, like the other business-level switches.
    | (CRM_PERMISSIONS - {"crm.erase", "crm.pii.reveal"})
    | (COMPLIANCE_PERMISSIONS - {"compliance.config.write"})
    | (PROCUREMENT_PERMISSIONS - {"procurement.supplier.create"})
    # The audit **dashboard** (not the raw ``audit.read`` query): a branch manager
    # must be able to investigate/inspect their own branch's trail. The lower-level
    # ``audit.read`` stays chain-only — this role gets the lens, not the raw query.
    | AUDIT_DASHBOARD_PERMISSIONS
    # Reorder analytics + dashboard for their own branch (Chain duyệt PA, §7am).
    | ANALYTICS_PERMISSIONS
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
    {"catalog.read", "inventory.read", "inventory.dispense", "location.read"}
    | SALES_PERMISSIONS
    # ``rx.read`` nhưng KHÔNG ``rx.image.read``: thu ngân cần biết đơn có hợp lệ để bán
    # hay không, không cần đọc chẩn đoán của khách. Xem ghi chú ở ``RX_PERMISSIONS``.
    | {"rx.read"}
    | {"crm.read", "crm.create", "crm.consent.manage"}
)

#: Stock/purchasing staff: goods in, no selling, no patient data at all. Gets
#: ``inventory.reconcile`` too — GRN lot collisions/failures are exactly the
#: discrepancies this role's own goods-receipt work produces.
_WAREHOUSE_PERMISSIONS = {
    "catalog.read",
    # Nhân viên kho ĐỌC được sơ đồ nhưng không dựng lại được nó — nhập hàng cần biết chỗ,
    # đổi cấu trúc kho là quyết định khác.
    "location.read",
    "inventory.read",
    "inventory.receive",
    "inventory.reconcile",
} | PROCUREMENT_PERMISSIONS

SYSTEM_ROLES: tuple[SystemRoleSpec, ...] = (
    SystemRoleSpec(
        code=SYSTEM_ADMIN,
        name="Quản trị hệ thống",
        description=(
            "Toàn quyền kỹ thuật trên tenant, gồm quản lý người dùng và vai trò. Không tự "
            "cấp được uỷ quyền quản trị — quyền đó thuộc chủ chuỗi (Chain chốt 03/08)."
        ),
        permissions=_SYSTEM_ADMIN_PERMISSIONS,
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
