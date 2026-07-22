# TODO — AI Pharmacy OS

> Trạng thái công việc theo hạng mục. Cập nhật cuối: **2026-07-22**.
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
- [x] ~~Uniqueness của `registration_no` (SĐK) chưa enforce~~ — bật `uq_drugs_tenant_registration_no` trong migration `0005_compliance` (Compliance C.2, 2026-07-21). `barcode` vẫn chỉ chặn ở tầng ứng dụng (không phải nợ mới, không đổi).
- [ ] `StarletteDeprecationWarning` (httpx + TestClient) — không ảnh hưởng, theo dõi khi nâng cấp.

---

### Sprint 4 — Sales / POS offline *(BACKEND HOÀN THÀNH 2026-07-21)*
- [x] Module `sales`: SalesOrder, items, payments, returns (domain thuần, Hexagonal 4 lớp).
- [x] Idempotency `client_uuid` + `/sync/sales` (offline-first, upsert 200).
- [x] Cross-module: `SaleCompleted` → inventory FEFO dispense (nối ở `api/v1/cross_module.py`; idempotent cấp đơn; thiếu tồn → `StockShortfallDetected`, không chặn bán).
- [x] Rule chặn ETC thiếu đơn (`ensure_rx_for_etc`) — catalog là nguồn thẩm quyền qua port `DrugInfoProvider` + adapter.
- [ ] **Nợ Sprint 4 (S4.6, tách đợt sau):** khởi tạo `frontend/` (Next.js + Dexie) POS tối thiểu + hàng đợi offline gọi `/sync/sales`.
- [ ] **Nợ Sprint 4:** persist trả hàng (`register_return`) ở tầng use-case + trả tồn (cross-module) — domain đã có, use-case/khôi phục tồn chưa làm (ngoài DoD lần này).

### Compliance — kéo sớm từ Sprint 7 *(C.1–C.4 XONG 2026-07-21, DỪNG chờ lệnh C.5)*
- [x] Spec pháp lý khóa: [docs/13_COMPLIANCE_SPEC.md](docs/13_COMPLIANCE_SPEC.md) đối chiếu văn bản gốc
      (`docs/legal/*.docx`: QĐ540, TT20/2017, QĐ1867) + code thật (`catalog`/`inventory`) — bảng Traceability đầu file.
- [x] C.1 — domain thuần: `ControlledSubstanceCategory`, `NationalDrugRecord` (23 trường Bảng 1 QĐ540),
      `ControlledLedgerEntry`/`CustomerDetail` (Phụ lục XXI), converter helpers, rule GN/HT/TC +
      `EtcPrescriptionPolicy` (feature-flag tắt mặc định — nguồn C.3.1 chưa xác định), read-port `DrugMasterProvider`.
      Contract `compliance-domain-innermost` (**9/0**).
- [x] C.2 — application (`ComplianceService`: record_controlled_entry/get_ledger_entry/set_tenant_config/get_tenant_config)
      + infrastructure + migration `0005_compliance` (`controlled_ledger_entries`, `tenant_compliance_configs` mới;
      `uq_drugs_tenant_registration_no` bật trên `drugs` cùng migration) — live trên Postgres, `alembic check` sạch,
      downgrade/upgrade OK.
- [x] C.3 — `interface/schemas.py` (`RecordControlledEntryRequest` với `model_validator` rule C.3,
      `SetTenantComplianceConfigRequest` cỡ 12) + `interface/export.py` (`to_national_drug_record_export`,
      23-field DTO dùng converter helpers, enforce cỡ tối đa Bảng 1). Chưa có router/endpoint HTTP.
- [x] C.4 — `NationalSyncLog` (state machine PENDING→SENT→ACK/FAILED, retry) + port `NationalDrugDbGateway`
      + `NationalSyncService.push_payload` (idempotent, best-effort) + migration `0006_national_sync_log`.
      `MockNationalDrugDbGateway` ở composition root (`api/v1/national_sync.py`, `# BLOCKER: DAV API spec`,
      KHÔNG endpoint thật) + `wire_national_sync`. Live Postgres, `alembic check` sạch, downgrade/upgrade OK.
- [ ] C.5 (Opus, từng bước chờ duyệt) — cross-module: `SaleCompleted`/controlled dispense → ghi ledger + enqueue sync log
      (gọi `NationalSyncService.push_payload`). Cấp `compliance.sync.push`/`compliance.ledger.write` cho system-context.
- [ ] **Nguồn còn thiếu** (chặn phần liên quan, xem cảnh báo đầu docs/13): TT11/2025, NĐ163/2025, NĐ90/2026,
      đặc tả API DAV, văn bản kê đơn ngoại trú hiện hành (cho rule C.3.1 ETC).

### Sprint 5 — Clinical AI (S5.5, mock LLM only)
- [x] **5.5.1 domain** — `clinical/domain`: `DrugInteraction` (cặp hoạt chất canonical), `AiRecommendation`
      (audit bất biến + `accept()`), engine `find_interactions` + guardrail `requires_pharmacist_review`.
