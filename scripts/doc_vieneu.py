"""Đọc lời thoại bằng **VieNeu-TTS v3 Turbo** — 48 kHz, bộ phiên âm riêng cho tiếng Việt.

Chain duyệt 2026-08-02: *"Duyệt cho thử giọng tốt hơn, Video 01."*

Chạy bằng venv RIÊNG (`venv-vieneu`) vì phụ thuộc của nó không đi chung được với Piper:

    ~/.local/share/beras-tts/venv-vieneu/bin/python scripts/doc_vieneu.py \\
        docs/testing/09_LOI_THOAI_v01.md /tmp/tieng-vieneu "Đoan Trang"

🔴 **KHÔNG áp sổ phát âm ở đây.** `12_SO_PHAT_AM.md` chữa lỗi của **espeak-ng** bằng cách
viết lại chữ ("doanh" → "doăn"). VieNeu dùng bộ phiên âm khác hẳn (sea-g2p, làm riêng cho
tiếng Việt), nên nó đọc "doanh" đúng — mà nếu đưa "doăn" vào thì nó sẽ đọc thành "doăn"
thật. Bản vá cho bộ này là thuốc độc cho bộ kia.

🔴 **Nạp mô hình một lần cho cả tệp.** Nạp mất ~59 giây; gọi 16 lần cho 16 đoạn là ~16 phút
chỉ để nạp đi nạp lại cùng một thứ.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 🔴 Danh sách giọng CÓ GHI VÙNG MIỀN — "Tên — Giới · Vùng · Phong cách". Chỉ hai giọng nữ
#    miền Nam: **Thục Đoan** (kể chuyện) và **Thùy Dung** (tin tức). Chọn Thục Đoan vì video
#    hướng dẫn là chỉ việc tại quầy, không phải đọc bản tin.
#    (Bản so sánh gửi Chain trước đó có 2/3 giọng là miền BẮC — chọn mù vì chưa biết có nhãn.)
# Giọng chuẩn đọc từ `scripts/giong-he-thong.json` — MỘT chỗ duy nhất biết, đúng bài học
# N-4 (trước đây địa chỉ và tài khoản khai rải rác 33 chỗ, mỗi chỗ một kiểu).
_CAU_HINH = Path(__file__).parent / "giong-he-thong.json"
GIONG_MAC_DINH = json.loads(_CAU_HINH.read_text(encoding="utf8"))["giong"]


def tach_loi(md: str) -> list[tuple[str, str]]:
    """(mã đoạn, lời) — gộp mọi lượt của một đoạn thành một chuỗi, vì nay chỉ một giọng dẫn."""
    ra: list[tuple[str, str]] = []
    for dong in md.splitlines():
        if not dong.startswith("| ") or dong.startswith("| #"):
            continue
        o = [c.strip() for c in dong.strip("|").split("|")]
        if len(o) < 5 or not re.fullmatch(r"\d{2}[a-z]?", o[0]) or "*(" in o[4]:
            continue
        loi = re.sub(r"\*\*(NỮ|NAM)\*\*", " ", o[4])
        loi = re.sub(r"[*`]", "", loi).replace(" · ", " ").strip()
        if loi:
            ra.append((o[0], loi))
    return ra


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    nguon, ra_thu = Path(sys.argv[1]), Path(sys.argv[2])
    giong = sys.argv[3] if len(sys.argv) > 3 else GIONG_MAC_DINH
    ra_thu.mkdir(parents=True, exist_ok=True)

    doan = tach_loi(nguon.read_text(encoding="utf8"))
    # Tự kiểm phép đo trước khi tin nó (kỷ luật #15): mẫu bảng đổi ⇒ 0 đoạn, và một danh
    # sách rỗng làm mọi khẳng định phía sau thành đúng vô nghĩa.
    if len(doan) < 5:
        print(f"🔴 Chỉ tách được {len(doan)} đoạn từ {nguon} — mẫu bảng đã đổi?")
        return 2

    from vieneu import Vieneu  # nặng, chỉ nạp khi thật sự chạy

    tts = Vieneu()
    # Nhãn giọng có dạng "Thục Đoan — Nữ · Nam · Phong cách kể chuyện"; khớp theo TÊN
    # đứng trước dấu gạch, đừng bắt người gọi phải chép cả nhãn.
    nhan = [n for n, _ in tts.list_preset_voices()] if hasattr(tts, "list_preset_voices") else []
    khop = [n for n in nhan if n.split("—")[0].strip() == giong]
    if nhan and not khop:
        print(f"🔴 Không có giọng {giong!r}. Đang có:")
        for n in sorted(nhan):
            print("   ", n)
        return 2
    if khop:
        print(f"   → {khop[0]}")
    print(f"bộ đọc: VieNeu-TTS v3 Turbo · giọng {giong} · 48 kHz")

    import wave

    nhip: dict[str, int] = {}
    tong = 0.0
    for ma, loi in doan:
        tep = ra_thu / f"{ma}.wav"
        tts.save(tts.infer(loi, voice=giong), str(tep))
        with wave.open(str(tep)) as w:
            giay = w.getnframes() / w.getframerate()
        nhip[ma] = max(1, round(giay))
        tong += giay
        print(f"  {ma}.wav {giay:5.1f}s  {loi[:52]}")

    (ra_thu / "durations.json").write_text(json.dumps(nhip, indent=2), encoding="utf8")
    print(f"\n{len(doan)} đoạn · tổng {tong / 60:.1f} phút · nhịp {ra_thu / 'durations.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
