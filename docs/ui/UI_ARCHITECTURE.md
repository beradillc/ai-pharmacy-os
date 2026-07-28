# UI_ARCHITECTURE — Kiến trúc giao diện đề xuất

> PHASE 2. Đặc tả, **chưa code**. Đọc cùng `DESIGN_SYSTEM.md` và `ROUTING_PLAN.md`.

## 1. Một quyết định phải nói trước mọi thứ khác

Yêu cầu mục 6: *"Không tạo hai hệ thống logic khác nhau. Dùng cùng route/navigation
model."* Hiện tại **đang có đúng hai hệ**: `(pos)` toàn màn hình với header tự vẽ, và
`(app)` có menu ngang.

**Đề xuất: gộp về MỘT shell duy nhất**, trong đó màn bán hàng là *một route bình
thường* chứ không phải một thế giới riêng.

**Rủi ro phải nói thẳng:** POS toàn màn hình không phải lỗi thiết kế — nó là lựa
chọn có lý do (thu ngân cần tối đa diện tích, ít thứ bấm nhầm). Gộp vào shell chung
sẽ **lấy mất ~56px chiều cao** cho bottom nav trên máy tính bảng đặt tại quầy.

**Cách dung hoà đề xuất:** một shell, nhưng route bán hàng khai `chrome: "focus"` —
shell tự ẩn sidebar/bottom nav khi đang bán dở (giỏ hàng khác rỗng), hiện lại khi
giỏ trống. Vẫn **một** mô hình điều hướng, một `NAV` duy nhất, một chỗ gating quyền;
chỉ khác ở mật độ hiển thị. Nếu Chain không đồng ý, phương án dự phòng là giữ POS
toàn màn hình và **bắt buộc** có nút quay lại rõ ràng (đã thêm ở Sprint 10).

## 2. Kiến trúc thư mục đích

```
src/
  app/
    layout.tsx                 ← root: font, QueryProvider, viewport, reduced-motion
    login/page.tsx             ← ngoài shell
    (shell)/                   ← MỘT shell duy nhất, thay cho (app) + (pos)
      layout.tsx               ← AppHeader + Sidebar/BottomNavigation + PageTransition
      page.tsx                 ← "/" TỔNG QUAN (dashboard mới)
      ban-hang/page.tsx        ← POS (chuyển từ "/" cũ)
      hoa-don/ khach-hang/ don-thuoc/
      kho/  nhap-hang/
      bao-cao/  de-xuat-dat-hang/
      tuan-thu/  ai/  nhan-vien/  them/
  components/                  ← MỚI: tầng trình bày thuần, không gọi API
    layout/    AppHeader · Sidebar · BottomNavigation · PageTransition · NotificationBadge
    data/      KpiCard · DataTable · RevenueChart · RecentTransactionList · StatusChip
    feedback/  LoadingState · EmptyState · ErrorState · AlertCard · ComplianceCard
    overlay/   ConfirmDialog · BottomSheet
    action/    Button · QuickActionGrid · QuickActionItem · FilterBar · Pager
  features/                    ← GIỮ NGUYÊN: hook react-query + store
  shared/                      ← GIỮ NGUYÊN: api, offline, format
  styles/tokens.css            ← mở rộng theo DESIGN_SYSTEM.md
```

**Luật một chiều, kiểm được bằng mắt khi review:**
`app/*` gọi `features/*` và dựng `components/*`. **`components/*` không được import
`features/*` hay `shared/api/*`.** Component nhận dữ liệu qua props, không tự gọi API.

Đây là bản sao của quy tắc hexagonal mà backend đang giữ bằng `import-linter`. Frontend
chưa có công cụ cưỡng chế tương đương — ghi ra đây là **nợ đã biết**, và ứng viên
đầu tiên nếu sau này thêm cổng FE (`eslint-plugin-boundaries`).

## 3. Information architecture — màn Tổng quan

Đúng thứ tự yêu cầu mục 1, và thứ tự này có lý do vận hành:

| Thứ tự | Khối | Vì sao ở đây |
|---|---|---|
| 1 | `AppHeader` | tên nhà thuốc + chi nhánh + chuông + tài khoản |
| 2 | `QuickActionGrid` | **trên KPI**: mở app lúc 7h sáng là để *bán*, không phải để đọc số |
| 3 | KPI (4 thẻ) | doanh thu hôm nay · đơn hôm nay · cảnh báo kho · tuân thủ |
| 4 | `ComplianceCard` "Cần xử lý" | việc phải làm đứng **trước** biểu đồ: hành động trước phân tích |
| 5 | `RevenueChart` | 28 ngày, một đường |
| 6 | `RecentTransactionList` | 5–8 đơn gần nhất, bấm vào mở chi tiết |

Mobile: cuộn dọc đúng thứ tự trên. Desktop (≥900px): hàng 1 = quick actions ngang;
hàng 2 = 4 KPI; hàng 3 = 2 cột (chart 2/3 · cần xử lý 1/3); hàng 4 = giao dịch gần đây.

## 4. Nạp dữ liệu — chống "tải hết khi mở dashboard"

