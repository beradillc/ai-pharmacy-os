# Ảnh đơn thuốc ETC ở quầy — 2026-07-31

Chain giao: *"ETC demo chỉ cần có nút chụp, chụp lại đơn, có file ảnh lưu hệ thống là
xong"*, và sau đó: *"demo chỉ cần có ảnh chụp, không kể nội dung của ảnh"*.

Ảnh Firefox thật qua LAN IP, CSDL `nt650v2`. Sinh lại: `node scripts/check-pos-rx-photo.mjs`

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Lưu ảnh đơn thuốc | `image_url` có cột nhưng **0 test, 0 seed, không nơi cất tệp** | Ảnh nằm trong CSDL, **mã hoá at-rest** |
| Chỗ bấm | Không có `type="file"` nào trong toàn frontend | Nút **📷 Chụp đơn thuốc** ở quầy |
| Ai xem lại được | — | Dược sĩ + cấp chuỗi (`rx.image.read`). **Thu ngân không** |
| Ai đã xem | — | Mỗi lượt mở ghi một dòng `RX_IMAGE_VIEWED` |

## Nút hiện đúng lúc — ba trạng thái, đo cả ba

| Trạng thái giỏ | Kết quả |
|---|---|
| Toàn thuốc thường | Khối chụp đơn **không hiện** — nút thừa là nhiễu, và nhiễu thì người ta học cách bỏ qua |
| Có thuốc kê đơn, **chưa gắn khách** | Hiện lời nhắc *"Nhập số điện thoại khách ở trên…"*, **chưa có nút** |
| Có khách + tên bác sĩ | Ô chọn tệp **bật**, mang `capture="environment"` ⇒ mở thẳng camera sau trên điện thoại |

Đo được cả hai khổ: desktop ✓ · mobile ✓ · lỗi JS 0.

## Quyết định thiết kế

- **Nén trong trình duyệt trước khi gửi** (1600px, JPEG 0,7 ⇒ ~200–400 KB). Ảnh thô 2–5 MB
  qua base64 → mã hoá → base64 thành **3,6–9 MB một dòng**; vài chục dòng/ngày là `pg_dump`
  chậm tới mức người ta thôi chạy nó. Đây là **tiện lợi, không phải cổng** — máy chủ vẫn đo
  lại sau giải mã và từ chối quá 2 MB.
- **Bắt gắn khách mới chụp được.** Một ảnh đơn không gắn với ai thì không tra cứu lại được,
  và cũng không xoá theo yêu cầu được (Luật 91/2025).
- **Liều · tần suất · thời gian để TRỐNG** khi đơn tạo từ ảnh. Người đứng quầy không biết
  chúng — chúng chỉ có trên tờ giấy. Bắt gõ vào là bắt chép tay lại chính tờ vừa chụp; tự
  điền hộ `"1 viên"` là **bịa dữ liệu lâm sàng**.
- **Vẫn phải có ít nhất một dòng thuốc** (lấy từ giỏ, mã và số lượng là thật). Nếu cho rỗng,
  đơn kẹt vĩnh viễn ở `DRAFT` — `validate()` từ chối đơn rỗng, mà module không có đường thêm
  dòng sau khi tạo.

## 🔴 Cổng đỏ lần đầu vì lỗi PHÉP ĐO, và ảnh chụp là thứ lộ ra

Lần chạy đầu cổng báo *"có thuốc kê đơn ⇒ hiện khối: 🔴"*. Nhưng ảnh chụp cho thấy
**"Chưa có thuốc trong giỏ"** — cả hai lượt bấm "Thêm" đều trượt vì locator sai, và
`.catch(() => {})` của tôi **nuốt mất lỗi** rồi để cổng đi tiếp đo một màn hình không ở
trạng thái nó tưởng.

Đã bỏ `.catch()` khỏi các lượt bấm dựng bối cảnh: bấm trượt phải làm cổng ném lỗi ngay tại
dòng đó. Đây là lần thứ ba trong tuần một cổng đỏ **oan** — và lần thứ ba ảnh chụp là thứ
phân biệt được "sản phẩm hỏng" với "phép đo hỏng".
