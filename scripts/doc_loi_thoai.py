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
# Chain chốt 2026-08-02: **giọng MIỀN NAM, hai người** (nữ nói chính, nam hỏi lại).
# `vi-vn-x-south` là giọng Nam có sẵn trong espeak-ng-data; `+f3`/`+m3` là biến thể nữ/nam.
GIONG_NU = "vi-vn-x-south+f3"
GIONG_NAM = "vi-vn-x-south+m3"

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
    def __init__(self, giong: str = GIONG_NU) -> None:
        self.lib = ctypes.CDLL(THU_VIEN)
        self.tan_so = self.lib.espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0, None, 0)
        if self.tan_so <= 0:
            raise RuntimeError("espeak_Initialize thất bại")
        self.lib.espeak_SetSynthCallback(_nhan_mau)
        self.dat_giong(giong)
        # Chậm hơn mặc định: video hướng dẫn, người xem vừa nghe vừa nhìn tay bấm.
        self.lib.espeak_SetParameter(1, 145, 0)  # espeakRATE, từ/phút

    def dat_giong(self, giong: str) -> None:
        if self.lib.espeak_SetVoiceByName(giong.encode()) != 0:
            raise RuntimeError(f"Không đặt được giọng {giong!r}")

    def doc(self, luot: list[tuple[str, str]], ra: Path) -> float:
        """`luot` = [(giọng, lời), …] — MỘT đoạn có thể gồm nhiều lượt của hai người.

        🔴 Đọc từng lượt rồi NỐI mẫu âm lại, thay vì đọc cả đoạn bằng một giọng: kịch bản
        viết cho hai người đối đáp, và đọc phần NAM hỏi bằng giọng nữ thì mất hẳn nhịp hội
        thoại — thứ duy nhất làm video hướng dẫn nghe như một buổi chỉ việc chứ không như
        một bản tin.
        """
        gop: list[int] = []
        for giong, loi in luot:
            if not loi.strip():
                continue
            self.dat_giong(giong)
            _mau.clear()
            b = loi.encode("utf8")
            self.lib.espeak_Synth(b, len(b) + 1, 0, 0, 0, ESPEAK_CHARS_UTF8, None, None)
            self.lib.espeak_Synchronize()
            if not _mau:
                raise RuntimeError(f"espeak không trả mẫu âm cho {loi[:40]!r}")
            gop.extend(_mau)
            # Nghỉ 0,35 giây giữa hai lượt — không có nó thì câu hỏi dính câu trả lời.
            gop.extend([0] * int(self.tan_so * 0.35))
        if not gop:
            raise RuntimeError("không có lượt nào đọc được")
        return _ghi_wav(ra, gop, self.tan_so)


def tach_loi(md: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Lấy (mã đoạn, [(giọng, lời), …]) từ bảng lời thoại.

    Cột **Ai** cho biết ai mở lời. Trong ô **Lời**, nhãn `**NỮ**` / `**NAM**` xen giữa là
    chỗ ĐỔI người — ví dụ *"Vào rồi thì thấy gì trước? · **NỮ** Màn tổng quan: …"*. Bảng
    vốn đã ghi sẵn thông tin đó; trước đây bị vứt đi cùng lúc với việc gỡ dấu sao.
    """
    ra: list[tuple[str, list[tuple[str, str]]]] = []
    for dong in md.splitlines():
        if not dong.startswith("| ") or dong.startswith("| #"):
            continue
        o = [c.strip() for c in dong.strip("|").split("|")]
        if len(o) < 5 or not re.fullmatch(r"\d{2}", o[0]):
            continue
        loi = o[4]
        if "*(" in loi or not loi:
            continue
        giong = GIONG_NAM if "NAM" in o[3] else GIONG_NU
        luot: list[tuple[str, str]] = []
        for phan in re.split(r"·?\s*\*\*(NỮ|NAM)\*\*\s*", loi):
            if phan in ("NỮ", "NAM"):
                giong = GIONG_NAM if phan == "NAM" else GIONG_NU
                continue
            sach = re.sub(r"[*`]", "", phan).strip(" ·")
            if sach:
                luot.append((giong, sach))
        if luot:
            ra.append((o[0], luot))
    return ra


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--thu":
        ra = Path(sys.argv[3] if len(sys.argv) > 3 else "/tmp/tieng")
        ra.mkdir(parents=True, exist_ok=True)
        giay = BoDoc().doc([(GIONG_NU, sys.argv[2])], ra / "thu.wav")
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
    for ma, luot in doan:
        giay = bo.doc(luot, ra / f"{ma}.wav")
        nhip[ma] = max(1, round(giay))
        tong += giay
        ai = "+".join("nam" if "m3" in g else "nữ" for g, _ in luot)
        print(f"  {ma}.wav  {giay:5.1f}s  [{ai}]  {luot[0][1][:48]}")
    (ra / "durations.json").write_text(
        "{\n" + ",\n".join(f'  "{k}": {v}' for k, v in sorted(nhip.items())) + "\n}\n",
        encoding="utf8",
    )
    print(f"\n{len(doan)} đoạn · tổng {tong / 60:.1f} phút · nhịp đã ghi {ra / 'durations.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
