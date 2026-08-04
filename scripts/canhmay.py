#!/usr/bin/env python3
"""Canh sức khoẻ máy `bera-saas`, gửi email khi có bất thường.

Chạy mỗi 10 phút bằng systemd timer. Chỉ dùng thư viện chuẩn (như `canhtin_vinhlong.py`
— server không có node, và cài gói thì phải mở `dnf` trong sudoers, mà `dnf` là đường
lên root).

NGUYÊN TẮC THIẾT KẾ — vì sao không phải "cứ xấu là gửi":

1. **Gửi theo CẠNH, không theo mức.** Chỉ gửi khi một phép kiểm ĐỔI trạng thái
   OK→XẤU (và một thư mừng khi XẤU→OK). Đĩa đầy 3 ngày mà cứ 10 phút một thư là
   432 thư — người nhận sẽ lọc thẳng vào thùng rác, và lúc có chuyện thật thì
   không ai đọc. Một cảnh báo bị làm ngơ thì tệ hơn không có cảnh báo.

2. **Nhắc lại thưa dần, không im hẳn.** Còn xấu thì nhắc lại mỗi 6 giờ — đủ để
   không quên, không đủ để phiền.

3. **Gộp một thư cho nhiều lỗi.** Mất điện làm hỏng 5 thứ cùng lúc ⇒ 1 thư liệt kê
   5 dòng, không phải 5 thư.

4. **Báo cả lúc MÁY VỪA DẬY, kèm link demo MỚI.** Đây là lý do thực tế nhất:
   `trycloudflare` cấp URL ngẫu nhiên, mỗi lần reboot là địa chỉ demo đổi và
   **không ai biết cái mới nếu không SSH vào**. Đúng ngày 05/08 đã vấp: máy reboot,
   link cũ trả HTTP 530, SSH lại đang vướng xác thực Tailscale ⇒ mất luôn đường
   lấy link. Thư này gỡ đúng nút đó.

5. **Không cảnh báo thứ mình không đo được.** Đọc lỗi (thiếu lệnh, thiếu quyền) thì
   ghi "không đo được", KHÔNG suy ra "bình thường". Im lặng vì mù khác im lặng vì ổn.
"""

from __future__ import annotations

import json
import os
import shutil
import smtplib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

STATE = Path.home() / ".local/state/canhmay"
TRANGTHAI = STATE / "trangthai.json"
NHAC_LAI_GIAY = 6 * 3600
MOI_DAY_GIAY = 15 * 60  # uptime dưới mức này ⇒ coi là máy vừa khởi động lại

DIA_NGUONG = 85  # % dùng
RAM_TRONG_TOI_THIEU_MB = 250
BACKUP_TOI_DA_GIO = 3  # cron chạy hàng giờ, quá 3 tiếng là có chuyện
CONTAINER_MONG_DOI = 5


def chay(lenh: list[str], giay: int = 20) -> tuple[int, str]:
    try:
        r = subprocess.run(lenh, capture_output=True, text=True, timeout=giay)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return 127, f"{type(e).__name__}: {e}"


