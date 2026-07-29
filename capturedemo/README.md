# capturedemo — video hướng dẫn cơ bản

| | |
|---|---|
| Tệp | `BERAS-huong-dan-co-ban.mp4` |
| Thời lượng | **3 phút 00 giây** (180,5s) |
| Khổ hình | **804×1748** — tỉ lệ iPhone (402×874 điểm ở @2x) |
| Mã hoá | H.264 + AAC, `faststart` (mở là chạy ngay, không phải tải hết) |
| Engine quay | **WebKit** — đúng engine Safari trên iPhone |
| Giọng đọc | **Bera** — `vi-VN-NamMinhNeural`, nam, nhịp +8% |

## Nội dung — 15 đoạn, đúng thứ tự một ngày làm việc

| Đoạn | Nội dung |
|---|---|
| 1 | Bìa mở — Nhà thuốc 650 |
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

Nhà thuốc **thật sự chạy trên phần mềm**, không phải dựng hình: CSDL `nt650`,
36 thuốc, 4 nhà cung cấp, 3 đơn mua, **0 hoá đơn** lúc bắt đầu — nên câu *"nhà
thuốc mới mở nên các con số còn bằng không"* khớp đúng với màn hình. Mọi thao tác
trong video đều gọi API thật; hoá đơn 5.900 đ ở đoạn 13 là hoá đơn do chính lượt
quay đó tạo ra.

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
- **Dọn dữ liệu trước mỗi lượt quay.** Lượt trước để lại hoá đơn và phiếu nhập ⇒
  màn Tổng quan hiện doanh thu trong khi lời đọc nói "còn bằng không".
- **Quay bằng WebKit, không phải Firefox.** Ô `<input type="date">` vẽ theo vùng
  miền của *trình duyệt*, không theo `lang` của trang — Firefox headless ra
  `09/20/2026` kiểu Mỹ dù đã đặt `locale: "vi-VN"` và `LC_ALL`; WebKit ra
  `20/09/2026`. Không phải lỗi sản phẩm (máy Chain đặt tiếng Việt vẫn đúng),
  nhưng để nguyên thì video dạy sai.
