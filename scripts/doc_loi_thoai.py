"""Đọc lời thoại thành tệp WAV bằng `espeak-ng` có sẵn trên máy — giọng NỮ tiếng Việt.

Chain yêu cầu 2026-08-02: *"Phương án đưa kịch bản cho, máy này đọc thư viện sẵn có giọng nữ."*

Máy này KHÔNG có lệnh `espeak-ng`, nhưng CÓ thư viện `libespeak-ng.so.1` và bộ dữ liệu giọng
(`espeak-ng-data`), trong đó có **ba giọng tiếng Việt**: Bắc · Trung · Nam. Gọi thẳng thư viện
qua `ctypes` và hứng mẫu âm ra WAV.

🔴 **PHẢI NGHE THỬ TRƯỚC KHI DÙNG CHO VIDEO GIAO KHÁCH.** `espeak-ng` là bộ tổng hợp
*formant* — nó phát âm đúng nhưng nghe rõ là giọng máy, không phải giọng người. Đủ tốt để
**dựng bản nháp và canh nhịp**; có đủ tốt để giao khách hay không là **quyết định của Chain
sau khi nghe**, không phải kết luận của tôi trước khi Chain nghe.

Dùng:
    python3 scripts/doc_loi_thoai.py docs/testing/09_LOI_THOAI_tong-quan.md /tmp/tieng
    python3 scripts/doc_loi_thoai.py --thu "Câu đọc thử" /tmp/tieng   # nghe thử một câu
"""

from __future__ import annotations

import ctypes
import re
import struct
import sys
from pathlib import Path

THU_VIEN = "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1"
AUDIO_OUTPUT_RETRIEVAL = 1
ESPEAK_CHARS_UTF8 = 1
# `+f3` là biến thể giọng NỮ của espeak-ng (f1..f5). `vi` = giọng Bắc — dễ nghe nhất với
# người dùng toàn quốc; đổi sang `vi-vn-x-south` nếu Chain muốn giọng Nam.
GIONG_MAC_DINH = "vi+f3"

_mau: list[int] = []


@ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
def _nhan_mau(wav, so_mau, _events):  # type: ignore[no-untyped-def]
    """espeak gọi lại nhiều lần, mỗi lần một khúc. `so_mau == 0` là hết câu."""
    if wav and so_mau > 0:
        _mau.extend(wav[i] for i in range(so_mau))
    return 0


def _ghi_wav(duong: Path, mau: list[int], tan_so: int) -> float:
    """Ghi WAV 16-bit mono. Tự viết header thay vì dùng thư viện ngoài — 44 byte, không đáng
    thêm phụ thuộc."""
    du_lieu = struct.pack(f"<{len(mau)}h", *mau)
    duong.write_bytes(
        b"RIFF"
        + struct.pack("<I", 36 + len(du_lieu))
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, tan_so, tan_so * 2, 2, 16)
        + b"data"
        + struct.pack("<I", len(du_lieu))
        + du_lieu
    )
    return len(mau) / tan_so


class BoDoc:
    def __init__(self, giong: str = GIONG_MAC_DINH) -> None:
        self.lib = ctypes.CDLL(THU_VIEN)
        self.tan_so = self.lib.espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0, None, 0)
        if self.tan_so <= 0:
            raise RuntimeError("espeak_Initialize thất bại")
        self.lib.espeak_SetSynthCallback(_nhan_mau)
        if self.lib.espeak_SetVoiceByName(giong.encode()) != 0:
            raise RuntimeError(f"Không đặt được giọng {giong!r}")
        # Chậm hơn mặc định: video hướng dẫn, người xem vừa nghe vừa nhìn tay bấm.
        self.lib.espeak_SetParameter(1, 145, 0)  # espeakRATE, từ/phút

    def doc(self, van_ban: str, ra: Path) -> float:
        _mau.clear()
        b = van_ban.encode("utf8")
        self.lib.espeak_Synth(b, len(b) + 1, 0, 0, 0, ESPEAK_CHARS_UTF8, None, None)
        self.lib.espeak_Synchronize()
        if not _mau:
            raise RuntimeError("espeak không trả về mẫu âm nào")
        return _ghi_wav(ra, list(_mau), self.tan_so)


def tach_loi(md: str) -> list[tuple[str, str]]:
    """Lấy (mã đoạn, lời) từ bảng lời thoại. Bỏ nhãn NỮ/NAM và chú thích trong ngoặc."""
    ra: list[tuple[str, str]] = []
    for dong in md.splitlines():
        if not dong.startswith("| ") or dong.startswith("| #"):
            continue
        o = [c.strip() for c in dong.strip("|").split("|")]
        if len(o) < 5 or not re.fullmatch(r"\d{2}", o[0]):
            continue
        loi = o[4]
        if "*(" in loi or not loi:
            continue
        loi = re.sub(r"\*\*(NỮ|NAM)\*\*|·\s*\*\*(NỮ|NAM)\*\*", " ", loi)
        loi = re.sub(r"[*`]", "", loi).strip()
        if loi:
            ra.append((o[0], loi))
    return ra


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--thu":
        ra = Path(sys.argv[3] if len(sys.argv) > 3 else "/tmp/tieng")
        ra.mkdir(parents=True, exist_ok=True)
        giay = BoDoc().doc(sys.argv[2], ra / "thu.wav")
        print(f"thu.wav · {giay:.1f}s · {ra / 'thu.wav'}")
        return 0

    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    nguon, ra = Path(sys.argv[1]), Path(sys.argv[2])
    ra.mkdir(parents=True, exist_ok=True)
    doan = tach_loi(nguon.read_text(encoding="utf8"))
    # Tự kiểm phép đo trước khi tin nó (kỷ luật #15): bảng đổi định dạng ⇒ 0 đoạn, và một
    # danh sách rỗng làm mọi khẳng định phía sau thành đúng vô nghĩa.
    if len(doan) < 5:
        print(f"🔴 Chỉ tách được {len(doan)} đoạn từ {nguon} — mẫu bảng đã đổi?")
        return 2

    bo = BoDoc()
    tong = 0.0
    nhip: dict[str, int] = {}
    for ma, loi in doan:
        giay = bo.doc(loi, ra / f"{ma}.wav")
        nhip[ma] = max(1, round(giay))
        tong += giay
        print(f"  {ma}.wav  {giay:5.1f}s  {loi[:58]}")
    (ra / "durations.json").write_text(
        "{\n" + ",\n".join(f'  "{k}": {v}' for k, v in sorted(nhip.items())) + "\n}\n",
        encoding="utf8",
    )
    print(f"\n{len(doan)} đoạn · tổng {tong / 60:.1f} phút · nhịp đã ghi {ra / 'durations.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
