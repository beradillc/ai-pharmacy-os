"""Catalog domain exceptions (pure — no framework)."""

from __future__ import annotations


class CatalogError(Exception):
    """Base for catalog domain rule violations."""


class DuplicateUnitError(CatalogError):
    """Raised when adding a unit name that already exists on a drug."""


class InvalidIngredientError(CatalogError):
    """Raised when an :class:`ActiveIngredient`/:class:`DrugIngredient` is malformed."""


class DuplicateIngredientError(CatalogError):
    """Raised when adding an ingredient already present on a drug."""


class InvalidPriceError(CatalogError):
    """Giá bán mới không hợp lệ — âm, hoặc lẻ hơn đơn vị tiền lưu được.

    ``drugs.sale_price`` là ``Numeric(18, 2)``. Nhận một giá lẻ tới phần nghìn rồi để
    CSDL tự làm tròn là cách tạo ra một giá niêm yết **không ai gõ vào** — và Điều 6.5.i
    Luật Dược nói về chênh lệch giữa giá bán và giá niêm yết, nên chênh lệch do làm tròn
    im lặng cũng là chênh lệch. Từ chối, để người đặt giá tự chọn con số.
    """


class PriceUnchangedError(CatalogError):
    """Giá mới trùng đúng giá đang có.

    Không phải lỗi vô hại: ``drug_price_history`` là bảng chỉ-ghi-thêm dùng để trả lời
    *"giá mã X ngày ấy là bao nhiêu"*. Một dòng "đổi từ 12.000 sang 12.000" làm câu trả
    lời đó dài ra mà không thêm sự thật nào.
    """
