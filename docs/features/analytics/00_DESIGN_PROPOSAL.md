# Module `analytics` — Bản thiết kế đề xuất (DRAFT, chờ Chain duyệt)

> Trạng thái: **Q1–Q4 ĐÃ CHỐT (2026-07-25)** — còn chờ Chain gật quyền (mục 6) + lệnh bắt đầu code.
> Lập theo yêu cầu chốt PROJECT_STATE §7am
> (GĐ, Chain duyệt 2026-07-24) + Chain chọn **hướng (b) "dừng duyệt thiết kế trước khi code"**
> (2026-07-25). Đây là điểm nối cross-module 3 module đầu tiên của dự án nên bỏ 1 nhịp duyệt.
> Người lập: Trợ lý Code (Opus). Ngày: 2026-07-25.

## 0. Đích (từ §7am, không đổi)

`analytics` v1 = công cụ quản trị nội bộ (rủi ro pháp lý = 0, §7am):

1. **Dự báo nhu cầu** cấp **thuốc × chi nhánh** = trung bình trượt 90 ngày. KHÔNG AI/ML thật ở v1.
2. **Mốc tái đặt hàng** = (vận tốc bán bình quân/ngày × lead-time NCC) + tồn an toàn.
3. **Đề xuất nhập** → sinh **PO nháp (DRAFT)** trong `procurement` khi tồn dự kiến < mốc tái đặt —
   KHÔNG tự gửi NCC, người duyệt (triết lý "cảnh báo không chặn").
4. **Dashboard đầu**: doanh thu ngày/chi nhánh · top thuốc bán chạy · số cảnh báo cận date + tồn thấp ·
   số PO nháp chờ duyệt.

Hoãn v2 (không làm phiên này): phát hiện bất thường + mùa vụ/dịch bệnh.

## 1. Ràng buộc kiến trúc phải giữ

- **Module-independence:** `analytics` KHÔNG được import `sales`/`inventory`/`procurement`. Giống
  `sales` không import `catalog`/`prescription` — nó khai báo **read-ports (Protocol)** trong domain,
  composition root (`api/v1/`) viết **adapter** bọc service của các module kia và tiêm vào. Đây là
  contract `import-linter` số 1, tuyệt đối không phá.
- **Hexagonal 4 lớp:** domain (thuần) → application (use-case, chỉ phụ thuộc port) → infrastructure
  (repo SQLAlchemy cho dữ liệu RIÊNG của analytics) → interface (router HTTP + register).
- **Stepped-commit** 4 cổng xanh mỗi bước.

## 2. Sơ đồ phụ thuộc cross-module (đọc — KHÔNG viết chéo)

```
                      ┌─────────────────────────────────────────────┐
                      │  api/v1/analytics_wiring.py (composition root)│
                      │  — nơi DUY NHẤT biết cả 4 module —            │
                      └───────┬───────────┬───────────┬─────────────┘
     adapter bọc service      │           │           │
        (đọc)                 ▼           ▼           ▼
                        SalesService  InventoryService ProcurementService
                          │  đọc         │ đọc           │ GHI (PO nháp)
                          ▼              ▼               ▼
                   vận tốc bán/    tồn hiện tại/    tạo DRAFT PO
                   top thuốc       cận date+tồn thấp (materialize)
                          ╲             │             ╱
                           ╲            ▼            ╱
                            ─────►  AnalyticsService  ◄──── repo RIÊNG:
                                   (chỉ phụ thuộc port)      reorder_suggestions
```

Bốn read-port + một write-port `analytics` tự định nghĩa, adapter đặt ở `analytics_wiring.py`:

| Port (analytics định nghĩa) | Adapter bọc | Lấy gì | Cần thêm ở module nguồn? |
|---|---|---|---|
| `SalesVelocityPort` | `SalesService` | Tổng SL bán theo thuốc×chi nhánh trong [từ,đến] | **CÓ** — `sales` chưa có read theo *dòng* (report hiện tại chỉ order-level). Thêm 1 read-port line-level |
| `TopSellingPort` | `SalesService` | Top-N thuốc theo SL/doanh thu | Dùng chung query line-level trên |
| `StockLevelPort` | `InventoryService` | Tồn hiện tại thuốc×chi nhánh + đếm cận date/tồn thấp | `on_hand` đã có (theo drug); cần bản liệt kê toàn bộ thuốc có tồn theo chi nhánh |
| `ReorderTargetPort` (ghi) | `ProcurementService` | Tạo DRAFT PO từ 1 đề xuất | Dùng `create_purchase_order` + `add_po_item` sẵn có |
| `DraftPoCountPort` | `ProcurementService` | Đếm PO đang DRAFT chờ duyệt | **CÓ** — procurement chưa có query "list PO theo status". Thêm 1 read |

> Ghi chú: mỗi "cần thêm ở module nguồn" là 1 bước stepped-commit **nội bộ module đó** (domain-pure
> read-port + repo query), làm TRƯỚC, không phá module-independence.

