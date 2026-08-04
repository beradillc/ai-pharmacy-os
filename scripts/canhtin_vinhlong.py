#!/usr/bin/env python3
"""Canh tin tuyển dụng viên chức trên trang Sở GD&ĐT Vĩnh Long, gửi email khi có tin mới.

Chạy mỗi 30 phút bằng systemd user timer (`canhtin-vinhlong.timer`, `Persistent=true`
để chạy bù khi máy vừa bật lại). Chỉ dùng thư viện chuẩn — server không có node, và
cài thêm gói thì phải mở `dnf` trong sudoers, mà `dnf` là đường lên root.

THIẾT KẾ — vì sao không đưa thẳng trang cho Claude mỗi 30 phút:
  48 lần/ngày × ~15k token = ~21 triệu token/tháng, ăn chung hạn mức với việc Pharmacy.
  Nên: `urllib` lấy danh sách URL (0 token) → so với seen.txt → CHỈ khi có URL mới thì
  Claude mới vào cuộc để tóm tắt. Vẫn phát hiện tin trong vòng 30 phút như yêu cầu.

BA NGUỒN theo dõi (Chain chốt 04/08: "Tin tuyển dụng + Thông báo chung"):
  Phát hiện lúc khảo sát: thông báo tuyển dụng viên chức KHÔNG chỉ nằm ở mục Tin tuyển
  dụng — có bản nằm trong "Văn bản chỉ đạo điều hành". Canh mỗi một mục là có ngày sót.

  - tin-tuyen-dung          : mọi tin đều liên quan ⇒ LUÔN gửi mail
  - tin-tuc-su-kien         : tin chung, lượng lớn ⇒ lọc từ khoá rồi mới gửi
  - van-ban-chi-dao-dieu-hanh: văn bản của Sở       ⇒ lọc từ khoá rồi mới gửi

TỰ BẢO VỆ:
  - Chỉ ghi vào seen.txt SAU KHI gửi mail thành công ⇒ gửi lỗi thì vòng sau thử lại,
    không mất tin. Đây là chỗ dễ sai nhất: ghi trước là mất tin vĩnh viễn.
  - Tách được 0 link = COI LÀ LỖI (trang đổi HTML), báo động, không ghi seen.txt.
    Nếu không, trang đổi giao diện là script im lặng "không có tin mới" mãi mãi.
  - Claude hỏng/timeout KHÔNG chặn cảnh báo — gửi mail trơn (tiêu đề + link) thay vì
    nuốt luôn tin. Tóm tắt là tiện nghi, cảnh báo mới là nhiệm vụ.
  - KHÔNG tải file .pdf/.doc/.xls đính kèm: robots.txt của trang chặn. Chỉ gửi link.
"""

from __future__ import annotations

import html
import os
import re
import smtplib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

GOC = "https://vinhlong.edu.vn"
UA = "Mozilla/5.0 (canh-tin-tuyen-dung; lien he beradillc@gmail.com)"

# (đường dẫn, tên hiển thị, có lọc từ khoá không)
NGUON = [
    ("/tin-tuc/tin-tuyen-dung", "Tin tuyển dụng", False),
    ("/tin-tuc/tin-tuc-su-kien", "Tin tức - Sự kiện", True),
    ("/van-ban-chi-dao-dieu-hanh/so-giao-duc-va-dao-tao", "Văn bản chỉ đạo điều hành", True),
]

# Dùng cho 2 nguồn tin chung — bỏ dấu trước khi so, nên viết không dấu.
#
# CHỈ dùng từ khoá MẠNH. Bản đầu có thêm "xet tuyen"/"thi tuyen"/"chi tieu tuyen" và
# chạy thử 04/08 dính ngay 2 tin TUYỂN SINH LỚP 10 — chuyện của học sinh, không phải
# tuyển dụng viên chức. Thông báo tuyển dụng viên chức thật gần như luôn có chữ
# "tuyển dụng" hoặc "viên chức" trong tiêu đề, nên siết lại vẫn không sót.
TU_KHOA = [
    "tuyen dung",
    "vien chuc",
    "bien che",
    "tuyen giao vien",
    "hop dong lam viec",
    "tuyen nhan vien",
    "tuyen cong chuc",
]

STATE = Path.home() / ".local/state/canhtin-vinhlong"
SEEN = STATE / "seen.txt"
LASTRUN = STATE / "lastrun.txt"  # dấu thời gian lượt chạy thành công gần nhất

