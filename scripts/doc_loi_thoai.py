"""Đọc lời thoại thành tệp WAV — giọng tiếng Việt NAM + NỮ, ưu tiên bộ đọc thần kinh.

HAI BỘ ĐỌC, tự chọn cái tốt hơn nếu có:

  ① **Piper** (mặc định) — bộ đọc **thần kinh** chạy offline, cài 2026-08-02 theo yêu cầu
     Chain *"cài giọng chỉnh chu vào máy"*. Mô hình `vi_VN-vivos-x_low` dựng từ ngữ liệu
     VIVOS thu tại TP.HCM — **giọng miền Nam**, 65 người nói, có cả nam lẫn nữ. Chọn người
     nói bằng cách **đo tần số cơ bản** chứ không đoán: <165 Hz là nam, ≥165 Hz là nữ.
  ② **espeak-ng** (dự phòng) — bộ tổng hợp formant có sẵn trong hệ thống. Nghe rõ là giọng
     máy; giữ lại để máy nào chưa cài Piper vẫn dựng được bản nháp canh nhịp.

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
    BO_DOC=espeak python3 scripts/doc_loi_thoai.py ...   # ép dùng bộ dự phòng
"""

from __future__ import annotations

import ctypes
import os
import re
import struct
import subprocess
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

GOC_PIPER = Path.home() / ".local/share/beras-tts"
PIPER = GOC_PIPER / "venv/bin/piper"
# 🔴 HAI MÔ HÌNH KHÁC NHAU cho hai vai — quyết định bằng ĐO, và phép đo cho hai kết luận
#    NGƯỢC nhau nên không suy từ cái này ra cái kia được. (02/08, sau khi Chain nghe bản đầu
#    và nói "như không có dấu tiếng Việt".)
#
#    "Không có dấu" = MẤT THANH ĐIỆU, và thanh điệu đo được: tiếng Việt có thanh nên giọng
#    đọc đúng phải có F0 chuyển động mạnh TRONG từng âm tiết. Đo trên CÙNG một câu cho từng
#    vai (nửa cung / 10ms, càng cao càng rõ dấu):
#
#      câu NỮ:  vais1000-medium 0,91  ·  vivos spk3      0,67   ⇒ vais1000
#      câu NAM: vivos spk28     0,94  ·  vais1000 hạ 8 nửa cung 0,72   ⇒ vivos spk28
#
#    Giọng nữ hạ cao độ thành "nam" (rubberband giữ formant) nghe được nhưng **mất dấu** —
#    dịch cao độ kéo theo cả đường thanh điệu. Giọng nam THẬT giữ dấu tốt hơn.
#    🔴 LẦN CHỈNH THỨ HAI (02/08, Chain: "nghe như giọng miền Trung, chưa có nhấn nhá").
#    `vais1000` là mô hình của một đơn vị phía Bắc — rõ dấu nhưng SAI VÙNG MIỀN. Chain nghe
#    ra ngay, còn tôi thì không nghe được; bảng mô tả mô hình KHÔNG ghi vùng miền, nên chỉ
#    còn cách suy từ NGUỒN GỐC NGỮ LIỆU: `vivos` thu tại TP.HCM ⇒ giọng Nam.
#
#    Và lỗi thật của tôi: `vivos` có **65 giọng**, tôi mới thử ĐÚNG MỘT (spk3) rồi kết luận
#    cả mô hình bẹt dấu. Quét 19 giọng trên cùng một câu thì spk62 (nữ) và spk33 (nam) đều
#    HƠN `vais1000` — tức là kết luận cũ sai vì mẫu quá nhỏ, không phải vì mô hình kém.
#
#      nữ:  vivos spk62 0,96  ·  vais1000 0,91  ·  vivos spk3 0,67
#      nam: vivos spk33 1,29  ·  vivos spk28 0,94
#      (`25hours_single` đạt 1,31 — cao nhất — nhưng KHÔNG rõ vùng miền, để dự phòng)
#
#    Nay cả hai vai cùng một mô hình: cùng vùng miền, cùng tần số mẫu, cùng mức chất lượng.
MO_HINH_NU = GOC_PIPER / "voices/vi_VN-vivos-x_low.onnx"
MO_HINH_NAM = GOC_PIPER / "voices/vi_VN-vivos-x_low.onnx"
SPK_NU = 62  # F0 222,2 Hz · thanh điệu 0,96
SPK_NAM = 33  # F0 128,0 Hz · thanh điệu 1,29
# Đọc chậm hơn mặc định 15%: Chain yêu cầu "phát âm rõ chữ hơn". Người xem vừa nghe vừa
# nhìn tay bấm, nên chậm là đúng chứ không phải nhược điểm.
# 🔴 ĐO NHỊP THAY VÌ ĐOÁN. (02/08, lượt chỉnh thứ ba — Chain: "giọng quá chậm")
#    Lần trước tôi nâng lên 1.35 vì Chain bảo "nói chậm hơn", rồi nâng tiếp mà không đo.
#    Đếm ra: **2,20 âm tiết/giây** — đúng MỘT NỬA nhịp nói tự nhiên. Tiếng Việt hội thoại
#    ~5–6 âm tiết/giây; hướng dẫn chậm rãi ~4–4,5. Mỗi từ tiếng Việt gần đúng một âm tiết
#    nên đếm từ chia cho thời lượng là đủ chính xác để chỉnh.
#    0.80 ⇒ khoảng 3,8 âm tiết/giây: chậm hơn hội thoại một nhịp, vẫn trong khoảng tự nhiên.
NHIP_DOC = "0.55"  # đo dần: 1.35→2,20 · 0.80→3,17 · 0.66→3,51 âm tiết/giây
# Độ biến thiên ngôn điệu — "nhấn nhá". Mặc định 0,8; nâng lên cho câu bớt đều đều.
BIEN_THIEN = "1.0"

