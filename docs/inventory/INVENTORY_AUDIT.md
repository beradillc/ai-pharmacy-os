# INVENTORY_AUDIT — Phase 0 của BERAS V2 Smart Inventory

> **Không code ở bước này** (đúng yêu cầu Phase 0). Tệp này chỉ mô tả **hiện trạng đo
> được** và nêu rủi ro trước khi mở rộng.
>
> Ngày: **2026-07-31**. Đọc trên cây tại commit `328550b`. Mọi con số dưới đây lấy từ mã
> và từ truy vấn SQL thật trên `nt650v2`, không từ tài liệu.

## 1. Kiến trúc hiện tại

### 1.1 Bản đồ module

Hexagonal, 11 module nghiệp vụ. Bốn module liên quan trực tiếp tới kho:

| Module | Vai trò | Bảng |
|---|---|---|
| `catalog` | Hồ sơ thuốc (tên, `barcode`, `sale_price`, hoạt chất, đơn vị quy đổi) | `drugs`, `drug_units`, `drug_ingredients`, `drug_price_history` |
| `inventory` | **Tồn kho**: lô, chuyển động, số dư, cờ đối soát | `product_batches`, `stock_movements`, `stock_balances`, `stock_reconciliation_needed` |
| `procurement` | NCC, đơn mua, phiếu nhập | `suppliers`, `purchase_orders`, `purchase_order_items`, `goods_receipts`, `goods_receipt_items` |
| `analytics` | **Đề xuất nhập hàng** | `reorder_suggestions` |

Ranh giới được **cưỡng chế bằng máy**, không bằng quy ước: `import-linter` giữ 18 contract,
trong đó mỗi module có một contract *"domain không được import tầng ngoài hay framework"*.
Cross-module chỉ đi qua **port + adapter ở composition root** (`api/v1/cross_module.py`).

### 1.2 🔴 Tồn kho ĐÃ là event-sourced — đây là sự thật quan trọng nhất của bản audit

```
StockMovement (append-only, nguồn sự thật)
        │
        └──▶ StockBalance (projection: tồn theo drug × batch × branch)
```

`StockMovementORM` docstring nói thẳng: *"Append-only stock change (the source of truth for
on-hand levels)"*; `StockBalanceORM`: *"Projection of movements"*.

Kèm theo là một **chỉ mục duy nhất từng phần** chống ghi trùng khi phát lại:
`uq_movement_ref_batch (tenant_id, ref_type, ref_id, batch_id) WHERE ref_id IS NOT NULL`.
Docstring ghi rõ vì sao `batch_id` phải nằm trong khoá: một lượt xuất FEFO hợp lệ trải nhiều
lô và ghi mỗi lô một dòng cùng `ref_id` — bỏ `batch_id` ra là chặn nhầm nghiệp vụ đúng.

**Hệ quả cho Phase 15:** câu hỏi *"có nên dùng Event Sourcing / tách Inventory Ledger"* phần
lớn **đã được trả lời từ trước và đã trả tiền rồi**. Đề xuất "thêm Event Sourcing" ở giai
đoạn này sẽ là làm lại thứ đang chạy.

### 1.3 FEFO là hàm thuần, đã tách

`inventory/domain/fefo.py` — 56 dòng, không phụ thuộc gì ngoài `Decimal`/`date`. Nhận danh
sách `BatchAvailability`, trả `Allocation`. Ties theo thứ tự đầu vào (ổn định).

### 1.4 Đường đi của hàng

| Chiều | Đường |
|---|---|
| **Vào** | `POST /inventory/receive` (nhập tay) · hoặc `procurement` xác nhận GRN → sự kiện → `receive_from_goods_receipt` |
| **Ra** | `sales` hoàn tất đơn → sự kiện → `dispense_for_sale` (FEFO) · hoặc `POST /inventory/dispense` |
| **Hỏng giữa chừng** | `stock_reconciliation_needed` — cờ audit khi GRN đã xác nhận mà stock-in không vào trọn |

