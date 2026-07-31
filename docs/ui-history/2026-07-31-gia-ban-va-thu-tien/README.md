# Giá bán niêm yết & thu tiền ở quầy — 2026-07-31

Chain giao: *"rà soát cách quy định giá bán ra. Áp dụng cho chủ chuỗi cửa hàng mới quy
định được. Ghi nhận lại biến động giá mỗi lần điều chỉnh. Ngoài ra triển khai phần thành
tiền, nhận tiền, tiền thối lại… như một phần mềm bán hàng chuyên nghiệp."*

Ảnh Firefox thật qua LAN IP, CSDL `nt650v2`. Sinh lại:
`node scripts/check-danh-muc-thuoc.mjs` · `node scripts/check-pos-tien.mjs`

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Đổi giá một thuốc đã tạo | **Không có đường nào** — phải sửa thẳng CSDL | Nút **Giá** ở màn Danh mục thuốc |
| Biết giá cũ là bao nhiêu | Không — đổi giá là ghi đè | Bảng lịch sử ngay dưới ô nhập, mới nhất trước |
| Quầy bán lệch giá niêm yết | Bán được, **không ai biết** | Bán được, **phải ghi lý do**, vào sổ audit |
| Tiền khách đưa / thối lại | Không có | Nút mệnh giá · **Đủ tiền** · ô Khách đưa · dòng **Thối lại** |

## Đo được

| | desktop | mobile |
|---|---|---|
| Thuốc hiện giá niêm yết | 36/36 | 36/36 |
| Giỏ rỗng **không** hiện bảng tiền | ✓ | ✓ |
| Thành tiền 2.200 · khách đưa 200.000 ⇒ thối lại | **197.800** ✓ | 197.800 ✓ |
| Nút "Đủ tiền" ⇒ thối lại | **0** ✓ | 0 ✓ |
| Cuộn ngang | không | không |
| Lỗi JS | 0 | 0 |

## Quyết định giao diện

- **Tiền thối to hơn tổng tiền.** Nó là con số thu ngân đọc *trong lúc đang đếm tiền trong
  tay*; tổng tiền thì khách đã nhìn trên màn hình từ trước.
- **Thiếu tiền hiện số ÂM, không hiện 0.** Một số 0 ở đây đọc y hệt *"vừa đủ"*.
- **Nút "Đủ tiền" tách riêng** khỏi các mệnh giá: khách đưa đúng số tiền là ca phổ biến
  nhất, và nó không cộng dồn được từ mệnh giá.
- **Ô lý do lệch giá đặt NGAY TRÊN nút Thanh toán**, cùng chỗ và cùng lý do với ô lý do dị
  ứng: nó nằm trên đường tay thu ngân đi tới nút.
- **Lịch sử giá nằm ngay dưới ô nhập giá**, không ở trang khác: *"có nên đổi giá không"* và
  *"lần trước đổi vì sao"* là cùng một câu hỏi, hỏi cùng một lúc.

## 🔴 Tiền khách đưa KHÔNG được gửi lên máy chủ

`SaleOrder.complete()` đòi `paid_total >= subtotal` — trả **thừa được chấp nhận, không báo
gì**. Gửi tiền khách đưa vào `payments[].amount` sẽ thổi `paid_total` lên 200.000 cho một
đơn 2.200 và in sai hoá đơn. Thối lại là **phép tính của quầy**; `payments[].amount` giữ
nguyên bằng tổng đơn.

Nhờ vậy lượt này **không đổi một dòng hợp đồng API nào** cho phần tiền.

## Cổng đã chạy

`make ui-gates` **7/9 xanh**, thêm `check-pos-tien`. Hai cổng đỏ (`check-customers`,
`check-receive-flow`) là **lỗi phép đo đã chứng minh ở commit 78d0fec**: WebKit huỷ request
prefetch `_rsc` dưới `next start` và báo bằng thông điệp đọc y hệt lỗi CORS. Đo trên cây đã
commit cũng đỏ y hệt.

Kỷ luật #14 — cả hai cổng mới đã thấy đỏ vì lý do đúng:

| Đột biến | Kết quả |
|---|---|
| `thoiLai = soTienNhan` (bỏ trừ tổng) | `MUTANT_GATE_EXIT=1` — *thối lại hiện 200000 · phải là 197800* |
| `countPriceDeviations` so bằng **chuỗi** | `MUTANT_VITEST_EXIT=1` — bắt đúng ca `"12000"` vs `"12000.00"` |
