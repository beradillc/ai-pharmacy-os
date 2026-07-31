# Khởi tạo tồn kho — nhập theo kệ (2026-07-31)

Màn `/khoi-tao-ton` · BERAS V2 Phase 9-10. Thiết kế: `docs/inventory/SHELF_FIRST_ENTRY.md`.

## Trước / sau — 390×844, `deviceScaleFactor: 2`

| | Trước | Sau |
|---|---|---|
| Ảnh | `truoc-mobile.png` | `sau-mobile.png` |
| Cao trang | 1533px CSS (**1,8 màn**) | 901px CSS (**1,1 màn** — vừa hết biểu mẫu) |
| Ba ô nhập (đếm · lô · HSD) | mỗi ô ~125px CSS | mỗi ô ~44px CSS |

🔴 Ảnh chụp ở `deviceScaleFactor: 2` nên **mọi số đọc từ ảnh phải chia đôi** mới ra pixel CSS.
Bản đầu của bảng này ghi "3066px / 3,6 màn" — đó là pixel vật lý, gấp đôi sự thật. Cùng họ với
hai ca 29/07 suýt sửa thứ không hỏng vì tin ảnh thu nhỏ, chỉ ngược chiều: tin ảnh **phóng to**.

## 🔴 Cả bốn cổng tự động xanh trong lúc đó

`eslint` · `tsc` · `build` · cổng Playwright — không cái nào đo chiều cao. Chỉ ảnh chụp thấy.

Nguyên nhân: `.o` là flex **column**, còn `.input` dùng chung mang `flex: 1 1 auto` để giãn
**ngang** trong các hàng ngang. Đặt thêm `flex: 1 1 14rem` lên `.o` thì `flex-basis` đó thành
chiều **cao**. Sửa: bỏ `flex` khỏi `.o`, chỉ cấp lại trong `.oDang .o` — nơi thật sự là hàng
ngang.

**Lần thứ hai** của cùng một họ lỗi (ô tìm kiếm 260px, 30/07). Lần thứ ba thì theo kỷ luật #18
phải nâng thành kỷ luật chính thức.

## Ảnh khác

- `sau-desktop.png` — 1440×900
- `sau-mobile-trong-o.png` — mở ô ở Sơ đồ kho, thấy đúng hai lô vừa đếm
