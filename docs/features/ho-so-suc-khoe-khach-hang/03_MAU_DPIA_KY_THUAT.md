# Mẫu DPIA (Đánh giá tác động xử lý DLCN) — phần kỹ thuật

> Bước 4 mục 5 của `01_DECISIONS.md`, duyệt Q6: BeraLLC cung cấp **mẫu + endpoint trích xuất
> metadata**, tenant tự nộp cho Bộ Công an trong 60 ngày kể từ khi bắt đầu xử lý dữ liệu thật
> (Luật 91/2025 Điều 21). BeraLLC **không nộp thay**.
>
> **Nguồn dữ liệu của mọi bảng dưới đây:** `GET /api/v1/privacy/processing-record`
> (`core/privacy.py::processing_record()`), quyền `privacy.dpia.read`. Không chép tay — gọi API
> lấy bản mới nhất trước khi nộp, vì code là nguồn sự thật, tài liệu này chỉ là khung trình bày.
>
> **Phần KHÔNG có ở đây, tenant phải tự viết cùng luật sư:** danh tính bên kiểm soát dữ liệu, đánh
> giá tính cần thiết/tương xứng của việc xử lý, biện pháp tổ chức riêng của từng nhà thuốc (đào tạo
> nhân viên, chính sách nội bộ...). Đánh dấu `[TENANT + LUẬT SƯ ĐIỀN]` bên dưới.

---

## A. Thông tin bên kiểm soát dữ liệu — `[TENANT + LUẬT SƯ ĐIỀN]`

| Mục | Nội dung |
|---|---|
| Tên pháp nhân / hộ kinh doanh nhà thuốc | _[điền]_ |
| Mã số thuế / giấy phép kinh doanh dược | _[điền]_ |
| Người chịu trách nhiệm bảo vệ dữ liệu (nếu có) | _[điền]_ |
| Địa chỉ, thông tin liên hệ | _[điền]_ |

## B. Mô tả việc xử lý dữ liệu — lấy từ `processing_record().categories`

| Loại dữ liệu | Ví dụ | Nhạy cảm? | Mục đích | Căn cứ pháp lý | Quyền hạn kiểm soát truy cập | Thời hạn lưu |
|---|---|:---:|---|---|---|---|
| _(điền từ field `name`)_ | _(field `examples`)_ | _(field `sensitive`)_ | _(field `purposes`)_ | _(field `legal_basis`)_ | _(field `guarded_by`)_ | _(field `retention`)_ |

Tại thời điểm soạn tài liệu này, hệ thống có đúng 2 nhóm: dữ liệu định danh cơ bản (không nhạy
cảm) và dữ liệu sức khỏe (nhạy cảm — dị ứng, bệnh nền, lịch sử dùng thuốc). Chi tiết đầy đủ: gọi
API, không chép số liệu tĩnh vào đây vì sẽ lệch khi code đổi.

## C. Đánh giá tính cần thiết và tương xứng — `[TENANT + LUẬT SƯ ĐIỀN]`

Vì sao cần thu thập dữ liệu sức khỏe thay vì chỉ dữ liệu cơ bản? Có phương án nào ít xâm phạm hơn
đạt cùng mục đích (cảnh báo an toàn dược lý) không? Đây là đánh giá thuộc trách nhiệm bên kiểm
soát dữ liệu (nhà thuốc), không phải nhà cung cấp phần mềm — BeraLLC chỉ cung cấp cơ chế kỹ thuật
để *thực hiện* quyết định đã đánh giá, không đánh giá thay.

## D. Rủi ro và biện pháp giảm thiểu — phần kỹ thuật đã có sẵn

| Rủi ro | Biện pháp kỹ thuật đã triển khai | Nguồn |
|---|---|---|
| Nhân viên không đủ thẩm quyền đọc dữ liệu sức khỏe | RBAC tách `crm.read` / `crm.sensitive.read`, thu ngân không có quyền đọc nhạy cảm | `iam/domain/system_roles.py` |
| Không truy vết được ai đã xem hồ sơ bệnh | `audit_logs` append-only, action `CUSTOMER_SENSITIVE_READ`/`_WRITE`/`_AUTO_CHECK` | `core/audit`, field `audited_actions` |
| Rò rỉ nội dung nhạy cảm qua chính nhật ký truy vết | `audit_logs.context` chỉ ghi metadata (loại trường, IP), không chép nội dung dữ liệu | field `audit_storage` |
| Xử lý ngoài mục đích ban đầu khi bán hàng | Danh sách khách hàng (`GET /customers`) không bao giờ trả dữ liệu sức khỏe, kể cả cho vai có quyền | Quyết định #8, §7n `PROJECT_STATE.md` |
| Chuyển dữ liệu ra nước ngoài không kiểm soát | AI lâm sàng chỉ gửi tên hoạt chất, không gửi định danh khách hàng | field `cross_border_transfers` |
| Chủ thể không thực hiện được quyền của mình | 4 endpoint quyền chủ thể: xem, xuất, rút đồng ý, khử nhận dạng | field `subject_rights` |

## E. Khoảng trống đã biết (không giấu) — lấy từ `known_gaps`

Tại thời điểm soạn tài liệu này, `processing_record().known_gaps` liệt kê: chưa có văn bản điều
khoản thật cho `terms_version`, chưa có luồng người đại diện cho bệnh nhân trẻ em (Luật 91 Điều
24), chưa có xóa tự động khi hết hạn lưu trữ, `client_ip` có thể là IP của reverse proxy nếu triển
khai sau proxy. Gọi API để lấy danh sách mới nhất trước khi nộp — danh sách này có thể thay đổi.

## F. Biện pháp tổ chức riêng của nhà thuốc — `[TENANT ĐIỀN]`

Đào tạo nhân viên về xử lý dữ liệu sức khỏe, quy trình nội bộ khi có yêu cầu của chủ thể dữ liệu,
quy trình xử lý sự cố lộ dữ liệu (Luật 91 Điều 23 — báo cáo trong 72 giờ). Phần này khác nhau theo
từng nhà thuốc, phần mềm không thể điền thay.

---

**Ghi chú cho lần xem lại:** khi luật sư hoàn thiện phần pháp lý (mục A, C, F) và rà lại quyết
định Q2 (`01_DECISIONS.md`), hợp nhất bản nháp đó với bản kỹ thuật này thành 1 tài liệu nộp được.
