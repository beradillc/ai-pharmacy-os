# Hoá đơn — cửa sổ chi tiết + in đúng một đơn (P3, 2026-08-01)

Lệnh Chain giao 01/08 (`#7`) và khổ in Chain chốt: *"K80 nếu có kết nối, không thì PDF khổ K80"*.

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Xem chi tiết trên điện thoại | dải trượt ở **cuối trang** — phải cuộn hết bảng mới thấy, không gì báo là có thứ để cuộn tới | **cửa sổ** trượt từ đáy lên, có nút **✕** |
| Nút In | `window.print()` trần ⇒ in **cả trang**: bảng danh sách, bộ lọc, phân trang, thanh điều hướng | gọi `GET /sales/{id}/receipt?format=pdf_k80` ⇒ **đúng một đơn** |
| Mẫu in | trang web in ra giấy | mẫu hoá đơn của máy chủ: tên nhà thuốc · địa chỉ · MST · mã đơn · ngày giờ · **người bán** · từng dòng · tổng · khách đưa · **tiền thối** · ô ký |
| Người bán | không có | có (`SalespersonInfoProvider` + adapter ở composition root) |
| Khổ giấy | A5 · A4 | thêm **K80 (80mm)**, dài theo số dòng — mặc định của quầy |

## Trình duyệt KHÔNG dò được máy in nhiệt

Không API nào cho phép, và mọi cách "đoán" đều là đoán. Nên đường mặc định là **PDF rộng
đúng 80mm**, phục vụ được cả hai trường hợp Chain nêu: có máy in nhiệt thì hộp thoại in
chọn đúng nó và ra tờ bill chuẩn; không có thì vẫn in giấy thường hoặc lưu lại. Bản text
K80 thô giữ nguyên (`format=thermal_k80`) cho ai đẩy thẳng vào phần mềm in nhiệt.

## Mẫu in chuyên nghiệp ĐÃ CÓ SẴN — chỉ thiếu tên người bán

Kỷ luật #16 nói grep composition root trước khi code một tính năng "chưa có". Lần này nó
tiết kiệm cả một mục: `render_thermal_k80` và `render_pdf` đã dựng từ Sprint 7 với đầy đủ
thông tin Chain liệt kê. Việc phải làm chỉ là **nối dây** cho giao diện gọi đúng nó, thêm
một dòng người bán, và thêm một khổ giấy.

## Ảnh

| Tệp | Cảnh |
|---|---|
| `*-1-danh-sach.png` | danh sách hoá đơn |
| `*-2-cua-so-chi-tiet.png` | cửa sổ chi tiết, có nút **In** và **✕** |

Hai khổ: 390×844 và 1440×900, `deviceScaleFactor: 2`.

## 🔴 Một lỗi thật mà chỉ cổng trình duyệt bắt được

`problem.detail` của lỗi **422** (FastAPI/Pydantic) KHÔNG phải chuỗi mà là một **mảng
object** `{type, loc, msg, input, ctx}`. Render thẳng vào JSX thì React ném *"Objects are
not valid as a React child"* và **vỡ cả cây** — người dùng mất luôn màn hình đang đứng, chỉ
vì một lỗi lẽ ra chỉ cần hiện một dòng chữ đỏ.

Không cổng nào khác thấy được: `tsc` chiều lòng vì `ProblemDetail` khai `detail: string`, và
**máy chủ thì không đọc khai báo TypeScript của máy khách**. Đã gom thành `thongDiepLoi()`
trong `shared/api/errors.ts`.

## Còn treo cho P5

Ảnh `mobile-390-2` cho thấy bảng nền phía sau bị nén cột ở khổ 390px (cột mã đơn còn một
chữ). Cổng `check-nhin-thay` xanh — đúng, vì bảng cuộn ngang **trong khung riêng của nó**,
không phải cả trang cuộn. Đây là việc của P5 (cân xứng mobile), ghi lại để khỏi quên.
