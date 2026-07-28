# DESIGN_SYSTEM — Token BERAS

> PHASE 2. Đây là **đặc tả**, chưa phải mã. Khi code, toàn bộ mục dưới đây vào
> `src/styles/tokens.css` (mở rộng tệp đã có, **không** thay giá trị màu đang dùng).

Nguyên tắc: **component không được viết giá trị thẳng.** Mọi màu, khoảng cách, bo
góc, bóng, cỡ chữ, thời lượng đều tham chiếu biến.

## 1. Màu — giữ nguyên bảng đã chốt, bổ sung bậc còn thiếu

Bảng màu Eco-Tech (`tokens.css` hiện tại) **không đổi một giá trị nào** — nó do
Chain chốt 2026-07-28 từ gói bàn giao thiết kế. Chỉ **thêm** các bậc mà hệ thống
đang thiếu:

| Token mới | Giá trị | Dùng để |
|---|---|---|
| `--beras-leaf-soft` | `#e6efe3` | nền chip/hover của màu chính |
| `--beras-warning-bg` | `#fbf3e0` | nền cảnh báo (đã có `--beras-danger-bg`, thiếu bản vàng) |
| `--beras-success-bg` | `#e4f0ed` | nền trạng thái tốt |
| `--beras-focus` | `#0f6e9c` | **viền focus bàn phím** — cố ý KHÁC mọi màu trạng thái, để vòng focus không bị đọc nhầm thành "lỗi"/"ok" |
| `--beras-overlay` | `rgb(35 41 32 / 45%)` | nền mờ sau modal / bottom sheet |

## 2. Khoảng cách — thang 4px

| Token | px | Dùng |
|---|---|---|
| `--space-1` | 4 | khe giữa nhãn và giá trị |
| `--space-2` | 8 | trong một chip, giữa icon và chữ |
| `--space-3` | 12 | padding ô nhỏ |
| `--space-4` | 16 | padding thẻ, khe giữa thẻ |
| `--space-5` | 20 | padding trang (mobile) |
| `--space-6` | 24 | khe giữa các khối |
| `--space-8` | 32 | khe giữa các mục lớn |
| `--space-12` | 48 | đệm đáy trang trên mobile (chừa chỗ bottom nav) |

## 3. Bo góc · bóng · vùng chạm

| Token | Giá trị | Ghi chú |
|---|---|---|
| `--radius-sm` | 8px | chip, nút nhỏ |
| `--radius-md` | 10px | = `--beras-radius` hiện tại, giữ nguyên |
| `--radius-lg` | 16px | thẻ KPI, bottom sheet |
| `--radius-pill` | 999px | chip trạng thái |
| `--shadow-1` | `0 1px 2px rgb(35 41 32 / 6%)` | thẻ nghỉ |
| `--shadow-2` | `0 4px 12px rgb(35 41 32 / 10%)` | thẻ nổi, popover |
| `--shadow-3` | `0 -4px 20px rgb(35 41 32 / 14%)` | bottom sheet, bottom nav |
| `--touch-min` | **44px** | 🔴 chiều cao tối thiểu MỌI phần tử bấm được |

`--touch-min` là token chứ không phải quy ước ghi trong tài liệu, vì quy ước ghi
trong tài liệu chính là thứ đã trôi mất ở 10 chỗ hiện tại.

## 4. Màu biểu đồ — ĐÃ ĐO, không ước lượng

### 4.1 Vì sao không dùng thẳng màu thương hiệu

Chạy trình kiểm bảng màu trên 5 màu Eco-Tech
(`#5b8c51,#2f7a6b,#b98a2d,#a8452f,#6b4a32`) — **FAIL 3/6 phép kiểm**:

```
[FAIL] Chroma floor        #2f7a6b (0.078) · #6b4a32 (0.058) → đọc ra xám
[FAIL] CVD separation      #6b4a32 ↔ #a8452f  ΔE 3.9 (protan)
[FAIL] Normal-vision floor #2f7a6b ↔ #5b8c51  ΔE 8.7 — khó phân biệt kể cả mắt thường
```

Màu nhận diện tối ưu cho *chrome giao diện* (nền kem, nav xanh rừng). Chuỗi dữ liệu
là bài toán khác: cần tách bậc sáng, đủ chroma, và giữ khoảng cách dưới mắt mù màu.

### 4.2 Bảng màu chuỗi dữ liệu — 5 bậc, ĐÃ PASS 6/6

```
--chart-1: #5b8c51   (lá — giữ đúng màu chính thương hiệu, slot 1)
--chart-2: #0f6e9c   (lam)
--chart-3: #b98a2d   (nghệ)
--chart-4: #a8452f   (đỏ trầm)
--chart-5: #6a5aa8   (tím)
```

```
[PASS] Lightness band      cả 5 trong L 0.43–0.77
[PASS] Chroma floor        cả 5 >= 0.1
[PASS] CVD separation      xấu nhất #a8452f↔#b98a2d ΔE 14.6 (deutan) · tritan 7.7
[PASS] Normal-vision floor xấu nhất #0f6e9c↔#5b8c51 ΔE 17.6
[PASS] Contrast vs surface cả 5 >= 3:1
```

