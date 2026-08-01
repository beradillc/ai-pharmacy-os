"""Cổng: **mọi** dòng audit phải mang siêu dữ liệu thiết bị (UAT M-06, 2026-08-01).

Vì sao phải là một cổng đọc mã nguồn chứ không phải một test hành vi: thêm
``user_agent`` là sửa **21 chỗ gọi** rải khắp 12 module, và một chỗ bị quên **không làm
đỏ gì cả** — dòng audit vẫn ghi được, chỉ thiếu lặng lẽ đúng thứ vừa thêm. Đó là hình
dạng kỷ luật #22: chuỗi nối hai thế giới (chỗ dựng ``RequestContext`` ↔ chỗ ghi audit)
mà không trình biên dịch nào nối được hai đầu.

Test hành vi bắt được **một** đường; cổng này bắt **mọi** đường, kể cả đường viết ngày
mai. Nó cũng đã bắt được một ca thật ngay lượt chạy đầu: ``PASSWORD_CHANGED`` truyền
cứng ``client_ip=None`` — hành vi mà "từ máy nào" là câu hỏi đầu tiên khi tài khoản bị
chiếm — và không có gì báo động suốt từ Sprint 8.

**Tự kiểm chính phép quét** (kỷ luật #15): mỗi phép đếm đều khẳng định số lượng tìm được
lớn hơn một ngưỡng. Một danh sách rỗng vì đổi cú pháp hoặc sai đường dẫn làm mọi khẳng
định phía sau thành đúng vô nghĩa.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src" / "pharmacy_os"
_MODULES = _SRC / "modules"

#: Ngưỡng tự kiểm. Cố tình đặt sát dưới con số thật lúc viết (21 chỗ ghi audit qua
#: ``with_context``, 12 chỗ gọi ``_record``) chứ không đặt ``> 0``: ``> 0`` vẫn xanh khi
#: phép quét chỉ còn tìm thấy một chỗ vì cú pháp đã đổi.
_MIN_WITH_CONTEXT = 18
_MIN_RECORD_CALLS = 10


def _python_sources() -> list[Path]:
    files = sorted(_MODULES.rglob("*.py")) + sorted((_SRC / "core").rglob("*.py"))
    assert len(files) > 50, f"phép quét hỏng: chỉ thấy {len(files)} tệp .py"
    return files


def _balanced_call(text: str, start: int) -> str:
    """Chuỗi lời gọi từ ``start`` (đang ở ngay sau dấu mở ngoặc) tới ngoặc đóng khớp."""
    depth, i = 1, start
    while depth and i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    return text[start : i - 1]


def _with_context_calls() -> list[tuple[Path, str]]:
    calls: list[tuple[Path, str]] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\.with_context\(", text):
            calls.append((path, _balanced_call(text, m.end())))
    return calls


def test_moi_dong_audit_deu_mang_thiet_bi() -> None:
    """Mỗi ``with_context`` trong tầng ứng dụng phải mang ``user_agent``.

    Chấp nhận hai cách viết: ``**ctx.audit_meta`` (đường chính, một chỗ sửa duy nhất khi
    thêm trường mới) hoặc ``user_agent=`` tường minh (đường đăng nhập, nơi chưa có
    ``RequestContext`` vì người dùng chưa được xác thực).
    """
    calls = _with_context_calls()
    # Bỏ chính định nghĩa của ``with_context`` trong core/audit/entry.py.
    calls = [(p, c) for p, c in calls if p.name != "entry.py"]
    assert len(calls) >= _MIN_WITH_CONTEXT, (
        f"phép quét hỏng: chỉ thấy {len(calls)} lời gọi with_context, "
        f"chờ ít nhất {_MIN_WITH_CONTEXT}"
    )

    thieu = [
        f"{p.relative_to(_SRC)}: {' '.join(c.split())[:90]}"
        for p, c in calls
        if "**ctx.audit_meta" not in c and "user_agent=" not in c
    ]
    assert not thieu, "dòng audit không mang thiết bị:\n  " + "\n  ".join(thieu)


def test_moi_loi_goi_record_cua_auth_deu_mang_thiet_bi() -> None:
    """``AuthService._record`` là đường audit **không** đi qua ``ctx.audit_meta``.

    Nó nhận ``client_ip`` rời vì luồng đăng nhập chưa có ``RequestContext`` (người dùng
    chưa xác thực xong). Chính vì rời nên nó là chỗ dễ quên nhất — và đúng là đã quên 2/12
    lời gọi ở lượt chạy đầu tiên.
    """
    path = _SRC / "modules" / "iam" / "application" / "auth_service.py"
    text = path.read_text(encoding="utf-8")
    calls = [_balanced_call(text, m.end()) for m in re.finditer(r"self\._record\(", text)]
    assert len(calls) >= _MIN_RECORD_CALLS, (
        f"phép quét hỏng: chỉ thấy {len(calls)} lời gọi _record, chờ ít nhất {_MIN_RECORD_CALLS}"
    )

    thieu = [" ".join(c.split())[:90] for c in calls if "user_agent=" not in c]
    assert not thieu, "lời gọi _record không mang thiết bị:\n  " + "\n  ".join(thieu)


def test_khong_con_client_ip_roi_le_trong_duong_audit() -> None:
    """``client_ip=ctx.client_ip`` chỉ còn được phép ngoài đường audit.

    Hai chỗ hợp lệ còn lại là ``CustomerConsent`` (crm) — IP nằm trong **bản ghi đồng ý**
    theo NĐ 356/2025, không phải trong sổ audit. Cổng này canh việc một dòng audit mới
    quay lại lối viết cũ: viết thế vẫn chạy, vẫn ghi được, chỉ **không có thiết bị**.
    """
    con_lai = [
        (p, i + 1, line.strip())
        for p in _python_sources()
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines())
        if "client_ip=ctx.client_ip" in line
    ]
    ngoai_le = [t for t in con_lai if t[0].relative_to(_SRC).parts[1] == "crm"]
    assert len(ngoai_le) == 2, f"ngoại lệ CustomerConsent (crm) đổi rồi, xem lại: {ngoai_le}"

    vi_pham = [t for t in con_lai if t not in ngoai_le]
    assert not vi_pham, (
        "đường audit còn dùng client_ip rời lẻ (mất thiết bị), dùng **ctx.audit_meta:\n  "
        + "\n  ".join(f"{p.relative_to(_SRC)}:{n} {s}" for p, n, s in vi_pham)
    )


@pytest.mark.parametrize("truong", ["client_ip", "user_agent"])
def test_audit_meta_mang_du_hai_truong(truong: str) -> None:
    """``RequestContext.audit_meta`` là chỗ duy nhất phải sửa khi thêm trường mới.

    Khẳng định nội dung của nó ở đây để việc bỏ bớt một trường trở thành một test đỏ,
    chứ không phải 21 dòng audit lặng lẽ nghèo đi.
    """
    from uuid import uuid4

    from pharmacy_os.core.context import RequestContext

    ctx = RequestContext(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        client_ip="10.0.0.9",
        user_agent="Mozilla/5.0 (iPhone)",
    )
    assert truong in ctx.audit_meta
    assert ctx.audit_meta[truong]
