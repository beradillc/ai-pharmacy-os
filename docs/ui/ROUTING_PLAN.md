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

---

## 8. 🔴 QUYẾT ĐỊNH GĐ (2026-07-29) — Chain uỷ quyền, nguyên tắc "không đụng cái đang chạy tốt"

Chain: *"Uỷ quyền GĐ quyết định, theo quan điểm không đụng tới backend đã xây tốt,
đổi giao diện dựa trên cái đã có, chạy tốt. Các mục chưa có đưa vào mục Nâng cấp
sau này, hoặc làm ngay nếu không tốn thời gian sửa chữa lớn."*

Ba quyết định, và §1–§7 ở trên **bị sửa theo** chúng:

| # | Quyết định | Vì sao |
|---|---|---|
| **Q1** ⚠️ *đã sửa một nửa — xem §9* | **KHÔNG gộp POS vào shell chung. KHÔNG đổi tên một route nào.** `/` vẫn là màn bán hàng, dashboard vẫn ở `/bang-dieu-hanh`, kho vẫn ở `/ton-kho` | POS toàn màn hình đang chạy tốt và là lựa chọn có lý do. Đổi trang chủ là đổi thói quen người đứng quầy — chi phí thật, lợi ích thẩm mỹ. Cái yêu cầu thực sự cần là **một mô hình điều hướng**, và điều đó đạt được bằng một hằng số `NAV` dùng chung, không cần đổi URL |
| **Q2** | **KHÔNG thêm `GET /reports/revenue`.** Biểu đồ doanh thu dựng từ `GET /sales` đã có, gộp theo ngày ở FE | Chain nói rõ không đụng backend. `GET /sales` (Sprint 10 D1) trả `created_at` + `subtotal` từng đơn ⇒ đủ dựng đường 28 ngày. **Giới hạn đã biết:** ~280 đơn/28 ngày cần 2 lượt gọi (`limit` tối đa 200). Nhà thuốc lớn hơn sẽ tốn nhiều lượt ⇒ **Nâng cấp sau** |
| **Q3** | Làm **U1 → U2 → U3**, dừng cho Chain xem, rồi mới quyết tiếp | U1–U3 không đụng backend một dòng nào |

### Bảng route SỬA LẠI theo Q1 — giữ nguyên mọi URL đang có

| Route | Màn | Bottom nav | Đổi gì |
|---|---|---|---|
| `/` | Bán hàng (POS) | ② Bán hàng | **không đổi URL**, chỉ thay vỏ trình bày |
| `/bang-dieu-hanh` | Tổng quan | ① Tổng quan | dựng lại nội dung **tại chỗ** theo IA mới |
| `/ton-kho` | Kho | ③ Kho | không đổi |
| `/hoa-don` · `/khach-hang` · `/don-mua-hang` · `/de-xuat-dat-hang` | | trong "Thêm" | không đổi |
| `/them` | Mục lục | ⑤ Thêm | **mới** — bottom sheet trên mobile |
| ④ Báo cáo | | | **Nâng cấp sau** (U3) |

### Chuyển vào "NÂNG CẤP SAU" — có lý do, không phải bỏ quên

| Mục | Vì sao hoãn |
|---|---|
| Đổi tên route (`/ban-hang`, `/kho`) | Q1 — lợi ích không bù được chi phí đổi thói quen |
| `GET /reports/revenue` (JSON) | Q2 — chỉ cần khi số đơn/tháng vượt vài trăm |
| `/nhan-vien` (21 endpoint IAM) | Màn mới hoàn toàn, chặn pilot thật nhưng **không** chặn demo |
| `/tuan-thu` (12 endpoint) · `/ai` (5) · `/nhap-hang` (3) · `/don-thuoc` (5) | Mỗi màn là một tính năng mới, không phải "đổi giao diện dựa trên cái đã có" |
| KPI `comparison`/`trend` | Cần gọi hai kỳ; làm được nhưng **U2 sẽ để dành**: dashboard chưa có gì mà đã hai lượt gọi là tự chuốc chậm. Component `KpiCard` **có sẵn prop**, chỉ chưa truyền |
| Dark mode | Yêu cầu không đòi |


---

## 9. 🔴 Q1 BỊ SỬA MỘT NỬA (2026-07-29, sau khi Chain dùng thật)

Chain: *"Mục Bán hàng thiếu danh mục bên trái, mỗi lần về phải bấm vào Quản lý
thấy bất tiện."*

**Phần sai của Q1:** giữ POS ngoài shell, với lập luận *"thu ngân cần tối đa diện
tích"*. Đó là **giả định của tôi**, không phải quan sát. Người dùng thật đã trả
lời: mất điều hướng khó chịu hơn mất 232px sidebar. Một lập luận nghe hợp lý mà
trái với dữ liệu thì phải bỏ, không phải bảo vệ.

**Phần đúng của Q1, vẫn giữ:** không đổi URL nào. `/` vẫn là màn bán hàng.

| | Trước | Sau |
|---|---|---|
| Khung màn Bán hàng | layout riêng, header tự vẽ | **`AppShell` dùng chung** |
| Điều hướng ở màn Bán hàng | chỉ một nút "Quản lý" | sidebar (≥900px) · thanh dưới (<900px) |
| Số bản header trong mã | 2 | **1** |
| Chiều rộng nội dung | toàn màn | `wide` — không bó 1120px như các màn khác |

**Bài học ghi lại, vì nó lặp lần thứ hai trong một ngày:** cả lỗi này lẫn lỗi
`viewport` sáng nay đều là *tôi suy luận thay vì đo*. Lỗi viewport là suy từ
`grep` rỗng; lỗi này là suy từ "thu ngân chắc cần diện tích". Cả hai đều nghe rất
hợp lý, và cả hai đều sai. Với giao diện, thứ duy nhất kết luận được là **người
dùng thật bấm thử** — và đó là lý do vòng "tôi làm → Chain bấm → tôi sửa" đang
chạy đúng, không phải một phiền toái cần rút ngắn.
