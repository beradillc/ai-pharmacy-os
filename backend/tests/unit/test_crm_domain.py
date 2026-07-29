"""Unit tests for the crm domain: Customer aggregate, allergies, conditions, history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.crm.domain import (
    ANONYMISED_NAME,
    Allergy,
    AllergySeverity,
    Condition,
    ConsentBasis,
    ConsentPurpose,
    ConsentRequiredError,
    Customer,
    CustomerAnonymisedError,
    CustomerConsent,
    DuplicateAllergyError,
    DuplicateConditionError,
    InvalidConditionError,
    InvalidConsentError,
    InvalidCustomerError,
    InvalidMedicationHistoryEntryError,
    MedicationHistoryEntry,
    MedicationHistorySource,
)

NOW = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)


def _consent(
    purpose: ConsentPurpose = ConsentPurpose.HEALTH,
    *,
    granted: bool = True,
    at: datetime = NOW,
    basis: ConsentBasis = ConsentBasis.EXPLICIT,
) -> CustomerConsent:
    return CustomerConsent(
        purpose=purpose,
        granted=granted,
        terms_version="v1",
        recorded_at=at,
        basis=basis,
        actor_user_id=uuid4(),
        client_ip="10.0.0.1",
    )


def _customer(**overrides: object) -> Customer:
    """A customer who has already consented to health processing.

    Most tests below are about something other than consent, and without it every
    health-data call would raise — so the fixture grants it and the consent rules
    get their own section.
    """
    defaults: dict[str, object] = {"full_name": "Nguyễn Văn A"}
    defaults.update(overrides)
    customer = Customer(**defaults)  # type: ignore[arg-type]
    customer.record_consent(_consent())
    return customer


def _customer_without_consent(**overrides: object) -> Customer:
    defaults: dict[str, object] = {"full_name": "Nguyễn Văn A"}
    defaults.update(overrides)
    return Customer(**defaults)  # type: ignore[arg-type]


# --- Customer ----------------------------------------------------------------


def test_blank_name_rejected() -> None:
    with pytest.raises(InvalidCustomerError):
        _customer(full_name="   ")


def test_non_positive_weight_rejected() -> None:
    with pytest.raises(InvalidCustomerError):
        _customer(weight_kg=Decimal("0"))


def test_customer_defaults_have_empty_collections() -> None:
    c = _customer()
    assert c.allergies == []
    assert c.conditions == []
    assert c.history == []


# --- Allergy (ingredient-based, not free-text drug name) ----------------------


def test_add_allergy_ingredient_based() -> None:
    c = _customer()
    penicillin = uuid4()
    c.add_allergy(Allergy(ingredient_id=penicillin, severity=AllergySeverity.SEVERE))
    assert c.has_allergy_to(penicillin) is True
    assert c.has_allergy_to(uuid4()) is False


def test_duplicate_allergy_same_ingredient_rejected() -> None:
    c = _customer()
    penicillin = uuid4()
    c.add_allergy(Allergy(ingredient_id=penicillin, severity=AllergySeverity.MILD))
    with pytest.raises(DuplicateAllergyError):
        c.add_allergy(Allergy(ingredient_id=penicillin, severity=AllergySeverity.SEVERE))


# --- Condition (bệnh nền, ICD-10) ---------------------------------------------


def test_condition_requires_code() -> None:
    with pytest.raises(InvalidConditionError):
        Condition(condition_code="   ")


def test_add_condition_and_reject_duplicate_code() -> None:
    c = _customer()
    c.add_condition(Condition(condition_code="E11", note="Đái tháo đường type 2"))
    assert c.conditions[0].condition_code == "E11"
    with pytest.raises(DuplicateConditionError):
        c.add_condition(Condition(condition_code="E11"))


# --- MedicationHistoryEntry (minimal, cross-module ref only) ------------------


def test_medication_history_quantity_must_be_positive() -> None:
    with pytest.raises(InvalidMedicationHistoryEntryError):
        MedicationHistoryEntry(
            drug_id=uuid4(),
            quantity=Decimal("0"),
            source=MedicationHistorySource.SALE,
            ref_id=uuid4(),
            occurred_at=datetime.now(UTC),
        )


def test_record_history_entry_appends() -> None:
    c = _customer()
    entry = MedicationHistoryEntry(
        drug_id=uuid4(),
        quantity=Decimal("2"),
        source=MedicationHistorySource.PRESCRIPTION,
        ref_id=uuid4(),
        occurred_at=datetime.now(UTC),
    )
    c.record_history_entry(entry)
    assert c.history == [entry]


# --- Consent (Luật 91/2025 Điều 9, 26 — duyệt Q1) -----------------------------


def test_a_new_customer_has_consented_to_nothing() -> None:
    """Silence is not consent (Điều 9): the default is False, not configurable."""
    c = _customer_without_consent()
    assert c.consents == []
    assert c.has_consent(ConsentPurpose.HEALTH) is False
    assert c.has_consent(ConsentPurpose.BASIC) is False
    assert c.health_data_allowed is False


def test_consent_requires_a_terms_version() -> None:
    """Without it, nobody can say afterwards *what* the customer agreed to."""
    with pytest.raises(InvalidConsentError):
        CustomerConsent(
            purpose=ConsentPurpose.HEALTH, granted=True, terms_version="  ", recorded_at=NOW
        )


def test_the_two_purposes_are_independent() -> None:
    c = _customer_without_consent()
    c.record_consent(_consent(ConsentPurpose.BASIC))
    assert c.has_consent(ConsentPurpose.BASIC) is True
    assert c.has_consent(ConsentPurpose.HEALTH) is False


def test_consent_history_is_append_only_and_the_latest_decision_wins() -> None:
    c = _customer_without_consent()
    c.record_consent(_consent(granted=True, at=NOW))
    c.record_consent(_consent(granted=False, at=NOW + timedelta(days=1)))

    assert c.has_consent(ConsentPurpose.HEALTH) is False
    # Both rows survive — the question "was there consent that day" stays answerable.
    assert len(c.consents) == 2


def test_consent_can_be_granted_again_after_a_revocation() -> None:
    c = _customer_without_consent()
    c.record_consent(_consent(granted=True, at=NOW))
    c.record_consent(_consent(granted=False, at=NOW + timedelta(days=1)))
    c.record_consent(_consent(granted=True, at=NOW + timedelta(days=2)))
    assert c.has_consent(ConsentPurpose.HEALTH) is True


def test_consent_records_the_evidence_dieu_9_demands() -> None:
    actor = uuid4()
    consent = CustomerConsent(
        purpose=ConsentPurpose.HEALTH,
        granted=True,
        terms_version="v2026-07",
        recorded_at=NOW,
        actor_user_id=actor,
        client_ip="203.0.113.9",
    )
    assert (consent.recorded_at, consent.actor_user_id, consent.client_ip) == (
        NOW,
        actor,
        "203.0.113.9",
    )
    assert consent.terms_version == "v2026-07"


# --- Health data refuses to exist without consent -----------------------------


def test_allergy_cannot_be_recorded_without_health_consent() -> None:
    c = _customer_without_consent()
    with pytest.raises(ConsentRequiredError):
        c.add_allergy(Allergy(ingredient_id=uuid4(), severity=AllergySeverity.SEVERE))
    assert c.allergies == []


def test_condition_cannot_be_recorded_without_health_consent() -> None:
    c = _customer_without_consent()
    with pytest.raises(ConsentRequiredError):
        c.add_condition(Condition(condition_code="E11"))
    assert c.conditions == []


def test_history_cannot_be_recorded_without_health_consent() -> None:
    c = _customer_without_consent()
    with pytest.raises(ConsentRequiredError):
        c.record_history_entry(
            MedicationHistoryEntry(
                drug_id=uuid4(),
                quantity=Decimal("1"),
                source=MedicationHistorySource.SALE,
                ref_id=uuid4(),
                occurred_at=NOW,
            )
        )
    assert c.history == []


def test_basic_consent_alone_does_not_unlock_health_data() -> None:
    """The whole point of splitting the purposes (Điều 9)."""
    c = _customer_without_consent()
    c.record_consent(_consent(ConsentPurpose.BASIC))
    with pytest.raises(ConsentRequiredError):
        c.add_allergy(Allergy(ingredient_id=uuid4(), severity=AllergySeverity.MILD))


def test_revoking_health_consent_blocks_further_writes() -> None:
    c = _customer()
    c.add_allergy(Allergy(ingredient_id=uuid4(), severity=AllergySeverity.MILD))

    c.record_consent(_consent(granted=False, at=NOW + timedelta(days=1)))
    assert c.health_data_allowed is False
    with pytest.raises(ConsentRequiredError):
        c.add_allergy(Allergy(ingredient_id=uuid4(), severity=AllergySeverity.SEVERE))


def test_revoking_consent_does_not_silently_delete_existing_data() -> None:
    """Erasure is a separate, deliberate act (duyệt Q2) — never a side effect.

    Between "the customer withdrew consent" and "the data is gone" there is always a
    human pressing something, because anonymisation cannot be undone.
    """
    c = _customer()
    c.add_allergy(Allergy(ingredient_id=uuid4(), severity=AllergySeverity.MILD))
    c.record_consent(_consent(granted=False, at=NOW + timedelta(days=1)))

    assert len(c.allergies) == 1
    assert c.is_anonymised is False


# --- Anonymisation (khử nhận dạng, duyệt Q2) ----------------------------------


def test_anonymise_strips_identity_and_health_data() -> None:
    c = _customer(phone="0900000000", national_id="hash", weight_kg=Decimal("60"))
    c.add_allergy(Allergy(ingredient_id=uuid4(), severity=AllergySeverity.SEVERE))
    c.add_condition(Condition(condition_code="E11"))

    c.anonymise(NOW)

    assert c.full_name == ANONYMISED_NAME
    assert (c.phone, c.dob, c.gender, c.weight_kg, c.national_id) == (
        None,
        None,
        None,
        None,
        None,
    )
    assert c.allergies == []
    assert c.conditions == []
    assert c.is_anonymised is True


def test_anonymise_keeps_dispensing_history() -> None:
    """GPP TT02 I-1a.II.4.d requires the records be kept; once nothing identifies a
    person they no longer describe one."""
    c = _customer()
    c.record_history_entry(
        MedicationHistoryEntry(
            drug_id=uuid4(),
            quantity=Decimal("2"),
            source=MedicationHistorySource.SALE,
            ref_id=uuid4(),
            occurred_at=NOW,
        )
    )
    c.anonymise(NOW)
    assert len(c.history) == 1


def test_anonymise_is_idempotent_and_keeps_the_first_timestamp() -> None:
    c = _customer()
    c.anonymise(NOW)
    c.anonymise(NOW + timedelta(days=5))
    assert c.anonymised_at == NOW


def test_an_anonymised_record_cannot_be_written_to_again() -> None:
    c = _customer()
    c.anonymise(NOW)

    for write in (
        lambda: c.add_allergy(Allergy(ingredient_id=uuid4(), severity=AllergySeverity.MILD)),
        lambda: c.add_condition(Condition(condition_code="E11")),
        lambda: c.record_consent(_consent()),
    ):
        with pytest.raises(CustomerAnonymisedError):
            write()


def test_anonymised_record_never_allows_health_data_even_with_consent() -> None:
    c = _customer()
    c.anonymise(NOW)
    # The consent row is still in history, but the record is closed.
    assert c.has_consent(ConsentPurpose.HEALTH) is True
    assert c.health_data_allowed is False


# --- ConsentPurpose.LOYALTY (giai đoạn A1, docs/features/khach-hang-tich-diem) ---


def test_dong_y_co_ban_KHONG_keo_theo_dong_y_tich_diem() -> None:
    """🔴 Điều 9 đòi đồng ý theo TỪNG mục đích — đây là chỗ dễ sai nhất.

    Khách đồng ý cho lưu tên + SĐT để ghi lên hoá đơn. Điều đó **không** có nghĩa
    họ đồng ý cho nhà thuốc theo dõi mình mua gì để cộng điểm. Gộp hai thứ là lấy
    đồng ý cho việc A rồi dùng cho việc B.
    """
    c = _customer_without_consent(consents=[_consent(purpose=ConsentPurpose.BASIC, granted=True)])
    assert c.has_consent(ConsentPurpose.BASIC) is True
    assert c.loyalty_allowed is False


def test_dong_y_tich_diem_KHONG_mo_duong_cho_du_lieu_suc_khoe() -> None:
    """Và ngược lại — đồng ý tích điểm không phải đồng ý lưu dị ứng/bệnh nền."""
    c = _customer_without_consent(consents=[_consent(purpose=ConsentPurpose.LOYALTY, granted=True)])
    assert c.loyalty_allowed is True
    assert c.health_data_allowed is False


def test_rut_lai_dong_y_thi_ngung_cong_diem() -> None:
    """Rút lại = một dòng MỚI, không sửa dòng cũ. Quyết định sau cùng thắng."""
    early = datetime(2026, 1, 1, tzinfo=UTC)
    late = datetime(2026, 6, 1, tzinfo=UTC)
    c = _customer(
        consents=[
            _consent(purpose=ConsentPurpose.LOYALTY, granted=True, at=early),
            _consent(purpose=ConsentPurpose.LOYALTY, granted=False, at=late),
        ]
    )
    assert c.loyalty_allowed is False


def test_kho_so_da_khu_nhan_dang_thi_khong_cong_diem_du_con_dong_y() -> None:
    """Khử nhận dạng rồi thì không còn ai để thưởng — đừng để cờ đồng ý cũ nói khác."""
    c = _customer_without_consent(consents=[_consent(purpose=ConsentPurpose.LOYALTY, granted=True)])
    c.anonymise(NOW)
    assert c.loyalty_allowed is False


# --- ConsentBasis: nguồn gốc của sự đồng ý (Đ-4, Chain chốt 2026-07-29) -------


def test_khach_dua_so_o_quay_la_dong_y_CO_BAN() -> None:
    """Khách tự đọc số khi được hỏi = hành vi khẳng định, không phải im lặng."""
    c = _customer_without_consent(
        consents=[_consent(purpose=ConsentPurpose.BASIC, basis=ConsentBasis.COUNTER)]
    )
    assert c.has_consent(ConsentPurpose.BASIC) is True


@pytest.mark.parametrize("purpose", [ConsentPurpose.LOYALTY, ConsentPurpose.HEALTH])
def test_dong_y_o_quay_KHONG_the_mo_rong_sang_muc_dich_khac(purpose: ConsentPurpose) -> None:
    """🔴 Ranh giới Đ-4, chốt cứng trong domain chứ không để tầng trên tự giữ.

    Đưa số điện thoại để ghi lên hoá đơn **không phải** đồng ý cho theo dõi lịch
    sử mua, càng không phải đồng ý lưu dị ứng/bệnh nền. Nới chỗ này ra sẽ trông
    rất hợp lý lúc làm — vì đằng nào cũng chỉ là một số điện thoại — nên nó phải
    bị chặn ở nơi không ai đi vòng được.
    """
    with pytest.raises(InvalidConsentError):
        _consent(purpose=purpose, basis=ConsentBasis.COUNTER)


def test_mac_dinh_la_hoi_tuong_minh_khong_phai_o_quay() -> None:
    """Không ghi nguồn ⇒ coi là đã hỏi tường minh.

    Mặc định phải là cái CHẶT HƠN. Nếu mặc định là "lấy ở quầy" thì mọi dòng cũ
    trong CSDL bỗng nhiên tự khai một nguồn gốc chưa ai kiểm chứng.
    """
    assert _consent().basis is ConsentBasis.EXPLICIT
