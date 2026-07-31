"""Catalog persistence ports (implemented by infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.catalog.domain.entities import (
    ActiveIngredient,
    Drug,
    DrugPriceChange,
    DrugPriceRecord,
)


class DrugRepository(Protocol):
    async def add(self, drug: Drug) -> None: ...

    async def get(self, drug_id: UUID) -> Drug | None: ...

    async def by_barcode(self, barcode: str) -> Drug | None: ...

    async def list(
        self,
        *,
        search: str | None = None,
        ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Drug]:
        """Drugs of the tenant, by name.

        ``search`` matches a **substring of the name, case-insensitively**, or an
        **exact barcode** — the two ways a person at a counter identifies a box:
        they type part of what is printed on it, or they scan it.

        ``ids`` restricts to a known set. That is what lets a screen holding a page
        of stock/sale rows label them with one request instead of one per row; an
        empty sequence means "no ids asked for" and yields no rows, which is
        different from ``None`` ("no id filter").
        """
        ...

    async def names_by_ids(self, drug_ids: Sequence[UUID]) -> dict[UUID, str]:
        """Name-only projection for many ids in one query. Ids the tenant can't see are
        simply absent from the result — callers decide what to show for a missing name,
        because a drug deleted after a report was computed is not an error."""
        ...

    async def save_ingredients(self, drug: Drug) -> None:
        """Ghi lại danh sách hoạt chất của *drug* cho khớp với aggregate đang giữ.

        Hẹp có chủ ý — **không** phải một `update()` ghi mọi trường. Đây là đường sửa duy
        nhất mà catalog cần lúc này, và một cổng hẹp không thể vô tình ghi đè tên/giá/mã
        vạch khi bên gọi chỉ muốn sửa hoạt chất.

        Trả về im lặng nếu thuốc không thuộc tenant của người gọi — bên gọi đã đọc thuốc
        qua :meth:`get` (cũng tenant-scoped) nên tình huống này chỉ xảy ra khi thuốc bị xoá
        giữa hai lượt, và đó không phải lỗi cần dựng riêng một exception.
        """
        ...

    async def save_price(
        self,
        drug: Drug,
        change: DrugPriceChange,
        changed_by: UUID | None,
        changed_at: datetime,
    ) -> None:
        """Ghi giá mới lên thuốc **và** thêm một dòng vào lịch sử giá — cùng một lượt.

        Hai việc này cố ý nằm trong **một** phương thức, không tách thành `save_price` +
        `add_price_change`. Tách ra là mở đúng cái cửa mà `DrugPriceChange` sinh ra để
        đóng: một bên gọi ghi giá xong rồi quên ghi lịch sử, và không có gì đỏ lên.

        Hẹp như `save_ingredients`: chỉ chạm `sale_price`, không dùng `to_orm()` — bên gọi
        chỉ muốn đổi giá thì không có đường nào ghi đè tên/mã vạch/hoạt chất.

        Trả về im lặng nếu thuốc không thuộc tenant người gọi, cùng lý do `save_ingredients`.
        """
        ...

    async def price_history(self, drug_id: UUID, *, limit: int = 50) -> Sequence[DrugPriceRecord]:
        """Lịch sử giá của một thuốc, **mới nhất trước**. Rỗng khi mã chưa từng đổi giá.

        Thuốc không thuộc tenant người gọi trả về rỗng, không phải lỗi — cùng khuôn với
        các phép đọc khác của repo này.

        Kiểu trả về là ``Sequence`` chứ không ``list`` vì một lý do rất cụ thể: lớp này
        đã có một phương thức tên ``list``, nên trong thân lớp cái tên đó **không còn** trỏ
        tới kiểu dựng sẵn — mypy báo *"Function ... is not valid as a type"*. Đây là lỗi
        thật của phép chú kiểu, không phải nhiễu.
        """
        ...


class ActiveIngredientRepository(Protocol):
    """Read/seed access to the global ``active_ingredients`` reference table (not tenant-scoped)."""

    async def add(self, ingredient: ActiveIngredient) -> None: ...

    async def get(self, ingredient_id: UUID) -> ActiveIngredient | None: ...

    async def find_by_name(self, name: str) -> ActiveIngredient | None: ...

    async def list(self) -> list[ActiveIngredient]: ...
