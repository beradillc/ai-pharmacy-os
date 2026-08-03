"""Luật domain của uỷ quyền quản trị (Chain chốt 2026-08-03) — thuần, không CSDL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pharmacy_os.modules.iam.domain import (
    KHONG_UY_QUYEN_DUOC,
    THOI_HAN,
    UyQuyenKhongHopLe,
    loc_quyen_uy_quyen_duoc,
    tao_uy_quyen,
)

_LY_DO = "Sửa lỗi hoá đơn PO-0007 tính sai tiền thối"
_QUYEN = frozenset({"crm.read", "crm.sensitive.read", "sales.read", "rx.image.read"})


def _tao(**kw: object):  # type: ignore[no-untyped-def]
    tham_so = {
        "tenant_id": uuid4(),
        "nguoi_nhan_id": uuid4(),
        "nguoi_cap_id": uuid4(),
        "ly_do": _LY_DO,
        "quyen_nguoi_cap": _QUYEN,
    }
    tham_so.update(kw)
    return tao_uy_quyen(**tham_so)  # type: ignore[arg-type]


def test_thoi_han_dung_24_gio_chain_chot() -> None:
    """Chain chốt 24 giờ mỗi lần xác nhận, **cố định** — không cho người cấp tự chọn.

    Một ô nhập số giờ là một ô người ta sẽ điền số lớn nhất được phép, và khi ấy "có hạn"
    chỉ còn là hình thức.
    """
    assert timedelta(hours=24) == THOI_HAN
    luc = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    uq = _tao(bay_gio=luc)
    assert uq.het_han_luc - uq.cap_luc == timedelta(hours=24)


def test_con_hieu_luc_theo_PHEP_SO_THOI_GIAN_khong_can_tac_vu_nen() -> None:
    """Máy mất điện ba ngày rồi bật lại thì uỷ quyền cũ vẫn hết hạn đúng lúc nó phải hết.

    Không có job nào cần "đuổi kịp" — thứ phải nhớ chạy là thứ sẽ quên.
    """
    luc = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    uq = _tao(bay_gio=luc)
    assert uq.con_hieu_luc(luc + timedelta(hours=23, minutes=59))
    assert not uq.con_hieu_luc(luc + timedelta(hours=24))
    assert not uq.con_hieu_luc(luc + timedelta(days=3))


def test_thu_hoi_thi_het_hieu_luc_ngay_ca_khi_chua_toi_han() -> None:
    luc = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    uq = _tao(bay_gio=luc)
    uq.thu_hoi_luc = luc + timedelta(hours=1)
    assert not uq.con_hieu_luc(luc + timedelta(hours=2))


def test_KHONG_TU_UY_QUYEN_CHO_CHINH_MINH() -> None:
    """Một người vừa cấp vừa nhận thì không còn ai là người chịu trách nhiệm — mà
    *"chủ chuỗi chịu trách nhiệm"* là đúng điều kiện Chain đặt ra."""
    ai_do = uuid4()
    with pytest.raises(UyQuyenKhongHopLe, match="chính mình"):
        _tao(nguoi_cap_id=ai_do, nguoi_nhan_id=ai_do)


def test_KHONG_UY_QUYEN_DUOC_QUYEN_KY_SO() -> None:
    """🔴 Mệnh đề đắt nhất của cả tính năng.

    ``compliance.ledger.sign`` là chữ ký sổ thuốc kiểm soát đặc biệt — lời khai của một dược
    sĩ có Chứng chỉ hành nghề trước cơ quan quản lý. Chủ chuỗi nhận được trách nhiệm dân
    sự/quản trị, nhưng **tư cách chuyên môn không chuyển sang người khác bằng một thao tác
    trong phần mềm**. Một chữ ký sai người trong sổ pháp lý là thứ **không sửa lại được** sau
    khi đã nộp.

    🔴 **Canh cả HAI đường vào, sau sửa 2026-08-03.** Mệnh đề thật sự đáng canh không phải
    *"gọi kiểu này thì ném lỗi"* mà là *"quyền ký **không bao giờ** nằm trong một uỷ quyền"* —
    và nó phải đúng qua **mọi** đường, kể cả đường mặc định mới thêm. Một test chỉ canh một
    đường sẽ xanh trong lúc đường kia rò.
    """
    assert "compliance.ledger.sign" in KHONG_UY_QUYEN_DUOC
    co_quyen_ky = _QUYEN | {"compliance.ledger.sign"}

    # Đường 1 — xin đích danh: ném lỗi ồn ào.
    with pytest.raises(UyQuyenKhongHopLe, match="Chứng chỉ hành nghề"):
        _tao(quyen_nguoi_cap=co_quyen_ky, quyen_yeu_cau=co_quyen_ky)

    # Đường 2 — mặc định "cấp tất cả những gì tôi cấp được": lọc ra, không bao giờ lọt.
    assert "compliance.ledger.sign" not in _tao(quyen_nguoi_cap=co_quyen_ky).quyen


def test_danh_sach_cam_KHONG_suy_ra_duoc_tu_rang_buoc_khac() -> None:
    """🔴 Vì sao danh sách cấm phải tồn tại **tường minh**.

    Bản nháp thiết kế viết *"chủ chuỗi không có quyền ký nên ràng buộc 'không cấp thứ mình
    không có' tự chặn"*. Kiểm bằng lệnh: vai ``chain_pharmacist`` **CÓ**
    ``compliance.ledger.sign`` — đúng như phải thế, vì chủ chuỗi là người ký sổ hợp pháp. Nên
    ràng buộc kia **không** chặn được đường chuyển quyền ký sang tài khoản kỹ thuật.

    Test này canh chính giả định ấy: nếu một ngày ai đó gỡ quyền ký khỏi ``chain_pharmacist``
    và nghĩ *"giờ bỏ danh sách cấm được rồi"*, họ vẫn phải làm đỏ test này trước.
    """
    from pharmacy_os.modules.iam.domain.system_roles import SYSTEM_ROLES_BY_CODE

    chu_chuoi = SYSTEM_ROLES_BY_CODE["chain_pharmacist"].permissions
    assert "compliance.ledger.sign" in chu_chuoi, (
        "Chủ chuỗi PHẢI có quyền ký sổ (họ là dược sĩ phụ trách chuyên môn). Chính vì thế "
        "KHONG_UY_QUYEN_DUOC phải là danh sách tường minh, không phải hệ quả gián tiếp."
    )


def test_phai_co_ly_do_that() -> None:
    with pytest.raises(UyQuyenKhongHopLe, match="ít nhất"):
        _tao(ly_do=".")
    with pytest.raises(UyQuyenKhongHopLe, match="ít nhất"):
        _tao(ly_do="   sửa   ")


def test_khong_co_quyen_nao_thi_tu_choi() -> None:
    with pytest.raises(UyQuyenKhongHopLe, match="Không có quyền nào"):
        _tao(quyen_nguoi_cap=frozenset())


def test_quyen_la_ANH_CHUP_khong_suy_lai_sau() -> None:
    """Vai trò đổi được sau khi uỷ quyền đã cấp.

    Suy lại lúc dùng ⇒ một lần nâng quyền cho chủ chuỗi sẽ **âm thầm nới rộng mọi uỷ quyền
    đang mở**, và người cấp không hề biết mình vừa cho thêm cái gì.
    """
    uq = _tao()
    assert uq.quyen == _QUYEN
    assert isinstance(uq.quyen, frozenset)


def test_loc_quyen_LOC_IM_LANG_khac_han_tao_uy_quyen_NEM_LOI() -> None:
    """Hai hành vi cho hai chỗ dùng: màn hình cần biết *cấp được cái gì*; lúc ghi thì một
    quyền cấm **được xin** phải là **lỗi ồn ào**, không phải thứ bị bỏ qua lặng lẽ.

    🔴 **Kỳ vọng đổi có chủ ý 2026-08-03 (bước 3/5), không phải nới lỏng để cho xanh.** Bản cũ
    khẳng định ``_tao(quyen_nguoi_cap=<có quyền cấm>)`` phải ném lỗi. Nhưng ``quyen_nguoi_cap``
    là *thứ người cấp đang có*, và **chủ chuỗi luôn có quyền ký** — họ là dược sĩ ký sổ hợp
    pháp. Nên kỳ vọng cũ đồng nghĩa: vai duy nhất được phép cấp thì **không bao giờ cấp nổi
    gì**. Đo bằng lệnh trên tập quyền thật của ``chain_pharmacist``: ném lỗi 100%.

    Nguyên tắc "lỗi ồn ào" không mất — nó chuyển sang đúng mục tiêu của nó: thứ **được xin**
    (``quyen_yeu_cau``). Xem :func:`test_xin_dich_danh_quyen_ky_thi_van_NEM_LOI`.
    """
    co_quyen_cam = _QUYEN | {"compliance.ledger.sign"}
    assert loc_quyen_uy_quyen_duoc(co_quyen_cam) == _QUYEN
    # Đường mặc định: người cấp có quyền ký ⇒ cấp phần còn lại, KHÔNG ném lỗi.
    assert _tao(quyen_nguoi_cap=co_quyen_cam).quyen == _QUYEN


def test_xin_dich_danh_quyen_ky_thi_van_NEM_LOI() -> None:
    """Nguyên tắc "quyền cấm lọt vào phải ồn ào" — nay soi đúng tập **được xin**."""
    with pytest.raises(UyQuyenKhongHopLe, match="Chứng chỉ hành nghề"):
        _tao(
            quyen_nguoi_cap=_QUYEN | {"compliance.ledger.sign"},
            quyen_yeu_cau=_QUYEN | {"compliance.ledger.sign"},
        )


def test_KHONG_CAP_QUA_THU_MINH_CO() -> None:
    """🔴 Luật 2 — trước bước 3/5 nó **không tồn tại trong mã**, chỉ có trong docstring.

    Bản bước 2/5 chỉ nhận **một** tập quyền và cấp đúng bằng nó, nên "không cấp quá thứ mình
    có" là một mệnh đề luôn đúng: tập được cấp *chính là* tập người cấp. Một phép so hai vế
    cùng nguồn là một **phép gán đội lốt** — nó xanh bất kể sản phẩm đúng hay sai (kỷ luật
    #23). Nay hai vế đến từ hai chỗ, nên nó đỏ được, và đây là chỗ nó đỏ.
    """
    with pytest.raises(UyQuyenKhongHopLe, match="không có"):
        _tao(
            quyen_nguoi_cap=frozenset({"crm.read"}),
            quyen_yeu_cau=frozenset({"crm.read", "crm.erase"}),
        )


def test_chu_chuoi_THAT_cap_duoc_uy_quyen_khong_nem_loi() -> None:
    """🔴 Mệnh đề mà 10 test cũ đều bỏ lọt: **tính năng có chạy được trên vai thật không.**

    Mọi test cũ dùng ``_QUYEN`` — một tập bịa 4 mã, không phải tập của bất kỳ vai nào có thật.
    Nên cả bộ xanh trọn vẹn trong lúc đường dùng thật chết 100%. Cùng họ kỷ luật #14: một tín
    hiệu xanh chứng minh một mệnh đề **khác** với mệnh đề người đọc tưởng nó chứng minh.
    """
    from pharmacy_os.modules.iam.domain.system_roles import SYSTEM_ROLES_BY_CODE

    chu_chuoi = SYSTEM_ROLES_BY_CODE["chain_pharmacist"].permissions
    uq = _tao(quyen_nguoi_cap=chu_chuoi)
    assert "compliance.ledger.sign" not in uq.quyen
    assert "crm.sensitive.read" in uq.quyen, "Uỷ quyền phải mở được dữ liệu bệnh nhân"
    assert uq.quyen == chu_chuoi - KHONG_UY_QUYEN_DUOC
