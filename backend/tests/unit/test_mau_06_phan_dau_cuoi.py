"""Phần đầu/cuối Mẫu số 06 (NĐ163 Phụ lục II) — đóng nợ **N-2**.

Nguồn duy nhất được phép đối chiếu: `docs/legal/Nghị-định-163-2025-NĐ-CP.docx`. Quy tắc R-10
của vault cấm kết luận về nghĩa vụ pháp lý từ trí nhớ hay từ một văn bản cấp thấp hơn — nên
mọi chuỗi khẳng định dưới đây được chép từ chính bản .docx đã giải nén, không viết lại.
"""

from __future__ import annotations

from datetime import date

from pharmacy_os.modules.compliance.application import (
    MAU_06_TIEU_DE,
    mau_06_phan_cuoi,
    mau_06_phan_dau,
)


def _phang(dong: list[list[str]]) -> str:
    return "\n".join(" ".join(o) for o in dong)


def test_phan_dau_co_du_nam_thanh_phan_cua_ban_goc() -> None:
    txt = _phang(
        mau_06_phan_dau(
            ten_co_so="Quầy thuốc 650",
            dia_chi="xã Thạnh Trị, Vĩnh Long",
            tu_ngay=date(2026, 1, 1),
            den_ngay=date(2026, 6, 30),
        )
    )
    assert "TÊN CƠ SỞ Quầy thuốc 650" in txt
    assert "xã Thạnh Trị, Vĩnh Long" in txt
    assert "Số ………." in txt
    assert MAU_06_TIEU_DE in txt
    assert "Kính gửi" in txt


def test_ky_bao_cao_dinh_dang_ngay_VIET_NAM_khong_phai_ISO() -> None:
    """`01/01/2026`, không phải `2026-01-01`.

    Đây là văn bản hành chính nộp UBND cấp tỉnh, không phải payload máy đọc. ISO trên một tờ
    trình cơ quan quản lý là thứ người nhận phải dịch lại trong đầu — và với `03/04` thì họ
    không có cách nào biết đó là ngày 3 tháng 4 hay ngày 4 tháng 3.
    """
    txt = _phang(
        mau_06_phan_dau(
            ten_co_so="X", dia_chi="Y", tu_ngay=date(2026, 1, 1), den_ngay=date(2026, 6, 30)
        )
    )
    assert "(Kỳ báo cáo từ ngày 01/01/2026 đến ngày 30/06/2026)" in txt
    assert "2026-01-01" not in txt


def test_chua_khai_thi_in_dau_cham_lung_chu_khong_in_rong() -> None:
    """Cơ sở chưa khai ⇒ vẫn xuất được, và ô trống mang **ký hiệu điền tay của bản gốc**.

    Một ô rỗng trên tờ trình đọc như *"cơ sở này không có tên"*; dấu chấm lửng đọc như
    *"chỗ này phải điền"* — đúng ý nghĩa nó mang trong biểu mẫu giấy.
    """
    txt = _phang(
        mau_06_phan_dau(
            ten_co_so="", dia_chi="", tu_ngay=date(2026, 1, 1), den_ngay=date(2026, 6, 30)
        )
    )
    assert "TÊN CƠ SỞ ……………………" in txt
    assert "Địa chỉ ……………………" in txt


def test_khong_tu_dien_so_van_ban_va_khong_tu_doan_tinh() -> None:
    """🔴 Mệnh đề đắt nhất của N-2 — hai ô PHẢI để trống.

    - ``Số:`` là số hiệu văn bản đi theo sổ văn thư của cơ sở. Hệ thống không giữ sổ văn thư,
      nên sinh đại một con số là **tạo ra một số hiệu văn bản không có thật**.
    - ``Kính gửi:`` là UBND cấp tỉnh nơi đặt trụ sở chính (NĐ163 Điều 35.2). Tách tỉnh từ
      chuỗi địa chỉ tự do là **đoán**, và đoán sai nghĩa là gửi báo cáo cho sai cơ quan.

    §7dm ghi lại một phiên đã suýt bịa đúng loại số liệu cơ sở này rồi ghi vào CSDL sắp thành
    sổ thật. Test này giữ cho lần sau không ai "tiện tay điền cho đủ".
    """
    dong = mau_06_phan_dau(
        ten_co_so="Quầy thuốc 650",
        dia_chi="xã Thạnh Trị, Vĩnh Long",
        tu_ngay=date(2026, 1, 1),
        den_ngay=date(2026, 6, 30),
    )
    so_van_ban = next(o for o in dong if o and o[0] == "Số")
    assert so_van_ban[1] == "……….", "số hiệu văn bản phải để người dùng điền"

    kinh_gui = next(o for o in dong if o and o[0] == "Kính gửi")
    assert kinh_gui[1].endswith("……………………"), "tên tỉnh phải để người dùng điền"
    assert "Vĩnh Long" not in kinh_gui[1], "KHÔNG được suy tỉnh từ chuỗi địa chỉ tự do"


def test_phan_cuoi_co_noi_nhan_cho_ky_va_ba_ghi_chu() -> None:
    txt = _phang(mau_06_phan_cuoi())
    assert "Nơi nhận:" in txt
    assert "- Như trên;" in txt
    assert "- Lưu tại cơ sở." in txt
    assert "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/NGƯỜI ĐƯỢC ỦY QUYỀN" in txt
    # Ghi chú về cột (11): cột đó LUÔN trống trong tệp (ledger không phân biệt lý do xuất),
    # nên người điền phải đọc được nó đòi gì — không in thì ô trống trông như số 0.
    assert "Số lượng hao hụt bao gồm cả hỏng, vỡ, hết hạn dùng" in txt


def test_khong_tu_dien_ngay_ky() -> None:
    """Ngày ký là ngày người đại diện thật sự ký, không phải ngày bấm nút xuất tệp."""
    txt = _phang(mau_06_phan_cuoi())
    assert "……, ngày …… tháng …… năm ……" in txt
    assert str(date.today().year) not in txt


def test_tieu_de_giu_nguyen_van_ban_goc() -> None:
    """Tiêu đề là chuỗi đi vào văn bản nộp cơ quan quản lý — cấm rút gọn cho "gọn hơn"."""
    assert MAU_06_TIEU_DE.startswith("BÁO CÁO ĐỊNH KỲ XUẤT, NHẬP, TỒN KHO, SỬ DỤNG")
    assert MAU_06_TIEU_DE.endswith("CỦA CƠ SỞ BÁN BUÔN, BÁN LẺ, CƠ SỞ TỔ CHỨC CHUỖI NHÀ THUỐC")
    # Bản gốc liệt kê đủ mọi nhóm thuốc phải kiểm soát đặc biệt; thiếu nhóm nào là đổi phạm vi
    # của một văn bản pháp lý.
    for nhom in (
        "THUỐC GÂY NGHIỆN",
        "THUỐC HƯỚNG THẦN",
        "THUỐC TIỀN CHẤT",
        "THUỐC PHÓNG XẠ",
        "THUỐC ĐỘC",
    ):
        assert nhom in MAU_06_TIEU_DE, nhom