Cái cuối là điểm mạnh đáng ghi: hệ thống **không giả vờ** rằng nhập kho luôn thành công.

### 1.5 Đề xuất nhập hàng đã có (`analytics`)

`ReorderPolicy(window_days, lead_time_days, safety_stock_days)`, dự báo bằng **trung bình
động 90 ngày**, điểm đặt hàng = `velocity × (lead_time + safety_stock)`, đặt lên tới
`ORDER_UP_TO_FACTOR = 2×` điểm đặt hàng. Có `MIN_SALES_FOR_FORECAST = 3` — dưới ngưỡng thì
**từ chối bịa một con số nhu cầu**.

Đã nối dây: tốc độ bán (`sales`), tồn (`inventory`), tên thuốc (`catalog`), NCC gần nhất
(`procurement`), và **sink tạo PO nháp**. AI/heuristic **chỉ gợi ý**, người bấm mới thành PO.

## 2. Điểm mạnh (đừng phá)

| # | Điểm mạnh | Vì sao đừng đụng |
|---|---|---|
| 1 | **Event-sourced + projection** | Đã có, đã có chống ghi trùng ở tầng CSDL. Mọi tính năng mới nên **ghi thêm movement**, không sửa `stock_balances` trực tiếp |
| 2 | **FEFO thuần, tách riêng** | Thuật toán picking mới nên **bọc ngoài** nó, không thay nó |
| 3 | **Cờ đối soát khi nhập hỏng** | Khuôn có sẵn cho mọi loại lệch mới (kiểm kê, chuyển vị trí) |
| 4 | **Ranh giới cưỡng chế bằng `import-linter`** | Module mới sẽ được canh miễn phí — nhưng phải khai contract |
| 5 | **Quyền theo module, đã tách phạm vi** | `inventory.read/receive/dispense/reconcile` + `archive.read.chain` (quyền **phạm vi**, mới 31/07) — khuôn sẵn cho quyền kho |
| 6 | **Audit có sẵn 3 action kho** | `INVENTORY_STOCK_RECEIVED/DISPENSED/RECONCILIATION_RESOLVED` |
| 7 | **Số tiền/số lượng đã chuẩn hoá** | `Numeric(18,3)` cho lượng, `Numeric(18,2)` cho tiền — nhất quán toàn hệ |

## 3. Điểm yếu

| # | Điểm yếu | Bằng chứng |
|---|---|---|
| 1 | **Không có khái niệm VỊ TRÍ.** Đơn vị không gian nhỏ nhất là `branch_id` | `TenantScopedMixin` = `tenant_id + branch_id`, hết. `grep` "shelf/bin/zone/location" toàn repo = **0** |
| 2 | **`ReorderPolicy` là hằng số toàn cục**, không cấu hình được theo thuốc hay theo tenant | `lead_time_days: int = 7`, `safety_stock_days: int = 3` truyền từ service; docstring ghi *"per-tenant override is deferred to v2"* |
| 3 | **NCC không có thuộc tính mua hàng**: không `lead_time`, không `MOQ`, không giá theo NCC, không tỷ lệ giao đúng | `SupplierORM` chỉ có tên, mã số thuế, liên hệ, `is_active` |
| 4 | **Quan hệ thuốc ⇄ NCC là suy ra từ lịch sử**, không phải dữ liệu | `last_supplier_for_drug` đọc PO gần nhất. Không bảng `drug_suppliers` |
| 5 | **Barcode chỉ ở tầng thuốc** | `drugs.barcode`. Không barcode cho lô, không QR cho vị trí |
| 6 | **Không có kiểm kê** | `grep "cycle count\|stocktake\|kiểm kê"` = 0 nghiệp vụ |
| 7 | **Nhập hàng nhanh chưa có đường riêng** | `POST /inventory/receive` có tồn tại và **không đòi PO** — nhưng giao diện chưa có màn cho nó |
| 8 | **`quantity_received` trên `ProductBatch` là tổng tích luỹ**, không phải tồn | Tồn nằm ở `stock_balances`. Hai con số dễ bị đọc nhầm là một |

