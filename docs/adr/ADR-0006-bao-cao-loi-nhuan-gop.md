# ADR-0006 · Báo cáo lợi nhuận gộp — quyền riêng, chi phí gộp, gộp theo kỳ

- **Ngày:** 2026-08-04
- **Trạng thái:** Đã áp dụng
- **Người quyết:** GĐ dưới uỷ quyền Chain (CHẾ ĐỘ FULL-AUTO, *"uỷ quyền GĐ toàn quyền tiếp
  tục hoàn thiện Code"* 2026-08-04) — đóng **V3-7a** (ROADMAP)

## Câu Chain chốt

*"Cần Chain chốt chiều xem: theo thuốc · theo ngày · hay theo nhà cung cấp"* (ROADMAP) —
Chain trả lời **"theo ngày, tháng, quý, năm"**: chiều xem là **thời gian**, không phải
thuốc/NCC. `RevenueGranularity` (đã có DAY/WEEK/MONTH cho báo cáo doanh thu) mở rộng thêm
QUARTER/YEAR, dùng chung cho cả hai báo cáo.

## Ba quyết định phải tự chốt (Chain chưa nói tới, không thể suy ra từ câu trả lời trên)

### 1. Quyền riêng `sales.profit.read`, không tái dùng `sales.read`

V3-5 (ADR-0005) tái dùng quyền an toàn vì lý do rõ: *"không nhạy cảm hơn thứ POS đã hiện
sẵn cho thu ngân"*. Biên lợi nhuận **không** khớp lý do đó — không màn nào hôm nay hiện giá
vốn hay % lợi nhuận cho thu ngân/thủ kho. Đây là dữ liệu thương mại nhạy cảm (giá nhập, biên
lợi nhuận) mà một nhân viên rời đi có thể mang sang đối thủ. Quyết định: quyền riêng, chỉ
cấp `chain_pharmacist` + `system_admin` (không `branch_pharmacist`/`cashier`/`warehouse`).

Kỷ luật #7 (thêm/sửa permission → thử trên CSDL có dữ liệu sẵn): đã ghi + chạy test giả lập
một `chain_pharmacist` role đã tồn tại **trước** khi quyền mới được thêm vào code, xác nhận
`sync_system_roles()` backfill đúng — đúng hình dạng lỗi PROJECT_STATE §7l đã từng gặp với
`audit.read`.

### 2. Giá vốn tính GỘP (gross), khớp đúng chính sách doanh thu đã có — không trừ hàng trả

`SalesService.revenue_report_rows` đã tự khai: đếm **gộp tại thời điểm bán**, khác
`aggregate_sold_by_drug` (top-drugs) đếm **ròng sau khi trừ hàng trả**. Báo cáo lợi nhuận
phải chọn một trong hai vế — chọn nhầm thì `Doanh thu` và `Giá vốn` không còn cùng một quy
ước, phép trừ giữa chúng vô nghĩa.

Quyết định: **gộp cả hai vế**. Một đơn hàng trả lại **không** đảo ngược `StockMovement` gốc
(nghiệp vụ trả hàng ghi `SaleReturned`, không xoá/bù dòng xuất kho FEFO đã ghi khi bán) —
nên `cogs_by_order` vốn dĩ đã gộp mà không cần xử lý riêng cho hàng trả. Đây **không phải
trùng hợp có lợi** mà là **ràng buộc thiết kế bắt buộc**: nếu chọn "ròng" cho doanh thu thì
phải tự dựng logic trừ giá vốn hàng trả riêng — tốn công hơn nhiều so với vẻ ngoài ROADMAP
dự đoán ("rẻ hơn nhiều"), và có nguy cơ hai vế lệch chính sách nếu làm không cẩn thận.

### 3. Giá vốn dùng `cost_price` HIỆN TẠI của lô, không phải giá tại thời điểm xuất kho

`ProductBatch.cost_price` là **bình quân gia quyền**, cập nhật lại mỗi lần lô đó nhận thêm
hàng (`merge_receipt`). `StockMovement` (sổ cái xuất/nhập) **không mang cột giá vốn riêng** —
nó chỉ ghi số lượng + hướng. Nghĩa là: một lô nhận thêm hàng ở giá khác **sau** một lượt bán
sẽ làm giá vốn tính lại cho lượt bán *cũ* đó trôi theo giá mới, dù thực tế lượt bán đó đã
chốt ở giá cũ.

**Đây là một xấp xỉ có ghi nhận, không phải lỗi ẩn.** Sửa đúng (giá vốn tại đúng thời điểm)
cần thêm cột giá vào `StockMovement` + backfill dữ liệu cũ — một thay đổi lược đồ, ngoài
phạm vi "rẻ" mà ROADMAP kỳ vọng cho V3-7a. Ghi vào sổ nợ để làm sau nếu Chain cần độ chính
xác cao hơn (VD đối chiếu thuế/kiểm toán).

## Tại sao gộp bucket trước rồi mới stream (không stream từng dòng)

`SalesService._bucket_by_period` (đã có, dùng cho báo cáo doanh thu) và bộ tích luỹ của báo
cáo lợi nhuận đều gom **toàn bộ bucket** (giới hạn bởi số kỳ×chi nhánh×loại tiền phân biệt,
luôn nhỏ) vào bộ nhớ trước khi phát dòng CSV cuối cùng — không phải giữ *toàn bộ đơn hàng*.
Phía tốn tài nguyên (số đơn hàng, có thể rất lớn) vẫn phân trang/stream qua
`order_revenue_rows` + `_chunked` (gộp giá vốn theo lô 500 đơn/lượt) — cùng khuôn bộ nhớ
phẳng ADR-0005 đã lập cho báo cáo tồn kho.

## Bốn câu bắt buộc của kỷ luật #17

| | Trước | Sau |
|---|---|---|
| Endpoint | không tồn tại | `GET /reports/profit/export` — **mới hoàn toàn**, không có gì "cũ" để phá vỡ |
| `RevenueGranularity` | DAY/WEEK/MONTH | + QUARTER/YEAR — **thêm giá trị enum**, DAY/WEEK/MONTH không đổi hành vi |
| `SalesService.revenue_report_rows` | tự phân trang + gộp bucket nội bộ | refactor dùng lại `order_revenue_rows` + `_bucket_by_period` — **hành vi/API không đổi**, đã chạy lại toàn bộ test doanh thu cũ, xanh |

Không có API/CSDL cũ nào bị đổi hình dạng — mục này thêm thuần tuý, không cần ADR về tương
thích như ADR-0002/0004/0005.

## Đột biến đã kiểm (kỷ luật #14)

Tạm cho `InventoryService.cogs_by_order` luôn trả `{}` — xác nhận đúng 2 test đỏ vì lý do
đúng (`Giá vốn`/`Lợi nhuận gộp` tính sai khi thiếu chi phí), đã khôi phục.
