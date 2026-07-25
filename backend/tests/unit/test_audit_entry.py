"""The audit record's shape and its context-merging rule."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pharmacy_os.core.audit import AuditAction, AuditEntry


def _entry(**kwargs: object) -> AuditEntry:
    defaults: dict[str, object] = {
        "tenant_id": uuid4(),
        "action": AuditAction.LOGIN_SUCCESS,
        "target_type": "user",
    }
    defaults.update(kwargs)
    return AuditEntry(**defaults)  # type: ignore[arg-type]


def test_entry_defaults_id_and_timestamp() -> None:
    before = datetime.now(UTC)
    entry = _entry()
    assert entry.id is not None
    assert before <= entry.occurred_at <= datetime.now(UTC)
    assert entry.occurred_at.tzinfo is not None


def test_actor_and_target_id_are_optional() -> None:
    """A failed login against an unknown address has no actor to name."""
    entry = _entry(action=AuditAction.LOGIN_FAILED)
    assert (entry.actor_user_id, entry.target_id) == (None, None)


def test_entry_is_immutable() -> None:
    entry = _entry()
    try:
        entry.action = AuditAction.ROLE_GRANTED  # type: ignore[misc]
    except (AttributeError, TypeError):
        return
    raise AssertionError("AuditEntry phải bất biến")


def test_with_context_merges_and_keeps_identity() -> None:
    entry = _entry(context={"branch_id": "b1"})
    enriched = entry.with_context(client_ip="10.0.0.1")

    assert enriched.context == {"branch_id": "b1", "client_ip": "10.0.0.1"}
    # Same fact, enriched — not a new one, so id and timestamp must not move.
    assert (enriched.id, enriched.occurred_at) == (entry.id, entry.occurred_at)
    # The original is untouched.
    assert entry.context == {"branch_id": "b1"}


def test_with_context_drops_none_instead_of_storing_nulls() -> None:
    enriched = _entry().with_context(client_ip=None, branch_id="b1")
    assert enriched.context == {"branch_id": "b1"}


def test_with_context_overwrites_an_existing_key() -> None:
    enriched = _entry(context={"client_ip": "10.0.0.1"}).with_context(client_ip="10.0.0.2")
    assert enriched.context == {"client_ip": "10.0.0.2"}


def test_every_action_the_codebase_emits_has_a_member() -> None:
    """Guards against an action string drifting away from the enum."""
    expected = {
        "LOGIN_SUCCESS",
        "LOGIN_FAILED",
        "ACCOUNT_LOCKED",
        "USER_CREATED",
        "USER_ACTIVATED",
        "USER_DEACTIVATED",
        "ROLE_GRANTED",
        "ROLE_REVOKED",
        "PASSWORD_CHANGED",
        "PASSWORD_RESET",
        "TOKEN_REPLAY_DETECTED",
        "CUSTOMER_SENSITIVE_READ",
        "CUSTOMER_SENSITIVE_AUTO_CHECK",
        "CUSTOMER_SENSITIVE_WRITE",
        "CUSTOMER_MEDICATION_HISTORY_RECORDED",
        "CONSENT_GRANTED",
        "CONSENT_REVOKED",
        "CUSTOMER_ERASED",
        "PRESCRIPTION_CREATED",
        "PRESCRIPTION_APPROVED",
        "PRESCRIPTION_REJECTED",
        "PRESCRIPTION_DISPENSED",
        "CONTROLLED_LEDGER_ENTRY_RECORDED",
        "TENANT_COMPLIANCE_CONFIG_SET",
        "PERIODIC_REPORT_EXPORTED",
        "DRUG_RETURN_RECORDED",
        "LEDGER_DAILY_CLOSURE_EXPORTED",
        "LEDGER_BOOK_SIGNED",
        "SALE_COMPLETED",
        "INVENTORY_STOCK_RECEIVED",
        "INVENTORY_STOCK_DISPENSED",
        "PROCUREMENT_PO_ORDERED",
        "PROCUREMENT_GRN_CONFIRMED",
        "CLINICAL_INTERACTION_CHECKED",
        "CLINICAL_RECOMMENDATION_ACCEPTED",
        "CATALOG_DRUG_CREATED",
        "SALE_RETURN_REGISTERED",
        "INVENTORY_RECONCILIATION_RESOLVED",
        "ANALYTICS_REORDER_RUN",
        "ANALYTICS_SUGGESTION_MATERIALIZED",
        "ANALYTICS_SUGGESTION_DISMISSED",
    }
    assert {a.value for a in AuditAction} == expected


def test_action_is_a_string_enum_so_it_round_trips_through_the_db() -> None:
    assert AuditAction("ROLE_GRANTED") is AuditAction.ROLE_GRANTED
    assert str(AuditAction.ROLE_GRANTED) == "ROLE_GRANTED"


def test_every_action_fits_the_audit_logs_column() -> None:
    """Postgres rejects an over-long ``action`` with a 500; SQLite (what the rest of
    the suite runs on) silently accepts it, so nothing else here would catch a new
    action name that outgrows the column. Three already had — see migration ``0023``.
    The width is read off the model so the two can never drift apart.
    """
    from pharmacy_os.core.audit.models import AuditLogORM

    width = AuditLogORM.__table__.c.action.type.length
    assert width is not None
    too_long = sorted(a.value for a in AuditAction if len(a.value) > width)
    assert too_long == [], f"action names longer than varchar({width}): {too_long}"
