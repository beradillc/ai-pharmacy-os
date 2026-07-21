from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.prescription.domain import (
    EmptyPrescriptionError,
    InvalidPrescriptionStateError,
    Prescription,
    PrescriptionItem,
    PrescriptionSource,
    PrescriptionStatus,
)


def _rx(**kw: object) -> Prescription:
    return Prescription(  # type: ignore[arg-type]
        tenant_id=uuid4(),
        branch_id=uuid4(),
        customer_id=uuid4(),
        doctor_name="BS. Nguyễn Văn A",
        **kw,
    )


def _item(*, qty: str = "10") -> PrescriptionItem:
    return PrescriptionItem(
        drug_id=uuid4(),
        quantity=Decimal(qty),
        dose="1 viên",
        frequency="2 lần/ngày",
        duration="5 ngày",
    )


def test_new_prescription_is_draft() -> None:
    rx = _rx()
    assert rx.status is PrescriptionStatus.DRAFT
    assert rx.source is PrescriptionSource.MANUAL


def test_add_item_while_draft() -> None:
    rx = _rx()
    rx.add_item(_item())
    assert len(rx.items) == 1


def test_validate_happy_path_sets_status_and_validator() -> None:
    rx = _rx()
    rx.add_item(_item())
    validator = uuid4()
    rx.validate(validated_by=validator)
    assert rx.status is PrescriptionStatus.VALIDATED
    assert rx.validated_by == validator


def test_validate_empty_prescription_rejected() -> None:
    rx = _rx()
    with pytest.raises(EmptyPrescriptionError):
        rx.validate(validated_by=uuid4())


def test_validate_twice_rejected() -> None:
    rx = _rx()
    rx.add_item(_item())
    rx.validate(validated_by=uuid4())
    with pytest.raises(InvalidPrescriptionStateError):
        rx.validate(validated_by=uuid4())


def test_reject_from_draft() -> None:
    rx = _rx()
    rx.reject("Chữ ký bác sĩ không rõ ràng")
    assert rx.status is PrescriptionStatus.REJECTED
    assert rx.rejection_reason == "Chữ ký bác sĩ không rõ ràng"


def test_reject_from_validated() -> None:
    rx = _rx()
    rx.add_item(_item())
    rx.validate(validated_by=uuid4())
    rx.reject("Phát hiện tương tác thuốc nguy hiểm")
    assert rx.status is PrescriptionStatus.REJECTED


def test_reject_after_dispensed_rejected() -> None:
    rx = _rx()
    rx.add_item(_item())
    rx.validate(validated_by=uuid4())
    rx.dispense()
    with pytest.raises(InvalidPrescriptionStateError):
        rx.reject("quá muộn")


def test_dispense_requires_validated() -> None:
    rx = _rx()
    rx.add_item(_item())
    with pytest.raises(InvalidPrescriptionStateError):
        rx.dispense()


def test_dispense_happy_path() -> None:
    rx = _rx()
    rx.add_item(_item())
    rx.validate(validated_by=uuid4())
    rx.dispense()
    assert rx.status is PrescriptionStatus.DISPENSED


def test_add_item_after_draft_rejected() -> None:
    rx = _rx()
    rx.add_item(_item())
    rx.validate(validated_by=uuid4())
    with pytest.raises(InvalidPrescriptionStateError):
        rx.add_item(_item())


def test_zero_quantity_item_rejected() -> None:
    with pytest.raises(ValueError):
        PrescriptionItem(
            drug_id=uuid4(),
            quantity=Decimal("0"),
            dose="1 viên",
            frequency="1 lần/ngày",
            duration="1 ngày",
        )