## 4. Thiếu nghiệp vụ so với yêu cầu V2

| Phase | Yêu cầu | Hiện trạng |
|---|---|---|
| 1 | Warehouse→Zone→Shelf→Bin→Location | ❌ **Không có gì** |
| 2 | Primary/Reserve/Overflow location | ❌ Không có |
| 3 | Picking assist sau khi quét | 🟡 FEFO có; **vị trí, lô, HSD chưa hiện ở màn quét** |
| 4 | Pick list nhiều thuốc | ❌ Không có |
| 5 | Nhập hàng gắn vị trí | ❌ Không có trường vị trí |
| 6 | Quick receiving không cần PO | 🟡 **API đã có**, thiếu màn |
| 7 | Smart purchase | ✅ **Phần lớn đã có**. Thiếu: seasonal trend, dead stock, min/max theo thuốc |
| 8 | Multi supplier | ❌ Không có bảng quan hệ |
| 9 | Stock initialization | 🟡 Dùng tạm `POST /inventory/receive`; **không phân biệt được với nhập mua** trong sổ |
| 10 | Shelf-first entry | ❌ Không có |
| 11 | Cycle count | ❌ Không có |
| 12 | Location map | ❌ Không có |
| 13 | Barcode → vị trí/lô/HSD | 🟡 Barcode→thuốc có; phần còn lại phụ thuộc Phase 1 |
| 14 | Audit đủ loại thao tác | 🟡 3/7 loại đã có; thiếu Init · Move · Pick · Cycle Count · Location Change |

## 5. Rủi ro khi mở rộng

| # | Rủi ro | Mức | Ghi chú |
|---|---|---|---|
| 1 | **Thêm `location_id` vào `stock_balances` làm vỡ khoá duy nhất** `uq_balance_batch (drug_id, batch_id, branch_id)` | 🔴 Cao | Tồn theo vị trí nghĩa là **một lô ở nhiều vị trí** ⇒ đổi hạt của projection. Đây là chỗ dễ phá dữ liệu nhất trong cả V2 |
| 2 | **FEFO hiện chọn theo LÔ, không theo VỊ TRÍ** | 🔴 Cao | Primary/Reserve (Phase 2) và FEFO (đang có) **có thể mâu thuẫn**: lô cận date nhất có thể nằm ở Reserve. Phải quyết cái nào thắng — đây là quyết định **nghiệp vụ**, không phải kỹ thuật |
| 3 | Chuyển vị trí (`Move`) là một loại chuyển động **không đổi tổng tồn** | 🟠 Vừa | `MovementType.TRANSFER` đã có trong enum **nhưng chưa ai dùng**. Dùng lại được, đừng thêm loại mới |
| 4 | Kiểm kê sinh chênh lệch ⇒ cần bút toán điều chỉnh có kiểm soát | 🟠 Vừa | `MovementType.ADJUST` đã có. Khuôn `stock_reconciliation_needed` tái dùng được |
| 5 | Multi-supplier đổi ngữ nghĩa `last_supplier_for_drug` | 🟠 Vừa | Analytics đang suy ra NCC từ PO gần nhất; có bảng quan hệ rồi thì nguồn sự thật đổi |
| 6 | **51 bảng hiện có**; V2 thêm ~8-10 bảng nữa | 🟡 Thấp | Không phải vấn đề kỹ thuật, là vấn đề người đọc |
| 7 | Máy dev **3,7 GB RAM** | 🟠 Vừa | Đã ghi ở `REMAINING_UI_ISSUES` mục 13. V2 nhiều màn ⇒ mỗi lần dựng lại giao diện tốn ~3 phút |

## 6. Đề xuất kiến trúc (tóm tắt — chi tiết ở `INVENTORY_ARCHITECTURE.md` khi tới bước đó)