# 🔴 LẦN CHỈNH THỨ NĂM (02/08, Chain: "ngắt câu nghe cụp cụp, thiếu tính liên kết câu").
#    Ba triệu chứng, MỘT gốc: tôi cắt lời ra từng mảnh, đọc riêng, rồi chèn im lặng.
#      · "cụp cụp"        — chỗ nối biên độ nhảy đột ngột từ sóng đang dao động sang 0;
#      · "thiếu liên kết" — mỗi mảnh được đọc như một câu ĐỘC LẬP nên đều xuống giọng ở
#                           cuối, kể cả khi nó chỉ là một vế giữa câu.
#    Cắt theo dấu là cách sửa SAI VẤN ĐỀ: mô hình vốn tự biết ngắt theo dấu khi được đưa cả
#    câu. Nó chỉ chia sai khi bị đưa từng mảnh rời.
#    Nay: đưa NGUYÊN đoạn cho mô hình, để `--sentence-silence` lo khoảng nghỉ giữa câu, và
#    chỉ cắt khi ĐỔI NGƯỜI NÓI. Một giọng ⇒ gần như không cắt lần nào.
# Rút 35% so với lượt trước: nghỉ dài cộng với đọc chậm thành ra lê thê. Nghỉ vẫn PHÂN
# BIỆT theo dấu — đó là thứ tạo ngắt câu đúng, chỉ là không cần dài đến thế.
NGHI_CAU = "0.35"  # giây nghỉ giữa hai câu, do chính mô hình chèn (có ngôn điệu, không im chết)
# Vuốt 12ms hai đầu mỗi mảnh: dù còn chỗ nối nào cũng không còn nhảy biên độ ⇒ hết "cụp".
VUOT_MS = 12

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


