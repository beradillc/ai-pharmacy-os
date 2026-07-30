# Changelog

Theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/). Chỉ-ghi-thêm — **không sửa
mục đã phát hành**, sai thì ghi một mục mới đính chính.

> **Phạm vi tệp này:** *cái gì đổi*, cho người dùng và người tích hợp.
> Vì sao đổi và đo thế nào ⇒ `PROJECT_STATE.md` (§7xx). Quyết định kiến trúc ⇒ `docs/adr/`.
> Quy tắc rút ra ⇒ `CLAUDE.md`. Không chép nội dung giữa bốn chỗ này.

## [Chưa phát hành]

### 🔴 Thay đổi phá vỡ tương thích

- **`GET /customers` và `GET /customers/{id}` nay trả số điện thoại ĐÃ CHE** (`*494` —
  một dấu sao + ba số cuối). Đường dẫn, hình dạng phản hồi, mã trạng thái **không đổi**;
  chỉ **giá trị** đổi, nên bên gọi nào dùng trường này để nhắn tin/gọi điện sẽ hỏng **im
  lặng**. Số đầy đủ lấy qua `GET /customers/{id}/phone` (quyền `crm.pii.reveal`).
  → `docs/adr/ADR-0002`

### Đã thêm

- **Cảnh báo dị ứng hiện ở quầy (POS)** — trước đây cổng chỉ có ở máy chủ nên quầy là
  *"bấm hoàn tất rồi mới biết"*. Nay hiện ngay khi gắn khách + thêm thuốc, **trên** tổng
  tiền; có xung đột thì nút đổi thành "Ghi lý do để bán" cho tới khi thu ngân ghi lý do.
  Phân biệt rõ **"chưa được phép kiểm"** với **"đã kiểm và sạch"** — hai thứ này cùng trả
  `conflict_count = 0`. → `docs/ui-history/2026-07-31-pos-canh-bao-di-ung/`

- **Sửa được hoạt chất của thuốc đã tạo**: `PUT /drugs/{id}/ingredients` (quyền
  `catalog.update`, cấp chuỗi). Trước đó không có đường nào sửa — nhập sai một hoạt chất
  là cảnh báo dị ứng sai người **vĩnh viễn**.
- **Cảnh báo dị ứng ở quầy**: `POST /sales/allergy-check` hỏi trước khi bán; cưỡng chế lúc
  hoàn tất đơn — có xung đột mà không ghi lý do ⇒ `422`, ghi lý do ⇒ bán được và vào sổ
  audit (`SALES_ALLERGY_WARNING_OVERRIDDEN`).
- **Cột "Điểm"** trên màn Khách hàng — tiền đã mua trong năm dương lịch, kèm
  `boxes_this_year` tính sẵn ở backend. → `docs/adr/ADR-0001`
- **Đồng ý BASIC ghi tự động** khi tạo khách có số điện thoại, cơ sở `COUNTER`. **Không**
  lan sang `LOYALTY`/`HEALTH` — hai mục đó vẫn phải hỏi riêng (Luật 91/2025 Điều 9).
- **Quyền mới**: `catalog.update`, `crm.pii.reveal` — chỉ cấp chuỗi. Tới được deployment
  cũ qua `python -m seeds.run` (`sync_system_roles`), đã đo trên CSDL có dữ liệu sẵn.
- **Lệnh `seeds.backfill_drug_ingredients`** — nối thuốc → hoạt chất cho CSDL seed trước
  bản vá; `--dry-run`, `--verify`, an toàn khi chạy lại, chỉ thêm không xoá.
- **Hai cổng trình duyệt thật**: `frontend/scripts/shot-desktop-mobile.mjs` và
  `measure-mobile.mjs` — chụp desktop + khung điện thoại rồi **đo**, không chỉ nhìn.

### Đã sửa

- **Cảnh báo dị ứng chưa từng kích hoạt được**: seeder tạo thuốc và hoạt chất nhưng không
  nối, `drug_ingredients` = 0 dòng trên mọi CSDL. Nay 26/36 thuốc có hoạt chất; trên
  `nt650v2` hai khách khai dị ứng Acid clavulanic nay được cảnh báo ở **Augmentin 625mg** —
  tên thuốc không chứa chữ nào của tên hoạt chất, nên không cách khớp theo tên nào bắt được.
- **Tìm khách không thấy → bấm "Thêm" phải gõ lại số**: hộp thoại luôn nằm trong cây nên
  `useState(initialPhone)` chỉ chạy một lần lúc tải trang. Nay gắn khi mở.
- **Bảng khách tràn ngang trên điện thoại**: 322px → **0px**, qua bốn lượt đo.
- **Bảng chọn hoạt chất / mức độ dị ứng phủ kín màn, không có chỗ đóng**: bỏ `<select>`
  gốc (nó mở bộ chọn của hệ điều hành). Mức độ thành ba nút; hoạt chất thành bảng chọn của
  ứng dụng có ô tìm và **ba** lối thoát (nút Đóng, bấm nền mờ, phím Esc).
- **Khoảng trắng thừa ở bảng Đồng ý trên điện thoại**: `flex: 1 1 260px` đúng cho hàng
  ngang nhưng hộp xoay thành cột ở khổ hẹp, và `flex-basis` khi ấy ăn theo **chiều cao**.
- **Bệnh nền chỉ chọn được một mã mỗi lượt** → chọn nhiều, thêm một lượt.
- **Hai bảng (Đồng ý + Sức khoẻ) mở chồng nhau được** — nút "Đóng" nào đóng bảng nào là
  chuyện phải đoán.
- **`test_sales_list.py` đỏ ngẫu nhiên**: `date.today()` tính lúc import module, nên một
  lượt `pytest` chạy qua nửa đêm làm 4 test đỏ với `assert 0 == 3` — trông y hệt lỗi phân
  trang. Lỗi có sẵn, chỉ lộ khi chạy trúng giao thừa.
- Chú thích `CUSTOMER_SENSITIVE_AUTO_CHECK` bị tách khỏi thành viên nó mô tả.

### Đã dọn

- Bỏ mã chết `.spaced` (màn Khách hàng) và hằng `MOC_DOI_QUA` — mốc 2 triệu từng khai ở
  **hai ngôn ngữ**, đổi một bên thì bên kia im lặng sai.
