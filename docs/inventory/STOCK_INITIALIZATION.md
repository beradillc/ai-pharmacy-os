# Khởi tạo tồn kho (BERAS V2 Phase 9)

> Ngày: 2026-07-31 · Màn `/khoi-tao-ton` · `POST /api/v1/inventory/initialize`

## Vấn đề

Nhà thuốc chuyển từ sổ giấy hoặc phần mềm cũ sang đây đã có sẵn hàng trên kệ. Trước Phase 9,
đường duy nhất để đưa số tồn đó vào hệ thống là `POST /inventory/receive` — tức **khai nó là
hàng vừa mua vào**.

## Vì sao KHÔNG dùng lại đường nhập mua

Hiệu ứng lên **tồn kho** giống hệt nhau. Cái khác nằm ở chỗ khác:

| | Nhập mua | Khởi tạo tồn |
|---|---|---|
| Giá vốn | có thật, từ hoá đơn | **không biết** — hàng đã nằm trên kệ từ trước |
| Đi vào bình quân gia quyền | đúng | **sai** |
| Nên có trong báo cáo mua hàng | có | không |

`merge_receipt` tính **giá vốn bình quân gia quyền** của lô. Khởi tạo với giá vốn 0 đi chung
đường nhập mua sẽ kéo tụt giá vốn — một con số sai **lặng lẽ**, không mã lỗi nào, chỉ lộ ra ở
báo cáo lãi gộp nhiều tháng sau.

## Quyết định

**Không thêm loại chuyển động mới.** Vẫn là `MovementType.IN`; cái khác là **`ref_type`**:

| Đường | `ref_type` |
|---|---|
| `POST /inventory/receive` | `GRN` |
| `POST /inventory/initialize` | `INIT` |

Vì sao không thêm vào enum `MovementType`: thêm một giá trị buộc **mọi** chỗ đang phân nhánh
theo `type` phải biết về nó, và phần lớn những chỗ đó nên đối xử với khởi tạo **y hệt** nhập
kho (cộng tồn, FEFO, hạn dùng). Cái khác nhau là **ý nghĩa**, và ý nghĩa thuộc về `ref_type` —
trường vốn đã tồn tại để làm đúng việc này.

Hệ quả: báo cáo nào cần loại trừ khởi tạo thì lọc `ref_type <> 'INIT'`. Báo cáo nào không quan
tâm thì **không phải sửa gì** — đó là điểm của lựa chọn này.

## Tương thích ngược

| Câu hỏi | Trả lời |
|---|---|
| Frontend cũ còn chạy? | Có — thêm màn mới, không sửa màn nào |
| API cũ còn chạy? | Có — `/receive` không đổi hình dạng lẫn ngữ nghĩa; `is_initial` mặc định `false` |
| CSDL cũ còn chạy? | Có — không thêm cột, không thêm bảng. `ref_type` là `str` sẵn có |
| Migration lùi được? | Không có migration |

## Cổng

`frontend/scripts/check-khoi-tao-ton.mjs` (nhóm **ghi**, chỉ chạy với `--all`) và
`backend/tests/integration/test_inventory_location_e2e.py`.

Kiểm răng theo kỷ luật #14: đổi `ref_type="INIT" if data.is_initial else "GRN"` thành
`ref_type="GRN"` ⇒ đúng `test_khoi_tao_ton_ghi_ref_type_INIT_khong_phai_GRN` đỏ, 16 test kia
xanh. Khôi phục ⇒ 17/17 xanh.

🔴 Bản đầu của test đó **chỉ khẳng định tồn kho**, nên nó xanh kể cả khi `ref_type` không hề
được đặt. Phải cho nó đọc thẳng `SELECT ref_type FROM stock_movements` thì mới có răng.
