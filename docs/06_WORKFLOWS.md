# 06 — QUY TRÌNH NGHIỆP VỤ (Workflows)

> Các luồng nghiệp vụ chính dạng sequence/flow. Kết nối với FR trong [01_ANALYSIS.md](01_ANALYSIS.md).

---

## 1. Bán thuốc OTC tại POS (offline-first)

```mermaid
sequenceDiagram
    actor C as Khách hàng
    actor S as NV bán hàng
    participant POS as POS Client
    participant AI as Dược sĩ AI
    participant API as Backend
    participant INV as Inventory

    C->>S: Yêu cầu mua thuốc
    S->>POS: Quét barcode / chọn thuốc
    POS->>POS: Thêm vào giỏ (local)
    POS->>AI: (nếu bật) kiểm tra tương tác với đơn hiện có
    AI-->>POS: Cảnh báo/không có cảnh báo + nguồn
    S->>POS: Xác nhận thanh toán
    POS->>POS: Ghi SaleOrder local (client_uuid)
    Note over POS: Nếu offline → hàng đợi sync
    POS->>API: Sync SaleCompleted (idempotent)
    API->>INV: Trừ tồn theo FEFO
    API-->>POS: Xác nhận + số hóa đơn
```

---

## 2. Bán thuốc kê đơn (ETC) có kiểm soát

```mermaid
flowchart TD
    A[Tiếp nhận yêu cầu ETC] --> B{Có đơn thuốc hợp lệ?}
    B -- Không --> R1[Từ chối bán / hướng dẫn khám]
    B -- Có --> C[Nhập/nhận đơn: tay, ảnh, e-prescription]
    C --> D{Nguồn = ảnh?}
    D -- Có --> E[AI OCR + trích cấu trúc đơn]
    D -- Không --> F[Nhập tay các mục]
    E --> G[Dược sĩ xác thực đơn]
    F --> G
    G --> H[AI kiểm tra: tương tác, dị ứng, liều, chống chỉ định]
    H --> I{An toàn?}
    I -- Cảnh báo --> J[Dược sĩ đánh giá & quyết định]
    I -- OK --> K[Cấp phát]
    J --> K
    K --> L[Ghi lịch sử bệnh nhân + audit + sổ kiểm soát nếu thuốc đặc biệt]
    L --> M[Tạo SaleOrder gắn prescription_id]
```

> **Nguyên tắc an toàn:** bước H là *khuyến nghị*; bước J/K do **dược sĩ** quyết định. AI không tự cấp phát (NFR — human-in-the-loop).

---

## 3. Kiểm tra tương tác thuốc (Clinical/AI)

```mermaid
sequenceDiagram
    participant UC as Use-case (sale/rx)
    participant GW as AI Gateway
    participant RULE as Rule Engine (drug_interactions)
    participant RAG as RAG (pgvector)
    participant LLM as Claude

    UC->>GW: check(items, patient_profile)
    GW->>RULE: tra cứu tương tác đã biết (deterministic)
    RULE-->>GW: danh sách cặp tương tác + severity
    GW->>RAG: truy hồi tri thức liên quan (liều, chống chỉ định)
    RAG-->>GW: chunks + nguồn
    GW->>LLM: tổng hợp + diễn giải (có nguồn, không bịa)
    LLM-->>GW: khuyến nghị có cấu trúc + confidence
    GW->>GW: Guardrail: nếu thiếu nguồn/low-confidence → hạ cấp cảnh báo
    GW-->>UC: kết quả + log ai_recommendations
```

> **Lai (hybrid):** ưu tiên **rule engine tất định** cho tương tác đã biết; LLM chỉ *diễn giải & bổ sung*, không thay thế nguồn y khoa.

---

## 4. Nhập kho từ nhà cung cấp (Procurement → Inventory)

```mermaid
flowchart LR
    A[Analytics đề xuất nhập] --> B[Tạo PO]
    B --> C[Gửi NCC]
    C --> D[Hàng về: Goods Receipt]
    D --> E[Tạo product_batches: lô, hạn dùng, giá vốn]
    E --> F[stock_movement IN]
    F --> G[Cập nhật stock_balances]
    G --> H[Đối chiếu PO vs thực nhận]
```

---

## 5. Xuất kho theo FEFO

```mermaid
flowchart TD
    A[Yêu cầu xuất N đơn vị thuốc X tại chi nhánh Y] --> B[Lấy các lô còn hàng, chưa hết hạn]
    B --> C[Sắp xếp theo expiry_date tăng dần]
    C --> D{Đủ số lượng?}
    D -- Không --> E[Báo thiếu hàng / gợi ý thay thế AI]
    D -- Có --> F[Phân bổ lần lượt từ lô cận date nhất]
    F --> G[Ghi stock_movement OUT theo từng lô]
    G --> H[Cập nhật balances + ledger nếu thuốc kiểm soát]
```

---

## 6. Đồng bộ offline (Sync)

```mermaid
sequenceDiagram
    participant POS as POS (offline)
    participant Q as Local Queue
    participant API as Backend
    participant DB as Postgres

    Note over POS: Mất mạng — ghi giao dịch local
    POS->>Q: enqueue(SaleCompleted, client_uuid)
    Note over POS: Có mạng trở lại
    Q->>API: POST /sync (batch, client_uuid[])
    API->>DB: upsert idempotent theo client_uuid
    alt Xung đột (đã tồn tại)
        DB-->>API: bỏ qua (đã xử lý)
    else Mới
        DB-->>API: áp dụng + phát events
    end
    API-->>POS: kết quả từng client_uuid
```

---

## 7. Liên thông Dược Quốc gia (Compliance plugin)

```mermaid
flowchart LR
    A[Sự kiện: nhập/xuất/bán thuốc] --> B[outbox_events]
    B --> C[Worker đọc outbox]
    C --> D[Plugin dav_connector map dữ liệu]
    D --> E[Gửi tới cổng DAV]
    E --> F{Thành công?}
    F -- Có --> G[regulatory_submissions = SUCCESS]
    F -- Lỗi --> H[Retry backoff + cảnh báo]
```

---

## 8. Quy trình phát triển & CI/CD (DevWorkflow)

```mermaid
flowchart LR
    A[Branch feature] --> B[Pre-commit: ruff, mypy]
    B --> C[Push → CI]
    C --> D[Lint + import-linter]
    D --> E[Unit tests]
    E --> F[Integration tests: testcontainers]
    F --> G[Build images]
    G --> H{Nhánh main?}
    H -- Có --> I[Deploy staging]
    I --> J[Smoke/e2e]
    J --> K[Promote production thủ công]
    H -- Không --> L[Report PR]
```

---

## 9. Ma trận Workflow ↔ Module ↔ Event

| Workflow | Module chủ | Events phát ra |
|----------|-----------|----------------|
| Bán OTC | sales | `SaleCompleted` |
| Bán ETC | prescription + sales | `PrescriptionDispensed`, `SaleCompleted` |
| Kiểm tra tương tác | clinical | `AIRecommendationCreated` |
| Nhập kho | procurement + inventory | `GoodsReceived`, `StockMovedIn` |
| Xuất FEFO | inventory | `StockMovedOut` |
| Sync offline | sales | `SaleCompleted` (idempotent) |
| Liên thông DAV | compliance | `RegulatorySubmitted` |
