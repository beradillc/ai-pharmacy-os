"""Converter helpers for QĐ 540 data-format rules (docs/13_COMPLIANCE_SPEC.md mục A).

CSDL nội bộ dùng kiểu ``date``/``datetime`` ISO chuẩn (domain purity) — các hàm ở đây chỉ
chạy tại thời điểm xuất payload lên cổng CSDL Dược Quốc gia, không thay đổi cách lưu nội bộ.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

_SEPARATORS_RE = re.compile(r"[\s\-]+")
_DD_MAP = str.maketrans({"đ": "d", "Đ": "D"})


def to_qld_date(d: date) -> int:
    """``date`` → số 8 chữ số ``YYYYMMDD`` (VD: 15/12/2018 → 20181215)."""
    return int(d.strftime("%Y%m%d"))


def to_qld_datetime(dt: datetime) -> int:
    """``datetime`` → số 12 chữ số ``YYYYMMDDHHmm`` (VD: 10:30 08/08/2018 → 201808081030)."""
    return int(dt.strftime("%Y%m%d%H%M"))


def to_qld_code(s: str) -> str:
    """Mã hóa mã thuốc: bỏ dấu tiếng Việt, khoảng trắng, dấu gạch ngang — giữ nguyên chữ hoa/thường.

    VD gốc (QĐ540 Bảng 1 mục 1): ``VN-12345-18-lọ 200 viên`` → ``VN1234518lo200vien``.
    """
    without_dd = s.translate(_DD_MAP)
    normalized = unicodedata.normalize("NFD", without_dd)
    without_diacritics = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return _SEPARATORS_RE.sub("", without_diacritics)
