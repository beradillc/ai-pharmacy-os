"""``ENCRYPTION__KEYS_FILE`` — tách nơi giữ khoá khỏi máy chủ CSDL (Chain chốt 2026-08-03).

Mệnh đề trung tâm **không phải** *"đọc được tệp khoá"* — mà là *"từ chối khởi động khi tệp
khoá không thật sự kín"*. Một tệp khoá `chmod 644` nằm ngoài thư mục ứng dụng vẫn ai cũng đọc
được: nó **đổi chỗ chứ không đổi ai đọc được**, mà lại tạo cảm giác đã tách xong. Đúng dạng
"niềm tin giả" kiểm toán 26/07 đếm được 16 ca.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pharmacy_os.core.config import (
    AppSettings,
    DatabaseSettings,
    EncryptionSettings,
    SecuritySettings,
    Settings,
)
from pharmacy_os.core.security.crypto import encode_key, generate_key


def _viet_tep_khoa(thu_muc: Path, *, che_do: int = 0o600, van_tay: bool = True) -> Path:
    tep = thu_muc / "khoa.json"
    noi_dung: dict[str, object] = {"keys": {"1": encode_key(generate_key())}}
    if van_tay:
        noi_dung["blind_index_key"] = encode_key(generate_key())
    tep.write_text(json.dumps(noi_dung), encoding="utf-8")
    os.chmod(tep, che_do)
    return tep


def _dung(tep: Path | None, **kw: object) -> Settings:
    return Settings(
        app=AppSettings(env="dev"),
        db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
        security=SecuritySettings(allow_dev_auth=True),
        encryption=EncryptionSettings(keys_file=tep, **kw),  # type: ignore[arg-type]
    )


def test_nap_duoc_khoa_tu_tep_kin(tmp_path: Path) -> None:
    tep = _viet_tep_khoa(tmp_path)
    s = _dung(tep)
    assert set(s.encryption.keys) == {1}
    assert s.encryption.keys[1].get_secret_value()
    assert s.encryption.blind_index_key.get_secret_value() != "__set_me__"


@pytest.mark.parametrize("che_do", [0o644, 0o640, 0o604, 0o666])
def test_TU_CHOI_KHOI_DONG_khi_tep_khoa_ho(tmp_path: Path, che_do: int) -> None:
    """🔴 Mệnh đề đắt nhất.

    Dời khoá ra khỏi thư mục ứng dụng mà để `chmod 644` thì **không tách được ai khỏi dữ
    liệu** — người chạy sao lưu vẫn đọc được y như cũ. Từ chối khởi động chứ không cảnh báo:
    một cảnh báo lúc khởi động là thứ cuộn qua trong log và không ai đọc lại.
    """
    tep = _viet_tep_khoa(tmp_path, che_do=che_do)
    with pytest.raises(ValueError, match="đọc được|0600"):
        _dung(tep)


def test_TU_CHOI_khi_khai_ca_hai_nguon_khoa(tmp_path: Path) -> None:
    """Hai nguồn khoá cùng lúc ⇒ không ai biết chắc bản ghi mới mã hoá bằng khoá nào.

    Cố ý **không** chọn thứ tự ưu tiên: một quy tắc ưu tiên nghe thì gọn, nhưng nó biến một
    lỗi cấu hình thành một hành vi im lặng — và lần xoay khoá kế tiếp sẽ đi vào chỗ sai mà
    không ai thấy.
    """
    tep = _viet_tep_khoa(tmp_path)
    from pydantic import SecretStr

    with pytest.raises(ValueError, match="CẢ ENCRYPTION__KEYS_FILE"):
        _dung(tep, keys={1: SecretStr(encode_key(generate_key()))})


def test_TU_CHOI_khi_tep_khong_ton_tai(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="không tồn tại"):
        _dung(tmp_path / "khong-co-that.json")


def test_TU_CHOI_khi_tep_thieu_khoi_keys(tmp_path: Path) -> None:
    tep = tmp_path / "khoa.json"
    tep.write_text(json.dumps({"blind_index_key": encode_key(generate_key())}), encoding="utf-8")
    os.chmod(tep, 0o600)
    with pytest.raises(ValueError, match="thiếu khối"):
        _dung(tep)


def test_thong_diep_loi_KHONG_chua_noi_dung_tep(tmp_path: Path) -> None:
    """Thông điệp lỗi đi vào log và vào màn hình người vận hành — nó không được mang khoá."""
    tep = tmp_path / "khoa.json"
    bi_mat = "KHOA-BI-MAT-KHONG-DUOC-LOT-RA"
    tep.write_text(bi_mat + " {hỏng json", encoding="utf-8")
    os.chmod(tep, 0o600)
    with pytest.raises(ValueError) as loi:
        _dung(tep)
    assert bi_mat not in str(loi.value)


def test_khong_khai_gi_thi_giu_nguyen_hanh_vi_cu(tmp_path: Path) -> None:
    """Tương thích ngược (kỷ luật #17): không đặt `keys_file` ⇒ mọi thứ như trước."""
    s = _dung(None)
    assert s.encryption.keys == {}
