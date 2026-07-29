# democapture — ảnh chụp giao diện BERAS

Chụp **2026-07-29** bằng một phiên đăng nhập THẬT (`demo@bera.vn`) trên CSDL demo
`demo_v4` — không dựng cảnh, không chèn token bằng tay, không sửa dữ liệu cho đẹp.

| Thư mục | Khổ | Kiểu ảnh |
|---|---|---|
| `mobile/` | 390 × 844 (cỡ iPhone) | đúng **khung nhìn**, để thanh điều hướng dưới nằm đúng chỗ |
| `desktop/` | 1440 × 900 | **trọn trang**, để thấy hết nội dung một màn |

Cả hai chụp ở `deviceScaleFactor: 2` (ảnh nét gấp đôi), `locale: vi-VN`,
`timezone: Asia/Ho_Chi_Minh`.

| Ảnh | Màn |
|---|---|
| `01-dang-nhap` | Đăng nhập |
| `02-tong-quan` | Tổng quan — hành động nhanh · KPI · cần xử lý · biểu đồ · giao dịch |
| `03-ban-hang` | Bán hàng (POS) |
| `04-ton-kho` | Tồn kho theo lô |
| `05-hoa-don` | Hoá đơn |
| `06-khach-hang` | Khách hàng |
| `07-don-mua-hang` | Đơn mua hàng |
| `08-de-xuat-dat-hang` | Đề xuất đặt hàng |
| `09-bao-cao` | Báo cáo |

## Chụp lại

```bash
DB__URL='postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os_demo' make lan
# rồi chạy scripts/capture-screens.mjs (xem PROJECT_STATE §7by)
```

🔴 **Ảnh này KHÔNG thay được việc cầm điện thoại thật.** Trình duyệt không đầu
dựng đúng bố cục nhưng không nói được: chữ có đọc nổi dưới đèn huỳnh quang không,
ngón tay có bấm trúng không, cuộn có mượt không. Bảng kiểm tay: `docs/dev/LAN_MOBILE_TEST.md`.