## 3. Dữ liệu riêng của `analytics`

Một bảng mới `reorder_suggestions` (migration mới, +1 số thứ tự sau `0021`):

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| id, tenant_id, branch_id | UUID | Chuẩn tenant-scoped |
| drug_id | UUID | Thuốc (plain UUID, không FK chéo module) |
| avg_daily_velocity | Numeric | Vận tốc bán bq/ngày (90 ngày) |
| reorder_point | Numeric | Mốc tái đặt đã tính |
| on_hand_at_calc | Numeric | Tồn tại thời điểm tính |
| suggested_qty | Numeric | SL đề xuất nhập |
| status | str | `PENDING` / `MATERIALIZED` (đã tạo PO nháp) / `DISMISSED` / `INSUFFICIENT_DATA` |
| po_id | UUID? | PO nháp đã sinh (nếu materialized) |
| calculated_at | datetime | Mốc tính |

## 4. Luồng nghiệp vụ v1

1. **Tính đề xuất** (on-demand, `POST /analytics/reorder/run?branch_id=`): với mỗi thuốc có phát sinh
   bán trong 90 ngày ở chi nhánh → tính velocity → reorder_point → nếu `on_hand ≤ reorder_point` thì
   ghi 1 `reorder_suggestion` PENDING với `suggested_qty`. Thuốc **thiếu dữ liệu** (chưa đủ ngày lịch
   sử / velocity=0) → ghi `INSUFFICIENT_DATA`, **KHÔNG** sinh số bịa, **KHÔNG** tạo PO (chốt an toàn
   theo GĐ).
2. **Xem** (`GET /analytics/reorder/suggestions`): liệt kê để người duyệt.
3. **Materialize** (`POST /analytics/reorder/suggestions/{id}/materialize`): tạo **DRAFT PO** qua
   procurement adapter, gắn `po_id`, đổi status `MATERIALIZED`. Người dùng vào procurement duyệt/gửi
   NCC như thường — analytics KHÔNG tự `place_order`.
4. **Dashboard** (`GET /analytics/dashboard?branch_id=`): gộp doanh thu (sales) + top thuốc (sales) +
   đếm cận date/tồn thấp (inventory) + đếm PO nháp chờ duyệt (procurement).

## 5. Điểm business/data — CHAIN ĐÃ CHỐT 2026-07-25

| # | Câu hỏi | **Chain chốt** |
|---|---|---|
| Q1 | Nguồn vận tốc bán | **Dòng bán `sales`** (đúng chữ §7am). Ghi rõ giới hạn: kê đơn ETC không qua bán lẻ KHÔNG tính vào velocity |
| Q2 | Lead-time NCC & tồn an toàn | **Mặc định cấu hình theo tenant** (`lead_time_days` + `safety_stock_days`, mặc định đề xuất 7 & 3 ngày), cho override sau. KHÔNG bịa theo thuốc |
| Q3 | Chọn NCC cho PO nháp | **NCC gần nhất từng cấp thuốc đó** (suy từ lịch sử PO). Thuốc chưa từng mua → đề xuất KHÔNG materialize được, cảnh báo "chưa có NCC", không vỡ |
| Q4 | Kích hoạt tính toán | **Chỉ on-demand** (bấm nút) ở v1. Chạy nền định kỳ để v2 |

## 6. Quyền & tuân thủ

- Quyền mới `analytics.read` (dashboard + xem đề xuất) và `analytics.reorder.run` (tính + materialize).
  → **Kỷ luật #7 áp dụng:** thêm permission phải thử trên CSDL đã có dữ liệu (seed role) trước commit.
- Ai được cấp: admin + chain + branch (quản lý). KHÔNG cashier/warehouse. Chờ Chain xác nhận.
- Materialize tạo PO nháp = cần cả `analytics.reorder.run` (khởi) — hành động system-gated đi qua
  procurement với identity người bấm, KHÔNG dùng system-user (vì có người chịu trách nhiệm duyệt).

## 7. Thứ tự stepped-commit dự kiến (sau khi duyệt)

1. `sales`: read-port line-level (SL bán theo thuốc×chi nhánh) — domain+infra, nội bộ.
2. `inventory`: read liệt kê tồn theo chi nhánh + đếm cận date/tồn thấp — nội bộ.
3. `procurement`: read list PO theo status — nội bộ.
4. `analytics` domain: entity `ReorderSuggestion` + công thức reorder thuần + ports.
5. `analytics` app/infra/migration: service + repo + bảng `reorder_suggestions`.
6. `analytics` interface: router + register.
7. `api/v1/analytics_wiring.py`: adapter cross-module + đăng ký + quyền mới + seed role.
8. e2e + smoke live-DB (kỷ luật #7).

**Chưa làm gì cho tới khi Chain duyệt mục 5 (Q1–Q4) + mục 6 (ai được cấp quyền).**
