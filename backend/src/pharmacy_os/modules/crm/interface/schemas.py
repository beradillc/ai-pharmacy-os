"""Pydantic request/response schemas for crm."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.crm.application.dto import (
    AddAllergyInput,
    AddConditionInput,
    ConsentOutput,
    CreateCustomerInput,
    CustomerDataExport,
    CustomerOutput,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.domain import AllergySeverity, ConsentBasis, ConsentPurpose


class CreateCustomerRequest(BaseModel):
    # max_length khớp đúng độ rộng cột — không chặn ở đây thì Postgres ném
    # StringDataRightTruncationError và client nhận 500 thay vì 422 (PROJECT_STATE §7aq).
    full_name: str = Field(max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    dob: date | None = None
    gender: str | None = Field(default=None, max_length=16)
    weight_kg: Decimal | None = Field(default=None, gt=0)
    national_id: str | None = Field(default=None, max_length=128)

    def to_input(self) -> CreateCustomerInput:
        return CreateCustomerInput(
            full_name=self.full_name,
            phone=self.phone,
            dob=self.dob,
            gender=self.gender,
            weight_kg=self.weight_kg,
            national_id=self.national_id,
        )


DEFAULT_TERMS_VERSION = "v1"
"""Recorded when the client sends no version.

Counter staff press one button (chốt của sếp 2026-07-23), so the flow must not
demand a version they would have to type. Send a real one once a written terms
document exists — the field is what lets an inspection ask *what* the customer was
told, and today it can only answer *that* someone recorded a yes.
"""


class RecordConsentRequest(BaseModel):
    """Grant or revoke one purpose.

    ``granted`` deliberately has **no default**: a default would make an unanswered
    request count as agreement, which is precisely what Luật 91/2025 Điều 9 forbids
    ("im lặng ≠ đồng ý"). Someone must actually press the button.
    """

    purpose: ConsentPurpose
    granted: bool
    terms_version: str = Field(default=DEFAULT_TERMS_VERSION, min_length=1, max_length=32)
    #: Mặc định EXPLICIT — cái CHẶT hơn. Người gọi phải NÓI RA nếu đây là số
    #: khách tự đưa ở quầy; im lặng không được tự nhận một nguồn gốc dễ dãi hơn.
    basis: ConsentBasis = ConsentBasis.EXPLICIT

    def to_input(self) -> RecordConsentInput:
        return RecordConsentInput(
            purpose=self.purpose,
            granted=self.granted,
            terms_version=self.terms_version,
            basis=self.basis,
        )


class ConsentResponse(BaseModel):
    id: UUID
    purpose: str
    granted: bool
    terms_version: str
    recorded_at: datetime
    actor_user_id: UUID | None
    client_ip: str | None
    #: Phơi ra vì đây là thứ đoàn kiểm tra hỏi — "đồng ý đó lấy thế nào" — chứ
    #: không phải chi tiết nội bộ.
    basis: str

    @classmethod
    def of(cls, out: ConsentOutput) -> ConsentResponse:
        return cls(
            id=out.id,
            purpose=out.purpose,
            granted=out.granted,
            terms_version=out.terms_version,
            recorded_at=out.recorded_at,
            basis=out.basis,
            actor_user_id=out.actor_user_id,
            client_ip=out.client_ip,
        )


class CustomerExportResponse(BaseModel):
    """The data-subject export, with the provenance line that makes it traceable."""

    customer: CustomerResponse
    exported_at: datetime
    exported_by: UUID

    @classmethod
    def of(cls, out: CustomerDataExport) -> CustomerExportResponse:
        return cls(
            customer=CustomerResponse.of(out.customer),
            exported_at=out.exported_at,
            exported_by=out.exported_by,
        )


class AddAllergyRequest(BaseModel):
    ingredient_id: UUID
    severity: AllergySeverity
    note: str | None = None

    def to_input(self) -> AddAllergyInput:
        return AddAllergyInput(
            ingredient_id=self.ingredient_id, severity=self.severity, note=self.note
        )


class AddConditionRequest(BaseModel):
    condition_code: str = Field(max_length=16)
    note: str | None = None  # cột Text, không giới hạn

    def to_input(self) -> AddConditionInput:
        return AddConditionInput(condition_code=self.condition_code, note=self.note)


class AllergyResponse(BaseModel):
    id: UUID
    ingredient_id: UUID
    severity: str
    note: str | None


class ConditionResponse(BaseModel):
    id: UUID
    condition_code: str
    note: str | None


class MedicationHistoryResponse(BaseModel):
    id: UUID
    drug_id: UUID
    quantity: Decimal
    source: str
    ref_id: UUID
    occurred_at: datetime


class PhoneRevealResponse(BaseModel):
    """Số điện thoại đầy đủ, trả riêng khi người dùng bấm xem.

    Là một tài nguyên riêng chứ không phải một trường của ``CustomerResponse``: nhờ vậy
    số đầy đủ chỉ đi qua dây khi có người **chủ động hỏi**, và mỗi lần hỏi là một dòng
    audit — không phải một trường lặng lẽ đi kèm mọi lượt tải danh sách.
    """

    customer_id: UUID
    phone: str | None


class CustomerResponse(BaseModel):
    id: UUID
    full_name: str
    phone: str | None
    dob: date | None
    gender: str | None
    weight_kg: Decimal | None
    national_id: str | None
    allergies: list[AllergyResponse]
    conditions: list[ConditionResponse]
    history: list[MedicationHistoryResponse]
    consents: list[ConsentResponse]
    anonymised_at: datetime | None
    health_data_allowed: bool

    @classmethod
    def of(cls, out: CustomerOutput) -> CustomerResponse:
        return cls(
            id=out.id,
            full_name=out.full_name,
            phone=out.phone,
            dob=out.dob,
            gender=out.gender,
            weight_kg=out.weight_kg,
            national_id=out.national_id,
            allergies=[
                AllergyResponse(
                    id=a.id, ingredient_id=a.ingredient_id, severity=a.severity, note=a.note
                )
                for a in out.allergies
            ],
            conditions=[
                ConditionResponse(id=c.id, condition_code=c.condition_code, note=c.note)
                for c in out.conditions
            ],
            history=[
                MedicationHistoryResponse(
                    id=h.id,
                    drug_id=h.drug_id,
                    quantity=h.quantity,
                    source=h.source,
                    ref_id=h.ref_id,
                    occurred_at=h.occurred_at,
                )
                for h in out.history
            ],
            consents=[ConsentResponse.of(k) for k in out.consents],
            anonymised_at=out.anonymised_at,
            health_data_allowed=out.health_data_allowed,
        )
