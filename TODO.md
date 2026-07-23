# TODO — AI Pharmacy OS

> Trạng thái công việc theo hạng mục. Cập nhật cuối: **2026-07-23** (rà lại đối chiếu
> `PROJECT_STATE.md`, mục A6 danh sách ưu tiên đã duyệt — chỉ sửa dòng đã xác nhận lại bằng lệnh
> thật/PROJECT_STATE, không rà toàn bộ file để tránh sai sót do thiếu bối cảnh phiên cũ hơn).
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
- [x] Audit cho `inventory` (2 action: `INVENTORY_STOCK_RECEIVED`/`INVENTORY_STOCK_DISPENSED`, chỉ
      2 endpoint HTTP con người gõ tay — không audit 2 use-case cross-module tự động vì đã có vết ở
      nơi phát sinh thật) — **XONG 2026-07-23** (PROJECT_STATE §7w).
- [x] Audit cho `catalog` (1 action: `CATALOG_DRUG_CREATED`) — **XONG 2026-07-23** (PROJECT_STATE
      §7z). **⇒ Mạch audit 5 module GĐ chọn đã đóng — 9/9 module nghiệp vụ nay đều có audit trail**
      (xem bảng tổng kết PROJECT_STATE §7z).

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

- [x] ~~`api/deps.py`: request-context dev-header tạm — thay bằng JWT thật khi có IAM~~ — **module `iam` thật đã XONG
      (2026-07-23, PROJECT_STATE §7k)**: JWT thật, `branch_id` ký trong token, dev-header fallback mặc định
      **TẮT** (`SECURITY__ALLOW_DEV_AUTH=false`, fail-closed).
- [ ] FK `drugs.atc_code → atc_codes` chưa bật (đang lưu string). Cân nhắc bật khi seed ATC là bắt buộc.
- [x] ~~Uniqueness của `registration_no` (SĐK) chưa enforce~~ — bật `uq_drugs_tenant_registration_no` trong migration `0005_compliance` (Compliance C.2, 2026-07-21). `barcode` vẫn chỉ chặn ở tầng ứng dụng (không phải nợ mới, không đổi).
- [ ] `StarletteDeprecationWarning` (httpx + TestClient) — không ảnh hưởng, theo dõi khi nâng cấp.

---

### Sprint 4 — Sales / POS offline *(BACKEND HOÀN THÀNH 2026-07-21)*
- [x] Module `sales`: SalesOrder, items, payments, returns (domain thuần, Hexagonal 4 lớp).
- [x] Idempotency `client_uuid` + `/sync/sales` (offline-first, upsert 200).
- [x] Cross-module: `SaleCompleted` → inventory FEFO dispense (nối ở `api/v1/cross_module.py`; idempotent cấp đơn; thiếu tồn → `StockShortfallDetected`, không chặn bán).
- [x] Rule chặn ETC thiếu đơn (`ensure_rx_for_etc`) — catalog là nguồn thẩm quyền qua port `DrugInfoProvider` + adapter.
- [x] ~~**Nợ Sprint 4 (S4.6, tách đợt sau):** khởi tạo `frontend/` (Next.js + Dexie) POS tối thiểu + hàng đợi offline gọi `/sync/sales`.~~ —
      **XONG 5/5 bước (2026-07-23)**: đăng nhập JWT thật+chọn chi nhánh, tra thuốc, giỏ hàng, thanh toán
      `POST /sales`, hàng đợi offline Dexie tự đồng bộ khi có mạng lại. Xem `frontend/README.md`. Chưa
      click-through trình duyệt thật (môi trường không có browser tool).
- [ ] **Nợ Sprint 4:** persist trả hàng (`register_return`) ở tầng use-case + trả tồn (cross-module) — domain đã có, use-case/khôi phục tồn chưa làm (ngoài DoD lần này).
- [x] Audit cho `sales` (1 action: `SALE_COMPLETED`, ghi 1 lần/`client_uuid`, không nhân đôi khi
      sync lại) — **XONG 2026-07-23** (PROJECT_STATE §7v). **Còn lại 4/9 module chưa có audit:**
      `inventory`/`procurement`/`clinical`/`catalog` (GĐ chọn thứ tự tiếp theo).

