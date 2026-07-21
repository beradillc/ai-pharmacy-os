# TODO — AI Pharmacy OS

> Trạng thái công việc theo hạng mục. Cập nhật cuối: **2026-07-21**.
> Nguồn sự thật tổng quan: [PROJECT_STATE.md](PROJECT_STATE.md). Lộ trình: [ROADMAP.md](ROADMAP.md).

---

## ✅ Đã hoàn thành

### Sprint 1 — Thiết kế
- [x] 12 tài liệu `docs/` + README/ROADMAP/PROJECT_STATE.

### Sprint 2 — Kernel
- [x] core: config, DI, event bus, UoW, security, audit, AI port, plugin loader, errors.
- [x] API v1 + health, Alembic `0001` (pgvector), docker-compose, CI, Makefile.

### Sprint 3 — Catalog & Inventory
- [x] Module `catalog` (Drug, quy đổi đơn vị, RxClass) — Hexagonal 4 lớp.
- [x] Module `inventory` (ProductBatch, StockMovement event-sourced, FEFO, balances).
- [x] API v1: `/drugs`, `/inventory/{receive,dispense,on-hand,alerts/near-expiry}`.
- [x] Migration `0002` (6 bảng) live + reversible; seed ATC idempotent.
- [x] Contract import-linter: domain-purity + module-independence.

### Demo & Self-Refine *(2026-07-21)*
- [x] **`demo_preview.py`** — script độc lập, chạy end-to-end trên SQLite in-memory:
      tạo Drug OTC/ETC, quy đổi đơn vị, thuật toán `allocate_fefo`, nhập/xuất kho FEFO,
      cảnh báo cận date, và các edge case (xuất quá tồn, nhập 0, lô rỗng). In console trực quan.
      Phần Clinical Safety **ghi rõ CHƯA hiện thực** (Sprint 5), không bịa kết quả.
- [x] **Self-refine** `backend/src/pharmacy_os/modules/`:
      - [x] Bổ sung docstring cho các use-case public (catalog & inventory service) + `signed_quantity`.
      - [x] Rà edge case: qty=0 (chặn), demand=0 (chặn), lô rỗng → ConflictError, on_hand thuốc lạ = 0,
            barcode trùng cùng tenant (chặn) / khác tenant (cho phép). Thêm `tests/integration/test_edge_cases.py` (8 test).
      - [x] Type hints: đã đầy đủ từ trước (mypy strict pass 92 file) — không phát sinh thiếu sót mới.
- [x] Gate xanh sau refactor: `pytest` **54** · `mypy` strict · `ruff`/format · `import-linter` 6/0.

---

## ⚠️ Nợ kỹ thuật (theo dõi, chưa chặn)

- [ ] `api/deps.py`: request-context **dev-header tạm** — thay bằng JWT thật khi có IAM (Sprint 6). Prod đã chặn unauth.
- [ ] FK `drugs.atc_code → atc_codes` chưa bật (đang lưu string). Cân nhắc bật khi seed ATC là bắt buộc.
- [ ] Uniqueness của `registration_no` (SĐK) chưa enforce — hiện chỉ chặn trùng `barcode` theo tenant.
- [ ] `StarletteDeprecationWarning` (httpx + TestClient) — không ảnh hưởng, theo dõi khi nâng cấp.

---

### Sprint 4 — Sales / POS offline *(BACKEND HOÀN THÀNH 2026-07-21)*
- [x] Module `sales`: SalesOrder, items, payments, returns (domain thuần, Hexagonal 4 lớp).
- [x] Idempotency `client_uuid` + `/sync/sales` (offline-first, upsert 200).
- [x] Cross-module: `SaleCompleted` → inventory FEFO dispense (nối ở `api/v1/cross_module.py`; idempotent cấp đơn; thiếu tồn → `StockShortfallDetected`, không chặn bán).
- [x] Rule chặn ETC thiếu đơn (`ensure_rx_for_etc`) — catalog là nguồn thẩm quyền qua port `DrugInfoProvider` + adapter.
- [ ] **Nợ Sprint 4 (S4.6, tách đợt sau):** khởi tạo `frontend/` (Next.js + Dexie) POS tối thiểu + hàng đợi offline gọi `/sync/sales`.
- [ ] **Nợ Sprint 4:** persist trả hàng (`register_return`) ở tầng use-case + trả tồn (cross-module) — domain đã có, use-case/khôi phục tồn chưa làm (ngoài DoD lần này).

## ⏳ Chưa hiện thực (theo ROADMAP — KHÔNG demo/bịa)

### Sprint 5 — Prescription & Clinical AI
- [ ] Module `prescription` (đơn thuốc nháp, xác thực, cấp phát).
- [ ] **`ClinicalSafetyEngine`**: kiểm tra dị ứng theo hoạt chất (xử lý danh sách dị ứng rỗng),
      tương tác thuốc chéo (rule engine + bảng `drug_interactions`), kiểm tra liều.
- [ ] Nối `core.ai.LLMProvider` → Claude; RAG trên `drug_knowledge_chunks` (pgvector).

> Điểm tích hợp đã sẵn sàng cho Sprint 5: `Drug.is_prescription_required()`, `core.ai.LLMProvider` port,
> ERD `drug_interactions` / `drug_knowledge_chunks`.

---

## Cách chạy demo

```bash
source .venv/bin/activate          # venv của backend (đã cài -e ".[dev]")
python demo_preview.py             # không cần Postgres (SQLite in-memory)
# NO_COLOR=1 python demo_preview.py  # tắt màu ANSI
```
