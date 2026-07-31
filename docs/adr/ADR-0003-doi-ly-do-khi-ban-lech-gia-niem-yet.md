# ADR-0003 — `POST /sales` đòi lý do khi bán lệch giá niêm yết

- **Ngày:** 2026-07-31
- **Trạng thái:** Đã áp dụng
- **Người quyết:** Chain (CEO). GĐ đề nghị phương án khác, Chain giữ nguyên — xem "Đánh đổi".

## Bối cảnh

`POST /sales` nhận `unit_price` từ máy khách và **không đối chiếu** với `drugs.sale_price`.
Quầy bán giá nào cũng được, không lớp nào biết.

`docs/legal/Luật-105-2016-QH13.SUMMARY.md` đã ghi khoảng trống này từ trước:

| Điều | Nội dung | Ghi chú trong chính tệp đó |
|---|---|---|
| 6.5.i | Cấm *"Bán thuốc cao hơn giá kê khai, giá niêm yết"* | *"Không có enforcement tự động trong `sales` hiện tại"* |
| 107.4 | Niêm yết giá bán lẻ bằng VNĐ tại nơi bán | — |

## Quyết định

`POST /sales` (và `POST /sync/sales`) từ chối **422** khi đơn có ít nhất một dòng mà
`unit_price != sale_price` của thuốc **và** thân yêu cầu thiếu `price_override_reason`
không rỗng. Đơn đi qua được thì ghi một dòng audit `SALE_PRICE_OVERRIDE` mang **số dòng
lệch** (không mang giá).

Ba điều cố ý **không** làm:

| Không làm | Vì sao |
|---|---|
| Không chặn cứng | Cùng lý do Đ-6 chọn cảnh báo thay vì cấm với dị ứng: cấm cứng đẩy quầy sang chỗ tệ hơn — bán bằng mã khác, hoặc thôi không cập giá niêm yết nữa. Khi đó chính giá niêm yết, thứ Điều 107.4 đòi, mới là cái hỏng |
| Không coi mã **chưa có giá** là lệch | `sale_price is None` ⇒ không có gì để lệch. Đòi giải thích một phép so không tồn tại sẽ chặn đúng những mã vừa nhập từ NPP, chưa kịp chốt giá |
| Không áp bất đối xứng | Xem "Đánh đổi" |

## Đây là thay đổi **ngữ nghĩa**, không phải hình dạng

Kỷ luật #17 (và ADR-0002 trước đó) đòi khai báo thay đổi ngữ nghĩa y như thay đổi hình
dạng. Đường dẫn, mã trạng thái thành công và kiểu dữ liệu **không đổi**; cái đổi là **một
yêu cầu trước đây thành công nay có thể trả 422**.

Bốn câu hỏi tương thích của kỷ luật #17:

| Câu hỏi | Trả lời |
|---|---|
| Frontend cũ còn chạy? | **Có, ở đường thường.** Quầy điền sẵn `unit_price` từ `drug.sale_price`, nên đơn bình thường không lệch. Đường **hỏng**: thu ngân sửa tay đơn giá của một mã đã có giá ⇒ 422 cho tới khi giao diện có ô lý do (bước 6/6) |
| API cũ còn chạy? | Có, trừ đúng ca trên. Không đổi đường dẫn, không đổi kiểu, trường mới không bắt buộc |
| CSDL cũ còn chạy? | Có — không đổi lược đồ nào ở `sales` |
| Migration lùi được? | Không có migration nào cho ADR này |

## Đánh đổi — GĐ đề nghị khác, Chain giữ nguyên

GĐ đề nghị **bất đối xứng**: bán **cao hơn** giá niêm yết ⇒ chặn hẳn (Điều 6.5.i cấm đích
danh chiều đó); bán **thấp hơn** ⇒ cho, kèm lý do. Lập luận: một dòng lý do trong audit
không hợp pháp hoá một hành vi bị cấm, và tệ hơn, nó tạo ra bằng chứng có ký tên rằng nhà
thuốc biết mình bán vượt giá.

**Chain giữ nguyên phương án đối xứng** sau khi nghe lập luận đó. Ghi lại để phiên sau
không phải đoán: cách này giữ linh hoạt ở quầy, đổi lại hệ thống **không chặn** hành vi
Điều 6.5.i cấm — nó chỉ ghi lại.

Nếu về sau muốn siết, chỗ sửa là **đúng một hàm**: `ensure_price_override_acknowledged`
trong `sales/domain/rules.py` — thêm tham số hướng lệch. Không đụng lược đồ, không đụng
hợp đồng API.

## Liên quan

- `docs/features/gia-ban-va-thu-tien-quay/01_DECISIONS.md` — Bước 0-3, mục cờ pháp lý
- `ADR-0002` — tiền lệ về thay đổi ngữ nghĩa mà hình dạng không đổi
- Quyết định Đ-6 (cảnh báo dị ứng) — cùng khuôn "xác nhận có chữ, không cấm cứng"