- [x] **5.5.2 app+infra+migration** *(2026-07-22)* — `ClinicalService.check_interactions/get_recommendation/accept_recommendation`;
      ORM+mapper+repo cho `drug_interactions`+`ai_recommendations`; migration `0007_clinical` (live Postgres, `alembic check`
      sạch, downgrade/upgrade sạch); `MockLLMProvider` ở `core/ai` (KHÔNG gọi API); seed 5 cặp tương tác **mẫu**
      (`seed_drug_interactions`, idempotent — nguồn `SAMPLE …`, không chính thức); quyền `clinical.check`/`clinical.accept`
      thêm vào dev context + system permissions test. 4 cổng xanh (**233 test**, 10 contract kept/0).
- [x] **5.5.3 interface** *(2026-07-22)* — `interface/schemas.py` + router `/clinical/*` (`POST /clinical/check-interactions`,
      GET/accept recommendation); DI: `bootstrap` đăng ký `LLMProvider → MockLLMProvider`, `api/v1` nối `register_clinical`.
      e2e HTTP thật `test_clinical_api_e2e.py` (6) — response có **nguồn + confidence**, mock (không API). **⇒ Sprint 5 DONE mức MOCK.**
- [ ] **5.5.4 cross-module** — auto-check tương tác ở sale/prescription. **BỊ CHẶN** bởi mô hình hoạt chất → **chính thức hoãn sang
      Sprint 6 Bước 2** (KHÔNG quay lại trong Sprint 5; cần Opus + phiên riêng, cross-module rủi ro cao).

**Quyết định đã chốt (2026-07-22):**
- [x] **Catalog thiếu mô hình hoạt chất** → chốt **(b) tách sang Sprint 6**, KHÔNG thêm vội vào catalog trong S5.5. Gộp cùng mạch dị
      ứng khách hàng (`crm`). Không đổi 10 contract sẵn có.
- [x] **`drug_knowledge_chunks` (RAG) — HOÃN**, chưa tạo bảng. Lý do: là blocker (nguồn tri thức dược thật + bản quyền, bảng rỗng
      vô nghĩa cho A1) **và** cột `vector(1536)` (pgvector) phá test-harness SQLite (`create_all`).
      Sẽ tạo bảng + index embedding + migration riêng **khi làm RAG thật** (gỡ được blocker), test đầy đủ khi đó.
- [ ] Nối `core.ai.LLMProvider` → Claude thật (`AnthropicProvider`) — `# BLOCKER: AI__API_KEY thật`. Nay dùng `MockLLMProvider`.

### Sprint 5 — Prescription (đã có từ S5.1–S5.4)
- [x] Module `prescription` (đơn thuốc nháp, xác thực, cấp phát) — Hexagonal 4 lớp, migration `0004`.

> Điểm tích hợp đã sẵn sàng: `Drug.is_prescription_required()`, `core.ai.LLMProvider` port + `MockLLMProvider`,
> bảng `drug_interactions` (+seed mẫu). `drug_knowledge_chunks` HOÃN (xem trên).

### Sprint 6 — Procurement & CRM (ĐANG MỞ, 2026-07-22)
- [x] **Bước 1 — mô hình hoạt chất trong `catalog`, domain thuần** *(2026-07-22)* — `ActiveIngredient` (hoạt chất, global reference,
      không tenant-scope) + `DrugIngredient` (hàm lượng: `ingredient_id`+`amount>0`+`unit`) + `Drug.add_ingredient()` (chặn trùng,
      cho phép nhiều hoạt chất/thuốc — thuốc phối hợp là bình thường); port `ActiveIngredientRepository` (chưa impl). Không đổi
      infra/migration/interface catalog hiện có (field `ingredients` default rỗng, tương thích ngược). **KHÔNG động clinical/compliance.**
      4 cổng xanh (**245 test**, 10 contract kept/0).
- [ ] **Bước 1 tiếp — app+infra+migration hoạt chất** — `ActiveIngredientRepository` impl (SQLAlchemy) + ORM `DrugIngredientORM`
      (FK `drugs.id`+`active_ingredients.id`) + mapper + cập nhật `DrugRepository`/mappers để persist `Drug.ingredients` + migration
      mới (live Postgres, `alembic check` sạch, downgrade/upgrade) + có thể mở rộng `catalog/interface/schemas.py`.
- [ ] **Bước 2 — 5.5.4 auto-check tương tác** (cần Opus + phiên riêng) — phụ thuộc Bước 1 tiếp xong.
- [ ] Module `crm` (Customer, dị ứng, bệnh nền, lịch sử) + nối dị ứng KH vào kiểm tra clinical.
- [ ] Feature flag AI theo tenant (SaaS) — `enable_clinical_ai` từ toàn cục sang theo tenant.
- [ ] Module `procurement` (Supplier, PO, GRN → inventory IN).

---

## Cách chạy demo

```bash
source .venv/bin/activate          # venv của backend (đã cài -e ".[dev]")
python demo_preview.py             # không cần Postgres (SQLite in-memory)
# NO_COLOR=1 python demo_preview.py  # tắt màu ANSI
```
