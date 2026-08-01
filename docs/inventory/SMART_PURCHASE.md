# Nhập hàng thông minh (BERAS V2 Phase 8 — multi-supplier)

> Trạng thái: **HOÃN**, GĐ chốt 2026-08-01 dưới uỷ quyền của Chain. Tệp này ghi *vì sao
> hoãn* và *cần gì khi mở lại* — để lần sau không phải cân nhắc lại từ đầu.

## Vì sao hoãn

Multi-supplier giải bài toán **so giá giữa nhiều nhà cung cấp cho cùng một mặt hàng**.
BeraLLC hiện là **một nhà thuốc**, và mọi lệnh Chain giao ngày 01/08 đều là việc ở quầy:
bán được đơn ETC, in hoá đơn, cửa sổ trên điện thoại, cỡ chữ. Không lệnh nào đụng tới mua
hàng.

Nguyên tắc đã dùng suốt sáu phiên: **sửa cái đang gãy trước cái chưa có**. Phase 8 không
gãy — nó chưa tồn tại, và chưa ai cần nó.

## Cần gì khi mở lại

| Việc | Ghi chú |
|---|---|
| `supplier_prices` — giá theo (nhà cung cấp, mặt hàng, thời điểm) | Giá đổi theo đợt; lưu một giá hiện tại là mất lịch sử để đối chiếu |
| Chọn NCC khi tạo PO | Hiện `procurement` đã có `supplier`, thiếu phần **so sánh** |
| Quy tắc chọn | 🔴 **Quyết định nghiệp vụ của Chain, không phải kỹ thuật**: rẻ nhất? giao nhanh nhất? đang nợ ai ít nhất? Đừng đoán |

## Ràng buộc phải giữ

- Không đổi hợp đồng `POST /purchase-orders` đang chạy (kỷ luật #17).
- Giá vốn vào bình quân gia quyền — đây là **quyết định kế toán**, cần Trợ lý Kế toán rà
  trước khi chạy thật (cùng lý do với quyết định #4 ở §7cu).
