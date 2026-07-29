# UI_IMPLEMENTATION_REPORT — Kết quả triển khai giao diện

> PHASE 8 của yêu cầu UI/UX. 2026-07-29, GĐ chạy liên tục trong lúc Chain đi vắng.
> Mọi con số đo bằng lệnh, không ước lượng.

## 1. Đã làm — bốn đợt

| Đợt | Nội dung | Backend |
|---|---|---|
| **U1** | `shared/nav.ts` (một mô hình điều hướng) · `AppShell` · Sidebar · BottomNavigation · MoreSheet · PageTransition · NavIcon · 6 nhóm token · focus-visible · reduced-motion · viewport | 0 dòng |
| **U2** | Màn Tổng quan dựng lại theo IA mới · KpiCard · QuickActionGrid · RevenueChart (SVG tự vẽ) · ComplianceCard · Loading/Empty/ErrorState | 0 dòng |
| **U3** | Màn Báo cáo (3 endpoint CSV có từ Sprint 7, chưa từng có cửa bấm) | 0 dòng |
| **W1–W3** | 4 màn danh sách theo hệ token · ConfirmDialog thay `window.prompt`/`confirm` · kiểu in · **3 lỗi tương phản WCAG** · xoá CSS chết | 0 dòng |

**Tổng: 0 dòng backend, 0 dòng nghiệp vụ.** Xác nhận bằng `git diff -- backend/`
rỗng ở từng commit.

## 2. Đối chiếu Definition of Done

| DoD | Trạng thái | Bằng chứng |
|---|---|---|
| Header | ✅ | `AppHeader`, dùng chung mọi màn |
| Quick Actions | ✅ | 8 ô, 4 cột mobile → 8 cột desktop, gating theo quyền |
| KPI | ✅ | `KpiCard` tái dùng, có `comparison`/`trend`/`status`/`icon` |
| Compliance alerts | ✅ | `ComplianceCard`, dựng từ dữ liệu thật, không bịa mục |
| Revenue chart | ✅ | SVG tự vẽ, 1 chuỗi, crosshair + tooltip, nhãn 3 điểm |
| Recent transactions | ✅ | 6 dòng gần nhất từ `GET /sales` |
| Bottom navigation mobile | ✅ | 5 ô, ẩn ≥900px |
| Sidebar desktop | ✅ | hiện ≥900px, nhóm theo cụm |
| Responsive | ⚠️ | Đo được: 0 hex cứng, mobile-first, không tràn ngang theo cấu trúc. **Chưa mắt người nào nhìn ở 390px** |
| Loading / Empty / Error state | ✅ | 3 component dùng chung |
| Page transitions | ✅ | fade + trượt 8px, chỉ `transform`/`opacity` |
| Reduced motion | ✅ | khối `prefers-reduced-motion` ở `globals.css`, dùng `1ms` không phải `0s` |
| Accessibility | ⚠️ | Tương phản **7/7 PASS sau khi vá 3 lỗi**; focus-visible; `aria-current`; trạng thái luôn kèm chữ. **Chưa test bằng trình đọc màn hình thật** |
| No horizontal overflow | ⚠️ | Theo cấu trúc: bảng cuộn trong khung, `overscroll-behavior-x: contain`. Chưa đo trên máy thật |
| No hard-coded production data | ✅ | Mọi số đến từ API |
| No business logic in UI | ✅ | `components/*` không import `features/*` hay `shared/api/*` |
| Backend authorization unchanged | ✅ | 0 dòng backend; kiểm LAN: 401/403/tenant isolation nguyên vẹn |
| Build/test pass | ✅ | `LINT=0 TSC=0 BUILD=0` · backend `MAKE_CHECK_EXIT=0` (1135+16) |

## 3. Phát hiện đáng giá nhất — ba lỗi tương phản

PHASE 6 chạy bằng **công thức WCAG trên đúng cặp màu sản phẩm đang dùng**, không
bằng mắt:

| Cặp | Trước | Sau | Ngưỡng |
|---|---|---|---|
| chữ trắng / nút chính | **3,95 🔴** | 4,55 | 4,5 |
| chip "cận hạn dùng" | **2,82 🔴** | 4,55 | 4,5 |
| chip trạng thái tốt | **4,37 🔴** | 4,60 | 4,5 |

Nút chính là nút bấm nhiều nhất cả sản phẩm. Chip "cận hạn" là **cảnh báo an toàn
thuốc**, đọc dưới đèn huỳnh quang ở quầy. 2,82 không phải chuyện thẩm mỹ.

**Không đổi màu nhận diện.** Thêm ba bậc "mực" cùng tông cho vai trò *chữ*; màu
gốc vẫn dùng cho viền/vạch/nét biểu đồ, nơi ngưỡng là 3:1 và nó đạt 3,95.

## 4. Đo hiệu năng (PHASE 7)

| | |
|---|---|
| Chunk JS | 21 tệp · **928 KB** chưa nén |
| Phụ thuộc runtime | **6** — `next`, `react`, `react-dom`, `@tanstack/react-query`, `zustand`, `dexie` |
| Thư viện UI / chart / icon | **0** — biểu đồ vẽ tay bằng SVG, 8 icon vẽ tay |
| Tải dữ liệu | mỗi khối một `useQuery` riêng, có `staleTime`, phân trang 50 dòng |
| Animation | chỉ `transform`/`opacity` — không ép tính lại bố cục |

## 5. Kỷ luật giữ được trong lúc làm

| | |
|---|---|
| Hex cứng ngoài `tokens.css` | **0** (trước: 4) |
| CSS chết | xoá `(app)/layout.module.css`, 87 dòng |
| `window.prompt` / `confirm` | **0** trong mã chạy (chỉ còn trong ghi chú giải thích) |
| Khai báo `min-height` dưới 44px ở phần tử bấm được | **0** |
| Số bản header trong mã | **1** (trước: 2) |
