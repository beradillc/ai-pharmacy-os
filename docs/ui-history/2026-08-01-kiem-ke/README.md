# Kiểm kê theo ô (2026-08-01)

Màn `/kiem-ke` · BERAS V2 Phase 11. Thiết kế: `docs/inventory/CYCLE_COUNT.md`.

## 🔴 Ảnh bắt được lỗi cổng Playwright bỏ qua

| | Ảnh |
|---|---|
| Trước | `truoc-mobile-cot-chenh-bi-cat.png` |
| Sau | `sau-mobile-the.png` |

Trên 390×844, cột **Chênh** — đúng cột là lý do màn này tồn tại — nằm ngoài rìa màn hình.
Cổng vẫn xanh vì `innerText` đọc được cả phần tràn ra ngoài khung nhìn.

Cùng họ với ca *"cột định danh trượt khỏi màn hình ở 5/5 bảng"* ngày 29/07: chỉ ảnh thấy,
phép đo không thấy. Sửa: bảng → **thẻ** dưới 720px, dùng lại đúng khuôn đã đo ở
`danh-muc-thuoc` (lưới hai cột nhãn/giá trị, đệm nhỏ — bản đầu ở màn đó cho mỗi ô một hàng
flex riêng và trang phình từ 3,5 lên 12,5 màn).

## Ảnh nghiệm thu

- `mobile-da-duyet.png` — 390×844: chênh **−3** đỏ, và cảnh báo **"(cùng một người)"** khi
  người đếm tự duyệt phiếu mình
- `desktop-cho-duyet.png` — 1440×900, trạng thái Chờ duyệt
