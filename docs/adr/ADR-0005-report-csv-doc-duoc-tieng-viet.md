# ADR-0005 · Báo cáo CSV đổi sang tiêu đề tiếng Việt + tên thuốc/chi nhánh

- **Ngày:** 2026-08-04
- **Trạng thái:** Đã áp dụng
- **Người quyết:** GĐ dưới uỷ quyền Chain (CHẾ ĐỘ FULL-AUTO, *"uỷ quyền GĐ toàn quyền tiếp
  tục hoàn thiện Code"* 2026-08-04) — đóng **V3-5** (ROADMAP)

## Vấn đề

Ba báo cáo xuất CSV (`/reports/revenue/export`, `/reports/inventory/stock/export`,
`/reports/top-drugs/export`) có tiêu đề cột toàn tiếng Anh dạng máy
(`period_start`, `branch_id`, `revenue_total`…) và **không cột nào có tên thuốc** — chỉ
`drug_id` dạng UUID. Với một chủ quầy mở file này trong Excel, tệp *"bằng không"*: không
đọc được cột nào nói lên điều gì mà không tra chéo UUID thủ công.

## Quyết định

Ba thay đổi, cả ba đều **thêm/đổi nhãn**, không đổi bộ dữ liệu:

1. **Tiêu đề cột đổi sang tiếng Việt có dấu** (không phải snake_case kiểu
   `compliance/application/csv_export.py`, vì đó là để khớp đúng mẫu sổ pháp lý TT18 — ở
   đây không có mẫu nào phải khớp, mục tiêu là đọc được trong Excel).
2. **Thêm cột tên thuốc / tên chi nhánh**, đặt cạnh cột mã (id) tương ứng — **không xoá**
   cột mã: một người cần đối chiếu vẫn tra được bằng UUID, và không có gì đọc file này theo
   vị trí cột (`frontend/.../bao-cao/page.tsx` chỉ kích hoạt tải file, không đọc nội dung).
3. **Định dạng ngày/tiền theo lối Việt Nam**: `dd/mm/yyyy` (đã dùng sẵn ở hoá đơn in,
   `sales/interface/receipt_rendering.py`), tiền phân cách hàng nghìn bằng dấu chấm, số
   lượng bỏ số 0 thừa sau dấu thập phân (`Numeric(18,3)` trả "100.000" cho 100 viên — đúng
   hình dạng CLAUDE.md kỷ luật #26 đã ghi nhận gây đọc nhầm "100 nghìn").

## Đọc tên thuốc/chi nhánh mà không nới quyền của người gọi

`sales`/`inventory` không được import `catalog`/`iam` (module-independence). Tên được tra
tại **composition root** (`api/v1/reports.py`), dưới **danh tính hệ thống cố định** — đúng
khuôn `CatalogDrugInfoProvider`/`ComplianceOrgProfileReader` (`cross_module.py`, ADR-0004):
thu ngân xuất báo cáo doanh thu chỉ giữ `sales.read`, không cần thêm `catalog.read`/
`iam.user.read` chỉ để cột tên hiện đúng.

`IamService.branch_names` (mới) tái dùng quyền `iam.user.read` đã có thay vì thêm quyền
mới — phương pháp không cần seed/migration, vì phương thức này chỉ được gọi dưới danh
tính hệ thống, không ai thật sự cần quyền đó qua vai trò.

## Streaming vs. tra tên hàng loạt — điểm khó thật sự của quyết định này

`revenue`/`top-drugs` không stream (đã gom danh sách trước khi xếp hạng/nhóm), nên tra tên
một lượt là đủ. `stock` **thật sự stream** (`InventoryService.stock_report_rows`, phân
trang 500 dòng/lượt, cố ý giữ bộ nhớ phẳng dù báo cáo lớn cỡ nào) — tra tên **tất cả**
`drug_id` trước khi stream sẽ phá đúng thiết kế đó. Giải: `reports.py::_chunked` gom
stream thành từng lô ≤500 dòng (khớp `_STOCK_REPORT_BATCH`), tra tên theo lô, rồi mới
sinh CSV — bộ nhớ vẫn phẳng (chỉ giữ 1 lô + tên của nó tại một thời điểm), không phải giữ
toàn bộ id trước.

## Đây là thay đổi NGỮ NGHĨA, khai báo theo kỷ luật #17

| | Trước | Sau |
|---|---|---|
| `GET /reports/*/export` — đường dẫn, mã trạng thái, `Content-Type` | không đổi | **không đổi** |
| **Tiêu đề cột + một số giá trị ô** (ngày, tiền, số lượng) | tiếng Anh/ISO/raw | tiếng Việt, `dd/mm/yyyy`, phân cách nghìn, bỏ số 0 thừa |
| **Cột mã (`*_id`)** | có | **vẫn có**, không đổi vị trí tương đối trong nhóm của nó |

**Bốn câu bắt buộc của kỷ luật #17:** frontend cũ còn chạy ✓ (`bao-cao/page.tsx` chỉ tải
file, không parse — xác nhận bằng `grep`, xem PROJECT_STATE §7dt) · API cũ còn chạy ✓
(path/status/Content-Type không đổi) · CSDL cũ còn chạy ✓ (không migration — dùng bảng đã
có) · lùi lại được ✓ (`git revert`, không bước dữ liệu nào phải hoàn tác).

**Ai có thể bị ảnh hưởng:** bất kỳ script/công cụ ngoài Claude Code đang tự động tải 3 file
này và đọc cột theo **tên tiêu đề** (không phải vị trí) sẽ phải đổi tên cột tra cứu. Không
có bằng chứng nào về việc này đang tồn tại trong repo tính đến hôm nay — nhưng ghi lại vì
đây là kiểu thay đổi có thể ảnh hưởng người ngoài repo mà `grep` không thấy được.

## Hệ luận đã kiểm — không có cổng nào canh câu cũ bị sai

Không giống N-1 (ADR-0004), không cổng UI/backend nào đang khẳng định *"cột này là
`drug_id`"* — `test_reports_e2e.py` là nơi duy nhất tra theo tên cột, và đã sửa cùng lượt
này (không phải nợ để lại). Đã chạy đột biến (kỷ luật #14): tạm cho `_branch_names` trả về
`{}`, xác nhận đúng 2 test đỏ vì lý do đúng (cột "Chi nhánh" không khớp "Chi nhánh chính"),
rồi khôi phục.
