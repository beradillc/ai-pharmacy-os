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

- **`POST /sales` và `POST /sync/sales` nay trả `422` nếu đơn có dòng bán lệch giá niêm
  yết mà thiếu `price_override_reason`.** Đường dẫn, hình dạng và mã trạng thái thành
  công **không đổi**; cái đổi là một yêu cầu trước đây thành công nay có thể bị từ chối.
  Bán **đúng** giá niêm yết, hoặc bán một mã **chưa đặt giá**, không bị ảnh hưởng.
  → `docs/adr/ADR-0003`

- **3 báo cáo CSV xuất ra (`GET /reports/revenue/export`, `.../inventory/stock/export`,
  `.../top-drugs/export`) đổi tiêu đề cột sang tiếng Việt và thêm cột tên thuốc/tên chi
  nhánh.** Đường dẫn, mã trạng thái, `Content-Type` **không đổi**; cột mã (`*_id`) vẫn còn,
  chỉ thêm cột mới cạnh nó. Bên nào tự động đọc file này **theo tên tiêu đề cột** (không
  phải vị trí) sẽ phải đổi tên cột tra cứu, VD `revenue_total` → `Doanh thu`.
  → `docs/adr/ADR-0005`

### Đã thêm

- **`GET /reports/profit/export`** — lợi nhuận gộp (doanh thu − giá vốn) theo
  ngày/tuần/tháng/quý/năm, gộp chi nhánh/loại tiền, CSV tiếng Việt (ROADMAP V3-7a).
  Quyền **mới `sales.profit.read`** — chỉ cấp `chain_pharmacist`/`system_admin`, không
  tái dùng `sales.read` (margin không phải dữ liệu cashier đã thấy sẵn). Giá vốn tính
  gộp (không trừ hàng trả) và dùng giá vốn hiện tại của lô (bình quân gia quyền) —
  chi tiết `docs/adr/ADR-0006`.
- **Cài đặt → Lưu trữ** (`/cai-dat/luu-tru`): xem lại ảnh đơn thuốc đã chụp. Dữ liệu hiện
  **theo phân quyền** — quyền mới **`archive.read.chain`** (cấp chuỗi) cho xem toàn bộ chi
  nhánh; không có thì chỉ chi nhánh đang đăng nhập. Ảnh chỉ tải khi bấm mở, và mỗi lượt mở
  ghi một dòng audit.
- **`GET /prescriptions/archive`** — đơn thuốc đã có ảnh, mới nhất trước.
- **`GET /prescriptions/{id}` nay trả thêm `created_at`.**
- **`customer_id` của đơn thuốc nay cho phép `null`**, chỉ khi `source=IMAGE`: khách không
  để lại số điện thoại vẫn chụp được đơn. Đơn nhập tay **vẫn bắt buộc** có khách.
- **Ảnh đơn thuốc ETC**: nút **📷 Chụp đơn thuốc** ở quầy (chỉ hiện khi giỏ có thuốc kê
  đơn và đã gắn khách), ảnh nén trong trình duyệt rồi lưu **mã hoá at-rest** trong CSDL.
- **`PUT /prescriptions/{id}/image`** — gắn ảnh (base64, ≤ 2 MB sau giải mã; nhận
  `image/jpeg` · `image/png` · `image/webp`). Quyền `rx.create`.
- **`GET /prescriptions/{id}/image`** — đọc ảnh. Quyền **mới `rx.image.read`**, cấp cho
  Dược sĩ và cấp chuỗi, **không** cho Thu ngân: ảnh mang chẩn đoán. Mỗi lượt đọc ghi một
  dòng audit `RX_IMAGE_VIEWED`.
- **`GET /prescriptions/{id}` nay trả thêm `has_image`** (bool). Nội dung ảnh **không** đi
  kèm phép đọc đơn thường — phải hỏi đích danh đường `/image`.
- Đơn tạo với `source=IMAGE` được phép để trống `dose`/`frequency`/`duration` (nghĩa là
  *chưa phiên từ ảnh*). Đơn nhập tay **vẫn bắt buộc** ba trường này.
- Hai `AuditAction` mới: `RX_IMAGE_ATTACHED`, `RX_IMAGE_VIEWED`.

- **Màn Danh mục thuốc** (`/danh-muc-thuoc`): xem toàn bộ danh mục kèm hoạt chất và giá
  niêm yết; sửa hoạt chất; đặt/đổi giá. Nút sửa chỉ hiện với `catalog.update` (cấp chuỗi).
- **`PUT /drugs/{id}/price`** — đặt lại giá bán niêm yết. Quyền `catalog.update`. Trả
  `422` nếu đổi giá một mã **đã có giá** mà không kèm `reason`, hoặc giá âm/lẻ quá 2 chữ
  số thập phân/trùng giá đang có.
- **`GET /drugs/{id}/price-history`** — lịch sử biến động giá, mới nhất trước. Quyền
  `catalog.read`. `old_price: null` nghĩa là lần **đầu** đặt giá.
- **`GET /drugs` nay trả thêm `ingredients`** trên mỗi thuốc (trường mới, không phá vỡ).
- **Quầy bán hàng: thành tiền · khách đưa · thối lại**, kèm nút mệnh giá nhanh và nút
  "Đủ tiền". Tiền khách đưa **không** gửi lên máy chủ — `payments[].amount` vẫn là tổng
  đơn, nên không có thay đổi API nào cho phần này.
- Hai `AuditAction` mới: `CATALOG_DRUG_PRICE_CHANGED`, `SALE_PRICE_OVERRIDE`.

- **`make ui-gates`** — chạy cả 6 cổng trình duyệt bằng một lệnh, in mã thoát tường minh
  của từng cổng. Tách hai nhóm: **đọc-thuần** (an toàn trên mọi CSDL, mặc định) và **ghi**
  (bán đơn thật — phải xác nhận, chỉ dùng CSDL dùng-một-lần). Kèm `make check-ui` cho lúc
  đóng một mục có động tới giao diện.

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

- 🔴 **MẤT DỮ LIỆU: đơn bán offline bị máy chủ từ chối thì biến mất không dấu vết.**
  `flushQueue` **xoá** đơn khỏi IndexedDB rồi chỉ báo qua một callback mà **không màn nào
  đọc**; state chết khi rời trang. Thu ngân đã thu tiền của khách, đơn không tồn tại ở đâu
  cả, và không ai biết. Nay đơn bị từ chối **chuyển sang bảng `rejectedSales`** (bền vững,
  sống qua F5), hiện thành khối cảnh báo đỏ **trên mọi màn**, với **Thử lại** / **Bỏ hẳn**
  — bỏ hẳn nay là hành động có người bấm, không còn tự xảy ra.

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