### Compliance — kéo sớm từ Sprint 7 *(C.1–C.5 XONG, ĐÃ ĐÓNG — PROJECT_STATE §7b; router mount 2026-07-23 §7q)*
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
- [x] C.5 — cross-module: `SaleCompleted`/controlled dispense → ghi ledger + enqueue sync log XONG (PROJECT_STATE §7b, ĐÃ ĐÓNG).
- [x] Router HTTP cho `compliance` (ledger/tenant-config/sync-logs) — **mount 2026-07-23** (PROJECT_STATE §7q); trước đó
      module chỉ có domain/app/infra, không endpoint nào.
- [x] Audit cho `compliance` (2 action: `CONTROLLED_LEDGER_ENTRY_RECORDED`, `TENANT_COMPLIANCE_CONFIG_SET`) — **XONG
      2026-07-23** (PROJECT_STATE §7r).
- [ ] **Nguồn còn thiếu** (chặn phần liên quan, xem cảnh báo đầu docs/13): NĐ163/2025, NĐ90/2026, đặc tả API DAV, văn bản
      kê đơn ngoại trú hiện hành (cho rule C.3.1 ETC). **TT11/2025 đã có** (`docs/legal/Thông-tư-11-2025-TT-BYT.SUMMARY.md`,
      xác nhận lại 2026-07-23) — bớt 1/5 so với danh sách gốc.

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
- [x] **5.5.4 cross-module** — auto-check tương tác ở sale/prescription. Hoãn sang Sprint 6 Bước 2 và **đã XONG ở đó**
      *(2026-07-22)* — xem Sprint 6 › Bước 2 bên dưới (gồm cả nối dị ứng KH).
- [x] Audit cho `clinical` (2 action: `CLINICAL_INTERACTION_CHECKED`/`CLINICAL_RECOMMENDATION_ACCEPTED`
      — không audit `check_allergies`/settings vì không có gì để ghi vết hoặc tần suất quá thấp) —
      **XONG 2026-07-23** (PROJECT_STATE §7y). **Còn lại 1/9 module chưa có audit:** `catalog`.

**Quyết định đã chốt (2026-07-22):**
- [x] **Catalog thiếu mô hình hoạt chất** → chốt **(b) tách sang Sprint 6**, KHÔNG thêm vội vào catalog trong S5.5. Gộp cùng mạch dị
      ứng khách hàng (`crm`). Không đổi 10 contract sẵn có.
- [x] **`drug_knowledge_chunks` (RAG) — HOÃN**, chưa tạo bảng. Lý do: là blocker (nguồn tri thức dược thật + bản quyền, bảng rỗng
      vô nghĩa cho A1) **và** cột `vector(1536)` (pgvector) phá test-harness SQLite (`create_all`).
      Sẽ tạo bảng + index embedding + migration riêng **khi làm RAG thật** (gỡ được blocker), test đầy đủ khi đó.
- [ ] Nối `core.ai.LLMProvider` → Claude thật (`AnthropicProvider`) — `# BLOCKER: AI__API_KEY thật`. Nay dùng `MockLLMProvider`.

### Sprint 5 — Prescription (đã có từ S5.1–S5.4)
- [x] Module `prescription` (đơn thuốc nháp, xác thực, cấp phát) — Hexagonal 4 lớp, migration `0004`.
- [x] Audit cho `prescription` (4 action: created/approved/rejected/dispensed) — **XONG 2026-07-23**
      (PROJECT_STATE §7r) — đúng câu hỏi thanh tra dược hay hỏi đầu tiên ("ai đã cấp phát đơn này").

> Điểm tích hợp đã sẵn sàng: `Drug.is_prescription_required()`, `core.ai.LLMProvider` port + `MockLLMProvider`,
> bảng `drug_interactions` (+seed mẫu). `drug_knowledge_chunks` HOÃN (xem trên).

