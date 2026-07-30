"""CRM aggregate: :class:`Customer` and its clinical/history sub-entities.

``Customer`` is deliberately independent of ``compliance.CustomerDetail`` (the
Phụ lục XXI ledger snapshot): that value object has no identity and is scoped to a
single controlled-substance ledger row at the moment of sale, while ``Customer`` here
is tenant-owned master data with its own id, reused across sales/clinical checks.
Linking the two (if ever needed) is a cross-module composition-root decision for a
later step, not a domain concern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.crm.domain.exceptions import (
    ConsentRequiredError,
    CustomerAnonymisedError,
    DuplicateAllergyError,
    DuplicateConditionError,
    InvalidConditionError,
    InvalidConsentError,
    InvalidCustomerError,
    InvalidMedicationHistoryEntryError,
)

ANONYMISED_NAME = "(đã khử nhận dạng)"
"""Placeholder left in ``full_name`` after erasure — the row must stay readable as a
row (the dispensing lines referencing it keep their retention obligation) while no
longer naming anyone."""


class AllergySeverity(StrEnum):
    """Clinical severity of a recorded allergy."""

    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class MedicationHistorySource(StrEnum):
    """Where a medication-history entry originated (cross-module ref, not FK)."""

    SALE = "SALE"
    PRESCRIPTION = "PRESCRIPTION"


class ConsentPurpose(StrEnum):
    """What the customer agreed to, one purpose at a time.

    Luật 91/2025 Điều 9 requires consent to be given **per purpose** and forbids
    treating silence as agreement, so a single "accepted the terms" flag would not
    be lawful. Two levels (duyệt Q1): more would push counter staff into clicking
    through, which produces consent that is formally recorded and practically
    worthless.
    """

    BASIC = "BASIC"
    """Name and phone — to identify the buyer on a sale and its invoice."""

    LOYALTY = "LOYALTY"
    """Tracking what the customer buys, in order to award points.

    A **separate purpose from** :attr:`BASIC`, and deliberately so. ``BASIC`` is
    consent to *identify the buyer on an invoice*; awarding points means following
    their buying behaviour over time, which is a different purpose. Điều 9 requires
    consent per purpose, so folding this into ``BASIC`` would be taking agreement
    for one thing and using it for another.

    Not :attr:`HEALTH` either: the points ledger deliberately carries no drug
    identity (quyết định Đ-3, ``docs/features/khach-hang-tich-diem/01_DECISIONS.md``),
    so no health data is processed for this purpose.

    Withdrawing it **freezes** the balance rather than erasing it — points already
    earned are an obligation the pharmacy owes the customer, and deleting them
    would cancel their entitlement unasked. Erasure happens only on an actual
    erasure request (Điều 13, 14), which goes through
    :meth:`Customer.anonymise`.
    """

    HEALTH = "HEALTH"
    """Allergies, conditions, medication history — for pharmacological safety advice.
    Sensitive personal data (NĐ356 Điều 4.1.d)."""


DEFAULT_TERMS_VERSION = "v1"
"""Phiên bản điều khoản đang hiệu lực, ghi kèm mỗi lần lấy đồng ý.

Đặt ở DOMAIN vì đây là dữ kiện nghiệp vụ, không phải mặc định của một biểu mẫu HTTP —
tầng application cũng ghi đồng ý (lúc tạo khách có SĐT) và không được nhập ngược lên
tầng interface.

Recorded when the client sends no version.

