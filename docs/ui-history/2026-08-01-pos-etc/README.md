# Quầy — bán được thuốc kê đơn (P1, 2026-08-01)

Chain báo: *"Đã chụp ảnh nhưng vẫn thông báo cần đơn thuốc ETC hợp lệ"*.

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Chụp đơn xong | nhãn *"✓ Đã lưu ảnh đơn"*, bấm Thanh toán vẫn bị từ chối | nhãn đổi + hiện nút **✍️ Dược sĩ duyệt đơn** |
| Mã đơn thuốc | `useRxPhoto` trả về rồi **bị vứt** | gắn vào giỏ, gửi kèm `prescription_ref` khi thanh toán |
| Giỏ đổi sau khi chụp | tờ đơn cũ vẫn được coi là hợp lệ | tự hết hiệu lực (gắn chữ ký tập dòng ETC), phải chụp lại |
| Không có quyền `rx.approve` | không có gì giải thích | câu nói rõ *cần dược sĩ duyệt*, dẫn chiếu Luật Dược Đ6.5.h |
| Bán xong trên điện thoại | **không thấy xác nhận nào** — dòng "Đã bán thành công" đi theo giỏ vào `display:none` | thanh cố định trên thanh điều hướng, đọc được ngay |

## Ảnh

| Tệp | Cảnh |
|---|---|
| `*-1-truoc-khi-chup.png` | giỏ có thuốc ETC, chưa chụp đơn |
| `*-2-da-chup-hien-nut-duyet.png` | đã lưu ảnh ⇒ nút *Dược sĩ duyệt đơn* xuất hiện |
| `*-3-da-duyet.png` | duyệt xong |
| `*-4-ban-xong.png` | xác nhận bán thành công, **nhìn thấy được** |

Cả hai khổ: `mobile-390` (390×844) và `laptop-1440` (1440×900), `deviceScaleFactor: 2`.

## Ba lần ảnh chụp thắng phép đo, trong cùng một bước

Kỷ luật #20 nói *ảnh là thứ Chain duyệt*; #21 nói *phép đo cũng phải biết cái mà ảnh biết*.
Bước này là ví dụ đắt nhất từ trước tới nay:

| Phép đo | Nói gì | Ảnh nói gì | Vì sao phép đo sai |
|---|---|---|---|
| `count() > 0` | ✓ bán xong | không thấy xác nhận nào | đếm cả phần tử trong `display: none` |
| `isVisible()` | ✓ bán xong | vẫn không thấy | Playwright chỉ hỏi *có hộp và không ẩn*, không hỏi *có trong khung nhìn* |
| `trongKhungNhin()` | ✓ | ✓ khớp | đo `boundingBox` so với khung nhìn thật |

Và cổng ban đầu chỉ chạy khổ **1440×900**, trong khi lỗi chỉ có ở khổ điện thoại — một
cổng chạy đúng một khổ không canh được thứ chỉ hỏng ở khổ kia.