def http_ma(url: str, giay: int = 15) -> int:
    """Trả mã HTTP, 0 nếu không nối được."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "canhmay"})
        with urllib.request.urlopen(req, timeout=giay) as r:
            return int(r.status)
    except urllib.error.HTTPError as e:
        return int(e.code)
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return 0


# ── các phép kiểm ────────────────────────────────────────────────────────────
# Mỗi hàm trả (khoá, ổn?, mô tả). `ổn?` = None nghĩa là KHÔNG ĐO ĐƯỢC — sẽ báo
# riêng, không gộp vào "bình thường".


def kiem_dia() -> tuple[str, bool | None, str]:
    try:
        t = shutil.disk_usage("/")
    except OSError as e:
        return "dia", None, f"không đọc được dung lượng đĩa: {e}"
    pct = round(t.used / t.total * 100)
    con = t.free / 1024**3
    mo_ta = f"đĩa / dùng {pct}%, còn {con:.1f} GB"
    return "dia", pct < DIA_NGUONG, mo_ta


def kiem_ram() -> tuple[str, bool | None, str]:
    try:
        so = {}
        for d in Path("/proc/meminfo").read_text().splitlines():
            k, _, v = d.partition(":")
            so[k] = int(v.strip().split()[0])  # kB
    except (OSError, ValueError, IndexError) as e:
        return "ram", None, f"không đọc được /proc/meminfo: {e}"
    kha_dung = so.get("MemAvailable", 0) / 1024  # MB
    tong_gb = so.get("MemTotal", 0) / 1024 / 1024
    mo_ta = f"RAM khả dụng {kha_dung:.0f} MB / tổng {tong_gb:.1f} GB"
    return "ram", kha_dung >= RAM_TRONG_TOI_THIEU_MB, mo_ta


def kiem_tai() -> tuple[str, bool | None, str]:
    try:
        tai5 = os.getloadavg()[1]
        nhan = os.cpu_count() or 1
    except OSError as e:
        return "tai", None, f"không đọc được tải: {e}"
    mo_ta = f"tải 5 phút {tai5:.2f} trên {nhan} nhân"
    # Ngưỡng 2× số nhân: dưới mức này máy vẫn đáp ứng được, trên là hàng đợi dài thật.
    return "tai", tai5 < nhan * 2, mo_ta


def kiem_container() -> tuple[str, bool | None, str]:
    ma, ra = chay(["podman", "ps", "--format", "{{.Names}}|{{.Status}}"])
    if ma != 0:
        return "container", None, f"không chạy được podman ps: {ra[:200]}"
    dong = [d for d in ra.splitlines() if d.strip()]
    xau = [d for d in dong if "healthy" not in d.lower() and "Up" not in d]
    if len(dong) < CONTAINER_MONG_DOI:
        thieu = CONTAINER_MONG_DOI - len(dong)
        return (
            "container",
            False,
            f"chỉ có {len(dong)}/{CONTAINER_MONG_DOI} container — THIẾU {thieu}",
        )
    if xau:
        return "container", False, f"{len(xau)} container không khoẻ: " + "; ".join(xau)
    return "container", True, f"{len(dong)}/{CONTAINER_MONG_DOI} container khoẻ"


def kiem_app() -> tuple[str, bool | None, str]:
    ma = http_ma("http://localhost:8080/api/v1/health")
    return "app", ma == 200, f"API nội bộ trả HTTP {ma or 'không nối được'}"


def kiem_duong_ham() -> tuple[str, bool | None, str]:
    ma, ra = chay(["systemctl", "--user", "is-active", "cloudflared-demo.service"])
    if ra.strip() != "active":
        return "duongham", False, f"cloudflared-demo.service = {ra.strip() or 'không rõ'}"
    u = link_demo()
    if not u:
        return "duongham", False, "unit active nhưng CHƯA CÓ link (đường hầm chưa đăng ký xong?)"
    ma_http = http_ma(u + "/api/v1/health", giay=20)
    return "duongham", ma_http == 200, f"link công khai trả HTTP {ma_http or 'không nối được'}"


def kiem_backup() -> tuple[str, bool | None, str]:
    thu_muc = Path.home() / "pharmacy_backups"
    if not thu_muc.is_dir():
        return "backup", None, "không thấy thư mục ~/pharmacy_backups"
    ban = sorted(thu_muc.glob("*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not ban:
        return "backup", False, "KHÔNG có bản backup nào trong ~/pharmacy_backups"
    gio = (time.time() - ban[0].stat().st_mtime) / 3600
    mo_ta = f"backup mới nhất {ban[0].name} — {gio:.1f} giờ tuổi"
    return "backup", gio <= BACKUP_TOI_DA_GIO, mo_ta


def kiem_canh_tin() -> tuple[str, bool | None, str]:
    f = Path.home() / ".local/state/canhtin-vinhlong/lastrun.txt"
    if not f.exists():
        return "canhtin", None, "canh tin chưa chạy lần nào"
    try:
        phut = (time.time() - float(f.read_text().strip())) / 60
    except (OSError, ValueError) as e:
        return "canhtin", None, f"không đọc được lastrun.txt: {e}"
    # Mốc 30' + RandomizedDelaySec 120s ⇒ quá 90 phút là bất thường thật.
    return "canhtin", phut <= 90, f"canh tin chạy cuối cách đây {phut:.0f} phút"


PHEP_KIEM = [
    kiem_dia,
    kiem_ram,
    kiem_tai,
    kiem_container,
    kiem_app,
    kiem_duong_ham,
    kiem_backup,
    kiem_canh_tin,
]

TEN = {
    "dia": "Dung lượng đĩa",
    "ram": "Bộ nhớ",
    "tai": "Tải CPU",
    "container": "Container",
    "app": "Ứng dụng (nội bộ)",
    "duongham": "Đường hầm công khai",
    "backup": "Backup",
    "canhtin": "Canh tin tuyển dụng",
}


# ── phụ trợ ──────────────────────────────────────────────────────────────────


def link_demo() -> str:
    """Đọc link công khai hiện tại từ log cloudflared. Cùng cách `link-demo` làm:
    chỉ nhận URL banner, loại `api.trycloudflare.com` trong dòng báo lỗi."""
    log = Path.home() / "cloudflared-demo.log"
    if not log.exists():
        return ""
    import re

    tim = re.findall(
        r"https://[a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com",
        log.read_text("utf-8", "replace"),
    )
    tim = [u for u in tim if not u.startswith("https://api.")]
    return tim[-1] if tim else ""


def uptime_giay() -> float:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return 1e9


def doc_trangthai() -> dict:
    if not TRANGTHAI.exists():
        return {}
    try:
        return json.loads(TRANGTHAI.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def ghi_trangthai(d: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    TRANGTHAI.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")


def gui_mail(tieu_de: str, than: str) -> None:
    user = os.environ.get("SMTP_USER", "").strip()
    mk = os.environ.get("SMTP_PASS", "").strip()
    nhan = os.environ.get("MAIL_TO", "").strip()
    if not (user and mk and nhan):
        raise RuntimeError("thiếu SMTP_USER / SMTP_PASS / MAIL_TO — xem ~/.config/bera-mail.env")
    m = EmailMessage()
    m["Subject"] = tieu_de
    m["From"] = user
    m["To"] = nhan
    m["Date"] = formatdate(localtime=True)
    m.set_content(than)
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=60) as s:
        s.starttls()
        s.login(user, mk)
        s.send_message(m)


def bang(ket_qua: list[tuple[str, bool | None, str]]) -> str:
    d = []
    for khoa, on, mo_ta in ket_qua:
        dau = "✅" if on is True else ("🔴" if on is False else "⚠️")
        d.append(f"  {dau} {TEN.get(khoa, khoa):22} {mo_ta}")
    return "\n".join(d)


# ── vòng chạy ────────────────────────────────────────────────────────────────


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    cu = doc_trangthai()
    bay_gio = time.time()
    ket_qua = [f() for f in PHEP_KIEM]

    moi_day = uptime_giay() < MOI_DAY_GIAY
    da_bao_day = cu.get("_boot_da_bao") == int(bay_gio - uptime_giay()) // 60

    hong = [(k, m) for k, on, m in ket_qua if on is False]
    mu = [(k, m) for k, on, m in ket_qua if on is None]
    moi_hong = [k for k, _ in hong if cu.get(k) != "xau"]
    vua_lanh = [k for k, on, _ in ket_qua if on is True and cu.get(k) == "xau"]

    lan_nhac = float(cu.get("_lan_nhac", 0) or 0)
    can_nhac_lai = bool(hong) and (bay_gio - lan_nhac > NHAC_LAI_GIAY)

    thu_da_gui = False
    u = link_demo()
    duoi = (
        f"\nLink demo hiện tại: {u or '(chưa có)'}\n"
        f"Máy đã chạy: {uptime_giay() / 3600:.1f} giờ\n"
        f"\n(Thư tự động từ bera-saas, kiểm mỗi 10 phút. Chỉ gửi khi trạng thái ĐỔI,\n"
        f"còn xấu thì nhắc lại mỗi 6 giờ — không gửi thư định kỳ khi mọi thứ bình thường.)\n"
    )

    # ① Máy vừa khởi động lại — báo kèm link demo MỚI (link đổi sau mỗi lần reboot)
    if moi_day and not da_bao_day:
        gui_mail(
            "🔄 bera-saas vừa khởi động lại — link demo đã ĐỔI",
            f"Máy vừa khởi động lại (chạy được {uptime_giay() / 60:.0f} phút).\n\n"
            "⚠️ Link demo cũ đã CHẾT. Link mới:\n\n    "
            + (u or "(đường hầm chưa lên, thử lại sau vài phút)")
            + "\n\n"
            + "Tình trạng sau khi dậy:\n"
            + bang(ket_qua)
            + "\n"
            + duoi,
        )
        cu["_boot_da_bao"] = int(bay_gio - uptime_giay()) // 60
        thu_da_gui = True

    # ② Có phép kiểm vừa chuyển sang XẤU, hoặc còn xấu và tới hạn nhắc lại
    elif moi_hong or can_nhac_lai:
        tieu_de = (
            f"🔴 bera-saas: {len(hong)} bất thường"
            if moi_hong
            else f"🔴 bera-saas: {len(hong)} bất thường VẪN CHƯA XỬ LÝ"
        )
        gui_mail(
            tieu_de,
            ("Phát hiện bất thường:\n" if moi_hong else "Nhắc lại — vẫn chưa xử lý:\n")
            + "\n".join(f"  🔴 {TEN.get(k, k)}: {m}" for k, m in hong)
            + "\n\nToàn cảnh:\n"
            + bang(ket_qua)
            + "\n"
            + duoi,
        )
        cu["_lan_nhac"] = bay_gio
        thu_da_gui = True

    # ③ Mọi thứ vừa trở lại bình thường sau khi đã báo xấu
    elif vua_lanh and not hong:
        gui_mail(
            "✅ bera-saas: đã trở lại bình thường",
            "Các mục vừa hồi phục: "
            + ", ".join(TEN.get(k, k) for k in vua_lanh)
            + "\n\nToàn cảnh:\n"
            + bang(ket_qua)
            + "\n"
            + duoi,
        )
        cu["_lan_nhac"] = 0
        thu_da_gui = True

    for khoa, on, _ in ket_qua:
        cu[khoa] = "xau" if on is False else ("mu" if on is None else "tot")
    cu["_lan_chay"] = bay_gio
    ghi_trangthai(cu)

    dau_thu = "ĐÃ GỬI THƯ · " if thu_da_gui else ""
    print(f"[{time.strftime('%H:%M')}] {dau_thu}{len(hong)} xấu, {len(mu)} không đo được")
    print(bang(ket_qua))
    return 0


if __name__ == "__main__":
    sys.exit(main())
