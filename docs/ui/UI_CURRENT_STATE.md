# UI_CURRENT_STATE — Hiện trạng giao diện BERAS

> PHASE 1 của yêu cầu UI/UX (Chain giao 2026-07-29). **Không sửa một dòng mã nào**
> trong tài liệu này. Mọi con số đo bằng lệnh trên cây làm việc tại commit `03168bc`.

> 🔴 **Chưa nhận được hình ảnh tham khảo.** Yêu cầu nói *"tham khảo hình ảnh tôi
> cung cấp"* nhưng phiên này không có tệp ảnh nào. Toàn bộ phân tích dưới đây dựa
> trên **phần đặc tả chữ** (mục 1–14 của yêu cầu), vốn đã đủ chi tiết để thiết kế.
> Nếu ảnh mang thêm ràng buộc bố cục, gửi lại — sẽ đối chiếu trước khi code.

## 1. Quy mô

| Đo | Giá trị |
|---|---|
| Tệp `.tsx`/`.ts`/`.css` trong `src/` | 39 tệp · **3.831 dòng** |
| Màn hình (route) | **8** — `/login`, `/` (POS), `/bang-dieu-hanh`, `/de-xuat-dat-hang`, `/ton-kho`, `/hoa-don`, `/khach-hang`, `/don-mua-hang` |
| Endpoint backend đang có | **98** (đo từ `openapi.json` của API đang chạy) |
| Component dùng chung | **0** — không có thư mục component nào |
| Test frontend | **0** |
| Thư viện biểu đồ | **không có** |
| Thư viện UI / icon | **không có** |

Phụ thuộc runtime đúng **6**: `next` 16.2.11, `react` 19.2.4, `react-dom`,
`@tanstack/react-query`, `zustand`, `dexie`. Script kiểm: chỉ `eslint`.

## 2. Cấu trúc route hiện tại

```
src/app/
  layout.tsx            ← font + QueryProvider (root)
  login/page.tsx
  (pos)/                ← NHÓM ROUTE RIÊNG, layout riêng, header riêng
    layout.tsx          ← chỉ canh đăng nhập, không có điều hướng
    page.tsx            ← "/" màn bán hàng
  (app)/                ← nhóm quản lý, thanh điều hướng trên cùng
    layout.tsx          ← header + menu ngang, gating theo quyền
    bang-dieu-hanh/ de-xuat-dat-hang/ ton-kho/ hoa-don/ khach-hang/ don-mua-hang/
```

🔴 **Hai hệ điều hướng khác nhau đang cùng tồn tại** — đúng thứ mục 6 của yêu cầu
cấm. `(pos)` có header tự vẽ (`page.module.css`), `(app)` có header khác
(`layout.module.css`). Chúng không dùng chung một component, một token khoảng
cách, hay một mô hình trạng thái active nào.

## 3. Tầng dữ liệu và trạng thái (phần ĐANG CHẠY TỐT — sẽ giữ)

| Lớp | Hiện trạng | Đánh giá |
|---|---|---|
| `shared/api/client.ts` | `apiFetch` mỏng, gắn Bearer, đổi RFC 7807 thành `ApiError` | ✅ Giữ nguyên |
| `shared/api/types.ts` | 230 dòng, viết tay, khớp schema backend | ✅ Giữ |
| `features/*/use-*.ts` | 9 hook react-query, mỗi hook một endpoint, `retry: false` có lý do ghi rõ | ✅ Giữ |
| `features/auth/auth-store.ts` | zustand + hydrate từ localStorage sau mount | ✅ Giữ |
| `features/sales/cart-store.ts` | zustand giỏ hàng | ✅ Giữ |
| `shared/offline/` | dexie + hàng đợi đồng bộ + `useOfflineSync` | ✅ Giữ — đây là tính năng bán được, không phải mã kỹ thuật |
| `shared/format/number.ts` | `formatMoney/formatQty/formatTime` nhận `string` (không ép `number` sớm) | ✅ Giữ |

**Kết luận tầng dữ liệu: không cần đụng tới.** Yêu cầu *"giữ nguyên business logic
đang hoạt động"* thoả được mà không phải cố gắng — nghiệp vụ nằm ở backend, hook chỉ gọi.