Counter staff press one button (chốt của sếp 2026-07-23), so the flow must not
demand a version they would have to type. Send a real one once a written terms
document exists — the field is what lets an inspection ask *what* the customer was
told, and today it can only answer *that* someone recorded a yes.
"""


class ConsentBasis(StrEnum):
    """**Cách** sự đồng ý được lấy — không phải *có* đồng ý hay không.

    Câu đoàn kiểm tra thật sự hỏi không phải *"khách có đồng ý không"* mà *"sự
    đồng ý đó lấy thế nào"*. Hai nguồn dưới đây khác hẳn nhau về sức nặng, và một
    trường `granted=True` trơ trọi không phân biệt được.
    """

    EXPLICIT = "EXPLICIT"
    """Nhân viên đọc nội dung từng mục đích rồi bấm thay khách trên bảng đồng ý."""

    COUNTER = "COUNTER"
    """Khách **tự đọc số điện thoại** ở quầy khi được hỏi lúc lập đơn (Chain chốt
    2026-07-29, quyết định Đ-4).

    Là hành vi **khẳng định**, không phải im lặng — nên thoả Điều 9. Nhưng **chỉ
    thoả cho** :attr:`ConsentPurpose.BASIC`: đưa số để ghi lên hoá đơn không phải
    đồng ý cho theo dõi lịch sử mua, càng không phải đồng ý lưu dị ứng/bệnh nền.
    Suy rộng ra hai mục kia là đúng lỗi "lấy đồng ý cho việc A rồi dùng cho việc B"
    — và nó sẽ **trông rất hợp lý** lúc làm, vì đằng nào cũng chỉ là một số điện thoại.
    """


@dataclass(slots=True)
class CustomerConsent:
    """One consent decision, recorded and never edited.

    The collection is an **append-only history**, not a mutable flag: a revocation is
    a new row, so the record can answer "was there consent on the day that data was
    read" — which is the question an inspection actually asks. Each row carries the
    evidence Điều 9 demands: when, which staff account, from which IP, and against
    which version of the terms.
    """

    purpose: ConsentPurpose
    granted: bool
    terms_version: str
    recorded_at: datetime
    actor_user_id: UUID | None = None
    client_ip: str | None = None
    basis: ConsentBasis = ConsentBasis.EXPLICIT
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.terms_version = self.terms_version.strip()
        if not self.terms_version:
            raise InvalidConsentError("Thiếu phiên bản điều khoản đã đồng ý")
        # Chốt cứng ranh giới của Đ-4 ngay trong domain, không để tầng nào bên
        # trên "tiện tay" nới ra: quầy chỉ lấy được đồng ý CƠ BẢN.
        if self.basis is ConsentBasis.COUNTER and self.purpose is not ConsentPurpose.BASIC:
            raise InvalidConsentError(
                "Khách đưa số điện thoại ở quầy chỉ là đồng ý mục đích cơ bản; "
                f"mục đích {self.purpose} phải hỏi riêng"
            )


@dataclass(slots=True)
class Allergy:
    """A known allergy, keyed by active ingredient — not by free-text drug name.

    Ingredient-based so it can be matched against :class:`DrugInteraction`-style
    ingredient checks later (catalog Sprint 6 Bước 1), the same way clinical
    interactions are keyed, rather than against a specific branded product.
    """

    ingredient_id: UUID
    severity: AllergySeverity
    note: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class Condition:
    """A pre-existing condition (bệnh nền), coded per ICD-10."""

    condition_code: str
    note: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.condition_code.strip():
            raise InvalidConditionError("Mã bệnh nền (ICD-10) không được để trống")


@dataclass(slots=True)
class MedicationHistoryEntry:
    """One past dispense/sale fact for a customer — minimal, cross-module ref only.

    ``ref_id`` points at the originating ``SalesOrder``/``Prescription`` (by
    ``source``); it is a plain UUID reference, not a FK, matching the
    ``ref_type``/``ref_id`` convention already used by ``inventory.StockMovement``.
    Populating this from live sale/dispense events is a later, cross-module step —
    here it is only the shape a use-case can append to.
    """

    drug_id: UUID
    quantity: Decimal
    source: MedicationHistorySource
    ref_id: UUID
    occurred_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.quantity = Decimal(self.quantity)
        if self.quantity <= 0:
            raise InvalidMedicationHistoryEntryError("Số lượng dùng thuốc phải > 0")


@dataclass(slots=True)
class Customer:
    """Customer/patient master record (aggregate root). Not tenant-scoped here —
    tenant/branch ownership is attached at the repository boundary, like ``Drug``.
    """

    full_name: str
    phone: str | None = None
    dob: date | None = None
    gender: str | None = None
    weight_kg: Decimal | None = None
    national_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    allergies: list[Allergy] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    history: list[MedicationHistoryEntry] = field(default_factory=list)
    consents: list[CustomerConsent] = field(default_factory=list)
    anonymised_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.full_name.strip():
            raise InvalidCustomerError("Họ tên khách hàng không được để trống")
        if self.weight_kg is not None:
            self.weight_kg = Decimal(self.weight_kg)
            if self.weight_kg <= 0:
                raise InvalidCustomerError("Cân nặng phải > 0")

    # -- consent -------------------------------------------------------------

    def record_consent(self, consent: CustomerConsent) -> None:
        """Append a consent decision. Never rewrites an earlier one."""
        self._ensure_not_anonymised()
        self.consents.append(consent)

    def has_consent(self, purpose: ConsentPurpose) -> bool:
        """Whether the **latest** decision for *purpose* is a grant.

        Absence of any record is absence of consent — Điều 9 is explicit that silence
        does not count, so the default is ``False`` and never configurable.
        """
        latest: CustomerConsent | None = None
        for consent in self.consents:
            if consent.purpose is not purpose:
                continue
            if latest is None or consent.recorded_at >= latest.recorded_at:
                latest = consent
        return latest is not None and latest.granted

    @property
    def loyalty_allowed(self) -> bool:
        """Whether points may be awarded to this customer right now.

        Checked **at the moment of awarding**, not at profile creation: consent is
        an append-only history and can be withdrawn between the two (rủi ro R-3).
        """
        return not self.is_anonymised and self.has_consent(ConsentPurpose.LOYALTY)

    @property
    def health_data_allowed(self) -> bool:
        """Whether health data may lawfully be processed for this customer right now."""
        return not self.is_anonymised and self.has_consent(ConsentPurpose.HEALTH)

    # -- health data (chỉ khi có đồng ý HEALTH còn hiệu lực) -----------------

    def add_allergy(self, allergy: Allergy) -> None:
        self._ensure_health_consent()
        if any(a.ingredient_id == allergy.ingredient_id for a in self.allergies):
            raise DuplicateAllergyError("Dị ứng với hoạt chất này đã được ghi nhận")
        self.allergies.append(allergy)

    def add_condition(self, condition: Condition) -> None:
        self._ensure_health_consent()
        if any(c.condition_code == condition.condition_code for c in self.conditions):
            raise DuplicateConditionError("Bệnh nền này đã được ghi nhận")
        self.conditions.append(condition)

    def record_history_entry(self, entry: MedicationHistoryEntry) -> None:
        self._ensure_health_consent()
        self.history.append(entry)

    def has_allergy_to(self, ingredient_id: UUID) -> bool:
        return any(a.ingredient_id == ingredient_id for a in self.allergies)

    # -- erasure (khử nhận dạng, duyệt Q2) -----------------------------------

    def anonymise(self, now: datetime) -> None:
        """Strip identity and health data, keep the row.

        Resolves a real conflict between two statutes in force: Luật 91/2025 Điều
        13-14 gives the right to erasure, GPP TT02/2018 I-1a.II.4.d requires records
        to be kept for at least a year past a medicine's expiry. Deleting the row
        would break the second; keeping it whole would break the first. Removing what
        points at a person, while leaving the dispensing lines that carry the
        retention duty, satisfies both.

        ``history`` is **kept**: those are the dispensing records the retention duty
        attaches to, and once no field identifies anyone they no longer describe a
        person. Allergies and conditions are deleted outright — nothing obliges the
        pharmacy to keep them (see :class:`ConsentRequiredError`).

        One-way and idempotent: calling it twice changes nothing.
        """
        if self.is_anonymised:
            return
        self.full_name = ANONYMISED_NAME
        self.phone = None
        self.dob = None
        self.gender = None
        self.weight_kg = None
        self.national_id = None
        self.allergies.clear()
        self.conditions.clear()
        self.anonymised_at = now

    @property
    def is_anonymised(self) -> bool:
        return self.anonymised_at is not None

    # -- guards --------------------------------------------------------------

    def _ensure_not_anonymised(self) -> None:
        if self.is_anonymised:
            raise CustomerAnonymisedError("Hồ sơ đã khử nhận dạng, không thể ghi thêm")

    def _ensure_health_consent(self) -> None:
        self._ensure_not_anonymised()
        if not self.has_consent(ConsentPurpose.HEALTH):
            raise ConsentRequiredError(
                "Khách hàng chưa đồng ý cho xử lý dữ liệu sức khỏe (dị ứng, bệnh nền, "
                "lịch sử dùng thuốc)"
            )
