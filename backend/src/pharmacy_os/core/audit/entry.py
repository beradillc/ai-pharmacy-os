"""What an audit record is: the closed set of auditable actions and one entry.

Framework-free on purpose — the same shape is written to the ``audit_logs`` table,
emitted to the structured log stream, and read back by the query endpoint.

**Append-only.** There is no ``update``/``delete`` on the repository port, matching
``compliance.ControlledLedgerEntry`` and ``NationalSyncLog``: an audit trail whose
rows can be edited answers "who accessed what" with "whatever someone last wrote".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class AuditAction(StrEnum):
    """Auditable actions, closed set.

    Derived from the calls iam already makes (docs/15 §6) rather than invented up
    front, so every member has a real emitter. Two members go beyond the list in the
    original request because iam distinguishes cases the short list collapses:
    ``USER_ACTIVATED`` (re-enabling an account is as reportable as disabling one) and
    ``PASSWORD_RESET`` (an admin resetting somebody else's password is a different
    fact from a user changing their own, and only the first is a privileged act).
    """

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    USER_CREATED = "USER_CREATED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    ROLE_GRANTED = "ROLE_GRANTED"
    ROLE_REVOKED = "ROLE_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    TOKEN_REPLAY_DETECTED = "TOKEN_REPLAY_DETECTED"

    # --- customer health data (dữ liệu nhạy cảm, NĐ356 Điều 4.2) ---
    CUSTOMER_SENSITIVE_READ = "CUSTOMER_SENSITIVE_READ"
    """A person opened a customer's allergies / conditions / medication history."""

    CUSTOMER_SENSITIVE_AUTO_CHECK = "CUSTOMER_SENSITIVE_AUTO_CHECK"
    """The system read the same data on its own (clinical safety check during a sale).

    Deliberately distinct from :attr:`CUSTOMER_SENSITIVE_READ` (duyệt Q3): machine
    reads outnumber human ones by orders of magnitude, and a report answering "who
    looked at this patient's file" is useless if it is buried in them.
    """

    CUSTOMER_SENSITIVE_WRITE = "CUSTOMER_SENSITIVE_WRITE"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CUSTOMER_ERASED = "CUSTOMER_ERASED"
    """Identity stripped from a customer record (khử nhận dạng, duyệt Q2).

    The audit row outlives the data it describes — which is why ``target_id`` is a
    bare UUID with no foreign key.
    """

    # --- prescription (cấp phát thuốc kê đơn — Luật Dược Điều 6.5.h) ---
    PRESCRIPTION_CREATED = "PRESCRIPTION_CREATED"
    PRESCRIPTION_APPROVED = "PRESCRIPTION_APPROVED"
    """Pharmacist validation — the act the statute reserves to a pharmacist."""

    PRESCRIPTION_REJECTED = "PRESCRIPTION_REJECTED"
    PRESCRIPTION_DISPENSED = "PRESCRIPTION_DISPENSED"
    """Handover of a prescription-only medicine — the act an inspection asks about
    first: "ai đã cấp phát đơn thuốc này"."""

    # --- compliance (sổ thuốc kiểm soát đặc biệt — TT20/2017, QĐ540) ---
    CONTROLLED_LEDGER_ENTRY_RECORDED = "CONTROLLED_LEDGER_ENTRY_RECORDED"
    """A line written to the sổ thuốc kiểm soát — the second thing an inspection asks
    about: "ai đã bán lô thuốc hướng thần/gây nghiện này"."""

    TENANT_COMPLIANCE_CONFIG_SET = "TENANT_COMPLIANCE_CONFIG_SET"
    """Mã cơ sở do Cục QLD cấp changed — a low-frequency admin act worth a trail."""

    # --- sales (bán thuốc — Luật Dược Điều 6.5.h, cùng lý do PRESCRIPTION_DISPENSED) ---
    SALE_COMPLETED = "SALE_COMPLETED"
    """A sale was finalised — the third thing an inspection asks about: "ai đã bán
    thuốc này, khi nào". Recorded once per ``client_uuid`` (not on idempotent replay)."""

    # --- inventory (sổ nhập/xuất kho — chỉ hành vi con người gõ tay qua API) ---
    INVENTORY_STOCK_RECEIVED = "INVENTORY_STOCK_RECEIVED"
    """Manual goods receipt (``POST /inventory/receive``) — a person keyed in a batch.

    Deliberately excludes the cross-module reaction ``receive_from_goods_receipt``
    (GRN confirmed → auto stock-in): that event already has its own audit trail
    once ``procurement`` gets one — recording it here too would double-count the
    same real-world fact under two actions.
    """

    INVENTORY_STOCK_DISPENSED = "INVENTORY_STOCK_DISPENSED"
    """Manual dispense (``POST /inventory/dispense``) — same exclusion logic as
    above: ``dispense_for_sale`` (the cross-module reaction to ``SaleCompleted``)
    is already covered by :attr:`SALE_COMPLETED`, not audited a second time here."""


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """One immutable fact: who did what, to what, when.

    ``context`` carries **metadata only** — client IP, the branch the actor was
    operating in, an email that failed to authenticate. Never request or response
    payloads: this table exists to prove access happened, and copying the data being
    accessed into it would turn the audit trail into a second, less guarded store of
    the very personal data it is meant to protect (NĐ 356/2025 Điều 4.2).

    ``actor_user_id`` is nullable for actions with no signed-in actor — a login
    attempt against an unknown address, or a system/CLI operation.
    """

    tenant_id: UUID
    action: AuditAction
    target_type: str
    actor_user_id: UUID | None = None
    target_id: str | None = None
    context: dict[str, str] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)

    def with_context(self, **extra: str | None) -> AuditEntry:
        """Return a copy with non-empty *extra* merged into ``context``.

        ``None`` values are dropped rather than stored as nulls, so an entry recorded
        without a client IP simply has no ``client_ip`` key.
        """
        merged = dict(self.context)
        merged.update({k: v for k, v in extra.items() if v is not None})
        return AuditEntry(
            tenant_id=self.tenant_id,
            action=self.action,
            target_type=self.target_type,
            actor_user_id=self.actor_user_id,
            target_id=self.target_id,
            context=merged,
            occurred_at=self.occurred_at,
            id=self.id,
        )
