"""Ghép tiếng vào hình: nhạc mở đầu + lời thoại đặt đúng mốc + xuất MP4.

Gom lại từ ba đoạn `ffmpeg` chạy tay rải rác 02/08. Chạy tay thì mỗi lượt một kiểu, và
lượt nào quên `aresample` thì giọng nam phát sai tốc độ mà không ai biết.

🔴 **Đặt từng câu vào ĐÚNG MỐC của nó (`adelay`), không nối đuôi nhau.** Nối đuôi thì lệch
dần vì giữa các đoạn còn `goto`, còn hiệu ứng gỡ bìa, còn thời gian trình duyệt tải — lượt
ghép đầu tiên lệch **7,1 giây** ở đoạn cuối, tức giọng nói về một màn hình đã trôi qua.

Dùng:
    python3 scripts/ghep_video.py <thư-mục-quay> <thư-mục-tiếng> <tệp-mp4-ra>
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TAN_SO = 22050
NHAC_GIAY = 3.0
# Hợp âm La trưởng — ba nốt, tắt dần. Sinh bằng ffmpeg nên KHÔNG cần tệp nhạc trong repo:
# một tệp nhạc nhị phân trong git là thứ không ai xem được diff, và mỗi lần đổi là một bản
# sao mới nằm lại vĩnh viễn.
NOT = (440.0, 554.37, 659.25)


def sinh_nhac(ra: Path) -> None:
    """Nhạc hiệu mở đầu ~3 giây: hợp âm vào mềm, tắt dần, âm lượng thấp hơn lời thoại."""
    nguon = "".join(
        f"sine=frequency={f}:duration={NHAC_GIAY}:sample_rate={TAN_SO}[n{i}];"
        for i, f in enumerate(NOT)
    )
    tron = "".join(f"[n{i}]" for i in range(len(NOT)))
    loc = (
        f"{nguon}{tron}amix=inputs={len(NOT)}:normalize=1[hop];"
        f"[hop]afade=t=in:st=0:d=0.35,afade=t=out:st={NHAC_GIAY - 1.6}:d=1.6,volume=0.22[out]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-filter_complex",
            loc,
            "-map",
            "[out]",
            "-ac",
            "1",
            "-ar",
            str(TAN_SO),
            str(ra),
        ],
        capture_output=True,
        check=True,
    )


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    quay, tieng, ra_mp4 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    tl = json.loads((quay / "timeline.json").read_text())

    nhac = quay / "nhac.wav"
    sinh_nhac(nhac)

    # Nhạc mở đầu đặt ở mốc 0; câu giới thiệu nội dung ("00b") vào SAU khi nhạc tắt.
    dat: list[tuple[Path, int]] = [(nhac, 0)]
    for ma in sorted(tl, key=lambda k: tl[k]):
        f = tieng / f"{ma}.wav"
        if f.exists():
            dat.append((f, tl[ma]))
        phu = tieng / f"{ma}b.wav"
        if phu.exists():
            dat.append((phu, tl[ma] + int(NHAC_GIAY * 1000) + 250))

    ins: list[str] = []
    loc: list[str] = []
    for i, (f, ms) in enumerate(dat):
        ins += ["-i", str(f)]
        # `aresample` trước `adelay`: hai mô hình giọng có hai tần số mẫu, và `amix` lấy tần
        # số của luồng ĐẦU TIÊN — luồng nào lệch sẽ phát sai tốc độ.
        loc.append(f"[{i}:a]aresample={TAN_SO},adelay={ms}|{ms}[a{i}]")
    loc.append(
        "".join(f"[a{i}]" for i in range(len(dat))) + f"amix=inputs={len(dat)}:normalize=0[out]"
    )

    tieng_gop = quay / "tieng.wav"
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            *ins,
            "-filter_complex",
            ";".join(loc),
            "-map",
            "[out]",
            "-ac",
            "1",
            "-ar",
            str(TAN_SO),
            str(tieng_gop),
        ],
        capture_output=True,
    )
    if r.returncode:
        print("🔴 ghép tiếng lỗi:", r.stderr.decode()[-400:])
        return 1
    print(f"ghép {len(dat)} nguồn tiếng (1 nhạc + {len(dat) - 1} câu)")

    webm = next(quay.glob("*.webm"), None)
    if webm is None:
        print("🔴 không thấy tệp .webm nào trong", quay)
        return 1
    ra_mp4.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(webm),
            "-i",
            str(tieng_gop),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(ra_mp4),
        ],
        capture_output=True,
    )
    if r.returncode:
        print("🔴 mux lỗi:", r.stderr.decode()[-400:])
        return 1

    dai = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(ra_mp4),
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()
    print(f"✅ {ra_mp4} · {float(dai) / 60:.1f} phút")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
