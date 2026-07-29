# democapture-warm — ảnh chụp giao diện **BERAS Warm**

Cùng 10 màn, cùng dữ liệu, cùng khổ máy như `democapture/` (Classic) — khác **duy
nhất** ở theme. Đặt cạnh nhau để so là thấy ngay hệ theme đổi cái gì và **không**
đổi cái gì (bố cục, khoảng cách, cỡ chữ, vùng chạm: y hệt).

Chụp bằng cách gieo `localStorage["beras.theme"] = "warm"` trước khi mở trang —
đúng trạng thái của người đã chọn theme ở lần dùng trước.

```bash
THEME=warm OUT_DIR=./democapture-warm node scripts/capture-screens.mjs
```
