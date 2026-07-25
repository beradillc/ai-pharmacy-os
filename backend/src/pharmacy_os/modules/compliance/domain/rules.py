"""Validation rules for controlled/prescription drug sales (docs/13_COMPLIANCE_SPEC.md mục C.3)."""

from __future__ import annotations

from dataclasses import dataclass

from pharmacy_os.modules.compliance.domain.entities import (
    ControlledSubstanceCategory,
    CustomerDetail,
)
from pharmacy_os.modules.compliance.domain.exceptions import (
    MissingControlledCustomerDetailError,
    MissingControlledPrescriptionCodeError,
    MissingEtcPrescriptionFieldsError,
)

_PRESCRIPTION_RETAINED_CATEGORIES = (
    ControlledSubstanceCategory.GAY_NGHIEN,
    ControlledSubstanceCategory.HUONG_THAN,
)

#: Nhóm CHỈ phải lập sổ xuất/nhập/tồn (Phụ lục XVI, Điều 12.3), KHÔNG có nghĩa vụ Sổ theo dõi
#: thông tin chi tiết khách hàng — Điều 12.2 chỉ buộc sổ khách hàng với thuốc DẠNG PHỐI HỢP.
_NO_CUSTOMER_LOG_CATEGORIES = (
    ControlledSubstanceCategory.THUOC_DOC,
    ControlledSubstanceCategory.DANH_MUC_CAM,
)


@dataclass(frozen=True, slots=True)
class EtcPrescriptionPolicy:
    """C.3 rule 1 (thuốc ETC nói chung).

    ⚠️ NGUỒN CHƯA XÁC ĐỊNH — chờ văn bản kê đơn ngoại trú hiện hành. TT 20/2017 không điều
    chỉnh thuốc kê đơn thông thường (chỉ GN/HT/TC/phóng xạ), nên rule này chưa có căn cứ pháp
    lý trực tiếp. Mặc định TẮT (``False``) — KHÔNG hard-validate cho tới khi có văn bản xác
    nhận; khi có nguồn, chỉ cần bật cờ này lên, không thiết kế lại rule/schema.
    """

    require_etc_prescription_fields: bool = False


def validate_etc_sale(
    policy: EtcPrescriptionPolicy,
    *,
    prescription_code: str | None,
    patient_name: str | None,
    doctor_name: str | None,
) -> None:
    """Áp dụng rule C.3.1 chỉ khi ``policy.require_etc_prescription_fields`` bật.

    TODO(compliance): bật khi có văn bản kê đơn ngoại trú hiện hành xác nhận nguồn.
    """
    if not policy.require_etc_prescription_fields:
        return
    if not (prescription_code and patient_name and doctor_name):
        raise MissingEtcPrescriptionFieldsError(
            "Thuốc kê đơn (ETC) cần prescription_code, patient_name và doctor_name"
        )


def validate_controlled_sale(
    category: ControlledSubstanceCategory,
    *,
    prescription_code: str | None,
    customer: CustomerDetail | None,
) -> None:
    """C.3 rule 2 — bán ra bắt buộc thông tin khách hàng (Phụ lục XIX: tên + địa chỉ).

    Áp cho GN/HT/TC (TT18 Điều 12.1.đ) và thuốc dạng phối hợp (Điều 12.2). **Không** áp cho
    thuốc độc / danh mục cấm: Điều 12.3 chỉ buộc 2 nhóm này lập sổ xuất/nhập/tồn Phụ lục XVI,
    không có nghĩa vụ sổ khách hàng.

    ``prescription_code`` chỉ bắt buộc riêng cho GN/HT (Điều 12.1.c) — KHÔNG bắt buộc cho TC
    (tiền chất không có nghĩa vụ lưu đơn theo văn bản gốc).
    """
    if category is ControlledSubstanceCategory.NONE:
        return
    if category in _NO_CUSTOMER_LOG_CATEGORIES:
        return
    if customer is None:
        raise MissingControlledCustomerDetailError(
            "Thuốc kiểm soát đặc biệt bán ra cần thông tin khách hàng (Phụ lục XIX: tên + địa chỉ)"
        )
    if category in _PRESCRIPTION_RETAINED_CATEGORIES and not prescription_code:
        raise MissingControlledPrescriptionCodeError(
            "Thuốc gây nghiện/hướng thần bán ra cần lưu prescription_code (Điều 12.1.c)"
        )