# Trang này có HAI kiểu markup khác nhau, phát hiện lúc chạy thử 04/08:
#   - Mục tin tức     : <a href="..." title="Tiêu đề"><img ...></a>  ⇒ tiêu đề ở thuộc tính
#   - Mục văn bản     : <a class="title-documment" href="...">Tiêu đề</a> ⇒ tiêu đề là chữ trong thẻ
# Bắt chung một lượt rồi ưu tiên `title=`, không có thì lấy chữ trong thẻ.
RE_TIN = re.compile(
    r'<a\s(?P<attr>[^>]*href="(?P<u>[^"]+\.html\?categoryId=\d+)"[^>]*)>(?P<chu>.*?)</a>',
    re.S | re.I,
)
RE_TITLE_ATTR = re.compile(r'title="(?P<t>[^"]*)"', re.I)
RE_THE = re.compile(r"<[^>]+>")


def khong_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt thô sơ — đủ để so từ khoá, không cần unicodedata cho chuẩn."""
    bang = str.maketrans(
        "àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ",
        "aaaaaaaaaaaaaaaaadeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyy",
    )
    return s.lower().translate(bang)


def tai(url: str, lan: int = 3) -> str:
    loi = None
    for i in range(lan):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            loi = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"không tải được {url} sau {lan} lần: {loi}")


def lay_danh_sach(duong_dan: str) -> list[tuple[str, str]]:
    trang = tai(GOC + duong_dan)
    ra, da_co = [], set()
    for m in RE_TIN.finditer(trang):
        u = html.unescape(m.group("u"))
        ta = RE_TITLE_ATTR.search(m.group("attr"))
        t = html.unescape(ta.group("t")).strip() if ta else ""
        if not t:  # kiểu mục văn bản: tiêu đề nằm trong thẻ, không ở thuộc tính
            t = re.sub(r"\s+", " ", html.unescape(RE_THE.sub(" ", m.group("chu")))).strip()
        if not u.startswith("http"):
            u = GOC + u
        if u not in da_co and t:
            da_co.add(u)
            ra.append((u, t))
    return ra


def doc_seen() -> set[str]:
    if not SEEN.exists():
        return set()
    return {d.strip() for d in SEEN.read_text("utf-8").splitlines() if d.strip()}


def ghi_seen(urls: list[str]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with SEEN.open("a", encoding="utf-8") as f:
        for u in urls:
            f.write(u + "\n")


def van_ban_bai(url: str) -> str:
    """Lấy phần chữ của bài, cắt bớt để không nạp thừa token vào Claude."""
    try:
        h = tai(url)
    except RuntimeError:
        return ""
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    chu = html.unescape(RE_THE.sub(" ", h))
    chu = re.sub(r"\s+", " ", chu).strip()
    return chu[:12000]


def tom_tat(tieu_de: str, url: str) -> str:
    """Nhờ Claude tóm tắt. Hỏng thì trả chuỗi rỗng — KHÔNG được ném lỗi lên trên,
    vì mất tóm tắt còn hơn mất cảnh báo."""
    noi_dung = van_ban_bai(url)
    if not noi_dung:
        return ""
    loi_nhac = (
        "Đây là nội dung một thông báo trên trang Sở GD&ĐT tỉnh Vĩnh Long. "
        "Tóm tắt bằng tiếng Việt, ngắn gọn, dùng đúng các mục sau (bỏ mục nào không có "
        "thông tin, KHÔNG suy đoán, KHÔNG bịa số liệu):\n"
        "- Loại thông báo (tuyển dụng mới / kết quả / triệu tập / đính chính / khác)\n"
        "- Đối tượng và vị trí tuyển\n"
        "- Chỉ tiêu\n"
        "- HẠN NỘP HỒ SƠ (ghi rõ ngày, đây là mục quan trọng nhất)\n"
        "- Nơi nộp / hình thức nộp\n"
        "Kết thúc bằng ĐÚNG MỘT DÒNG theo mẫu `Mức liên quan: X` với X là một trong ba "
        "chữ CAO / TRUNG BÌNH / THẤP (chỉ chọn một, không in cả ba). CAO = thông báo mở "
        "tuyển dụng còn hạn nộp; THẤP = tin kết quả đã xong.\n\n"
        f"Tiêu đề: {tieu_de}\n\nNội dung:\n{noi_dung}"
    )
    try:
        kq = subprocess.run(
            ["claude", "-p", loi_nhac],
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "HOME": str(Path.home())},
        )
        return kq.stdout.strip() if kq.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def gui_mail(tieu_de: str, than: str) -> None:
    user = os.environ.get("SMTP_USER", "").strip()
    mk = os.environ.get("SMTP_PASS", "").strip()
    nhan = os.environ.get("MAIL_TO", "").strip()
    if not (user and mk and nhan):
        raise RuntimeError(
            "thiếu SMTP_USER / SMTP_PASS / MAIL_TO — xem ~/.config/canhtin-vinhlong.env"
        )
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


def than_mail(muc: list[tuple[str, str, str, str]]) -> str:
    d = []
    for ten_nguon, tieu_de, url, tt in muc:
        d.append(f"[{ten_nguon}] {tieu_de}\n{url}\n")
        d.append(tt.strip() + "\n" if tt else "(không tóm tắt được — mở link để đọc bản gốc)\n")
        d.append("-" * 60 + "\n")
    d.append(
        "\n⚠️ Bản tóm tắt do máy tạo, CHỈ để biết sớm. Trước khi nộp hồ sơ phải mở link "
        "gốc đọc nguyên văn — điều kiện dự tuyển, mã ngạch và hạn nộp sai một chữ là hỏng hồ sơ.\n"
        "\n(Thư tự động, canh mỗi 30 phút trên máy bera-saas.)\n"
    )
    return "".join(d)


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    da_thay = doc_seen()
    lan_dau = not da_thay
    moi: list[tuple[str, str, str, str]] = []
    bo_qua: list[str] = []
    hong: list[str] = []

    for duong_dan, ten, co_loc in NGUON:
        try:
            ds = lay_danh_sach(duong_dan)
        except RuntimeError as e:
            hong.append(f"{ten}: {e}")
            continue
        if not ds:
            # Tách được 0 link = trang đổi HTML, KHÔNG phải "không có tin mới".
            hong.append(f"{ten}: tách được 0 link — nhiều khả năng trang đổi giao diện")
            continue
        for url, tieu_de in ds:
            if url in da_thay:
                continue
            if co_loc and not any(k in khong_dau(tieu_de) for k in TU_KHOA):
                bo_qua.append(url)
                continue
            moi.append((ten, tieu_de, url, ""))

    if hong:
        try:
            gui_mail(
                "⚠️ Canh tin Vĩnh Long: có nguồn đọc không được",
                "Các nguồn sau đọc không được — có thể trang đã đổi giao diện hoặc mất mạng.\n"
                "Script KHÔNG ghi nhận 'không có tin mới' cho các nguồn này, "
                "sẽ thử lại vòng sau.\n\n" + "\n".join("- " + x for x in hong),
            )
        except Exception as e:  # noqa: BLE001 — báo động hỏng không được làm sập vòng chạy
            print(f"[LỖI] không gửi được mail báo động: {e}", file=sys.stderr)

    if lan_dau:
        # Lần chạy đầu: ghi nhận toàn bộ tin đang có làm mốc, KHÔNG dội mail 30 tin cũ.
        tat_ca = [u for _, _, u, _ in moi] + bo_qua
        ghi_seen(tat_ca)
        LASTRUN.write_text(str(time.time()))
        print(f"[MỐC ĐẦU] ghi nhận {len(tat_ca)} tin đang có, không gửi mail")
        return 0

    if moi:
        moi = [(n, t, u, tom_tat(t, u)) for n, t, u, _ in moi]
        tieu_de_mail = (
            f"🔔 {len(moi)} tin tuyển dụng mới — Sở GD&ĐT Vĩnh Long"
            if len(moi) > 1
            else f"🔔 Tin mới: {moi[0][1][:70]}"
        )
        gui_mail(tieu_de_mail, than_mail(moi))
        # CHỈ ghi sau khi gửi xong — gui_mail ném lỗi thì không tới dòng này, vòng sau thử lại.
        ghi_seen([u for _, _, u, _ in moi] + bo_qua)
        LASTRUN.write_text(str(time.time()))
        print(f"[GỬI] {len(moi)} tin mới, bỏ qua {len(bo_qua)} tin không liên quan")
        return 0

    if bo_qua:
        ghi_seen(bo_qua)

    # Chain chốt 04/08: KHÔNG gửi thư nhịp tim hàng tuần. Chỉ gửi khi có tin mới.
    # Đổi lại, mỗi lượt chạy thành công đóng dấu thời gian vào lastrun.txt — hộp thư im
    # lặng thì vẫn kiểm được script còn sống hay không bằng `canhtin-conhong`, không cần
    # thư định kỳ. Thư báo động khi NGUỒN HỎNG vẫn giữ (khối `if hong` ở trên): nó chỉ
    # kêu khi thật sự có chuyện, không phải thư định kỳ.
    LASTRUN.write_text(str(time.time()))

    print(f"[OK] không có tin mới (bỏ qua {len(bo_qua)} tin không liên quan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