⚠️ Tritan 7,7 nằm trong dải sàn 6–8 ⇒ **chỉ hợp lệ khi có mã hoá phụ**: luôn có chú
giải, và ≤4 chuỗi thì nhãn trực tiếp. Đây là ràng buộc bắt buộc, không phải khuyến nghị.

**Thứ tự gán cố định, không xoay vòng.** Chuỗi thứ 6 trở đi ⇒ gộp "Khác" hoặc tách
biểu đồ nhỏ, tuyệt đối không sinh màu mới.

### 4.3 Biểu đồ doanh thu dùng gì

Doanh thu theo ngày là **một chuỗi** ⇒ **không cần bảng phân loại**: dùng
`--chart-1` cho đường/vùng, không chú giải (tiêu đề đã nói nó là gì).

- **Dạng:** line + vùng tô nhạt, không phải cột — dữ liệu liên tục theo thời gian.
- Đường 2px, điểm ≥8px, chỉ hiện điểm khi hover.
- Nhãn trực tiếp: chỉ **cao nhất / thấp nhất / hôm nay** — không phải mọi điểm.
- Lưới ngang mờ (`--beras-border`), trục không kẻ đậm.
- **Luôn có hover crosshair + tooltip** (mặc định, không phải tuỳ chọn).
- **Không bao giờ hai trục y.** Doanh thu và số đơn là hai biểu đồ, hoặc hai KPI.

### 4.4 Màu trạng thái — RIÊNG, không trộn vào chuỗi dữ liệu

`--beras-success` · `--beras-warning` · `--beras-danger` chỉ dùng cho trạng thái
(tốt / cảnh báo / nguy). **Không** được dùng làm "chuỗi thứ 4". Luôn đi kèm **icon +
chữ**, không bao giờ chỉ màu.

## 5. Chữ

| Token | Giá trị | Dùng |
|---|---|---|
| `--text-xs` | 12px / 1.4 | nhãn KPI viết hoa, chú thích |
| `--text-sm` | 14px / 1.45 | phụ đề, ô bảng phụ |
| `--text-base` | 15px / 1.5 | chữ thân, ô bảng |
| `--text-lg` | 18px / 1.35 | tiêu đề thẻ |
| `--text-xl` | 22px / 1.3 | tiêu đề màn |
| `--text-kpi` | 26px / 1.2 | số KPI (mono) |
| `--text-hero` | 32px / 1.15 | số doanh thu hôm nay trên dashboard |
| `--weight-regular/medium/semibold/bold` | 400/500/600/700 | |

Chữ số tiền/lượng/mã lô **luôn** `--beras-font-mono` — để cột số so được bằng mắt.

## 6. Chuyển động

| Token | Giá trị |
|---|---|
| `--motion-fast` | 150ms |
| `--motion-base` | 200ms |
| `--motion-slow` | 300ms |
| `--ease-out` | `cubic-bezier(0.2, 0, 0, 1)` |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` |

| Ngữ cảnh | Hiệu ứng | Thời lượng |
|---|---|---|
| Chuyển trang | fade + trượt lên 8px | `--motion-base` |
| Vào chi tiết | trượt trái | `--motion-base` |
| Modal | fade + scale 0.98→1 | `--motion-fast` |
| Bottom sheet | trượt lên | `--motion-slow` |
| Thành công | scale 1→1.04→1 + fade | `--motion-fast` |
| Skeleton | KHÔNG nhấp nháy | — |

**Bắt buộc, một khối, đặt ở `globals.css`:**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 1ms !important;
    scroll-behavior: auto !important;
  }
}
```

Dùng `1ms` chứ không `0s`: `transitionend` vẫn bắn, nên mã nào chờ sự kiện đó không
bị treo — `0s` ở một số trình duyệt không bắn sự kiện.

## 7. Điểm ngắt

| Tên | Từ | Bố cục |
|---|---|---|
| `--bp-sm` | 360px | 1 cột · quick action 4 cột · **bottom nav** |
| `--bp-md` | 600px | 2 cột KPI |
| `--bp-lg` | 900px | **sidebar** thay bottom nav · 4 cột KPI |
| `--bp-xl` | 1280px | nội dung tối đa 1120px, canh giữa |

Viết `@media (width >= …)` — **mobile-first**, ngược với 3 media query hiện có
(đều là `width <=`). Không trộn hai chiều trong cùng một tệp.

## 8. Ranh giới tự đặt cho hệ thống này

1. **Không thêm thư viện UI** (MUI/Chakra/shadcn). 17 component là lượng vừa sức
   viết tay; một thư viện kéo theo hệ token thứ hai cạnh tranh với hệ này.
2. **Chart tự vẽ bằng SVG, không kéo Recharts/Chart.js** — biểu đồ duy nhất cần là
   một đường theo thời gian. Một thư viện chart nặng hơn toàn bộ `src/` hiện tại.
   Nếu sau này cần 3 loại chart trở lên, mở lại quyết định này.
3. **Chưa làm dark mode.** Yêu cầu không đòi. Ghi ra để không ai tưởng đã có; khi
   làm thì phải **chọn lại từng bậc** và chạy lại trình kiểm với nền tối, không lật màu tự động.
