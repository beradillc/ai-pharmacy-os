# COMPONENT_INVENTORY — Kiểm kê từng mảnh giao diện đang có

> PHASE 1. Mỗi dòng có **phán quyết**: `GIỮ` (dùng lại nguyên) · `NÂNG` (trích ra
> thành component dùng chung) · `THAY` (kiến trúc sai, đổi) · `MỚI` (chưa có).
> Nguyên tắc của yêu cầu: *"nếu component hiện tại tốt: REUSE"*.

## A. Mảnh giao diện đang tồn tại (dạng markup cục bộ, chưa phải component)

| Mảnh | Sống ở đâu | Phán quyết | Lý do |
|---|---|---|---|
| Ô KPI (`Tile`) | hàm cục bộ trong `bang-dieu-hanh/page.tsx` | **NÂNG → `KpiCard`** | Đã có `label/value/hint/tone/muted` + skeleton. Thiếu `comparison`, `trend`, `icon`, `status`. Nâng chứ không viết lại |
| Thanh tiến độ "thuốc bán chạy" | `bang-dieu-hanh/page.module.css` `.barWrap/.bar` | **GIỮ, đổi tên** | Đây là bar chart ngang đúng nghĩa, mark mỏng, đã ẩn ở màn hẹp. Thành `<HorizontalBar>` trong `RevenueChart`/top-list |
| Bảng dữ liệu | `shared/ui/screen.module.css` `.table/.tableWrap` | **NÂNG → `DataTable`** | Đã có `overflow-x` cuộn trong khung (không đẩy trang trượt ngang), header uppercase, hover row, cột số dùng mono căn phải. Đúng chuẩn, chỉ thiếu vỏ React |
| Chip trạng thái | `screen.module.css` `.chip/.chipOk/.chipWarn/.chipDanger/.chipMuted` | **NÂNG → `StatusChip`** | Đã có **chữ + màu**, không phải màu-đơn-thuần ⇒ thoả mục 11. Thêm icon khi nâng |
| Khối lỗi + nút "Thử lại" | lặp ở 6 màn, `role="alert"` | **NÂNG → `ErrorState`** | Sáu bản sao gần giống nhau — đúng chỗ cần gom |
| Skeleton | `.skeleton/.skeletonRows` ở 3 tệp CSS | **NÂNG → `LoadingState`** | Đã có, chỉ chưa gom |
| Trạng thái rỗng | `<p className={styles.empty}>` ở 5 màn, chữ khác nhau | **NÂNG → `EmptyState`** | Hiện chỉ có chữ; cần thêm chỗ cho hành động gợi ý |
| Phân trang | `.pager` + 2 nút Trước/Sau | **NÂNG → `Pager`** | Đã disable đúng khi hết trang. Vùng chạm cần lên 44px |
| Header quản lý | `(app)/layout.module.css` | **THAY → `AppHeader` + `Sidebar`** | Menu ngang không mở rộng được lên 7+ mục, và không có bản mobile |
| Header POS | `(pos)/page.module.css` `.header` | **THAY** | Bản sao thứ hai của cùng một ý tưởng — nguồn gốc của "hai hệ điều hướng" |
| Ô tìm/lọc | `.input/.select` ở `screen.module.css` | **GIỮ → `FilterBar`** | Gom thành một hàng bộ lọc phía trên bảng, đúng `interaction.md` |
| Ngăn kéo chi tiết hoá đơn | `hoa-don/page.tsx` `.drawer` | **NÂNG → `BottomSheet`** (mobile) / panel (desktop) | Đang là khối chèn dưới bảng; nâng lên đúng ngữ nghĩa |
| Nút | `.button/.ghost` | **NÂNG → `Button`** với `variant` | Đang có 2 biến thể, thiếu size và trạng thái focus |
| Form đăng nhập | `login/page.tsx` | **GIỮ** | Màn độc lập, không nằm trong shell dashboard |
| Giỏ hàng POS | `(pos)/page.tsx` | **GIỮ nghiệp vụ, NÂNG vỏ** | Logic giỏ đang chạy đúng và có test thủ công thật; chỉ thay lớp trình bày |

## B. 17 component yêu cầu — đối chiếu

| Component yêu cầu | Trạng thái | Nguồn dùng lại |
|---|---|---|
| `AppHeader` | **MỚI** | gộp 2 header hiện có |
| `QuickActionGrid` | **MỚI** | — |
| `QuickActionItem` | **MỚI** | — |
| `KpiCard` | **NÂNG** | `Tile` trong `bang-dieu-hanh` |
| `AlertCard` | **MỚI** | khuôn từ `.error` |
| `ComplianceCard` | **MỚI** | dữ liệu từ 12 endpoint `compliance` chưa dùng |
| `RevenueChart` | **MỚI** | mark từ `.bar`; xem `DESIGN_SYSTEM.md` §4 |
| `RecentTransactionList` | **NÂNG** | `GET /sales` đã có (Sprint 10 D1) |
| `BottomNavigation` | **MỚI** | — |
| `Sidebar` | **MỚI** | logic gating lấy từ `(app)/layout.tsx` |
| `PageTransition` | **MỚI** | — |
| `LoadingState` | **NÂNG** | `.skeleton` |
| `EmptyState` | **NÂNG** | `.empty` |
| `ErrorState` | **NÂNG** | khối lỗi 6 màn |
| `ConfirmDialog` | **MỚI** | hiện dùng `window.confirm`/`window.prompt` — xem §C |
| `BottomSheet` | **NÂNG** | `.drawer` màn Hoá đơn |
| `NotificationBadge` | **NÂNG** | `.pendingTag` (đếm đơn chờ đồng bộ) ở POS |

**Tổng: 8 NÂNG (có sẵn ruột) · 9 MỚI.** Không có mục nào phải viết lại từ đầu vì
kiến trúc sai — đây là lý do đề xuất **refactor tăng dần**, không rewrite.

## C. Ba chỗ dùng API trình duyệt thay cho component — phải thay

| Chỗ | Đang dùng | Vấn đề |
|---|---|---|
| `(pos)/page.tsx` `handleAdd` | `window.prompt` khi thuốc chưa có giá | Không style được, không a11y, không hoạt động trong một số webview |
| `de-xuat-dat-hang` | `window.confirm` (kiểm tra lại khi code) | Như trên |
| `hoa-don` nút In | `window.print()` | Chấp nhận được — in là hành vi trình duyệt. **GIỮ**, nhưng cần CSS `@media print` (chưa có) |

## D. Cái KHÔNG được đụng (yêu cầu: giữ nguyên business logic)

```
src/shared/api/*        ← client, types, errors, token-storage
src/features/*/use-*.ts ← 9 hook react-query
src/features/*/​*-store.ts ← auth-store, cart-store
src/shared/offline/*    ← dexie, hàng đợi, useOfflineSync
src/shared/format/*     ← định dạng số/tiền/giờ
```

Toàn bộ thư mục trên là **tầng dữ liệu**, không phải tầng trình bày. Refactor UI
không có lý do chính đáng nào để sửa chúng. Nếu một bước nào đó buộc phải sửa,
đó là dấu hiệu bước đó đang kéo nghiệp vụ lên UI — dừng lại và xem lại (yêu cầu
mục "No business logic moved into UI").