### Sprint 6 — Procurement & CRM (backend ĐÃ ĐÓNG 2026-07-22 — PROJECT_STATE §9, đạt DoD lõi)
- [x] **Bước 1 — mô hình hoạt chất trong `catalog`, domain thuần** *(2026-07-22)* — `ActiveIngredient` (hoạt chất, global reference,
      không tenant-scope) + `DrugIngredient` (hàm lượng: `ingredient_id`+`amount>0`+`unit`) + `Drug.add_ingredient()` (chặn trùng,
      cho phép nhiều hoạt chất/thuốc — thuốc phối hợp là bình thường); port `ActiveIngredientRepository` (chưa impl). Không đổi
      infra/migration/interface catalog hiện có (field `ingredients` default rỗng, tương thích ngược). **KHÔNG động clinical/compliance.**
      4 cổng xanh (**245 test**, 10 contract kept/0).
- [x] **Bước 1 tiếp — app+infra+migration hoạt chất** *(2026-07-22)* — `SqlAlchemyActiveIngredientRepository` (global, session-only)
      + ORM `ActiveIngredientORM` (unique `name`)/`DrugIngredientORM` (FK `drugs.id`+`active_ingredients.id`) + mapper + `CatalogService`
      validate `ingredient_id` tồn tại khi tạo thuốc (404 nếu không) + `CreateDrugRequest`/`DrugResponse` mở rộng `ingredients`.
      Migration `0008_catalog_ingredients` live Postgres, `alembic check` sạch, downgrade/upgrade OK. 4 cổng xanh (**249 test**,
      10 contract kept/0). **⇒ Bước 1 XONG hoàn toàn — sẵn sàng cho Bước 2.**
- [x] ~~**Nợ mới:** chưa có HTTP endpoint tạo/liệt kê `active_ingredients`~~ — **XONG (2026-07-23)**:
      `POST`/`GET /api/v1/active-ingredients`, tái dùng quyền `catalog.create`/`catalog.read` có sẵn,
      không migration mới. Xem PROJECT_STATE §7u.
- [x] **Bước 2 — 5.5.4 auto-check tương tác + dị ứng, XONG hoàn toàn** *(2026-07-22, Opus, phiên riêng, từng bước duyệt)* —
      cross-module ở composition root (`api/v1/cross_module.py`), **cảnh báo không chặn** (hậu-commit; quyết định pháp lý sếp chốt).
      4 bước con, mỗi bước 4 cổng xanh:
      - **B1** `catalog.get_drug_ingredients(drug_id) -> [(ingredient_id, name)]` (hạ tầng chung, nội bộ catalog) — commit `68a0d74`.
      - **B2** `wire_safety_checks`: bắt `SaleCompleted`+`PrescriptionDispensed` → `clinical.check_interactions` qua tên hoạt chất;
        audit `AiRecommendation`; tenant-gated (`TenantAiSettings`, default OFF); bỏ qua giỏ <2 hoạt chất — commit `aeea74d`.
      - **B3a** `clinical.check_allergies` thuần (domain `AllergyAlert`+`find_allergy_alerts`, khớp theo `ingredient_id`; **không**
        cổng AI, **không** persist — sếp chốt) — commit `f0281f2`.
      - **B3b** nối dị ứng KH vào handler dispense: đọc `crm.get_customer(customer_id).allergies` (chỉ luồng prescription — sale
        không có customer_id); log `allergy_warning_raised` — commit `2de9d2b`.
      **304 test, 11 contract kept/0 — module-independence GIỮ NGUYÊN** (api compose catalog+clinical+crm+prescription; các module
      không import nhau).
- [x] **Module `crm` — domain thuần** *(2026-07-22)* — `Customer` (aggregate) + `Allergy` (theo `ingredient_id`, khớp
      `catalog.ActiveIngredient`) + `Condition` (ICD-10) + `MedicationHistoryEntry` (tối giản, chưa nối event). Đã hỏi sếp
      trước khi code về overlap với `compliance.CustomerDetail` — chốt tách biệt hoàn toàn (xem PROJECT_STATE §7e). Port
      `CustomerRepository` chưa impl. Contract `crm-domain-innermost` (**11/0**). 4 cổng xanh (**258 test**).