| Khối | Nguồn | Chiến lược |
|---|---|---|
| KPI doanh thu/đơn hôm nay | `GET /analytics/dashboard` + `GET /sales?limit=1` | 1 lời gọi mỗi thứ, `staleTime` 60s |
| KPI so với hôm qua | **gọi lần hai** `/analytics/dashboard` kỳ trước | Song song; hỏng thì ẩn phần so sánh, **không** hiện 0% |
| Cảnh báo kho | `GET /inventory/alerts/near-expiry` | `staleTime` 5 phút |
| Cần xử lý | gộp ở FE từ 3 nguồn đã có (xem `UI_GAP_REPORT.md` B-03) | |
| Chart | `GET /reports/revenue` **(cần thêm — B-02)** | **lazy**: chỉ nạp khi khối vào viewport |
| Giao dịch gần đây | `GET /sales?limit=8` | |

Mỗi khối **tự chịu trách nhiệm trạng thái của mình**: một khối lỗi thì hiện
`ErrorState` tại chỗ, năm khối kia vẫn dùng được. Không có màn "toàn trang đang tải".

## 5. Điều hướng — một mô hình, hai cách hiển thị

```ts
// Một hằng số DUY NHẤT. Sidebar và BottomNavigation cùng đọc từ đây.
type NavItem = {
  href: string;
  label: string;
  permission: string;   // gating theo QUYỀN, không theo tên vai
  primary: boolean;     // true = có mặt trong 5 ô bottom nav
  icon: IconName;
};
```

- **Mobile (<900px):** `BottomNavigation` 5 mục `primary` — Tổng quan · Bán hàng ·
  Kho · Báo cáo · **Thêm**. "Thêm" mở `BottomSheet` chứa mọi mục còn lại.
- **Desktop (≥900px):** `Sidebar` hiện **toàn bộ** mục có quyền, nhóm theo cụm.
- Mục thiếu quyền: **không hiện**, không hiện-rồi-báo-lỗi (giữ nguyên nguyên tắc
  đang có ở `(app)/layout.tsx`).
- Nếu số mục `primary` mà người dùng có quyền < 5 ⇒ bottom nav **co lại**, không độn
  ô giả.

## 6. Chuyển cảnh

`PageTransition` bọc `children` trong shell layout, đọc `usePathname()` làm khoá.

| Loại | Hiệu ứng | Token |
|---|---|---|
| Đổi trang cùng cấp | fade + trượt lên 8px | `--motion-base` |
| Vào chi tiết | trượt trái | `--motion-base` |
| Modal | fade + scale | `--motion-fast` |
| Bottom sheet | trượt lên | `--motion-slow` |
| Thành công (bán xong) | scale nhẹ + fade | `--motion-fast` |

Chỉ animate `transform` và `opacity` — không animate `height`/`top`/`width`, vì hai
cái sau ép trình duyệt tính lại bố cục mỗi khung hình (yêu cầu mục 12: *"không
animation gây re-render toàn dashboard"*).

## 7. AI Assist — ràng buộc là phần khó, không phải giao diện

Luồng bắt buộc, đúng mục 5:

```
Gợi ý AI  →  bằng chứng (vì sao)  →  người xem  →  chấp nhận / sửa / từ chối  →  nhật ký
```

**Ràng buộc phải hiện lên trong chính giao diện, không chỉ nằm trong mã:**

1. Mọi thẻ AI mang nhãn **"Gợi ý — cần dược sĩ xác nhận"**. Không có nút nào của AI
   tự thi hành.
2. Nút hành động (bán, đổi tồn, đổi danh mục) **không bao giờ** nằm trong thẻ AI —
   chúng nằm ở màn nghiệp vụ tương ứng, sau khi người dùng chuyển sang đó.
3. Mỗi gợi ý phải hiện **bằng chứng**: dữ liệu nào dẫn tới kết luận đó.
4. Từ chối cũng ghi nhật ký như chấp nhận — nếu chỉ ghi "accept" thì sổ nhật ký sẽ
   nói dối rằng AI luôn đúng.

Backend đã có `POST /clinical/recommendations/{id}/accept` và ghi audit; UI **không
thêm quyền nào**, chỉ hiển thị.

## 8. Ranh giới bảo mật — không đổi một dòng

| Việc | Ai làm |
|---|---|
| Ẩn/hiện mục menu | UI (tiện lợi) |
| **Quyết định được phép hay không** | **Backend** — `require_permission` ở service |
| Phạm vi tenant/chi nhánh | Backend — từ claim JWT đã ký; header `X-Branch-Id` **không** đè được |

UI không có, và sẽ không có, đường nào bỏ qua backend. Một người sửa
`session.permissions` trong localStorage chỉ làm hiện thêm mục menu, bấm vào vẫn 403.
**Đợt UI này không đụng vào một dòng nào của tầng phân quyền.**

## 9. Cái KHÔNG làm trong đợt này

| Không làm | Vì sao |
|---|---|
| Đổi bất kỳ hook `features/*` hay `shared/api/*` nào | Chain: *"không làm thay đổi code các sprint"*. Nghiệp vụ ở backend, hook chỉ gọi |
| Thêm thư viện UI / chart | Xem `DESIGN_SYSTEM.md` §8 |
| Dark mode | Yêu cầu không đòi |
| Đổi endpoint đang có | Chỉ **thêm** `GET /reports/revenue` (JSON) — và chỉ khi Chain duyệt |
| Viết lại POS | Giữ nghiệp vụ giỏ hàng + offline nguyên vẹn, chỉ thay vỏ |