## 4. Hệ token hiện tại

`src/styles/tokens.css` — **51 dòng**, 18 biến màu + 2 biến font + 1 radius.

| Nhóm | Có | Thiếu |
|---|---|---|
| Màu | 18 biến (nền, chữ, accent, leaf, brown, warning, success, danger, border) | **thang màu** (mỗi màu chỉ 1 bậc), màu biểu đồ, màu focus |
| Khoảng cách | **0 biến** — mọi `padding`/`gap` là số px viết thẳng | toàn bộ thang spacing |
| Bo góc | 1 biến `--beras-radius: 10px` | thang radius (sm/md/lg/pill) |
| Đổ bóng | **0 biến** — và **0 lần dùng `box-shadow`** trong toàn bộ `src/` | toàn bộ thang shadow |
| Chữ | 2 biến font-family | **0 biến** cỡ chữ / độ đậm / line-height |
| Chuyển động | **0 biến** | toàn bộ |

Vi phạm "không hard-code màu": đúng **2 chỗ** (`color: #fff` ở
`de-xuat-dat-hang/page.module.css:36` và `shared/ui/screen.module.css:86`). Kỷ luật
màu hiện tại **tốt hơn mức trung bình** — chỉ 2 lỗi trên 3.831 dòng.

## 5. Đo theo từng mục yêu cầu

| # | Mục | Hiện trạng đo được |
|---|---|---|
| 1 | Information architecture | ❌ Bảng điều hành hiện là: 4 ô KPI → bảng "thuốc bán chạy". Không có quick action, không có alert center, không có chart, không có giao dịch gần đây |
| 2 | Quick actions | ❌ Không tồn tại |
| 3 | KPI card | ⚠️ Có 4 ô, nhưng là component **cục bộ** trong `bang-dieu-hanh/page.tsx`, không tái dùng được, không có `trend`/`comparison` |
| 4 | Compliance center | ❌ Không tồn tại. Backend có **12 endpoint** `compliance` — 0 màn |
| 5 | AI assist | ❌ Không tồn tại. Backend có **5 endpoint** `clinical` (gợi ý + accept) — 0 màn |
| 6 | Navigation | ⚠️ Menu ngang desktop; **không có bottom nav**; hai hệ điều hướng rời nhau (xem §2) |
| 7 | Transitions | ❌ **0 lần** xuất hiện `transition`/`animation` trong toàn bộ CSS |
| 8 | Design system | ⚠️ Có token màu, thiếu 5/6 nhóm token (xem §4) |
| 9 | Components | ❌ 0/17 component yêu cầu tồn tại |
| 10 | Responsive | ⚠️ Không khai báo `viewport` (Next tự phát bản mặc định — **xem đính chính §6.1**, kết luận đầu của tôi sai). Chỉ **3 media query**, đều dạng `width <=` — desktop-first vá xuống, ngược hướng yêu cầu |
| 11 | Accessibility | ⚠️ Có `aria-label` ở input lọc, `role="alert"` ở khối lỗi, `aria-pressed` ở nút bật/tắt. **Không** có focus state tự đặt, **không** có `prefers-reduced-motion`, trạng thái chip hiện **chỉ bằng màu + chữ** (chữ có → không vi phạm "chỉ dùng màu") |
| 12 | Performance | ⚠️ Có skeleton ở 6 màn; react-query có `staleTime`. Chưa có lazy-load (chưa có chart để lazy) |
| 13 | Security | ✅ **Đã đúng** — UI chỉ ẩn/hiện menu theo `session.permissions`; mọi endpoint đều kiểm quyền ở service. Không có đường nào UI tự quyết quyền |

## 6. Ba phát hiện — và một trong ba đã bị chính tôi bác bỏ

### 6.1 ~~Không khai báo `viewport` — mobile-first hiện đang KHÔNG chạy~~ → **ĐÍNH CHÍNH**

> 🔴 **Kết luận ban đầu của tôi ở mục này SAI. Đính chính 2026-07-29, cùng ngày.**

