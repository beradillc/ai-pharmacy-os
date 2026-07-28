# ROUTING_PLAN — Bản đồ route và điều hướng

> PHASE 2. Đặc tả, **chưa code**.

## 1. Bảng route đích

| Route | Màn | Quyền | Bottom nav | Trạng thái |
|---|---|---|---|---|
| `/login` | Đăng nhập | — | — | ✅ có, ngoài shell |
| `/` | **Tổng quan** (dashboard mới) | `analytics.read` | ① Tổng quan | 🆕 dựng mới |
| `/ban-hang` | Bán hàng (POS) | `sales.create` | ② Bán hàng | ♻️ chuyển từ `/`, giữ nguyên nghiệp vụ |
| `/hoa-don` | Hoá đơn | `sales.read` | trong "Thêm" | ✅ có (Sprint 10) |
| `/khach-hang` | Khách hàng | `crm.read` | trong "Thêm" | ✅ có (Sprint 10) |
| `/don-thuoc` | Đơn thuốc | `rx.read` | trong "Thêm" | 🆕 backend có 5 endpoint, 0 màn |
| `/kho` | Kho (tồn theo lô) | `inventory.read` | ③ Kho | ♻️ đổi tên từ `/ton-kho` |
| `/nhap-hang` | Nhập hàng (GRN) | `procurement.grn.create` | trong "Thêm" | 🆕 backend có 3 endpoint, 0 màn |
| `/don-mua-hang` | Đơn mua hàng | `procurement.po.read` | trong "Thêm" | ✅ có (Sprint 10) |
| `/de-xuat-dat-hang` | Đề xuất đặt hàng | `analytics.read` | trong "Thêm" | ✅ có (Sprint 9) |
| `/bao-cao` | Báo cáo | `sales.read` | ④ Báo cáo | 🆕 3 endpoint CSV đã có, 0 màn |
| `/tuan-thu` | Tuân thủ | `compliance.ledger.read` | trong "Thêm" | 🆕 12 endpoint, 0 màn |
| `/ai` | BERAS AI | `clinical.check` | trong "Thêm" | 🆕 5 endpoint, 0 màn |
| `/nhan-vien` | Nhân viên & phân quyền | `iam.user.read`¹ | trong "Thêm" | 🆕 21 endpoint, 0 màn |
| `/them` | Thêm (mục lục) | — | ⑤ Thêm | 🆕 mobile: bottom sheet · desktop: chuyển hướng về `/` |

¹ Tên quyền IAM phải tra lại trong `system_roles.py` khi code — **không đoán**.

## 2. Đổi tên route — và giá của nó

| Cũ | Mới | Xử lý |
|---|---|---|
| `/` (POS) | `/ban-hang` | 🔴 Đổi ý nghĩa của trang chủ |
| `/ton-kho` | `/kho` | Khớp nhãn bottom nav "Kho" |
| `/bang-dieu-hanh` | `/` | Dashboard trở thành trang chủ |

**Giá phải trả, nói trước:** thu ngân đang quen mở app là ra thẳng màn bán hàng.
Sau khi đổi, họ ra dashboard rồi phải bấm thêm một lần.

**Đề xuất giảm đau:** trang `/` **tự chuyển hướng sang `/ban-hang`** nếu phiên có
`sales.create` mà **không** có `analytics.read` — tức tài khoản thu ngân thuần vẫn
vào thẳng chỗ làm việc, còn quản lý thì ra dashboard. Một luật, đọc từ đúng bộ quyền
mà bottom nav đã đọc; không phải một ngoại lệ cứng.

**Route cũ giữ chuyển hướng vĩnh viễn** (`/ton-kho` → `/kho`, `/bang-dieu-hanh` →
`/`): có người đã bookmark trong lúc demo.

## 3. Bottom navigation (mobile <900px) — 5 ô

| # | Nhãn | Route | Quyền |
|---|---|---|---|
| ① | Tổng quan | `/` | `analytics.read` |
| ② | Bán hàng | `/ban-hang` | `sales.create` |
| ③ | Kho | `/kho` | `inventory.read` |
| ④ | Báo cáo | `/bao-cao` | `sales.read` |
| ⑤ | Thêm | mở bottom sheet | — (luôn hiện) |

- Cao 56px + `env(safe-area-inset-bottom)` cho iPhone có thanh gạt.
- Mỗi ô ≥ `--touch-min` (44px) theo **cả hai chiều**.
- Ô đang chọn: **icon đặc + chữ đậm + màu**, không chỉ đổi màu (mục 11).
- Trang phải chừa `padding-bottom: var(--space-12)` để nội dung cuối không bị nav che.

## 4. Sidebar (desktop ≥900px)

Cùng dữ liệu `NAV`, hiện đủ mục có quyền, chia cụm:

```
BÁN HÀNG      Tổng quan · Bán hàng · Hoá đơn · Khách hàng · Đơn thuốc
KHO           Kho · Nhập hàng · Đơn mua hàng · Đề xuất đặt hàng
QUẢN TRỊ      Báo cáo · Tuân thủ · BERAS AI · Nhân viên
```

Cụm rỗng (không mục nào có quyền) ⇒ **ẩn cả tiêu đề cụm**, không để một tiêu đề trơ.

## 5. Quick actions (8 ô trên dashboard)

| Ô | Đi tới | Quyền |
|---|---|---|
| Bán hàng | `/ban-hang` | `sales.create` |
| Hoá đơn | `/hoa-don` | `sales.read` |
| Khách hàng | `/khach-hang` | `crm.read` |
| Đơn thuốc | `/don-thuoc` | `rx.read` |
| Kho | `/kho` | `inventory.read` |
| Nhập hàng | `/nhap-hang` | `procurement.grn.create` |
| Báo cáo | `/bao-cao` | `sales.read` |
| Thêm | `/them` | — |

Lưới: 4 cột (<600px) · 4 cột (600–900px) · 8 cột một hàng (≥900px). Ô thiếu quyền
**biến mất**, lưới dồn lại — không để ô xám vô nghĩa.

## 6. Canh đăng nhập

Giữ nguyên cách đang chạy (`hydrate()` sau mount rồi mới quyết định), vì nó đã xử lý
đúng ca F5 làm văng người đang đăng nhập. Chuyển từ hai layout `(app)`/`(pos)` về
**một** `(shell)/layout.tsx`.

## 7. Thứ tự triển khai route

| Đợt | Làm gì | Vì sao trước |
|---|---|---|
| **U1** | `viewport` + token + `(shell)` + Sidebar/BottomNav + chuyển hướng route cũ | Không có shell thì không gắn được gì |
| **U2** | Dashboard `/`: quick actions + KPI + cần xử lý + giao dịch gần đây | Giá trị thấy được ngay, chưa cần backend mới |
| **U3** | `/bao-cao` | 3 endpoint đã có, rẻ nhất trong các màn mới |
| **U4** | `RevenueChart` + `GET /reports/revenue` (JSON) | Mục **duy nhất** cần thêm endpoint |
| **U5** | `/nhan-vien` | Chặn pilot thật: hiện không tạo được nhân viên trên giao diện |
| **U6** | `/tuan-thu`, `/ai`, `/nhap-hang`, `/don-thuoc` | Mỗi màn một đợt, không gộp |

U1–U3 **không đụng backend một dòng nào**. U4 chỉ thêm một endpoint đọc dùng lại hàm
đã có test. U5 trở đi chưa lên lịch — chờ Chain chốt sau khi thấy U1–U3.
