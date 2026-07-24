"""The CSV column contract is pure and loss-free — no DB, no HTTP needed."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from pharmacy_os.core.audit.csv_export import CSV_HEADER, entry_to_row
from pharmacy_os.core.audit.entry import AuditAction, AuditEntry

_TENANT = UUID("00000000-0000-0000-0000-0000000a0001")
_ACTOR = UUID("00000000-0000-0000-0000-0000000d0001")


def test_row_aligns_to_header() -> None:
    entry = AuditEntry(
        tenant_id=_TENANT,
        action=AuditAction.SALE_COMPLETED,
        target_type="sales_order",
        actor_user_id=_ACTOR,
        target_id="ORDER-1",
        context={"branch_id": "b1", "client_ip": "10.0.0.1"},
        occurred_at=datetime(2026, 7, 24, 8, 30, tzinfo=UTC),
    )
    row = entry_to_row(entry)

    assert len(row) == len(CSV_HEADER)
    cells = dict(zip(CSV_HEADER, row, strict=True))
    assert cells["action"] == "SALE_COMPLETED"
    assert cells["target_type"] == "sales_order"
    assert cells["target_id"] == "ORDER-1"
    assert cells["actor_user_id"] == str(_ACTOR)
    assert cells["occurred_at"] == "2026-07-24T08:30:00+00:00"
    assert json.loads(cells["context"]) == {"branch_id": "b1", "client_ip": "10.0.0.1"}


def test_none_fields_become_empty_cells_not_the_literal_none() -> None:
    entry = AuditEntry(
        tenant_id=_TENANT,
        action=AuditAction.LOGIN_FAILED,
        target_type="user",
        actor_user_id=None,
        target_id=None,
        context={},
    )
    cells = dict(zip(CSV_HEADER, entry_to_row(entry), strict=True))
    assert cells["actor_user_id"] == ""
    assert cells["target_id"] == ""
    assert cells["context"] == "{}"


def test_context_json_is_deterministic() -> None:
    entry = AuditEntry(
        tenant_id=_TENANT,
        action=AuditAction.CUSTOMER_SENSITIVE_READ,
        target_type="customer",
        context={"b": "2", "a": "1"},
    )
    cells = dict(zip(CSV_HEADER, entry_to_row(entry), strict=True))
    # sorted keys → stable byte output across exports
    assert cells["context"] == '{"a":"1","b":"2"}'