### 6.1 Nguyên tắc

1. **`location` là một module MỚI, không nhét vào `inventory`.** Sơ đồ kho là dữ liệu cấu
   hình của cơ sở, vòng đời khác hẳn chuyển động hàng. Nhét chung sẽ làm `inventory` phình
   và làm contract `import-linter` của nó mất nghĩa.
2. **Không đổi khoá `uq_balance_batch`.** Thay vì sửa `stock_balances`, thêm một projection
   **thứ hai** `stock_balances_by_location`. Tồn tổng vẫn đọc chỗ cũ ⇒ **mọi mã hiện tại
   chạy nguyên vẹn**, kể cả FEFO, báo cáo, đề xuất nhập hàng.
3. **Vị trí là thuộc tính của CHUYỂN ĐỘNG**, không phải của lô. `stock_movements` thêm
   `from_location_id`/`to_location_id` **nullable** — dòng cũ để `NULL` nghĩa là *"không rõ
   vị trí"*, đọc được, không cần backfill.
4. **Dùng lại `MovementType.TRANSFER` và `ADJUST`** cho Move và Cycle Count. Không thêm loại.
5. **AI chỉ gợi ý** — giữ nguyên khuôn `analytics` đã có, mở rộng `ReorderPolicy` thay vì
   viết bộ thứ hai.

### 6.2 Vì sao KHÔNG tách Warehouse Service riêng (phản biện yêu cầu Phase 15 mục 5)

Tách service nghĩa là thêm một biên mạng, một vòng đời triển khai, một nguồn lỗi phân tán —
để đổi lấy điều gì? Nhà thuốc lớn nhất trong tầm nhìn là **một chuỗi**, không phải một trung
tâm phân phối. Ranh giới đang được cưỡng chế bằng `import-linter` **đã cho phần lớn lợi ích
của việc tách** mà không trả giá vận hành. Nếu sau này thật sự cần, module đã tách sạch thì
việc bóc ra thành service là cơ học.

Cùng lý do cho **CQRS**: hệ thống **đã có** dạng nhẹ của nó (movement ghi / balance đọc).
Dựng thêm khung CQRS đầy đủ là thêm từ vựng mà không thêm năng lực.

## 7. Điều phải hỏi Chain TRƯỚC khi code (quyết định nghiệp vụ, không phải kỹ thuật)

| # | Câu hỏi | Vì sao không tự quyết |
|---|---|---|
| 1 | **FEFO thắng hay Primary Location thắng** khi lô cận date nằm ở Reserve? | Đây là đánh đổi giữa **an toàn thuốc** (bán lô sắp hết hạn trước) và **năng suất quầy** (đi ít bước). Kỷ luật #3 nói quyết định nghiệp vụ luôn hỏi |
| 2 | Kiểm kê lệch thì **tự điều chỉnh tồn** hay **treo chờ duyệt**? | Chạm sổ sách và có thể chạm thuốc kiểm soát đặc biệt |
| 3 | Khởi tạo tồn kho có được coi là **nhập kho** trong báo cáo không? | Ảnh hưởng giá vốn và báo cáo doanh thu |
| 4 | Vị trí có **theo chi nhánh** không, hay dùng chung toàn chuỗi? | Quyết định hình dạng bảng, sửa sau rất đắt |

## 8. Kết luận Phase 0

Hệ thống **đã có nền tốt hơn yêu cầu V2 giả định**: event sourcing, FEFO thuần, cờ đối soát,
đề xuất nhập hàng có thật. Cái thiếu là **chiều không gian** — toàn bộ Phase 1-6, 10-13 đều
mọc từ đúng một khoảng trống: hệ thống biết *có bao nhiêu*, không biết *nằm ở đâu*.

⇒ Đề xuất: **Phase 1 (Storage Location) là điều kiện tiên quyết của 8 phase khác.** Làm nó
trước, làm đúng, rồi các phase còn lại phần lớn là giao diện và truy vấn.
