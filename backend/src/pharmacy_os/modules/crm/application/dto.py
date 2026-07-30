"""Crm data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.crm.domain import (
    AllergySeverity,
    ConsentBasis,
    ConsentPurpose,
    Customer,
    CustomerConsent,
)


@dataclass(slots=True)
class CreateCustomerInput:
    full_name: str
    phone: str | None = None
    dob: date | None = None
    gender: str | None = None
    weight_kg: Decimal | None = None
    national_id: str | None = None


@dataclass(slots=True)
class CustomerDataExport:
    """Everything held about one customer, for the data-subject right of access.

    Luật 91/2025 Điều 13-14 gives the subject the right to obtain their data; this is
    the machine-readable answer. ``exported_by``/``exported_at`` are part of the
    document on purpose — a copy of someone's medical record circulating without a
    provenance line is worse than none.
    """

    customer: CustomerOutput
    exported_at: datetime
    exported_by: UUID


@dataclass(slots=True)
class RecordConsentInput:
    """One consent decision taken at the counter on the customer's behalf."""

    purpose: ConsentPurpose
    granted: bool
    terms_version: str
    #: Mặc định EXPLICIT — cái chặt hơn. Xem ``ConsentBasis``.
    basis: ConsentBasis = ConsentBasis.EXPLICIT


@dataclass(slots=True)
class ConsentOutput:
    id: UUID
    purpose: str
    granted: bool
    terms_version: str
    recorded_at: datetime
    actor_user_id: UUID | None
    client_ip: str | None
    basis: str

    @classmethod
    def of(cls, consent: CustomerConsent) -> ConsentOutput:
        return cls(
            id=consent.id,
            purpose=consent.purpose.value,
            basis=consent.basis.value,
            granted=consent.granted,
            terms_version=consent.terms_version,
            recorded_at=consent.recorded_at,
            actor_user_id=consent.actor_user_id,
            client_ip=consent.client_ip,
        )


@dataclass(slots=True)
class AddAllergyInput:
    ingredient_id: UUID
    severity: AllergySeverity
    note: str | None = None


@dataclass(slots=True)
class AddConditionInput:
    condition_code: str
    note: str | None = None


@dataclass(slots=True)
class AllergyOutput:
    id: UUID
    ingredient_id: UUID
    severity: str
    note: str | None


@dataclass(slots=True)
class ConditionOutput:
    id: UUID
    condition_code: str
    note: str | None


@dataclass(slots=True)
class MedicationHistoryItemInput:
    """One dispensed drug + quantity to fold into a customer's history (system-driven)."""

    drug_id: UUID
    quantity: Decimal


@dataclass(slots=True)
class MedicationHistoryOutput:
    id: UUID
    drug_id: UUID
    quantity: Decimal
    source: str
    ref_id: UUID
    occurred_at: datetime


#: Số chữ số cuối còn hiện. Chain chốt 2026-07-31: "hiện ba số cuối".
PHONE_TAIL = 3


def mask_phone(phone: str | None) -> str | None:
    """Che số điện thoại, chừa ``PHONE_TAIL`` chữ số cuối: ``0357205494`` → ``*494``.

    🔴 Che ở **đây**, trong DTO, chứ không ở giao diện. Che ở giao diện là trang trí:
    số đầy đủ vẫn nằm trong phản hồi HTTP, mở tab Network là đọc được — nên nó không
    chặn được ai, chỉ làm người viết mã tưởng là đã chặn.

    **Một dấu sao, không phải một sao mỗi chữ số** (Chain chốt 2026-07-31). Ngắn gọn hơn
    trong bảng hẹp, và tình cờ lộ ít hơn: dãy sao dài đúng bằng phần bị che sẽ nói luôn
    số dài bao nhiêu.

    Chuỗi ngắn hơn hoặc bằng ``PHONE_TAIL`` che **toàn bộ** thành một dấu sao: chừa ba
    số cuối của một chuỗi ba ký tự là không che gì cả.
    """
    if phone is None:
        return None
    if not phone:
        return ""
    if len(phone) <= PHONE_TAIL:
        return "*"
    return "*" + phone[-PHONE_TAIL:]


@dataclass(slots=True)
class CustomerOutput:
    id: UUID
    full_name: str
    phone: str | None
    dob: date | None
    gender: str | None
    weight_kg: Decimal | None
    national_id: str | None
    allergies: list[AllergyOutput]
    conditions: list[ConditionOutput]
    history: list[MedicationHistoryOutput]
    consents: list[ConsentOutput]
    anonymised_at: datetime | None
    health_data_allowed: bool
    """Whether health data may lawfully be processed right now — the interface layer
    uses this (together with the caller's permissions) to decide what to return."""

    @classmethod
    def of(
        cls, customer: Customer, *, include_sensitive: bool = True, reveal_phone: bool = False
    ) -> CustomerOutput:
        """Build the DTO, optionally withholding the health data.

        ``include_sensitive=False`` returns empty allergy/condition/history lists
        rather than raising: a cashier looking a customer up to attach them to a sale
        has a legitimate reason to see the name and phone, and no reason at all to
        see the diagnoses (NĐ356 Điều 4.2 · GPP TT02 I-1a.III.4.a). Withholding is
        the whole point of splitting ``crm.read`` from ``crm.sensitive.read``.

        ``consents`` is **not** withheld: knowing whether consent exists is what lets
        counter staff ask for it, and the record itself carries no health data.

        ``reveal_phone=False`` (mặc định) trả về số đã che — xem :func:`mask_phone`.
        **Mặc định là che**, không phải mở: một đường đọc mới quên truyền cờ này thì hỏng
        về phía an toàn, chứ không lặng lẽ rò số ra.
        """
        return cls(
            id=customer.id,
            full_name=customer.full_name,
            phone=customer.phone if reveal_phone else mask_phone(customer.phone),
            dob=customer.dob,
            gender=customer.gender,
            weight_kg=customer.weight_kg,
            national_id=customer.national_id,
            allergies=[]
            if not include_sensitive
            else [
                AllergyOutput(
                    id=a.id,
                    ingredient_id=a.ingredient_id,
                    severity=a.severity.value,
                    note=a.note,
                )
                for a in customer.allergies
            ],
            conditions=[]
            if not include_sensitive
            else [
                ConditionOutput(id=c.id, condition_code=c.condition_code, note=c.note)
                for c in customer.conditions
            ],
            history=[]
            if not include_sensitive
            else [
                MedicationHistoryOutput(
                    id=h.id,
                    drug_id=h.drug_id,
                    quantity=h.quantity,
                    source=h.source.value,
                    ref_id=h.ref_id,
                    occurred_at=h.occurred_at,
                )
                for h in customer.history
            ],
            consents=[ConsentOutput.of(k) for k in customer.consents],
            anonymised_at=customer.anonymised_at,
            health_data_allowed=customer.health_data_allowed,
        )