- [x] **`crm` — app+infra+migration+interface, XONG hoàn toàn** *(2026-07-22)* — `SqlAlchemyCustomerRepository` (tenant-scoped)
      + ORM `CustomerORM`/`CustomerAllergyORM`(**FK ingredient_id→active_ingredients**, xuyên module đầu tiên nhưng an toàn
      với import-linter — xem PROJECT_STATE §7e)/`CustomerConditionORM`/`CustomerMedicationHistoryORM` + mapper. `CrmService`
      (create_customer/add_allergy/add_condition/get_customer/list_customers). Router `/customers/*` đủ (POST/GET/list +
      allergies/conditions), wire vào `api/v1`. Migration `0009_crm_customers` live Postgres, `alembic check` sạch,
      downgrade/upgrade OK. 4 cổng xanh (**272 test**, 11 contract kept/0).
- [x] ~~**Nợ:** `add_allergy` không validate ingredient ở app layer → `ingredient_id` sai trả 500 thô~~ — **đã gỡ
      (2026-07-22)**: `CrmService.add_allergy` bắt `IntegrityError` từ FK → `NotFoundError` (404), không cần cross-module
      với catalog (đã hỏi sếp trước vì cách "chuẩn" — validate qua `ActiveIngredientRepository` — là cross-module thật,
      cần Opus theo quy tắc S4.5/S5.4/C.5). Sửa kèm: `core/db/session.build_engine()` bật `PRAGMA foreign_keys=ON` cho
      SQLite để test thấy được lỗi này (trước đó SQLite mù, chỉ Postgres sống mới lộ bug). Xác nhận thủ công trên Postgres
      sống. +2 test. 4 cổng xanh (**274 test**).
- [ ] Chưa có use-case ghi `MedicationHistoryEntry` qua HTTP (chờ nối event `SaleCompleted`/`PrescriptionDispensed`,
      cross-module, cùng Bước 2).
- [x] Nối **dị ứng KH** vào kiểm tra clinical *(2026-07-22)* — XONG cùng Bước 2/5.5.4 ở trên (B3a+B3b). Chỉ luồng prescription;
      bán lẻ OTC hoãn (cần thêm `customer_id` vào `SalesOrder` + migration — sếp chốt hoãn).
- [x] **Feature flag AI theo tenant (SaaS), XONG hoàn toàn** *(2026-07-22)* — `clinical.TenantAiSettings` (entity mới,
      mặc định tắt) + `TenantAiSettingsRepository`/ORM/repo. Tự quyết tạo bảng riêng trong `clinical` thay vì tái dùng
      `compliance.tenant_compliance_configs` (báo lý do trong PROJECT_STATE §7f — tránh cross-module thật + 2 khái niệm
      không liên quan). `check_interactions` gate qua `_ensure_ai_enabled` (`FeatureDisabledError`, 403); thêm
      `GET`/`PUT /clinical/settings`. Xoá `AISettings.enable_clinical_ai` (cờ chết) khỏi config toàn cục. Migration
      `0010_clinical_tenant_ai_settings` live Postgres, `alembic check` sạch, downgrade/upgrade OK. 4 cổng xanh
      (**283 test**, 11 contract kept/0, không cross-module mới).
- [x] Module `procurement` (Supplier, PO, GRN → inventory IN) — **XONG đủ 4 lớp** (domain `55d2586` → app/infra/migration
      `0011` `518dafe` → interface `7a53457`), cross-module GRN xác nhận → tạo lô inventory. Xem PROJECT_STATE §9.
- [x] Audit cho `procurement` (2 action: `PROCUREMENT_PO_ORDERED`/`PROCUREMENT_GRN_CONFIRMED`, chỉ
      2/7 use-case — bỏ qua CRUD hành chính) — **XONG 2026-07-23** (PROJECT_STATE §7x). **Còn lại
      2/9 module chưa có audit:** `clinical`/`catalog`.

---

## Cách chạy demo

```bash
source .venv/bin/activate          # venv của backend (đã cài -e ".[dev]")
python demo_preview.py             # không cần Postgres (SQLite in-memory)
# NO_COLOR=1 python demo_preview.py  # tắt màu ANSI
```
