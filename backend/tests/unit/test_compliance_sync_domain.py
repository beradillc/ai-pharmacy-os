"""Domain tests for NationalSyncLog state machine — docs/13_COMPLIANCE_SPEC.md mục D.2."""

from uuid import uuid4

import pytest

from pharmacy_os.modules.compliance.domain import (
    ComplianceError,
    InvalidSyncStateError,
    NationalSyncLog,
    SyncPayloadType,
    SyncStatus,
)


def _log(**kw: object) -> NationalSyncLog:
    kw.setdefault("tenant_id", uuid4())
    kw.setdefault("payload_type", SyncPayloadType.DRUG)
    kw.setdefault("payload_hash", "deadbeef")
    kw.setdefault("client_uuid", "cli-001")
    return NationalSyncLog(**kw)  # type: ignore[arg-type]


def test_new_log_is_pending_with_request_at_and_zero_retries() -> None:
    log = _log()
    assert log.status is SyncStatus.PENDING
    assert log.request_at is not None
    assert log.response_at is None
    assert log.retry_count == 0
    assert log.error is None


def test_payload_type_has_three_values() -> None:
    assert {p.value for p in SyncPayloadType} == {"drug", "sale", "prescription"}


def test_status_has_four_values() -> None:
    assert {s.value for s in SyncStatus} == {"PENDING", "SENT", "ACK", "FAILED"}


def test_mark_sent_from_pending() -> None:
    log = _log()
    log.mark_sent()
    assert log.status is SyncStatus.SENT


def test_mark_acked_records_response() -> None:
    log = _log()
    log.mark_sent()
    log.mark_acked(response_code="200", response_body='{"ack":true}')
    assert log.status is SyncStatus.ACK
    assert log.response_code == "200"
    assert log.response_body == '{"ack":true}'
    assert log.response_at is not None


def test_mark_acked_requires_sent() -> None:
    log = _log()  # still PENDING
    with pytest.raises(InvalidSyncStateError):
        log.mark_acked(response_code="200", response_body="ok")


def test_mark_failed_increments_retry_and_records_error() -> None:
    log = _log()
    log.mark_sent()
    log.mark_failed(error="timeout", response_code="504")
    assert log.status is SyncStatus.FAILED
    assert log.retry_count == 1
    assert log.error == "timeout"
    assert log.response_code == "504"
    assert log.response_at is not None


def test_failed_can_be_retried_and_acked() -> None:
    log = _log()
    log.mark_sent()
    log.mark_failed(error="timeout")
    assert log.retry_count == 1

    log.mark_sent()  # retry from FAILED
    assert log.status is SyncStatus.SENT
    log.mark_acked(response_code="200", response_body="ok")
    assert log.status is SyncStatus.ACK
    assert log.retry_count == 1  # unchanged — retry_count counts failures


def test_second_failure_increments_retry_again() -> None:
    log = _log()
    log.mark_sent()
    log.mark_failed(error="e1")
    log.mark_sent()
    log.mark_failed(error="e2")
    assert log.retry_count == 2


def test_mark_sent_rejected_from_acked() -> None:
    log = _log()
    log.mark_sent()
    log.mark_acked(response_code="200", response_body="ok")
    with pytest.raises(InvalidSyncStateError):
        log.mark_sent()


def test_mark_failed_requires_sent() -> None:
    log = _log()  # PENDING
    with pytest.raises(InvalidSyncStateError):
        log.mark_failed(error="nope")


def test_invalid_sync_state_error_is_compliance_error() -> None:
    assert issubclass(InvalidSyncStateError, ComplianceError)
