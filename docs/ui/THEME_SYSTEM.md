# THEME_SYSTEM — Cách hệ theme của BERAS hoạt động

## 1. Ý tưởng một câu

**Nguồn sự thật là thuộc tính `data-theme` trên thẻ `<html>`.** CSS đọc nó; React
chỉ *đọc lại* để tô nút chọn. Không có màu nào đi qua cây React.

```
localStorage("beras.theme") ──► <html data-theme="warm"> ──► CSS ghi đè biến ──► giao diện
```

## 2. Vì sao KHÔNG dùng React Context

Đưa theme vào context nghĩa là **mọi component đọc context sẽ render lại khi đổi
theme** — đúng thứ đặc tả cấm (*"không render lại toàn bộ app"*), và nghĩa là có
hai nguồn sự thật phải giữ đồng bộ với DOM.

Dùng `useSyncExternalStore`: DOM là store bên ngoài, hook chỉ đọc. Đổi theme ⇒ đặt
một thuộc tính ⇒ trình duyệt tính lại các biến CSS đã kế thừa.
**Đúng một component render lại: nút chọn theme.**

Phần thưởng rơi ra miễn phí: hook bắt luôn sự kiện `storage`, nên **đổi theme ở
tab này thì tab kia đổi theo**.

## 3. Classic = KHÔNG có luật CSS nào

`warm.css` chỉ có khối `:root[data-theme="warm"]`. **Classic không có khối tương
ứng** — chọn Classic là `removeAttribute("data-theme")`, tức quay về đúng cascade
gốc.

Đây là quyết định có chủ đích: cách duy nhất chắc chắn Classic không đổi một pixel
là **không viết dòng CSS nào cho nó**. Một khối `:root[data-theme="classic"]` chép
lại 69 biến sẽ trôi khỏi bản gốc ngay lần sửa đầu tiên.

## 4. Chống nháy màu

React chỉ chạy **sau** khi HTML đã vẽ. Không xử lý gì thì người chọn Warm sẽ thấy
một nháy Classic ở **mỗi** lần tải trang.

`THEME_INIT_SCRIPT` nhúng thẳng vào `<head>`, chạy trước lượt vẽ đầu tiên, đọc
`localStorage` và đặt `data-theme`. Bọc `try/catch`: một trang không vẽ được chỉ
vì không đọc nổi tuỳ chọn màu là cái giá quá đắt.

## 5. ✅ Chứng minh Classic không đổi — so ảnh TỪNG BYTE

Không dựa vào mắt. Chụp 18 ảnh **trước** khi thêm hệ theme, chụp lại **sau**, rồi
`cmp` từng tệp:

```
Classic: giống hệt từng byte 10/18
khác:  desktop/02 … desktop/09  (8 ảnh — tất cả đều có sidebar)
```

Kiểm tay 8 ảnh đó: khác biệt **duy nhất** là một dòng `Cài đặt` mới trong nhóm
QUẢN TRỊ của sidebar — tức **điểm vào của chính tính năng này**, không phải hồi quy.

**9/9 ảnh khổ điện thoại giống hệt từng byte.** Lưới hành động nhanh cũng giữ
nguyên: `Cài đặt` khai `quickAction: false`, vì lưới đó là chỗ bắt đầu một việc
lúc 7 giờ sáng, không phải mục lục.

## 6. Tệp

| Tệp | Vai trò | Loại |
|---|---|---|
| `src/theme/themes.ts` | danh mục theme (mã, tên, ô màu xem trước) | **mới** |
| `src/theme/warm.css` | ghi đè biến cho Warm | **mới** |
| `src/theme/ThemeProvider.tsx` | `useTheme()` + script chống nháy | **mới** |
| `src/app/(app)/cai-dat/` | màn Cài đặt → Giao diện | **mới** |
| `src/styles/tokens.css` | **+1 biến** `--beras-header-bg` | sửa |
| `src/components/layout/AppHeader.module.css` | **1 dòng** đọc biến mới | sửa |
| `src/app/globals.css` | **1 dòng** `@import` warm.css | sửa |
| `src/app/layout.tsx` | bọc `ThemeProvider` + script `<head>` | sửa |
| `src/shared/nav.ts` | +1 mục nav, +cờ `quickAction` | sửa |
| `src/components/layout/NavIcon.tsx` | +1 icon | sửa |
| `src/components/action/QuickActionGrid.tsx` | đọc `quickActionItems()` | sửa |

**0 dòng** business logic · **0** thay đổi API/route cũ/CSDL/state/RBAC/tenant.
