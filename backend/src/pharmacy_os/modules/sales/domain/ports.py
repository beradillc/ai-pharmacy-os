"""Sales ports (implemented by infrastructure / composition root)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.sales.domain.entities import SalesOrder


@dataclass(frozen=True, slots=True)
class OrderRevenueRow:
    """One completed order's revenue facts, as read for the Sprint 7 revenue report.

    Deliberately order-level, not line-level: the report groups by period/branch, and
    an order-level ``subtotal`` (summed in SQL from its lines) is all that grouping
    needs. ``created_at`` doubles as the completion timestamp — ``complete_sale``
    builds and completes an order in the same call, so there is no separate
    "completed_at" to read (see ``SalesOrder.complete``).
    """

    order_id: UUID
    branch_id: UUID
    currency: str
    created_at: datetime
    subtotal: Decimal
    sold_by_user_id: UUID | None = None
    """Who completed the sale, or ``None`` for an order recorded before the column
    existed — see :attr:`SalesOrder.sold_by_user_id`. Defaulted so a repository (or
    a test double) that does not care about the salesperson dimension keeps
    building rows unchanged."""


@dataclass(frozen=True, slots=True)
class DrugSalesAggRow:
    """Net quantity a drug sold in one branch over a window, plus its net revenue.

    Line-level aggregation (group by ``drug_id``/``branch_id``), unlike
    :class:`OrderRevenueRow` which is order-level — this is what the analytics module
    reads to model demand velocity and rank top sellers (PROJECT_STATE §7am, Q1).

    ``quantity_sold`` is **net of returns** (``quantity - returned_quantity`` summed):
    a returned item was not consumed, so counting it would over-state demand and lead
    analytics to over-order. This deliberately differs from the revenue report, which
    counts gross at sale time (recognised revenue, PROJECT_STATE §7an) — different
    purpose, different convention, both documented. ``revenue`` is likewise net.
    Rows whose net quantity is ``0`` (fully returned) are dropped by the query.
    """

    drug_id: UUID
    branch_id: UUID
    quantity_sold: Decimal
    revenue: Decimal


@dataclass(frozen=True, slots=True)
class SalesOrderListRow:
    """One order as a till list shows it — the "hoá đơn hôm nay" read (Sprint 10, D1).

    Deliberately **not** :class:`OrderRevenueRow` reused: that row exists to be folded
    into revenue buckets, so it carries no ``status`` and no ``paid_total``, and it is
    ordered oldest-first because a report reads forwards. A till list needs exactly the
    two fields it lacks (an order can be ``RETURNED``/``PARTIALLY_RETURNED``, and the
    cashier looks for what was actually tendered) and reads backwards from now. Bending
    the report row into a UI row would have made both worse.

    ``subtotal`` is gross at sale time (same convention as the revenue report — see
    :class:`OrderRevenueRow`); ``line_count`` is the number of lines, not units.
    """

    order_id: UUID
    branch_id: UUID
    created_at: datetime
    status: str
    currency: str
    subtotal: Decimal
    paid_total: Decimal
    line_count: int
    customer_id: UUID | None
    sold_by_user_id: UUID | None


class SalesRepository(Protocol):
    async def add(self, order: SalesOrder) -> None: ...

    async def update(self, order: SalesOrder) -> None:
        """Persist mutations made to a previously-fetched order: status transitions,
        line ``returned_quantity``, and any :class:`~.entities.Payment` present on
        ``order`` that the stored row does not yet have (matched by ``id`` — a
        payment already in the row is left untouched, so this is safe to call
        again on a re-fetched order without duplicating tenders)."""
        ...

    async def get(self, order_id: UUID) -> SalesOrder | None: ...

    async def get_across_tenants(self, order_id: UUID) -> SalesOrder | None:
        """Look up one order by id, **ignoring tenant scoping**.

        The one deliberate exception to the tenant-scoping invariant every other
        method here upholds — exists solely for the ``payment_vnpay`` webhook
        (Sprint 8 mục 4/4): a gateway callback carries no ``RequestContext`` (VNPAY
        is not one of our authenticated users), so there is no tenant to scope by
        until *after* this call tells the caller which order — and thus which
        tenant — the callback is even about. Read-only, single-row-by-id: it
        cannot be used to list or search, so it cannot become a cross-tenant
        enumeration primitive. Every *write* that follows still goes through the
        normal tenant-scoped :meth:`update`, once the caller has built a
        :class:`~pharmacy_os.core.context.RequestContext` from the order's own
        ``tenant_id``/``branch_id``. Do not add a second call site for this."""
        ...

    async def by_client_uuid(self, client_uuid: str) -> SalesOrder | None: ...

    async def completed_in_range(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        sold_by_user_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
        limit: int,
        offset: int,
    ) -> list[OrderRevenueRow]:
        """Page of completed orders (any post-``DRAFT`` status) in ``[created_from,
        created_to)``, optionally narrowed to one branch and/or one salesperson,
        oldest first — the report service buckets these into periods in Python (no
        ``date_trunc``: the project keeps queries portable across Postgres/SQLite,
        see ``models.py``).

        ``sold_by_user_id`` filters to the orders that user completed; ``None``
        means "every salesperson", **not** "orders with no salesperson" — the
        unattributed pre-column orders stay in the unfiltered total and cannot be
        isolated on their own."""
        ...

    async def list_orders(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
        limit: int,
        offset: int,
    ) -> list[SalesOrderListRow]:
        """Page of orders in ``[created_from, created_to)``, **newest first**.

        Unlike :meth:`completed_in_range`, drafts are **included**: a draft on the till
        list is a sale someone started and abandoned, which is precisely what a shift
        handover wants to see. Callers that mean "revenue" must keep using
        ``completed_in_range`` — the two differ on purpose, and the difference is
        visible in the row's ``status``.
        """
        ...

    async def aggregate_sold_by_drug(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
    ) -> list[DrugSalesAggRow]:
        """Net quantity + revenue sold per ``(drug_id, branch_id)`` over
        ``[created_from, created_to)``, across completed (post-``DRAFT``) orders,
        optionally narrowed to one branch.

        Grouped in SQL — the result is bounded by the number of distinct drugs (a
        pharmacy's catalogue), not by order volume, so a plain list is returned (no
        paging, unlike :meth:`completed_in_range` which the report streams). Fully
        returned lines net to ``0`` and are excluded (see :class:`DrugSalesAggRow`)."""
        ...

    async def accrued_by_customer(
        self,
        tenant_id: UUID,
        customer_ids: Sequence[UUID],
        *,
        created_from: datetime,
        created_to: datetime,
    ) -> dict[UUID, Decimal]:
        """Tiền đã mua (đã trừ hàng trả) của từng khách trong ``[from, to)``.

        Đây là **cơ số tích luỹ** của chương trình khách quen — `crm.loyalty.boxes_earned`
        chia số này cho `REWARD_STEP`. Cố ý **tính ra từ đơn hàng thay vì giữ một cột số
        dư**: một cột số dư sẽ lệch khỏi doanh thu thật ngay lần đầu có đơn trả hàng, hoặc
        có đơn ghi bù, và không ai biết bên nào đúng. Tính ra thì luôn khớp, đổi kỳ chỉ là
        đổi khoảng ngày.

        Nhận nhiều id một lượt vì màn Khách hàng cần điền cả một trang — một lượt gọi,
        không phải một lượt mỗi dòng. Khách chưa mua gì **vắng mặt** trong kết quả (không
        phải `0`), để bên gọi tự chọn hiển thị "0" hay "—".
        """
        ...


@dataclass(frozen=True, slots=True)
class DrugInfo:
    """The authoritative dispensing facts sales needs about a drug.

    ``name``/``unit`` default to empty when the caller only cares about the Rx
    rule (e.g. tests) — a receipt renderer treats an empty ``name`` as "unknown
    drug" and falls back to the raw id.
    """

    drug_id: UUID
    requires_prescription: bool
    name: str = ""
    unit: str = ""
    sale_price: Decimal | None = None
    """Giá bán **niêm yết** của một đơn vị lẻ, hoặc ``None`` khi mã chưa đặt giá.

    Sales cần nó để trả lời đúng một câu: *đơn này có bán lệch giá niêm yết không*
    (Điều 6.5.i Luật Dược cấm bán cao hơn giá niêm yết; Điều 107.4 buộc niêm yết).
    ``None`` **không** phải "lệch" — không có giá niêm yết thì không có gì để lệch,
    và đòi thu ngân giải thích một phép so không tồn tại là vô nghĩa."""


@dataclass(frozen=True, slots=True)
class AllergyRisk:
    """The allergy verdict for one basket, as sales needs it to gate completion.

    Deliberately **not** the conflicts themselves: matching a basket against a
    customer's allergies is ``clinical``'s job (``find_allergy_alerts``), and sales
    duplicating that rule would give the pharmacy two answers to one clinical
    question. Sales needs only the facts its own rule turns on — *are there any*,
    *how bad is the worst one* — plus enough to write a meaningful audit line.

    ``consent_granted`` is carried separately from ``conflict_count == 0`` because
    the two mean different things at the counter and must not be shown the same way:
    *"this customer has no known allergies"* versus *"this pharmacy may not look"*.
    Luật 91/2025 Điều 9 gates health data behind its own consent purpose, so a
    customer identified only by phone at the till (``ConsentBasis.COUNTER``, quyết
    định Đ-4) yields ``consent_granted=False`` — and the counter must be told the
    check did not run, not that it came back clean.
    """

    consent_granted: bool
    conflict_count: int = 0
    worst_severity: str | None = None


class AllergyRiskProvider(Protocol):
    """Read-port for the allergy verdict, so sales imports neither crm nor clinical.

    Implemented at the composition root over ``CrmService`` (the customer's recorded
    allergies) and ``ClinicalService`` (the match). Returns ``None`` when no customer
    with that id exists for the tenant — distinct from an :class:`AllergyRisk` with
    ``consent_granted=False``, which means the customer exists but has not agreed to
    health-data processing.
    """

    async def for_sale(
        self, drug_ids: frozenset[UUID], customer_id: UUID, tenant_id: UUID
    ) -> AllergyRisk | None: ...


class DrugInfoProvider(Protocol):
    """Read-port for catalog facts, so sales never imports the catalog module.

    Implemented at the composition root (adapter over ``CatalogService``).
    Returns ``None`` when the drug is unknown to catalog.
    """

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None: ...


class SalespersonInfoProvider(Protocol):
    """Read-port for the *name* behind ``SalesOrder.sold_by_user_id``.

    Chain giao 2026-08-01: hoá đơn in ra phải có **người bán**. Tên người sống trong
    ``iam``, và ``sales`` không được import ``iam`` — nên đây là một cổng đọc, cài đặt ở
    composition root, đúng khuôn :class:`DrugInfoProvider` và :class:`PrescriptionInfoProvider`
    đã có.

    Trả ``None`` khi không tra được: đơn cũ hơn cột ``sold_by_user_id`` không mang người bán
    nào, và người bán có thể đã nghỉ việc và bị xoá. Hoá đơn khi đó **bỏ hẳn dòng đó** chứ
    không in một mã UUID cụt — một dãy hex trên tờ hoá đơn đưa khách không nói được gì với
    ai, và làm tờ giấy trông như lỗi hệ thống.
    """

    async def name_of(self, user_id: UUID, tenant_id: UUID) -> str | None: ...


@dataclass(frozen=True, slots=True)
class PrescriptionInfo:
    """The authoritative Rx facts sales needs to authorise a prescription sale.

    ``status`` is the prescription's raw status *value* (e.g. ``"VALIDATED"``);
    sales owns the accept-list of sale-authorising states in its domain rules, so
    it never imports the prescription module's status enum.
    """

    prescription_id: UUID
    status: str


class PrescriptionInfoProvider(Protocol):
    """Read-port for prescription facts, so sales never imports the prescription module.

    Implemented at the composition root (adapter over ``PrescriptionService``).
    Returns ``None`` when the prescription is unknown to the caller's tenant.
    """

    async def get(self, prescription_id: UUID, tenant_id: UUID) -> PrescriptionInfo | None: ...
