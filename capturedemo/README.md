# capturedemo — video hướng dẫn cơ bản

| | |
|---|---|
| Tệp | `BERAS-huong-dan-co-ban.mp4` |
| Thời lượng | **3 phút 07 giây** (186,8s) — gồm intro 3,4s |
| Khổ hình | **804×1748** — tỉ lệ iPhone (402×874 điểm ở @2x) |
| Mã hoá | H.264 + AAC, `faststart` (mở là chạy ngay, không phải tải hết) |
| Engine quay | **WebKit** — đúng engine Safari trên iPhone |
| Giọng đọc | **Bera** — `vi-VN-NamMinhNeural`, nam, nhịp +8% |
| Giao diện | **BERAS Warm** — coral · hổ phách · nền trắng ngà |
| Ghi chú | **Bản thử nghiệm** — nói rõ ở intro, ở lời chào và ở lời kết |

## Nội dung — 16 đoạn, đúng thứ tự một ngày làm việc

| Đoạn | Nội dung |
|---|---|
| 0 | **Intro 3,4s** — chữ hiện dần, vạch sáng quét ngang, nền coral→hổ phách |
| 1 | Lời chào — Nhà thuốc 650, bản thử nghiệm |
| 2 | Đăng nhập (DS. Trần Thị Trinh Thư) |
| 3 | Màn Tổng quan — KPI, việc cần xử lý, phím tắt |
| 4 | Đơn mua hàng — chọn đơn đã gửi NCC để nhận |
| 5 | Nhập hàng: số lượng, **số lô**, **hạn dùng** |
| 6 | Hạn gần ⇒ cảnh báo · nhận thiếu ⇒ "Nhận một phần" |
| 7 | Chốt phiếu — tồn kho tăng ngay |
| 8 | Kho — kiểm chứng lô vừa nhập |
| 9–11 | Bán hàng: tìm thuốc, thêm giỏ, cộng tiền |
| 12 | Thanh toán → mã hoá đơn |
| 13 | Hoá đơn — lọc theo ngày |
| 14 | Báo cáo — xuất CSV |
| 15 | Bìa kết |

## Dữ liệu trong video

Nhà thuốc **thật sự chạy trên phần mềm**, không phải dựng hình: CSDL `nt650v2`,
36 thuốc, 4 nhà cung cấp, 3 đơn mua, **572 hoá đơn trải 60 ngày**. Đây là nhà
thuốc **đã hoạt động lâu năm**, không phải mới mở — nên màn Tổng quan có doanh
thu thật (1,6 triệu hôm nay · 34,2 triệu trong 28 ngày), biểu đồ có hình, thẻ
*Cần xử lý* có việc tồn đọng thật. Mọi thao tác đều gọi API thật; hoá đơn ở đoạn
13 là hoá đơn do chính lượt quay tạo ra.

🔴 **Số liệu phải khớp lời đọc.** Bản đầu quay trên CSDL trống trong khi lời đọc
tả một nhà thuốc đang hoạt động — người xem tin cái nào? Dữ liệu nền của video
hướng dẫn không phải chuyện trang trí, nó là một phần của nội dung.

## Dựng lại

```bash
# 1 · giọng đọc  (cần: pip install edge-tts)
edge-tts --voice vi-VN-NamMinhNeural --rate=+8% --text "…" --write-media 01.mp3
# 2 · quay       (cần: máy chủ LAN đang chạy trên CSDL đã seed)
cd frontend
BERAS_EMAIL=… BERAS_PASSWORD=… BERAS_DURATIONS=…/durations.json \
BERAS_OUT=…/quay node scripts/record-tutorial.mjs
# 3 · ghép       (cần ffmpeg) — đặt từng câu vào mốc trong timeline.json
```

🔴 **Ghép theo `timeline.json`, đừng nối đuôi các câu.** Giữa các đoạn còn `goto`,
còn hiệu ứng, còn thời gian tải — lượt ghép đầu nối đuôi nhau **lệch 7,1 giây**
(hình 187,2s · tiếng 180,0s), tới đoạn cuối thì giọng nói về một màn hình đã trôi
qua. Script quay xuất ra mốc thật của từng đoạn để khâu ghép đặt đúng chỗ.

## Ghi chú khi quay lại

- **Dùng thuốc không kê đơn (OTC).** Thuốc ETC bị backend chặn đúng theo quy định
  (*"cần đơn thuốc hợp lệ"*); quay cảnh đó vào video **cơ bản** thì người mới
  tưởng phần mềm hỏng.
- **Dữ liệu nền phải khớp lời đọc, và dọn phiếu nhập của lượt trước.** Lượt quay
  trước để lại phiếu nhập đã chốt ⇒ đơn mua không còn ở trạng thái nhận được, và
  đoạn 4–7 hỏng. Riêng hoá đơn thì **giữ** — nhà thuốc trong video là nhà thuốc
  lâu năm, màn Tổng quan phải có doanh thu.
- **Bật theme bằng `localStorage`, đừng bấm qua màn Cài đặt.** Bấm qua Cài đặt
  thì khung hình đầu tiên vẫn là Classic rồi mới đổi — video mở màn bằng đúng cái
  theme không định giới thiệu. Đặt `beras.theme` trong `addInitScript` là không
  có nháy màu, vì `THEME_INIT_SCRIPT` đọc khoá đó ngay ở `<head>`.
- **Quay bằng WebKit, không phải Firefox.** Ô `<input type="date">` vẽ theo vùng
  miền của *trình duyệt*, không theo `lang` của trang — Firefox headless ra
  `09/20/2026` kiểu Mỹ dù đã đặt `locale: "vi-VN"` và `LC_ALL`; WebKit ra
  `20/09/2026`. Không phải lỗi sản phẩm (máy Chain đặt tiếng Việt vẫn đúng),
  nhưng để nguyên thì video dạy sai.
