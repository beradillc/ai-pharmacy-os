"""Compliance ports: persistence (implemented by infrastructure) and cross-module
read access (implemented at the composition root, same pattern as
``sales.DrugInfoProvider`` / ``CatalogDrugInfoProvider`` — ``compliance`` never imports
catalog/inventory/sales/prescription directly).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.compliance.domain.entities import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    DrugReturnRecord,
    LedgerBookSignature,
    LedgerBookType,
    NationalSyncLog,
    SyncPayloadType,
    TenantComplianceConfig,
)


@dataclass(frozen=True, slots=True)
class LedgerPeriodAggregate:
    """Tổng theo một thuốc trong một kỳ báo cáo (docs/13 mục C.7 — NĐ163 Mẫu số 06).

    Khác ``ControlledLedgerEntry`` (từng giao dịch) — đây là 3 số đã cộng dồn sẵn bằng SQL
    (không load từng dòng lịch sử vào Python). ``opening_balance`` là tồn lũy kế tính từ MỌI
    giao dịch trước ``from_date`` của kỳ, không phải chỉ trong kỳ.
    """

    drug_id: UUID
    category: ControlledSubstanceCategory
    opening_balance: Decimal
    received_in_period: Decimal
    issued_in_period: Decimal

    @property
    def closing_balance(self) -> Decimal:
        return self.opening_balance + self.received_in_period - self.issued_in_period


class ControlledLedgerRepository(Protocol):
    """Persistence port for :class:`ControlledLedgerEntry` (immutable — add/get/list only)."""

    async def add(self, entry: ControlledLedgerEntry) -> None: ...

    async def get(self, entry_id: UUID) -> ControlledLedgerEntry | None: ...

    async def list_for_book(
        self,
        book_type: LedgerBookType,
        *,
        from_date: date,
        to_date: date,
        drug_id: UUID | None = None,
    ) -> Sequence[ControlledLedgerEntry]:
        """Các dòng thuộc một mẫu sổ trong kỳ, sắp xếp theo (thuốc, thời điểm giao dịch).

        Sắp theo thuốc trước vì mẫu sổ pháp lý yêu cầu **mỗi thuốc một sổ riêng**
        (ghi chú Phụ lục VIII), và cột "Còn lại" là tồn lũy kế trong phạm vi từng thuốc.
        """
        ...

    async def aggregate_for_period(
        self,
        categories: Sequence[ControlledSubstanceCategory],
        *,
        from_date: date,
        to_date: date,
    ) -> Sequence[LedgerPeriodAggregate]:
        """Tổng theo từng thuốc cho báo cáo định kỳ (docs/13 mục C.7 — NĐ163 Mẫu số 06).

        Nhận thẳng danh sách ``categories`` thay vì ``LedgerBookType`` — phạm vi Điều 35.2.a
        NĐ163 (GN/HT/TC + 3 nhóm phối hợp) **không trùng** với cách chia PL_VIII/PL_XVI của TT18
        (PL_XVI còn gồm cả thuốc độc/danh mục cấm, không thuộc phạm vi báo cáo này). Tách hẳn khỏi
        khái niệm ``book_type`` để khỏi vô tình gộp nhầm 2 nhóm không thuộc Điều 35.2.a.

        Một dòng mỗi thuốc có giao dịch trong kỳ **hoặc** có tồn đầu kỳ khác 0 — thuốc hết hàng
        từ trước, không nhập/xuất gì trong kỳ vẫn phải xuất hiện trên báo cáo (tồn đầu kỳ = tồn
        cuối kỳ, không bị bỏ sót).
        """
        ...


class LedgerBookSignatureRepository(Protocol):
    """Persistence port for :class:`LedgerBookSignature` (docs/13 mục C.5, hướng A).

    Immutable — add/get only, cùng nguyên tắc với :class:`ControlledLedgerRepository`.
    """

    async def add(self, signature: LedgerBookSignature) -> None: ...

    async def get_for_day(
        self, book_type: LedgerBookType, book_date: date
    ) -> LedgerBookSignature | None:
        """Chữ ký của đúng ngày này (tenant hiện tại) — ``None`` nếu ngày đó chưa ký."""
        ...

    async def latest_before(
        self, book_type: LedgerBookType, book_date: date
    ) -> LedgerBookSignature | None:
        """Chữ ký gần nhất **trước** ``book_date`` (không nhất thiết ngày liền kề lịch — nhà
        thuốc có thể không ký một số ngày không phát sinh giao dịch) — dùng làm ``prev_hash``.
        """
        ...


class SigningReauthProvider(Protocol):
    """Read-port xác minh mật khẩu người dùng hiện tại trước khi ký sổ (docs/13 mục C.5).

    ``compliance`` không sở hữu ``User``/mật khẩu (thuộc ``iam``) — implement tại composition
    root bọc ``iam.AuthService``, cùng pattern ``DrugMasterProvider``/``CatalogDrugMasterProvider``
    (xem docs/features/tt18-kiem-soat-dac-biet/02_DECISIONS_KY_SO.md Bước 3).
    """

    async def verify(self, ctx: RequestContext, plain_password: str) -> bool: ...


class DrugReturnRecordRepository(Protocol):
    """Persistence port for :class:`DrugReturnRecord` (docs/13 mục C.6).

    Immutable — add/get only.
    """

    async def add(self, record: DrugReturnRecord) -> None: ...

    async def get(self, record_id: UUID) -> DrugReturnRecord | None: ...


class TenantComplianceConfigRepository(Protocol):
    """Persistence port for :class:`TenantComplianceConfig` (one row per tenant)."""

    async def upsert(self, config: TenantComplianceConfig) -> None: ...

    async def get(self, tenant_id: UUID) -> TenantComplianceConfig | None: ...


class NationalSyncLogRepository(Protocol):
    """Persistence port for :class:`NationalSyncLog` (tenant-scoped)."""

    async def add(self, log: NationalSyncLog) -> None: ...

    async def update(self, log: NationalSyncLog) -> None: ...

    async def get(self, log_id: UUID) -> NationalSyncLog | None: ...

    async def by_client_uuid(self, client_uuid: str) -> NationalSyncLog | None: ...


@dataclass(frozen=True, slots=True)
class SyncRequest:
    """A single record/batch to push to the national drug database (docs/13 mục D.2)."""

    payload_type: SyncPayloadType
    client_uuid: str
    payload: str  # serialized payload sent to the gateway; only its hash is persisted


@dataclass(frozen=True, slots=True)
class SyncAck:
    """The gateway's response to a push. ``ok`` distinguishes ACK from FAILED."""

    ok: bool
    response_code: str | None
    response_body: str | None


