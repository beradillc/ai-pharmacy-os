# ADR-0001 · Điểm tích luỹ đọc chéo module, không giữ cột số dư

- **Ngày:** 2026-07-31
- **Trạng thái:** Đã áp dụng (`e48d6e6`)
- **Bối cảnh quyết:** Chain yêu cầu màn Khách hàng có cột "Điểm (đã tích trong năm)"

## Vấn đề

`crm` cần biết mỗi khách đã mua bao nhiêu tiền trong năm. Dữ liệu đó nằm ở `sales`. Hai
module không được import lẫn nhau (contract `module-independence`).

## Các phương án đã cân

| Phương án | Ưu | Nhược — vì sao loại |
|---|---|---|
| **A. Cột số dư trong `customers`** | đọc nhanh, một truy vấn | 🔴 **Lệch khỏi doanh thu thật ngay lần đầu có đơn trả hàng**, và khi lệch thì không ai biết bên nào đúng. Còn phải có việc chạy nền cộng dồn, tức thêm một thứ hỏng được trong im lặng |
| **B. Bảng `loyalty_accruals` riêng** | truy được từng lần cộng | Đúng cho giai đoạn phát quà, nhưng **chưa cần cho việc HIỂN THỊ**, và nó kéo theo migration + phản ứng cross-module `sales`→`crm` đang bị chặn chờ Pháp Lý (Q-1…Q-3) |
| **C. Tính ra từ đơn hàng, đọc qua cổng** ✅ | luôn khớp doanh thu; đổi kỳ = đổi khoảng ngày; không migration, không mất dữ liệu | tốn một phép `GROUP BY` mỗi lần tải danh sách |

## Quyết định

Chọn **C**.

- Cổng đọc `LoyaltyAccrualReader` khai trong **domain của bên DÙNG** (`crm/domain/ports.py`)
  — `crm` nói nó cần gì; `sales` không phải biết `crm` tồn tại.
- Bản cài đặt `SalesLoyaltyAccrualReader` nằm ở **composition root**
  (`api/v1/cross_module.py`), giữ nguyên 18 contract.
- Adapter chạy dưới **danh tính hệ thống**: nhân viên chỉ cần `crm.read`, không phải cấp
  thêm `sales.read` trên toàn bộ đơn hàng chỉ vì một con số tổng. Cùng khuôn với đường
  tên thuốc cấp cho `analytics` (§7bt).
- Hỏi **một lượt cho cả trang** (`accrued_by_customer` nhận danh sách id), không phải một
  lượt mỗi dòng. Có test canh riêng chuyện này — N+1 là lỗi dễ nhất khi thêm một cột.

### Nối muộn, có chủ ý

Thứ tự đăng ký có vòng: `sales` cần `CrmService` (cổng dị ứng Đ-6), `crm` cần `SalesService`
(cột điểm). Một trong hai phải nối muộn. Chọn nối muộn **cái phụ**:
`CrmService.attach_accrual_reader()` gọi sau khi `sales` đã dựng. Thiếu cột điểm thì màn
Khách hàng vẫn chạy; thiếu cổng dị ứng thì mất một cơ chế an toàn.

`self._accrual` mặc định `None` và mọi đường đọc chịu được `None` — quên gọi thì mất một
cột, không sập gì.

## Hệ quả

- ✅ Tương thích ngược: thêm trường vào phản hồi, không đổi trường nào đang có, không migration.
- ✅ Số luôn khớp doanh thu, kể cả sau khi trả hàng.
- ⚠️ Mỗi lần tải danh sách khách tốn thêm một `GROUP BY` trên `sale_lines`. Chấp nhận được
  ở quy mô một nhà thuốc; nếu chậm thì **thêm chỉ mục**, chưa cần đổi sang phương án A.
- 🔴 **Chưa phải chương trình phát quà.** Không có bảng ghi "khách này đã nhận hộp nào
  chưa" ⇒ **không có gì chặn phát trùng**. Hôm nay con số chỉ để *nhìn*. Phát quà thật cần
  phương án B, và B đang chờ Pháp Lý trả lời tích điểm cho thuốc có phải khuyến mại bị cấm
  không. **Đừng đọc ADR này như đã xong tính năng tích điểm.**

## Luật tích điểm ở đúng một chỗ

Rà soát cùng ngày bắt được mốc 2 triệu khai ở **hai ngôn ngữ** (`REWARD_STEP` Python và
`MOC_DOI_QUA` TypeScript). Đã bỏ bản TypeScript: backend trả sẵn `boxes_this_year`, giao
diện chỉ hiện lại. Đổi mốc ở một bên mà bên kia im lặng sai là hỏng theo hướng tệ nhất —
quầy hứa với khách một con số hệ thống không công nhận.