def _vuot_hai_dau(pcm: bytes, tan_so: int) -> bytes:
    """Vuốt biên độ 12ms ở hai đầu một mảnh âm thanh.

    Chỗ nối giữa hai mảnh là chỗ sóng đang dao động bị cắt phựt về 0 — tai nghe ra tiếng
    "cụp". Vuốt vào/ra làm sóng về 0 mượt, và 12ms thì ngắn tới mức không ai nghe thấy có
    vuốt, chỉ nghe thấy hết cụp.
    """
    n = len(pcm) // 2
    mau = list(struct.unpack(f"<{n}h", pcm))
    k = min(int(tan_so * VUOT_MS / 1000), n // 2)
    for i in range(k):
        h = i / k
        mau[i] = int(mau[i] * h)
        mau[n - 1 - i] = int(mau[n - 1 - i] * h)
    return struct.pack(f"<{n}h", *mau)


class BoDocPiper:
    """Bộ đọc thần kinh. Cùng giao diện `doc()` với `BoDoc` để chỗ gọi không phải biết ai."""

    def __init__(self) -> None:
        if not PIPER.exists() or not MO_HINH_NU.exists() or not MO_HINH_NAM.exists():
            raise FileNotFoundError("chưa cài Piper hoặc thiếu mô hình giọng")

    def _mot_luot(self, loi: str, la_nam: bool, ra: Path) -> None:
        lenh = [
            str(PIPER),
            "-m",
            str(MO_HINH_NAM if la_nam else MO_HINH_NU),
            "-s",
            str(SPK_NAM if la_nam else SPK_NU),
            "--length-scale",
            NHIP_DOC,
            "--noise-w-scale",
            BIEN_THIEN,
            "--sentence-silence",
            NGHI_CAU,
            "-f",
            str(ra),
        ]
        r = subprocess.run(lenh, input=loi.encode("utf8"), capture_output=True)
        if r.returncode != 0 or not ra.exists():
            raise RuntimeError(f"piper lỗi: {r.stderr.decode()[-200:]}")

    def doc(self, luot: list[tuple[str, str]], ra: Path) -> float:
        """Đọc từng lượt rồi nối, chèn 0,35 giây nghỉ giữa hai người — không có nó thì câu
        hỏi dính câu trả lời."""
        khuc: list[bytes] = []
        tan_so = 22050
        # 🔴 NGẮT CÂU ĐÚNG CHỖ (Chain 02/08: "cần đúng ngắt câu"). Đưa cả đoạn vào một lần
        #    thì mô hình tự chia hơi theo phán đoán của nó — và nó chia sai ở câu dài có dấu
        #    gạch ngang hoặc mệnh đề phụ. Tách theo DẤU CÂU rồi đọc từng mảnh, chèn nghỉ
        #    đúng độ dài của dấu. Không phải dạy mô hình gì cả, chỉ là không bắt nó đoán.
        for giong, loi in luot:
            if not loi.strip():
                continue
            la_nam = "m3" in giong or giong == "nam"
            tam = ra.with_suffix(".tam.wav")
            self._mot_luot(loi, la_nam, tam)
            # 🔴 HAI MÔ HÌNH, HAI TẦN SỐ MẪU: vais1000 = 22 050 Hz, vivos = 16 000 Hz. Nối
            #    thẳng vào một tệp có MỘT header thì giọng nào không khớp sẽ phát sai tốc độ
            #    — nghe như tua nhanh hoặc kéo chậm, và người nghe sẽ tưởng mô hình hỏng.
            #    Quy tất cả về 22 050 Hz trước khi nối.
            with open(tam, "rb") as f:
                b = f.read()
            if int.from_bytes(b[24:28], "little") != tan_so:
                lai = ra.with_suffix(".lai.wav")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(tam), "-ar", str(tan_so), "-ac", "1", str(lai)],
                    capture_output=True,
                    check=True,
                )
                b = lai.read_bytes()
                lai.unlink(missing_ok=True)
            khuc.append(_vuot_hai_dau(b[44:], tan_so))
            # Chỉ còn nghỉ khi ĐỔI NGƯỜI NÓI. Trong một lượt, khoảng nghỉ giữa câu do chính
            # mô hình chèn (`--sentence-silence`) — có ngôn điệu dẫn vào, không im chết.
            if len(luot) > 1:
                khuc.append(b"\x00\x00" * int(tan_so * 0.22))
            tam.unlink(missing_ok=True)
        if not khuc:
            raise RuntimeError("không có lượt nào đọc được")
        mau = b"".join(khuc)
        ra.write_bytes(
            b"RIFF"
            + struct.pack("<I", 36 + len(mau))
            + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, tan_so, tan_so * 2, 2, 16)
            + b"data"
            + struct.pack("<I", len(mau))
            + mau
        )
        return len(mau) / 2 / tan_so


def chon_bo_doc():
    """Piper nếu có, espeak nếu không. Nói RA đang dùng cái nào — người đọc log phải biết
    bản tiếng vừa dựng là giọng thần kinh hay giọng máy."""
    if os.environ.get("BO_DOC") == "espeak":
        print("bộ đọc: espeak-ng (ép bằng BO_DOC)")
        return BoDoc()
    try:
        b = BoDocPiper()
        print(
            f"bộ đọc: Piper · nữ={MO_HINH_NU.name} · "
            f"nam={MO_HINH_NAM.name} spk{SPK_NAM} · nhịp {NHIP_DOC}"
        )
        return b
    except (FileNotFoundError, RuntimeError) as e:
        print(f"bộ đọc: espeak-ng (Piper không dùng được — {e})")
        return BoDoc()


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
        # Mã đoạn có thể là "00" hoặc "00b" — đoạn phụ chèn thêm (câu giới thiệu nội dung).
        if len(o) < 5 or not re.fullmatch(r"\d{2}[a-z]?", o[0]):
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
        giay = chon_bo_doc().doc([(GIONG_NU, sys.argv[2])], ra / "thu.wav")
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

    bo = chon_bo_doc()
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
