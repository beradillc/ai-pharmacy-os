"""Domain tests for NationalSyncRetryTask — docs/13_COMPLIANCE_SPEC.md mục D.4.

The queue's whole job is "eventually, but not forever": exponential backoff between
attempts and a hard stop at ``max_retries``. Both live in the entity, so they are
testable without a database, a gateway, or a running relay.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pharmacy_os.modules.compliance.domain import (
    InvalidSyncStateError,
    NationalSyncRetryTask,
    SyncPayloadType,
    SyncRetryStatus,
)

_NOW = datetime(2026, 7, 25, 9, 0, tzinfo=UTC)


def _task(**kw: object) -> NationalSyncRetryTask:
    kw.setdefault("tenant_id", uuid4())
    kw.setdefault("branch_id", uuid4())
    kw.setdefault("sync_log_id", uuid4())
    kw.setdefault("payload_type", SyncPayloadType.SALE)
    kw.setdefault("client_uuid", "cli-001")
    kw.setdefault("payload", '{"order_id":"1"}')
    return NationalSyncRetryTask(**kw)  # type: ignore[arg-type]


def test_new_task_is_pending_and_due_immediately() -> None:
    task = _task()
    assert task.status is SyncRetryStatus.PENDING
    assert task.attempt_count == 0
    assert task.next_attempt_at is None
    assert task.is_due(_NOW)


def test_retry_status_has_two_values() -> None:
    assert {s.value for s in SyncRetryStatus} == {"PENDING", "DEAD"}


def test_failure_schedules_next_attempt_with_exponential_backoff() -> None:
    task = _task()
    for expected_delay in (60.0, 120.0, 240.0):
        assert task.record_failure(
            error="cổng từ chối", now=_NOW, base_backoff_seconds=60.0, max_retries=10
        )
        assert task.next_attempt_at == _NOW + timedelta(seconds=expected_delay)
        assert task.status is SyncRetryStatus.PENDING
    assert task.attempt_count == 3
    assert task.last_error == "cổng từ chối"


def test_task_is_not_due_until_its_backoff_elapses() -> None:
    task = _task()
    task.record_failure(error="503", now=_NOW, base_backoff_seconds=60.0, max_retries=5)
    assert not task.is_due(_NOW + timedelta(seconds=59))
    assert task.is_due(_NOW + timedelta(seconds=60))


def test_retries_are_bounded_then_the_task_dies() -> None:
    task = _task()
    for _ in range(2):
        assert task.record_failure(error="503", now=_NOW, base_backoff_seconds=1.0, max_retries=3)
    assert not task.record_failure(error="503", now=_NOW, base_backoff_seconds=1.0, max_retries=3)
    assert task.status is SyncRetryStatus.DEAD
    assert task.attempt_count == 3
    assert task.next_attempt_at is None


def test_a_dead_task_is_never_due_again() -> None:
    task = _task()
    task.record_failure(error="503", now=_NOW, base_backoff_seconds=1.0, max_retries=1)
    assert task.status is SyncRetryStatus.DEAD
    assert not task.is_due(_NOW + timedelta(days=365))


def test_a_dead_task_rejects_further_bookkeeping() -> None:
    task = _task()
    task.record_failure(error="503", now=_NOW, base_backoff_seconds=1.0, max_retries=1)
    with pytest.raises(InvalidSyncStateError):
        task.record_failure(error="503", now=_NOW, base_backoff_seconds=1.0, max_retries=1)
    with pytest.raises(InvalidSyncStateError):
        task.lease_until(_NOW + timedelta(minutes=5))


def test_lease_hides_the_task_until_the_lease_expires() -> None:
    task = _task()
    deadline = _NOW + timedelta(minutes=5)
    task.lease_until(deadline)
    assert not task.is_due(_NOW)
    assert task.is_due(deadline)
    # A crashed relay loses its lease rather than the work: the task simply comes back.
    assert task.attempt_count == 0
