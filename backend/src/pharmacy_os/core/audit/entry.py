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

    # --- two-factor authentication (Sprint 8) ---
    # Every transition of a user's second factor is recorded, because each one either
    # raises or lowers the protection standing between a leaked password and a binding
    # ledger signature (TT18 Điều 15.1.d). ``context`` never carries the secret, a
    # code, or a backup code — only which account changed and how.
    TWO_FACTOR_ENROLLED = "TWO_FACTOR_ENROLLED"
    """A secret was issued and is awaiting confirmation (still inactive)."""

    TWO_FACTOR_ACTIVATED = "TWO_FACTOR_ACTIVATED"
    """Confirmed with a real code — from here the account is protected."""

    TWO_FACTOR_DISABLED = "TWO_FACTOR_DISABLED"
    """The user turned their own second factor off."""

    TWO_FACTOR_RESET = "TWO_FACTOR_RESET"
    """An **administrator** cleared somebody else's 2FA (lost-device recovery).

    Separate from :attr:`TWO_FACTOR_DISABLED` for the reason ``PASSWORD_RESET`` is
    separate from ``PASSWORD_CHANGED``: one person lowering another person's defences
    is a privileged act and must be answerable on its own."""

    TWO_FACTOR_FAILED = "TWO_FACTOR_FAILED"
    """A wrong code was submitted. A burst on one account is the signature of somebody
    who already holds the password and is guessing the six digits."""

    TWO_FACTOR_BACKUP_CODE_USED = "TWO_FACTOR_BACKUP_CODE_USED"
    """A recovery code was spent — worth its own action because it usually means the
    authenticator device is gone, and because ten of them is a finite supply."""

    # --- customer health data (dữ liệu nhạy cảm, NĐ356 Điều 4.2) ---
    CUSTOMER_SENSITIVE_READ = "CUSTOMER_SENSITIVE_READ"
    """A person opened a customer's allergies / conditions / medication history."""

    CUSTOMER_SENSITIVE_AUTO_CHECK = "CUSTOMER_SENSITIVE_AUTO_CHECK"
    """The system read the same data on its own (clinical safety check during a sale).

    Deliberately distinct from :attr:`CUSTOMER_SENSITIVE_READ` (duyệt Q3): machine
    reads outnumber human ones by orders of magnitude, and a report answering "who
    looked at this patient's file" is useless if it is buried in them.
    """

    SALES_ALLERGY_WARNING_OVERRIDDEN = "SALES_ALLERGY_WARNING_OVERRIDDEN"
    """Bán một đơn dù đã cảnh báo dị ứng — người bán ghi lý do và chịu trách nhiệm (Đ-6).

    Quyết định Đ-6 chọn *cảnh báo + xác nhận* thay cho chặn cứng, nên dòng audit này
    **chính là** cái làm cho lựa chọn đó chịu trách nhiệm được: nó ghi ai bán, đơn nào,
    bao nhiêu cảnh báo và mức nặng nhất. Không có nó thì "buộc xác nhận" chỉ là một ô
    nhập chữ rồi trôi mất."""

    SALE_PRICE_OVERRIDE = "SALE_PRICE_OVERRIDE"
    """Một đơn được bán với giá **khác giá niêm yết** (2026-07-31, Chain chốt).

    Điều 6.5.i Luật Dược cấm bán cao hơn giá niêm yết; Điều 107.4 buộc niêm yết giá.
    Quyết định của Chain là **cho lệch cả hai chiều, đòi lý do, ghi audit** — nên dòng
    này chính là thứ duy nhất còn lại để trả lời *"vì sao đơn ấy bán khác giá niêm yết"*.

    Cùng khuôn với :attr:`SALES_ALLERGY_WARNING_OVERRIDDEN`, và cùng lý do: khi cổng là
    một lời xác nhận chứ không phải lệnh cấm, dòng audit **chính là** cái làm cho lựa
    chọn đó chịu trách nhiệm được.

    ``context`` mang **số dòng lệch**, không mang giá từng dòng: một đơn `3 dòng lệch` đã
    đủ để người soát sổ kéo đơn đó ra đọc, còn chép giá từng dòng vào đây là biến sổ audit
    thành bản sao thứ hai của bảng ``sale_lines`` — thứ nó đang canh."""

    CUSTOMER_PHONE_REVEALED = "CUSTOMER_PHONE_REVEALED"
    """Một người bấm xem **số điện thoại đầy đủ** của khách (Chain chốt 2026-07-31).

    Danh sách khách nay chỉ trả về ``*******494`` — ba số cuối, che ở **server**. Xem đủ
    số là một hành động riêng, cần quyền ``crm.pii.reveal`` (chỉ cấp chuỗi), và phải để
    lại vết: che mà không ghi vết thì không trả lời được câu *"ai đã lấy số của khách
    này"* — mà đó mới là câu hỏi khi số điện thoại rò ra ngoài.

    ``context`` không mang số. Ghi lại chính thứ mình vừa hạn chế là vô nghĩa."""

    CUSTOMER_SENSITIVE_WRITE = "CUSTOMER_SENSITIVE_WRITE"
    CUSTOMER_MEDICATION_HISTORY_RECORDED = "CUSTOMER_MEDICATION_HISTORY_RECORDED"
    """The system appended a customer's medication history from a completed sale or
    dispense (not a human writing the file).

    Distinct from :attr:`CUSTOMER_SENSITIVE_WRITE` for the same reason
    :attr:`CUSTOMER_SENSITIVE_AUTO_CHECK` is distinct from the human read: this fires
    on every sale/dispense to a consenting known customer, so folding it into the
    manual-write trail would bury the writes a person actually made. Recorded once
    per (customer, source, ref_id), never on idempotent replay."""

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

    PERIODIC_REPORT_EXPORTED = "PERIODIC_REPORT_EXPORTED"
    """Mẫu số 06 (NĐ 163/2025 Điều 35.2) generated for a reporting period — the
    evidence an inspection asks for first: "đã báo cáo kỳ này chưa, lúc nào, ai tạo"."""

    DRUG_RETURN_RECORDED = "DRUG_RETURN_RECORDED"
    """A Phụ lục XVIII biên bản (TT18 Điều 6.2/12.1.d) was recorded — who logged the
    return of unused GN/HT/TC medicine. The returner's CCCD number is never written
    into the audit context, same discipline as :attr:`CONTROLLED_LEDGER_ENTRY_RECORDED`
    keeping the customer's name/address out."""

    LEDGER_DAILY_CLOSURE_EXPORTED = "LEDGER_DAILY_CLOSURE_EXPORTED"
    """Phụ lục VIII/XVI daily print-and-sign export generated (TT18 Điều 15.1 ghi chú —
    the mandatory "trích xuất, in cuối mỗi ngày" step). ``context`` carries the SHA-256
    of the exported content (not PII) so a later dispute over "was this page altered
    after printing" can be checked against this row."""

    LEDGER_BOOK_SIGNED = "LEDGER_BOOK_SIGNED"
    """Điện tử xác nhận 1 sổ/1 ngày (TT18 Điều 15.1.d, hướng A) — the act that answers
    "ai xác nhận sổ ngày này đúng, đủ". ``context`` carries the SHA-256 of the signed
    content (not PII) so a later dispute can be checked against this row, the same
    discipline as :attr:`LEDGER_DAILY_CLOSURE_EXPORTED`."""

    # --- sales (bán thuốc — Luật Dược Điều 6.5.h, cùng lý do PRESCRIPTION_DISPENSED) ---
    SALE_COMPLETED = "SALE_COMPLETED"
    """A sale was finalised — the third thing an inspection asks about: "ai đã bán
    thuốc này, khi nào". Recorded once per ``client_uuid`` (not on idempotent replay)."""

    SALE_RETURN_REGISTERED = "SALE_RETURN_REGISTERED"
    """A (partial) return was registered against a completed sale. Deliberately
    does **not** trigger an automatic inventory restock — a returned medicine
    needs a pharmacist to inspect it before it can go back on the shelf, so
    putting it back into sellable stock is a separate, manual decision (existing
    ``POST /inventory/receive``), not wired as a cross-module reaction here."""

    # --- sales via payment gateway (Sprint 8 mục 4/4, payment_vnpay) ---
    SALE_VNPAY_INITIATED = "SALE_VNPAY_INITIATED"
    """A ``DRAFT`` order was persisted and a VNPAY payment link issued — money has
    not moved yet. Worth its own record for the same reason as
    :attr:`TWO_FACTOR_ENROLLED`: issued-but-not-confirmed is a distinct fact from
    confirmed, and an inspection asking "was this ever attempted" needs it even if
    the customer never paid. The confirmed case reuses :attr:`SALE_COMPLETED` — one
    sale, one completion record, regardless of payment method."""

    SALE_VNPAY_CANCELLED = "SALE_VNPAY_CANCELLED"
    """A pending VNPAY payment failed, was cancelled at the gateway, or expired
    unpaid — the order moved ``DRAFT`` → ``CANCELLED``. No cash equivalent exists:
    a cash sale is only ever persisted already-``COMPLETED``, so there is nothing
    pending that could fail after the fact."""

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

    INVENTORY_RECONCILIATION_RESOLVED = "INVENTORY_RECONCILIATION_RESOLVED"
    """A ``stock_reconciliation_needed`` flag (GRN lot collision/failure) was marked
    handled — "ai đã xử lý chênh lệch tồn kho này". The record itself carries no
    actor/timestamp for the resolve action; this is the only place that does."""

    # --- procurement (cam kết tài chính với NCC, xác nhận nhận hàng thật) ---
    PROCUREMENT_PO_ORDERED = "PROCUREMENT_PO_ORDERED"
    """DRAFT -> ORDERED — the moment a purchase order becomes a real financial
    commitment to a supplier ("ai đã đặt đơn mua hàng này")."""

    PROCUREMENT_GRN_CONFIRMED = "PROCUREMENT_GRN_CONFIRMED"
    """A goods receipt note was confirmed — the fact that triggers real stock-in
    ("ai đã xác nhận nhận lô hàng này"), same reasoning as
    :attr:`INVENTORY_STOCK_RECEIVED`. The later ``inventory`` batch-creation step
    is a separate cross-module reaction, not re-audited here."""

    # --- clinical (quyết định lâm sàng có AI hỗ trợ — docs/12 mục 7 yêu cầu vết) ---
    CLINICAL_INTERACTION_CHECKED = "CLINICAL_INTERACTION_CHECKED"
    """A drug-interaction check ran and wrote an :class:`AiRecommendation`.

    The recommendation row itself already carries model/confidence/output as its
    own immutable record, but not *who* triggered the check (human via
    ``/clinical/check-interactions`` or the automatic cross-module safety net) —
    this fills that gap, same reasoning as :attr:`CONTROLLED_LEDGER_ENTRY_RECORDED`."""

    CLINICAL_RECOMMENDATION_ACCEPTED = "CLINICAL_RECOMMENDATION_ACCEPTED"
    """Pharmacist human-in-the-loop sign-off on an AI recommendation — the act
    docs/12 mục 6 requires before a serious finding can be treated as cleared."""

    # --- catalog (phân loại rx_class quyết định toàn bộ luồng kiểm soát downstream) ---
    CATALOG_DRUG_CREATED = "CATALOG_DRUG_CREATED"
    """A drug was added to the tenant's catalog — worth a trail because its
    ``rx_class`` (OTC/ETC/CONTROLLED) is the authoritative classification every
    downstream rule (sales Rx gate, compliance ledger) trusts; a wrong
    classification here is a compliance risk traced back to "ai đã thêm/phân
    loại thuốc này"."""

    CATALOG_DRUG_INGREDIENTS_REPLACED = "CATALOG_DRUG_INGREDIENTS_REPLACED"
    """Danh sách hoạt chất của một thuốc bị đặt lại (2026-07-30).

    Đáng ghi vết vì đây là **đường duy nhất làm cảnh báo dị ứng ngừng kêu**: bỏ hoạt chất
    ra khỏi một thuốc thì khách dị ứng chất đó mua thuốc đó sẽ đi qua quầy trong im lặng,
    và không có gì khác trong hệ thống ghi lại rằng điều đó đã xảy ra. Sổ audit là nơi duy
    nhất trả lời được "ai đã bỏ hoạt chất khỏi thuốc này, lúc nào".

    ``context`` chỉ mang **số lượng trước/sau** (``count_before``/``count_after``), không
    mang id hoạt chất: một dòng ``2 → 0`` đã đủ để cảnh báo người soát sổ, còn chép danh
    sách vào đây là biến sổ audit thành bản sao thứ hai của dữ liệu nó canh (NĐ 356/2025
    Điều 4.2 — cùng lý do đã ghi ở :class:`AuditEntry`)."""

    CATALOG_DRUG_PRICE_CHANGED = "CATALOG_DRUG_PRICE_CHANGED"
    """Giá bán niêm yết của một thuốc bị đặt lại (2026-07-31, Chain giao).

    Điều 107.4 Luật Dược buộc niêm yết giá bán lẻ; Điều 6.5.i cấm bán cao hơn giá niêm
    yết. Cả hai chỉ kiểm chứng được nếu trả lời được *"giá niêm yết ngày ấy là bao nhiêu,
    ai đặt"* — ``drugs.sale_price`` một mình không trả lời được, nó chỉ có giá **hiện tại**.

    Sổ audit ở đây là **lớp thứ hai**, không phải nguồn: nguồn là bảng chỉ-ghi-thêm
    ``drug_price_history``. Hai lớp vì chúng trả lời hai câu hỏi khác nhau — bảng lịch sử
    trả lời *"giá đổi thế nào"*, sổ audit trả lời *"ai chạm vào cái gì trong hệ thống"*,
    và mất một trong hai không suy ra được từ cái còn lại.

    ``context`` **được** mang giá cũ/mới, khác :attr:`CATALOG_DRUG_INGREDIENTS_REPLACED`:
    giá không phải dữ liệu cá nhân của ai, nên lý do NĐ 356/2025 Điều 4.2 không áp ở đây."""

    # --- analytics (đề xuất nhập hàng → PO nháp: ai bấm gì, PROJECT_STATE §7am) ---
    ANALYTICS_REORDER_RUN = "ANALYTICS_REORDER_RUN"
    """A reorder-suggestion run was executed for a branch — the act that regenerates
    the branch's PENDING/INSUFFICIENT_DATA suggestions from current sales+stock."""

    ANALYTICS_SUGGESTION_MATERIALIZED = "ANALYTICS_SUGGESTION_MATERIALIZED"
    """A human turned a suggestion into a DRAFT purchase order — worth a trail because
    it is the moment a machine-computed demand number becomes a (still-draft)
    procurement action, traced to "ai đã tạo PO nháp từ đề xuất này"."""

    ANALYTICS_SUGGESTION_DISMISSED = "ANALYTICS_SUGGESTION_DISMISSED"
    """A human decided not to act on a suggestion."""

    # --- vận hành mã hoá at-rest (D-SEC-01 đòi rotation phải có vết) ---
    ENCRYPTION_KEY_ROTATED = "ENCRYPTION_KEY_ROTATED"
    """Khoá mã hoá at-rest đã xoay sang phiên bản mới.

    D-SEC-01 khoá chu kỳ **90 ngày** và đòi thao tác xoay phải có audit trail. Xoay khoá
    là thao tác **vận hành** (đặt khoá mới vào cấu hình rồi trỏ ``current_version``), nên
    không có request HTTP nào để móc vào — dòng này do
    ``seeds.record_key_rotation`` ghi, và lệnh đó **đọc cấu hình đang chạy để xác nhận
    việc xoay có thật** trước khi ghi.

    Vì sao cần: sau lần xoay thứ hai, câu hỏi *"dòng mang thẻ v1 này còn khoá không, và
    ai bỏ nó lại đằng sau"* không trả lời được từ dữ liệu — thẻ phiên bản nằm trên
    ciphertext, còn lý do và thời điểm thì không nằm ở đâu cả."""

    ANALYTICS_SUGGESTION_UNDONE = "ANALYTICS_SUGGESTION_UNDONE"
    """A human undid a materialisation: the draft PO was cancelled and the suggestion
    went back to PENDING. Audited separately from the cancel that procurement records,
    because this path cancels under the **system** identity — without a row here, the
    trail would show a purchase order cancelled by nobody."""


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
