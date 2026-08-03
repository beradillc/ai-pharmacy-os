# V3-2 — Tạo đơn mua hàng thủ công (2026-08-04)

| | Trước | Sau |
|---|---|---|
| Tạo đơn mua | **Không có nút nào.** `POST /purchase-orders` có sẵn ở backend, không dòng frontend nào gọi | Nút *"+ Tạo đơn mua"* ở `/don-mua-hang` |
| Đường duy nhất đẻ ra đơn | Đề xuất đặt hàng → *Tạo đơn nháp* | Thêm đường thủ công, giữ nguyên đường cũ |
| Ca trình dược viên chào tận quầy | **Không ghi được** — ca đó không có đề xuất nào | Ghi được |
| `DRAFT → ORDERED` | không có nút | Nút *"Đặt đơn"* trên dòng đơn nháp |

**Lưu ở trạng thái NHÁP, không tự đặt.** Tạo đơn là soạn thảo; `ORDERED` là lúc nó thành một
**khoản phải trả thật**, và backend ghi audit `PROCUREMENT_PO_ORDERED` đúng ở mốc đó. Gộp hai
bước sẽ biến mỗi lần gõ thử thành một cam kết tài chính.

## Cổng

```
V32_EXIT=0   9 mệnh đề trên trình duyệt thật, LAN IP, khổ 390px
             nút trong khung nhìn (x=16 w=136) · không cuộn ngang · tạm tính 24×3.500=84.000
             · cửa sổ đóng · lọc về Nháp · có nút Đặt đơn
             · 🔴 đơn có ĐÚNG HÀNG bên trong (tổng do MÁY CHỦ tính)
TSC=0  LINT=0  VITEST=0 (125)  BUILD=0
```

🔴 **Đột biến bắt được một cổng hờ, và đây là bài học đáng giữ.**
Bản đầu của cổng khẳng định: cửa sổ đóng · danh sách về Nháp · có nút Đặt đơn.
Đột biến gửi `items: []` (đơn **rỗng**) ⇒ `MUTANT9_EXIT=0` — **cổng sống sót**, xanh trọn vẹn
cho một đơn không có mặt hàng nào. Ba mệnh đề ấy chứng minh *"một đơn đã được tạo"*, **không**
chứng minh *"đơn có đúng hàng"*.

Thêm mệnh đề đọc **tổng tiền do máy chủ tính** từ các dòng đã lưu — vế độc lập với con số
"tạm tính" mà trình duyệt tự cộng trước lúc gửi (kỷ luật #23). Chạy lại: `MUTANT9b_EXIT=1`,
dòng đơn hiện `0 mặt hàng · chưa chốt giá`.

## Dọn sau khi thử (kỷ luật #7)

Xoá `PO-0021` · `PO-0022` và 3 mã `Thuốc thử V31…` khỏi `qt650`. Kiểm trước khi xoá: cả ba mã
**0 lô tồn kho · 0 dòng bán · 0 dòng đơn mua**. Xác nhận sau khi xoá: còn `0 | 0`.