class NationalDrugDbGateway(Protocol):
    """Outbound port to the CSDL Dược Quốc gia (docs/13 mục D.3).

    ⚠️ The real endpoint spec does not exist yet (due ~6/2026 per QĐ1867 mục 1.2). Only a
    ``MockNationalDrugDbGateway`` implements this today, wired at the composition root — the
    real adapter is deliberately not built until the DAV API spec is available.
    """

    async def push(self, request: SyncRequest) -> SyncAck: ...


@dataclass(frozen=True, slots=True)
class DrugMasterFacts:
    """Catalog facts compliance needs to build a ``NationalDrugRecord`` (docs/13 mục B) and the
    Mẫu số 06 periodic report (docs/13 mục C.7 — NĐ163 Điều 35.2).

    ``name``/``form``/``strength`` were added 2026-07-25 alongside the first real wiring of this
    port (previously defined but never implemented at the composition root). Deliberately does
    NOT include manufacturer country or a formatted packaging string — ``catalog.Drug`` has no
    such fields yet; the periodic report leaves those columns blank rather than inventing data.
    """

    registration_no: str | None
    base_unit: str
    name: str
    form: str | None
    strength: str | None
    active_ingredients: str
    """Tên các hoạt chất, đã nối sẵn bằng " + " để hiển thị trực tiếp — báo cáo Mẫu số 06 không
    cần biết ``ingredient_id``, chỉ cần tên hiển thị (khác cách dùng ở `wire_safety_checks`, nơi
    cần giữ ``ingredient_id`` riêng để so khớp dị ứng)."""


class DrugMasterProvider(Protocol):
    """Read-port for catalog facts (docs/13 mục B mapping `so_dang_ky`/`don_vi_dong_goi_nn`).

    Returns ``None`` when the drug is unknown to catalog.
    """

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugMasterFacts | None: ...
