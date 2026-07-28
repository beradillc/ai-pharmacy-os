"""Bảng dữ liệu của ``seeds.demo_pharmacy`` phải tự nhất quán (Sprint 10, D4).

Đây là test cho một BẢNG DỮ LIỆU, không cho logic — và nó có mặt vì một lỗi
thật: lần chạy đầu tiên seed đổ ở thuốc thứ 23 với *"Đơn vị 'hộp' đã tồn tại
cho thuốc này"*, vì "Khẩu trang y tế 4 lớp" bán theo hộp mà script vẫn cố thêm
một đơn vị đóng gói tên "hộp". Catalog từ chối là đúng; danh sách dữ liệu mới là
chỗ sai.

Một lỗi kiểu này chỉ lộ ra sau ~40 giây chạy seed trên CSDL thật, và lộ ra khi
đã ghi được 22 thuốc — tức là để lại một tenant dở dang. Kiểm ngay trên bảng thì
mất 0,01 giây và không để lại gì.
"""

from __future__ import annotations

from seeds.demo_pharmacy import _CUSTOMERS, _DRUGS, _SUPPLIERS, _pack_units


def test_no_drug_in_the_table_would_get_a_duplicate_unit() -> None:
    """Chạy đúng quy tắc dựng đơn vị trên TỪNG dòng của bảng thật.

    Không phải "bảng có ít nhất một thuốc bán theo hộp" — câu đó xanh kể cả khi
    quy tắc sai. Câu này gọi thẳng ``_pack_units`` cho mọi thuốc và bắt lỗi trùng
    tên đơn vị, tức là đúng lỗi đã làm vỡ lần seed đầu.
    """
    for name, _rx, _form, _strength, unit, _price, _v in _DRUGS:
        unit_names = [unit] + [u.unit_name for u in _pack_units(unit)]
        assert len(unit_names) == len(set(unit_names)), f"{name}: đơn vị trùng {unit_names}"


def test_pack_unit_is_added_when_it_differs() -> None:
    """Và quy tắc không được "an toàn" bằng cách bỏ luôn đơn vị đóng gói."""
    assert [u.unit_name for u in _pack_units("viên")] == ["hộp"]
    assert _pack_units("hộp") == []


def test_drug_names_are_unique() -> None:
    names = [d[0] for d in _DRUGS]
    assert len(names) == len(set(names))


def test_barcodes_would_be_unique() -> None:
    """Mã vạch sinh theo chỉ số ⇒ chỉ trùng nếu bảng có hai dòng cùng vị trí."""
    assert len({f"893{5000000000 + i:010d}" for i in range(len(_DRUGS))}) == len(_DRUGS)


def test_only_otc_drugs_are_sold_in_history() -> None:
    """Thuốc kê đơn phải có mức bán = 0.

    Không phải chuyện thẩm mỹ: lịch sử demo không tạo đơn thuốc nào, nên một
    thuốc ETC có mức bán > 0 sẽ sinh ra những đơn bán thuốc kê đơn không có đơn —
    một buổi demo dạy sai luật, và là thứ khách hàng ngành dược nhận ra ngay.
    """
    from pharmacy_os.modules.catalog.domain import RxClass

    for name, rx, _form, _strength, _unit, _price, velocity in _DRUGS:
        if rx is not RxClass.OTC:
            assert velocity == 0, f"{name} là {rx} nhưng có mức bán {velocity}"


def test_prices_are_positive_and_cost_is_below_retail() -> None:
    from seeds.demo_pharmacy import _price_cost

    for name, _rx, _form, _strength, _unit, price, _v in _DRUGS:
        assert price > 0, name
        assert 0 < _price_cost(price) < price, name


def test_reference_lists_are_non_empty() -> None:
    assert len(_SUPPLIERS) >= 3
    assert len(_CUSTOMERS) >= 5
