# THEME_AUDIT — Hiện trạng trước khi thêm hệ theme

> 2026-07-29. Đo bằng lệnh trên cây làm việc, **trước** khi sửa gì.

## 1. Kiến trúc

| Hạng mục | Thực tế |
|---|---|
| Framework | Next.js **16.2.11** (App Router, Turbopack) · React 19.2.4 |
| Thư viện component | **không có** — mọi thứ viết tay |
| CSS | **CSS Modules** thuần — 18 tệp `*.module.css` |
| Tailwind / SCSS | **không có** (0 tệp `.scss`, không `tailwind.config`) |
| Design tokens | **69 biến CSS** trong `src/styles/tokens.css`, khai dưới `:root` |
| Nơi token được đọc | **61 tên biến** khác nhau, dùng khắp 18 tệp CSS |
| Dark mode | **không có** |
| Theme system | **không có** |
| Màu viết thẳng ngoài `tokens.css` | **0** (đã dọn ở đợt W1–W3) |

## 2. Kết luận quyết định kiến trúc

Dự án **đã ở đúng hình dạng để thêm theme mà không đụng component**: mọi màu,
khoảng cách, bo góc, bóng đều đi qua `var(--*)`. Thêm một theme = ghi đè giá trị
biến dưới một bộ chọn khác.

⇒ Không cần `ThemeProvider` kiểu truyền màu xuống cây React. Không cần đổi một
dòng component nào. Không cần lớp trừu tượng mới.

## 3. 🔴 Một chỗ DUY NHẤT chặn "ghi đè thuần biến"

`AppHeader.module.css` đặt `background: var(--beras-accent)`.

Đặc tả Warm đòi thanh trên là **dải màu** (coral → hổ phách). Không thể nhét dải
màu vào `--beras-accent`, vì biến đó **còn được dùng làm màu chữ** ở chỗ khác
(`.brand`, `.link`, nút ghost) — `color: linear-gradient(...)` là vô nghĩa.

**Cách xử lý:** thêm đúng **một** biến gián tiếp `--beras-header-bg`, mặc định
`var(--beras-accent)`. Sửa **một dòng** trong `AppHeader.module.css`.

Đây là toàn bộ phần "đụng vào mã cũ" của cả việc thêm theme, và nó **không đổi
một pixel nào của Classic** — đã chứng minh bằng so ảnh từng byte (xem
`THEME_SYSTEM.md` §5).

## 4. Điểm vào cho nút chọn theme

Dự án **không có màn Cài đặt**. Đặc tả yêu cầu nút chọn nằm ở *Settings →
Appearance → Theme* ⇒ phải **thêm** một route.

Thêm route là **bổ sung**, không phải sửa routing hiện có: không URL nào đổi tên,
không màn nào đổi đường dẫn.
