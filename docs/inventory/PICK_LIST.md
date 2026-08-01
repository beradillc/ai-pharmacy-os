# Lộ trình lấy hàng (BERAS V2 Phase 4)

> Trạng thái: **đã chạy** — `POST /api/v1/inventory/pick-route`, màn quầy có nút
> *"🧭 Lộ trình lấy hàng"*. Đóng 2026-08-01, xem `PROJECT_STATE.md` §7db.

## Câu hỏi nó trả lời

`GET /inventory/where?drug_id=` (Phase 2) trả lời *"một mã nằm ở đâu"*.
`POST /inventory/pick-route` trả lời **"đi một vòng thì đi thế nào"**.

Với giỏ hai mã, hai câu hỏi cho cùng một đáp án. Với giỏ mười mã trải bốn kệ thì không —
và đó là lúc người đứng quầy cần tờ thứ hai.

## Quy tắc, và vì sao

| Quy tắc | Vì sao |
|---|---|
| Đơn vị của lộ trình là **Ô**, không phải mặt hàng | Cái tốn công là *đi tới ô*; nhặt thêm một hộp khi đã đứng trước ô gần như không tốn gì. Liệt kê theo mặt hàng bắt người ta đi A → B → **quay lại A** cho mã thứ ba |
| Sắp theo **`pick_order`**, không theo hạn dùng | FEFO đã quyết xong ở bước **chọn lô** (`sort_pick_candidates`). Sắp lại theo HSD ở đây cho lộ trình nhảy cóc giữa các kệ mà **không đổi được một hộp nào** |
| Khoá phụ là `location_path` | Hai lượt gọi phải cho cùng thứ tự — nếu không người đi lấy in ra hai tờ khác nhau cho cùng một đơn |
| Thiếu hàng ⇒ **vẫn trả lộ trình** cho phần lấy được | Giỏ mười mã mà một mã chưa xếp ô thì họ vẫn cần chín mã kia. Bỏ trắng cả tờ vì một dòng là làm hỏng công việc của người đang đứng chờ |
| `POST`, không `GET` | Giỏ hai chục mã trong query string chạm giới hạn độ dài URL của proxy; hỏng ở đó hiện ra dưới dạng lỗi mạng khó hiểu |

## Khác `allocate_from_locations` ở đâu

`allocate_from_locations` ném `InsufficientStockError` — nó phục vụ **một lượt xuất kho**,
phải toàn-vẹn-hoặc-không. `lo_trinh_lay_hang` gom lỗi đó vào danh sách `thieu` — nó phục vụ
**một người đang đi lấy hàng**. Cùng một phép tính, hai hợp đồng khác nhau, và trộn lẫn là
cách làm hỏng một trong hai.

## Ranh giới module

`inventory` không import `location`. Đường dẫn ô và `pick_order` đi qua port
`LocationInfoProvider`, cài đặt ở composition root (`api/v1/cross_module.py`).

## Thiếu ≠ hết hàng

`thieu` gộp hai chuyện khác nhau: **chưa ai xếp vào ô** và **trong ô không đủ**. Cả hai đều
không có nghĩa là kho hết hàng. Màn hình nói *"chưa xếp ô hoặc không đủ trong ô — hỏi kho"*
chứ không nói *"hết hàng"*. Tách hai trường hợp là việc còn nợ nếu quầy thấy cần.