**Bản đầu viết:** *"Next 16 không tự chèn thẻ viewport ⇒ mọi media query
`width <= 720px` chưa từng kích hoạt trên điện thoại thật ⇒ mọi kết luận 'đã
responsive' trước hôm nay đều không có căn cứ."*

**Đo lại bằng cách gỡ khai báo rồi build thật** (kỷ luật #14 — bắt buộc thấy đỏ vì
đúng lý do trước khi tin một cổng mới):

```
# gỡ export const viewport → npm run build → đọc .next/server/app/login.html
<meta name="viewport" content="width=device-width, initial-scale=1"/>   ← VẪN CÓ
```

**Next 16 CÓ phát thẻ viewport mặc định.** Mobile chưa bao giờ hỏng, media query
vẫn kích hoạt bình thường trên điện thoại thật.

**Khác biệt thật mà khai báo mới tạo ra** (đo bằng cách so hai bản build):

| | Không khai báo | Có khai báo |
|---|---|---|
| `viewport` | `width=device-width, initial-scale=1` | `…, viewport-fit=cover` |
| `theme-color` | không có | `#1f3d2b` |

Tức là nó thêm **hỗ trợ vùng an toàn iPhone** (`env(safe-area-inset-*)` chỉ khác 0
khi có `viewport-fit=cover` — cần cho bottom nav) và **màu thanh trạng thái
Android**. Hai thứ có ích, nhưng là *cải thiện*, không phải *vá lỗi*.

**Vì sao chép nguyên lỗi này lại đây thay vì lặng lẽ xoá:** tôi đã báo cáo với
Chain rằng mọi kết luận responsive trước đây đều vô căn cứ. Câu đó sai, và nó là
loại sai làm người đọc đánh giá lại chất lượng của cả một sprint. Đúng họ lỗi mà
kiểm toán 26/07 gọi tên — **văn bản nói sai về mã** — chỉ khác là lần này nó nằm
trong chính báo cáo kiểm toán.

### 6.2 Vùng chạm nhỏ hơn 44px ở gần như mọi nút

Nút phổ biến nhất dùng `padding: 6px 12px` + `font-size: 14px` ⇒ cao khoảng
**30–32px**. Yêu cầu tối thiểu 44px. Đếm được **≥10 khai báo** dưới ngưỡng ở
`(pos)/page.module.css`, `(app)/layout.module.css`, `bang-dieu-hanh`, `screen.module.css`.

### 6.3 Không có biểu đồ, và bảng màu thương hiệu KHÔNG dùng được cho biểu đồ nhiều chuỗi

"Doanh thu" hiện là các thanh CSS ngang trong bảng thuốc bán chạy, không phải chart
theo thời gian. Khi làm `RevenueChart` thật:

Đã **chạy trình kiểm màu** trên 5 màu thương hiệu
(`#5b8c51,#2f7a6b,#b98a2d,#a8452f,#6b4a32`) → **FAIL 3/6 phép kiểm**: hai màu tụt
dưới sàn chroma (đọc ra xám), cặp nâu↔đỏ trầm ΔE 3,9 với người mù màu protan, cặp
xanh lá↔xanh bạc hà ΔE 8,7 **ngay cả với mắt thường**.

Kết luận: màu nhận diện dùng cho *chrome giao diện* thì tốt, dùng làm *bảng màu
chuỗi dữ liệu* thì không. Cách xử lý ở `DESIGN_SYSTEM.md` §4.

## 7. Cái gì đang tốt — đừng viết lại

1. **Tầng dữ liệu** (§3) — không đụng.
2. **Kỷ luật token màu** — 2 lỗi hard-code trên 3.831 dòng.
3. **Gating theo quyền, không theo tên vai** — `(app)/layout.tsx` lọc menu bằng
   `session.permissions`. Đúng nguyên tắc, giữ nguyên khi chuyển sang sidebar/bottom nav.
4. **Ghi chú lý do trong mã** — hầu hết quyết định giao diện đều có comment giải
   thích *vì sao*. Tài sản, không phải rác; giữ khi refactor.
5. **`screen.module.css`** (247 dòng, Sprint 10) — đã là một hệ bảng/chip/phân
   trang nhất quán cho 4 màn. Đây là **hạt giống** của design system, không phải thứ vứt đi.
