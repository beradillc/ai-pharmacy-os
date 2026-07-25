# PROJECT_STATE — AI Pharmacy OS

> Nguồn sự thật về **trạng thái hiện tại** của dự án. Cập nhật mỗi khi có thay đổi quan trọng.
> Cập nhật cuối: **2026-07-25** · Sprint hiện tại: **Sprint 7 (Compliance & Analytics) — ✅ ĐÓNG (DoD đạt, verify trên Postgres thật, §7ap)**. Sprint 1–6 đã đóng; Sprint 5 DONE mức MOCK (`# BLOCKER: AI__API_KEY` thật). Sprint 8 **chưa mở** — chờ lệnh Chain.
>
> **Kế tiếp:** 2 blocker nền cũ (§7j) đã gỡ 1 — RBAC/IAM thật XONG (§7k), nên hồ sơ KH đã làm được và **đã xong**; còn lại **tích điểm KH** (chưa làm, phải qua [docs/14](docs/14_FEATURE_PROCESS.md)) và **`docs/legal/` vẫn thiếu** Luật BVDLCN 91/2025, Luật Dược, NĐ 356/2025, GPP. Nợ mang sang sau Sprint 7: report đợt 2, retry DAV lên outbox, tồn-âm khi outbox async, `analytics` v2, FE cho các module đã có backend.

> ⚠️ **Lưu ý vận hành — trạng thái docker/hạ tầng trong tài liệu này là ảnh chụp tại thời điểm ghi, KHÔNG phải trạng thái sống.**
> Container có thể tự `Exited` giữa các phiên dù tài liệu ghi "đang chạy"/"healthy" (đã xảy ra 2026-07-22: postgres Exited 5h,
> redis Exited 18h dù §7b ghi "đang chạy healthy"). **Luôn chạy `docker compose ps` để xác nhận thực tế mỗi khi resume phiên —
> không tin nội dung mục "Hạ tầng dev"/"Hạ tầng còn mở" trong tài liệu.**

---

## 1. Trạng thái tổng quan

| Hạng mục          | Trạng thái                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| Giai đoạn         | Giai đoạn 3 — Vận hành (Sprint 7 đóng 2026-07-25); kế tiếp Giai đoạn 4                                |
| Sprint            | **Sprint 7 — Compliance & Analytics ✅ ĐÓNG (2026-07-25)** · Sprint 1–6 đã đóng · Sprint 5 DONE mức MOCK (`# BLOCKER: AI__API_KEY` thật) |
| Tình trạng Sprint | ✅ **Sprint 7 ĐÓNG, DoD đạt và đã verify trên Postgres thật** (§7ap): `iam` thật · `audit_logs` persist + **audit query dashboard** · hồ sơ sức khỏe KH (qua cổng docs/14) · `compliance` C.1–C.5 + router · **transactional outbox** + retention · **report xuất khẩu đợt 1** (doanh thu ngày/tuần/tháng/chi nhánh/nhân viên + tồn kho theo lô/HSD) · **module `analytics`** (dự báo 90 ngày, mốc tái đặt, đề xuất → PO nháp, dashboard). **Nợ mang sang (đã ghi rõ, không tính DoD):** report đợt 2 (không bắt buộc) · retry DAV lên outbox · tồn-âm khi outbox async · `analytics` v2 · FE cho analytics. |
| Kernel backend    | ✅ (Sprint 2)                                                                                          |
| Module nghiệp vụ  | ✅ `catalog` (Hexagonal 4 lớp + hoạt chất `ActiveIngredient`/`DrugIngredient` persist được, migration `0008`), `inventory`, `sales`, `prescription` (cross-module: sale→dispense, sale↔prescription-ref S5.4); ✅ `compliance` (C.1–C.5 đủ); ✅ `clinical` (S5.5 A1 đủ 4 lớp + auto-check tương tác/dị ứng cross-module + `TenantAiSettings` feature-flag theo tenant, router `/clinical/*` + `/clinical/settings`, mock LLM); ✅ `crm` (Hexagonal 4 lớp đủ: `Customer`/`Allergy`(theo hoạt chất, FK `active_ingredients`)/`Condition`/`MedicationHistoryEntry`, `CrmService`, router `/customers/*`, migration `0009`); ✅ `procurement` (Hexagonal 4 lớp đủ: `Supplier`/`PurchaseOrder`+`PurchaseOrderItem`/`GoodsReceiptNote`+`GoodsReceiptItem`, `ProcurementService`, router `/suppliers`+`/purchase-orders`+`/goods-receipts`, migration `0011`; **cross-module GRN confirmed → `inventory` tạo lô** ở composition root, migration `0012` bảng `stock_reconciliation_needed`); ✅ `iam` (§7k); ✅ **`analytics`** (Hexagonal 4 lớp đủ: `ReorderSuggestion` + công thức reorder thuần, `AnalyticsService`, bảng `reorder_suggestions` migration `0022`, router `/analytics/*`; **cross-module qua 5 adapter ở `api/v1/analytics_wiring.py`** đọc `sales`/`inventory`/`procurement` và ghi PO nháp — `analytics` KHÔNG import module nghiệp vụ nào, §7ap) |
| Demo              | ✅ `demo_preview.py` — chạy end-to-end, trung thực (clinical đánh dấu CHƯA làm)                        |
| Self-Refine       | ✅ docstring use-case + edge-case test; xem [TODO.md](TODO.md)                                         |
| Chất lượng        | *(2026-07-25)* ✅ ruff · ✅ format (353 file) · ✅ import-linter (**16/0**) · ✅ mypy strict (**245 file**) · ✅ pytest (**741**) |
| Hạ tầng dev       | ✅ docker compose healthy (xác nhận `docker compose ps` 2026-07-25 09:0x — bật lại sau cúp điện 07:00); ✅ alembic `0001`..`0023` (áp live Postgres, `0023` reversible/no-drift); ✅ seed ATC + tương tác mẫu + system roles idempotent |
| Sprint kế tiếp    | **Sprint 7 ĐÓNG** — kế tiếp **Sprint 8 (Plugin & Liên thông)** theo ROADMAP. **Chưa mở** — chờ lệnh Chain. Trước khi mở, cân nhắc 2 việc nền: FE cho các module đã có backend (hiện chỉ có POS tối thiểu), và `# BLOCKER: AI__API_KEY` thật của Sprint 5. |

---

## 2. Quyết định nền tảng đã chốt (Locked Decisions)

| Quyết định | Giá trị | Nguồn |
|-----------|---------|-------|
| Ngôn ngữ tài liệu | Tiếng Việt + thuật ngữ Anh | Sprint 1 kickoff |
| Thị trường / pháp lý | Việt Nam (Bộ Y tế / DAV, TT 20/2017, NĐ 13/2023) | Sprint 1 kickoff |
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic | ADR-002 |
| Database | PostgreSQL 16 + pgvector | ADR-003 |
| Async/Queue | Redis + Celery | [05](docs/05_DEPENDENCIES.md) |
| AI | Anthropic Claude (opus-4-8 / sonnet-5) qua port `LLMProvider` | ADR-005 |
| Frontend | Next.js + TypeScript, offline-first (Dexie) | [04](docs/04_FOLDER_STRUCTURE.md) |
| Kiến trúc | Modular Monolith + Hexagonal + event-driven | ADR-001/004/007 |
| Mở rộng | Plugin system (compliance/payment/hardware) | ADR-006 |
| Multi-tenancy | Shared DB, row-level (tenant_id + branch_id) | [02](docs/02_ARCHITECTURE.md) §7 |

---

## 3. Tài liệu đã hoàn thành

| # | File | Trạng thái |
|---|------|-----------|
| — | `README.md` | ✅ |
| — | `ROADMAP.md` | ✅ |
| — | `PROJECT_STATE.md` | ✅ (tài liệu này) |
| 01 | `docs/01_ANALYSIS.md` | ✅ |
| 02 | `docs/02_ARCHITECTURE.md` | ✅ |
| 03 | `docs/03_DATABASE_ERD.md` | ✅ |
| 04 | `docs/04_FOLDER_STRUCTURE.md` | ✅ |
| 05 | `docs/05_DEPENDENCIES.md` | ✅ |
| 06 | `docs/06_WORKFLOWS.md` | ✅ |
| 07 | `docs/07_UML.md` | ✅ |
| 08 | `docs/08_MODULES.md` | ✅ |
| 09 | `docs/09_PLUGIN_SYSTEM.md` | ✅ |
| 10 | `docs/10_CONFIG.md` | ✅ |
| 11 | `docs/11_API_DESIGN.md` | ✅ |
| 12 | `docs/12_AI_INTEGRATION.md` | ✅ |

**Tổng:** 15 tài liệu Markdown (Sprint 1) + kernel backend chạy được (Sprint 2).

---

## 3b. Kernel backend đã hiện thực (Sprint 2)

| Thành phần | File | Trạng thái |
|------------|------|-----------|
| Config phân lớp (fail-fast prod) | `core/config.py` | ✅ + test |
| DI container | `core/di.py` | ✅ + test |
| Event bus in-process (isolate handler) | `core/events/` | ✅ + test |
| Unit of Work (publish-after-commit) | `core/db/uow.py` | ✅ |
| DB engine/Base/mixins | `core/db/` | ✅ |
| Security: bcrypt, JWT, RBAC | `core/security/` | ✅ + test |
| Audit logger | `core/audit/` | ✅ |
| AI `LLMProvider` port | `core/ai/provider.py` | ✅ (impl Sprint 5) |
| Plugin loader (entry points) | `core/plugins/` | ✅ |
| Errors RFC 7807 | `core/errors.py` | ✅ |
| Bootstrap/DI wiring | `core/bootstrap.py` | ✅ |
| API v1 + health | `api/v1/` | ✅ + test |
| App factory + lifespan | `main.py` | ✅ |
| Alembic + migration `0001` | `migrations/` | ✅ áp dụng live |
| CI, Makefile, docker-compose, Dockerfile | (gốc + `infra/`) | ✅ |

**Bằng chứng chạy:** `pytest` 21 passed · `mypy` strict no issues (35 file) · `ruff`+format sạch · `import-linter` 3 kept/0 broken · `docker compose up` healthy · `alembic upgrade head` bật `vector`+`pgcrypto`.

## 3c. Module nghiệp vụ đã hiện thực (Sprint 3)

| Module | Điểm chính | Trạng thái |
|--------|-----------|-----------|
| `catalog` | `Drug` aggregate, `DrugUnit` quy đổi (`to_base_quantity`), `RxClass` (OTC/ETC/CONTROLLED) | ✅ domain+app+infra+interface |
| `inventory` | `ProductBatch`, `StockMovement` event-sourced, `allocate_fefo` thuần, projection `stock_balances` | ✅ |
| — | Use-cases: `receive_stock`, `dispense_stock` (FEFO), `on_hand`, `list_near_expiry` | ✅ |
| — | Events: `StockMovedIn/Out`, `LowStockDetected` (publish-after-commit) | ✅ |
| — | API v1: `/drugs`, `/inventory/{receive,dispense,on-hand,alerts/near-expiry}` | ✅ |
| — | Migration `0002_catalog_inventory` (6 bảng, unique + index) | ✅ live + reversible |
| — | Seed ATC (10 mã) idempotent — `make seed` | ✅ |
| — | Context dep **tạm** (dev header-based) tới khi có IAM (Sprint 6) — xem `api/deps.py` | ⚠️ interim |

**Bằng chứng Sprint 3:** `pytest` **46 passed** · domain coverage **97%** · `mypy` strict (92 file) · `import-linter` **6 kept/0 broken** (thêm domain-purity + module-independence) · migration `0002` autogenerate→apply→`alembic check` không drift→downgrade/upgrade OK · seed chạy live (10→0).

## 3d. Sprint 4 — Sales / POS offline (ĐANG CHẠY)

> Phạm vi Sprint 4: **chỉ backend S4.1–S4.5** (FE tách sang đợt sau). Nhịp: S4.1→S4.3 tự chạy;
> S4.4 & S4.5 (cross-module rủi ro cao) dừng chờ duyệt sau mỗi bước.

| Bước | Nội dung | Trạng thái |
|------|----------|-----------|
| S4.1 | Sales **domain thuần**: `SalesOrder`/`SaleLine`/`Payment`/`Return`, `SaleStatus`, event `SaleCompleted`+`SoldItem`, exceptions, `SalesRepository` port, rule `ensure_rx_for_etc`. Contract mới `sales-domain-innermost` + `sales` vào `module-independence` (**7/0**). | ✅ (commit tiếp theo) |
| S4.2 | Sales **application + infrastructure** + migration `0003_sales` (unique `client_uuid`/tenant = idempotency). `SalesService.complete_sale` (idempotent theo `client_uuid`) + `get_sale`; ORM/mapper/repo; publish `SaleCompleted` sau commit (chưa ai subscribe). | ✅ (commit tiếp theo) |
| S4.3 | Sales **interface + API** `/sales` (201), `/sales/{id}`, `/sync/sales` (idempotent 200), quyền `sales.*` (deps + wiring api/v1). | ✅ (commit tiếp theo) → **DỪNG chờ duyệt S4.4** |
| S4.4 ⚠️ | Cross-module: `SaleCompleted` → inventory FEFO dispense (handler `api/v1/cross_module.py`). Idempotent cấp đơn (`MovementRepository.exists_for_ref`); thiếu tồn → xuất phần có sẵn (tồn≥0) + event `StockShortfallDetected`, **không** chặn bán. | ✅ (commit tiếp theo) |
| S4.5 ⚠️ | Chặn ETC end-to-end: port `DrugInfoProvider` (sales.domain) + adapter `CatalogDrugInfoProvider` đọc catalog ở composition root. Catalog là **nguồn thẩm quyền** rx_class — client khai gian OTC/ETC đều bị ghi đè. | ✅ (commit tiếp theo) |

**Ghi chú thiết kế:** rx_class **không** để sales import catalog — dùng cờ `requires_prescription` snapshot trên `SaleLine`;
S4.1–S4.3 nhận cờ từ request, **S4.5** ghi đè bằng nguồn thẩm quyền (catalog qua port `DrugInfoProvider` + adapter ở lớp `api`).
`DispenseInput.ref_type/ref_id` dùng làm khoá idempotent ở S4.4. Cả 2 điểm cross-module (S4.4 dispense, S4.5 read) đều nối ở
composition root `api/v1/` → `module-independence` giữ nguyên 7/0.

**Bằng chứng S4.1:** `ruff` sạch · `import-linter` **7/0** · `mypy` strict **78 file** · `pytest` **69 passed** (+15 test domain sales).
**Bằng chứng S4.2:** `ruff` sạch · `import-linter` **7/0** · `mypy` strict **85 file** · `pytest` **76 passed** (+7 integration sales) · migration `0003_sales` apply→`alembic check` **không drift**→downgrade/upgrade OK (SQLite; Postgres pending khi docker bật).
**Bằng chứng S4.3:** `ruff` sạch · `import-linter` **7/0** · `mypy` strict **89 file** · `pytest` **81 passed** (+5 e2e sales API). Endpoints live: `POST /api/v1/sales` (201), `GET /api/v1/sales/{id}`, `POST /api/v1/sync/sales` (idempotent 200). ETC thiếu đơn → 422; `/sync/sales` re-post cùng `client_uuid` → cùng `id`.
**Bằng chứng S4.4:** `ruff` sạch · `import-linter` **7/0** (handler ở lớp `api` — `module-independence` KEPT) · `mypy` strict **90 file** · `pytest` **88 passed** (+7: 4 service dispense_for_sale + 3 e2e sale→kho). E2e: bán 12/tồn 20 → tồn **8**; re-sync cùng `client_uuid` → tồn vẫn **8** (không nhân đôi); bán 10/tồn 5 → đơn vẫn 201, tồn về **0** (không âm). Không cần migration mới.
**Bằng chứng S4.5:** `ruff` sạch · `import-linter` **7/0** (sales vẫn KHÔNG import catalog) · `mypy` strict **90 file** · `pytest` **94 passed** (+6: 3 service override + 3 e2e). E2e: thuốc ETP tạo trong catalog bán như OTC không đơn → **422**; kèm `prescription_ref` → 201; thuốc OTC dù client gắn cờ Rx → 201 (catalog ghi đè). Thuốc lạ (không có trong catalog) → fallback theo cờ client.

## 3e. Sprint 5 — Prescription & Clinical AI (ĐANG CHẠY)

> Phạm vi phiên này: **S5.1 → S5.3, backend thuần cho module `prescription`** (chưa cross-module,
> chưa clinical/AI). Nhịp: S5.1→S5.3 tự chạy liên tục; dừng báo cáo sau S5.3. S5.4 (cross-module,
> nếu có) và S5.5 (Clinical AI) để phiên sau.

| Bước | Nội dung | Trạng thái |
|------|----------|-----------|
| S5.1 | Prescription **domain thuần**: `Prescription` aggregate (`DRAFT`→`VALIDATED`→`DISPENSED`, hoặc →`REJECTED` từ `DRAFT`/`VALIDATED`), `PrescriptionItem`, `PrescriptionSource`, events `PrescriptionValidated`/`PrescriptionRejected`/`PrescriptionDispensed`, exceptions, `PrescriptionRepository` port. Contract mới `prescription-domain-innermost` + `prescription` vào `module-independence` (**8/0**). | ✅ (commit tiếp theo) |
| S5.2 | Prescription **application + infrastructure** + migration `0004_prescription` (bảng `prescriptions`, `prescription_items`). `PrescriptionService`: create/validate/reject/dispense/get. | ✅ (commit tiếp theo) |
| S5.3 | Prescription **interface + API**: `POST /prescriptions` (201), `GET /prescriptions/{id}`, `POST /prescriptions/{id}/validate`, `POST /prescriptions/{id}/reject`, `POST /prescriptions/{id}/dispense`; quyền `rx.create`/`rx.read`/`rx.approve`/`rx.dispense`. → **DỪNG báo cáo tổng kết**. | ✅ (commit tiếp theo) |

**Ghi chú thiết kế:** module thuần, không phụ thuộc catalog/sales/clinical — `drug_id` trên `PrescriptionItem` chỉ là UUID tham chiếu
(không FK, giống `SaleLine.drug_id`). `/prescriptions/{id}/reject` là điểm khác nhỏ so với phác thảo ban đầu ở
[docs/11_API_DESIGN.md](docs/11_API_DESIGN.md) (chỉ liệt kê create/extract/validate/dispense) — thêm endpoint riêng cho `reject`
vì đây là 1 trong 3 hành động độc lập của dược sĩ trên state machine (docs/07 §4), tách khỏi `validate` cho rõ ràng REST + dễ test,
thay vì gộp chung bằng 1 flag `approved` trong `/validate`. Endpoint `/prescriptions/extract` (OCR/vision) **không làm** trong phiên
này — thuộc S5.5 Clinical AI.

**Bằng chứng S5.1:** `ruff` sạch · `import-linter` **8/0** · `mypy` strict **96 file** · `pytest` **106 passed** (+12 test domain prescription).
**Bằng chứng S5.2:** `ruff` sạch · `import-linter` **8/0** · `mypy` strict **103 file** · `pytest` **112 passed** (+6 integration: create→validate→dispense, reject từ DRAFT, chặn dispense chưa validate, chặn validate đơn rỗng). Migration `0004_prescription` (bảng `prescriptions`, `prescription_items`) autogenerate→apply **live trên Postgres** (docker compose)→`alembic check` không drift→downgrade/upgrade OK. Đăng ký `models_registry`.
**Bằng chứng S5.3:** `ruff` sạch · `import-linter` **8/0** · `mypy` strict **107 file** · `pytest` **118 passed** (+6 e2e). Endpoints live: `POST /api/v1/prescriptions` (201), `GET /api/v1/prescriptions/{id}`, `POST /api/v1/prescriptions/{id}/validate`, `POST /api/v1/prescriptions/{id}/reject`, `POST /api/v1/prescriptions/{id}/dispense`. Dispense trước khi validate → 422 (problem+json); items rỗng bị chặn ngay ở schema (Pydantic `min_length=1`); đơn không tồn tại → 404. Quyền dev `rx.*` thêm vào `api/deps.py`.

## 3f. Compliance — kéo sớm từ Sprint 7 (ĐANG CHẠY)

> **Bối cảnh:** ROADMAP xếp module `compliance` vào Sprint 7 (Giai đoạn 3), nhưng sếp yêu cầu khóa spec
> pháp lý và dựng module ngay trong phiên này do áp lực tuân thủ QĐ 1867 (deadline liên thông CSDL Dược
> 6/2026). Spec đã khóa tại [docs/13_COMPLIANCE_SPEC.md](docs/13_COMPLIANCE_SPEC.md) — đối chiếu trực
> tiếp với văn bản gốc (`docs/legal/*.docx`: QĐ540, TT20/2017, QĐ1867) + code thật (`catalog`/`inventory`),
> có bảng Traceability đầu file. Nhịp: C.1→C.3 tự chạy liên tục, dừng báo cáo sau C.3. C.4 (MockAdapter,
> Opus) và C.5 (cross-module, Opus, từng bước chờ duyệt) để phiên sau.

| Bước | Nội dung | Trạng thái |
|------|----------|-----------|
| C.1 | Compliance **domain thuần**: `ControlledSubstanceCategory` (7 giá trị, TT20/2017 Điều 3), `NationalDrugRecord` (23 trường Bảng 1 QĐ540 — mapping đã sửa: `lot_no` không phải `batch_no`, `Drug.base_unit` không phải `DrugUnit`), `ControlledLedgerEntry` + `CustomerDetail` (Phụ lục XXI — chỉ `patient_name`+`patient_address`, KHÔNG có CCCD), converter helpers thuần `to_qld_date`/`to_qld_datetime`/`to_qld_code` (đã sửa: bỏ dấu tiếng Việt), rule `validate_controlled_sale` (GN/HT bắt buộc `prescription_code`, TC thì không) + `validate_etc_sale` dưới cờ `EtcPrescriptionPolicy.require_etc_prescription_fields` (**mặc định `False`** — nguồn C.3.1 chưa xác định, TODO bật khi có văn bản), read-port `DrugMasterProvider`. Contract mới `compliance-domain-innermost` + `compliance` vào `module-independence` (**9/0**). | ✅ (commit tiếp theo) |
| C.2 | Compliance **application + infrastructure** + migration `0005_compliance` (bảng `controlled_ledger_entries`, `tenant_compliance_configs` — xác nhận code hiện KHÔNG có bảng tenant config nào trước đó, đã tạo mới). `ComplianceService`: `record_controlled_entry`/`get_ledger_entry`/`set_tenant_config`/`get_tenant_config`. Enforce unique `registration_no` theo tenant (`uq_drugs_tenant_registration_no`) trong cùng migration (nợ cũ TODO.md). | ✅ (commit tiếp theo) |
| C.3 | Compliance **schemas + validators**: Pydantic v2 schemas (`interface/schemas.py`), `model_validator` cho rule C.3 (defense-in-depth ở boundary, song song domain rule); export mapper `interface/export.py` domain → 23-field DTO (`NationalDrugRecordExport`) dùng converter helpers, enforce đúng cỡ tối đa Bảng 1. | ✅ (commit tiếp theo) |
| C.4 | Compliance **NationalSyncLog + MockAdapter** (mục D): entity `NationalSyncLog` (state machine `PENDING`→`SENT`→`ACK`/`FAILED`, `FAILED` gửi lại được, `retry_count` đếm số lần lỗi) + enum `SyncPayloadType`/`SyncStatus`; port thuần `NationalDrugDbGateway` + DTO `SyncRequest`/`SyncAck` (domain); `NationalSyncService.push_payload` (idempotent theo `client_uuid`, best-effort — lỗi gateway ghi FAILED không ném) + `get_sync_log`; ORM+mapper+repo; migration `0006_national_sync_log`. **MockNationalDrugDbGateway ở composition root** `api/v1/national_sync.py` (log + ACK giả), đánh dấu `# BLOCKER: DAV API spec`, KHÔNG wiring endpoint thật. → **DỪNG báo cáo, chờ duyệt C.5**. | ✅ (commit tiếp theo) |

**Ghi chú thiết kế:** `NationalDrugRecord` là value object thuần (frozen dataclass), KHÔNG có bảng riêng — lắp ráp tại thời điểm đồng bộ,
không lưu trữ nội bộ. `ControlledLedgerEntry` hợp nhất cột Phụ lục VIII (xuất/nhập/tồn, mọi giao dịch) và Phụ lục XXI (khách hàng,
chỉ chiều `XUAT`) thành 1 bảng ghi sổ (`customer_name`/`customer_address` nullable trên cùng bảng — đúng cấu trúc phẳng của mẫu sổ
gốc, không tách bảng khách hàng riêng), theo đúng cấu trúc đã bổ sung ở docs/13 mục C.2.1 khi sửa spec. Rule ETC (C.3.1) giữ nguyên
dưới dạng feature-flag tắt thay vì xóa — theo đúng yêu cầu sếp, để khi có văn bản kê đơn ngoại trú chỉ cần bật cờ, không thiết kế lại.
`TenantComplianceConfig` là entity mới hoàn toàn (tenant_id unique, `ma_co_so_ban_le` bắt buộc, `ma_co_so_ban_buon` optional) —
không phải bổ sung field vào bảng cấu hình có sẵn (xác nhận GAP khi khóa spec). Unique constraint `registration_no` cho phép nhiều
`NULL` trùng nhau (chuẩn SQL) — thuốc chưa có SĐK không bị chặn tạo.

**Bằng chứng C.1:** `ruff` sạch · `import-linter` **9/0** · `mypy` strict **114 file** · `pytest` **144 passed** (+26 test domain compliance,
gồm: converter helpers khớp đúng ví dụ văn bản gốc, `NationalDrugRecord` immutable + coerce Decimal, `ControlledLedgerEntry` chặn category
`NONE`/quantity≤0, `CustomerDetail` chặn tên/địa chỉ rỗng và xác nhận không có field `patient_id`, rule GN/HT cần `prescription_code`
còn TC thì không, rule ETC no-op khi cờ tắt và enforce khi bật).
**Bằng chứng C.2:** `ruff` sạch · `import-linter` **9/0** · `mypy` strict **121 file** · `pytest` **155 passed** (+11 integration: record
controlled sale GN/HT/TC đúng rule, NHAP không cần khách hàng, get ledger entry 404 khi không có, set/get tenant config roundtrip,
upsert lần 2 không tạo dòng trùng, get config khi chưa cấu hình → 404). Migration `0005_compliance` autogenerate→apply **live trên
Postgres** (docker compose)→`alembic check` không drift→downgrade→upgrade lại→`alembic check` vẫn sạch. `uq_drugs_tenant_registration_no`
thêm vào bảng `drugs` hiện có cùng migration. Đăng ký `models_registry`. Chưa wiring API (không có router — module này chưa cần
router riêng ở giai đoạn này, xem ghi chú thiết kế).
**Bằng chứng C.3:** `ruff` sạch · `import-linter` **9/0** · `mypy` strict **124 file** · `pytest` **168 passed** (+13: `RecordControlledEntryRequest`
chặn XUAT controlled thiếu khách hàng/thiếu `prescription_code` cho GN/HT nhưng không chặn TC, bỏ qua rule khi NHAP hoặc category NONE,
`SetTenantComplianceConfigRequest` enforce cỡ 12; export mapper mã hóa đúng `ma_thuoc` qua `to_qld_code` và ngày/giờ qua `to_qld_date`/
`to_qld_datetime` khớp ví dụ văn bản gốc, `NationalDrugRecordExport` enforce đúng cỡ tối đa Bảng 1). Không có `router.py`/`register()` —
Pydantic schemas sống ở `interface/` làm boundary sẵn sàng cho khi cần, nhưng chưa có endpoint HTTP nào ở phiên này (xem ghi chú thiết kế).

**Ghi chú thiết kế C.4:** `NationalSyncLog` tenant-scoped (chỉ `tenant_id`, KHÔNG `branch_id` — liên thông ở cấp cơ sở, đồng nhất với
`TenantComplianceConfig`); mục D.2 liệt kê `tenant_id` chứ không có `branch_id`, nên bám sát spec thay vì dùng `TenantScopedMixin`.
Chỉ lưu `payload_hash` (sha256), KHÔNG lưu payload thô (đúng mục D.2 — có test khẳng định payload thô không lọt vào log). `client_uuid`
unique theo tenant = khóa idempotency (đã ACK → trả nguyên trạng, không gửi lại; `FAILED`/`PENDING` → gửi lại trên cùng dòng, giữ
`retry_count`). Đồng bộ **best-effort**: gateway từ chối/ném lỗi → ghi `FAILED` + tăng `retry_count`, KHÔNG ném ra ngoài (để subscriber
sự kiện ở C.5 không sập khi sync trục trặc). **MockNationalDrugDbGateway đặt ở composition root** (`api/v1/national_sync.py`), không phải
trong module — nên `module-independence` giữ nguyên **9/0**; port `NationalDrugDbGateway` thuần trong domain, adapter thật để trống có
chủ đích (`# BLOCKER: DAV API spec`). `wire_national_sync(container)` đăng ký `NationalSyncService` (backed by mock) vào container ở
`build_api_router` — sẵn cho subscriber C.5 resolve; chưa có event subscription (đó là C.5), chưa có endpoint HTTP.

**Bằng chứng C.4:** `ruff` sạch · `import-linter` **9/0** · `mypy` strict **126 file** · `pytest` **187 passed** (+19: 12 domain state-machine
— chuyển trạng thái hợp lệ/không hợp lệ, `retry_count`, gửi lại từ FAILED; 7 integration — happy path ACK qua MockAdapter, chỉ lưu hash
không lưu payload thô, idempotent replay trả đúng bản ghi ACK cũ, gateway từ chối/ném lỗi → FAILED, FAILED rồi gửi lại thành công dùng
lại cùng dòng log, get theo id). Migration `0006_national_sync_log` autogenerate→apply **live trên Postgres**→`alembic check` không
drift→downgrade→upgrade lại→vẫn sạch. Smoke: `build_api_router` chạy `wire_national_sync`, `NationalSyncService` resolve được từ container.

## 4. Cấu trúc hiện có trên đĩa

```text
AI_Pharmacy_OS/
├── README.md · ROADMAP.md · PROJECT_STATE.md · Makefile · docker-compose.yml
├── .github/workflows/ci.yml
├── docs/                       # 01..12 (Sprint 1)
├── backend/
│   ├── pyproject.toml · alembic.ini · .importlinter · .env.example
│   ├── src/pharmacy_os/        # core/, api/, workers/, shared/, modules/(rỗng)
│   ├── migrations/versions/0001_enable_extensions.py
│   └── tests/unit/             # 21 test
├── infra/docker/backend.Dockerfile
└── scripts/bootstrap.sh
```

> `frontend/`, `plugins/` **vẫn chỉ ở dạng thiết kế** ([04_FOLDER_STRUCTURE.md](docs/04_FOLDER_STRUCTURE.md)) — bắt đầu từ Sprint 4 (FE) / Sprint 8 (plugins). `modules/` rỗng đúng chủ đích.

---

## 5. Phạm vi đã quyết & chưa quyết

**Đã chốt:** stack, kiến trúc, ranh giới module, ERD, API v1 map, cơ chế plugin/AI, cấu hình.

**Chưa quyết (đẩy sang sprint tương ứng):**
- Nguồn tri thức dược cụ thể cho RAG + bản quyền (trước Sprint 5).
- Nhà cung cấp object storage cụ thể (Sprint 4).
- Định dạng liên thông DAV chi tiết (Sprint 8, qua plugin).
- Mô hình ML dự báo nhu cầu cụ thể (Sprint 7).

---

## 6. Rủi ro đang theo dõi (từ [01_ANALYSIS.md](docs/01_ANALYSIS.md) §8)

| ID | Rủi ro | Mức | Trạng thái |
|----|--------|-----|-----------|
| R1 | AI khuyến nghị dược lý sai | Cao | Đã thiết kế giảm thiểu (hybrid + human-in-loop + guardrails) |
| R2 | Rò rỉ dữ liệu bệnh nhân | Cao | Đã thiết kế (mã hóa, RBAC, audit) — hiện thực Sprint 8 |
| R3 | Sai lệch tồn kho offline sync | Trung | Đã thiết kế (event-sourcing + idempotency) |
| R4 | Thay đổi quy định DAV | Trung | Cô lập qua plugin |
| R5 | Khóa nhà cung cấp AI | Trung | Cô lập qua `LLMProvider` |

---

## 7. S5.4 Cross-module prescription↔sales — XONG (để phiên sau nối lại ngay)

> **Trạng thái:** Sprint 5 **S5.1–S5.3 xong** + **S5.4 XONG** (prescription↔sales). **S5.5 (Clinical AI) CHƯA làm — dừng đúng theo
> lệnh sếp**, không tự ý tiếp tục. Working tree sạch, **206 test xanh, 9 contract kept/0 broken**, mypy strict 127 file, ruff sạch.
>
> **S5.4 đã làm (PA1 — sales đọc prescription qua read-port, sếp duyệt):** khi bán thuốc ETC, `SalesService.complete_sale` xác thực
> `prescription_ref` là đơn **có thật** của tenant và **đã `VALIDATED`/`DISPENSED`** trước khi hoàn tất (accept-list sếp chốt; chặn
> DRAFT/REJECTED/không tồn tại). Giữ đúng khuôn S4.5:
> - Read-port mới `PrescriptionInfoProvider` + VO `PrescriptionInfo(prescription_id, status: str)` trong `sales/domain/ports.py`
>   (sales **không** import enum status của prescription — chính sách accept-list nằm ở `sales.domain.rules._SALE_AUTHORISING_RX_STATES`).
> - Rule thuần `ensure_prescription_valid_for_sale(status)` + exception `InvalidPrescriptionRefError` (họ `SalesError`→`ValidationError` 422).
> - Adapter `PrescriptionInfoAdapter` over `PrescriptionService` ở `api/v1/cross_module.py` (quyền `rx.read`, system-context), wire qua
>   `register_sales(container, get_context, drug_info, rx_info)` trong `build_api_router`. `sales` không import `prescription`.
> - Provider optional: `_prescription_info is None` (unit/integration cũ, hoặc chưa wire) → giữ nguyên rule cũ "chỉ cần có ref"
>   (`ensure_rx_for_etc`), nên test không-provider vẫn xanh.
> - Test: unit `test_sales_rx_prescription_rule.py` (rule) · integration `test_sales_prescription_authority.py` (service + stub provider:
>   VALIDATED/DISPENSED cho bán, DRAFT/REJECTED/unknown chặn, OTC bỏ qua, no-provider giữ rule cũ) · cập nhật 2 e2e app-level
>   (`test_sales_api_e2e`, `test_sales_rx_authority_e2e`): đơn ETC cần đơn thuốc thật đã duyệt; ref uuid giả → 422.

**⚠️ Điều kiện bắt buộc trước khi mở S5.5 (yêu cầu của sếp, giữ như S5.4):**
- **Dùng model Opus 4.8** (không dùng Sonnet) — bước rủi ro cao, làm **từng bước dừng chờ duyệt**.
- **Mở vào phiên có hạn mức còn đầy** — không bắt đầu giữa chừng phiên sắp cạn hạn mức (giữ tính nguyên tử 1 bước = 1 commit).

**Quyết định S5.4 đã chốt (khỏi bàn lại):** chọn **PA1 (b)** — sales đọc prescription qua read-port, KHÔNG dùng PA2 (event
`PrescriptionDispensed` gắn ngược `SalesOrder`) vì event chỉ mang `prescription_id`, không dựng lại được đơn bán và không cho bảo đảm
xác thực đồng bộ. Accept-list = **{VALIDATED, DISPENSED}**. Chi tiết thực thi ở khối trạng thái đầu §7.

**S5.5 (Clinical AI) vẫn còn nguyên 2 blocker cũ, chưa gỡ:**
- Nguồn tri thức dược cụ thể cho RAG + bản quyền hợp pháp (chưa có → không seed `drug_knowledge_chunks`).
- `AI__API_KEY` thực (hiện test vẫn dùng `"test-key"`).

**Hook code đã sẵn cho S5.4/S5.5 (không phải làm lại):**
- `Prescription`/`PrescriptionService` đủ 4 lớp (S5.1–S5.3) — `PrescriptionDispensed`/`PrescriptionValidated`/`PrescriptionRejected` đã phát sau commit, sẵn để subscribe ở composition root.
- `SalesOrder.prescription_ref` (Sprint 4) — chỗ để nối đơn thuốc ↔ đơn bán.
- `core.ai.LLMProvider` port — `backend/src/pharmacy_os/core/ai/provider.py` (chỉ có interface, chưa impl).
- ERD `drug_interactions`, `drug_knowledge_chunks`, `ai_recommendations` — [docs/03](docs/03_DATABASE_ERD.md); pgvector + pgcrypto đã bật live (migration `0001`).

**Khuôn mẫu bắt buộc giữ (theo Sprint 3–5):**
- Cross-module **nối ở composition root** `api/v1/cross_module.py` — không để module import module (tiền lệ Sprint 4, giữ nguyên ở S5.1–S5.3).
- Mỗi bước = 1 commit chạy được, 4 cổng xanh (ruff + import-linter + mypy strict + pytest), cập nhật PROJECT_STATE sau mỗi commit.
- Bước rủi ro cao (cross-module, S5.4) → dừng chờ duyệt sau bước đó, không tự chạy tiếp sang S5.5.

**Hạ tầng còn mở từ phiên này (ảnh chụp tại thời điểm ghi — LUÔN `docker compose ps` để xác nhận thực tế, không tin dòng này):** docker compose (postgres+redis) đang chạy — `make down` nếu không cần nữa. Migration hiện tại: `0001`→`0006` (`0006_national_sync_log` đã apply live trên Postgres, `alembic check` sạch, downgrade/upgrade reversible).

> **Nợ kỹ thuật mang sang (chưa chặn S5.4):** `api/deps.py` dev-header context tạm (thay bằng JWT thật ở Sprint 6); FK `drugs.atc_code`→`atc_codes` chưa bật; **persist trả hàng** (`register_return`, Sprint 4) chưa có use-case + trả tồn. (Uniqueness `registration_no` đã enforce ở Compliance C.2, xem §7b.) Chi tiết ở [TODO.md](TODO.md).

---

## 7b. Compliance C.1–C.5 (ĐÃ ĐÓNG — lưu vết để phiên sau nối lại nếu mở tiếp)

> **Trạng thái:** Compliance **C.1→C.4 xong** + **C.5 (5a thiết kế · 5b implement · 5c e2e) XONG — SPRINT COMPLIANCE ĐÓNG.** ✅
> **HEAD `main` = C.5 5c** (e2e), working tree **sạch**. **192 test xanh, 9 contract kept/0 broken**,
> mypy strict 127 file, ruff sạch. Migration `0001`→`0006` (không thêm migration ở C.5 — không có bảng/field mới).
> Docker compose (postgres+redis) — ảnh chụp tại thời điểm ghi, **LUÔN `docker compose ps` để xác nhận thực tế** (2026-07-22:
> phát hiện cả 2 container Exited dù dòng này từng ghi "đang chạy healthy" — đã `up -d` lại, xem lưu ý vận hành đầu file).
>
> **Quyết định phạm vi 5a (sếp đã chốt):** C.5 **CHỈ enqueue `NationalSyncLog`** từ `SaleCompleted`, **KHÔNG auto-ghi
> `ControlledLedgerEntry`**. Lý do: `SaleCompleted` không mang `category`/`lot_no`/`expiry_date`/`prescription_code`/`customer`
> (tên+địa chỉ) — các field rule C.3 bắt buộc cho chiều XUAT; cấp chúng sẽ phải hoặc đổi contract `SaleCompleted` (cấm) hoặc thêm
> 3 read-port cross-module (category từ catalog, lot/expiry từ inventory, customer+prescription từ sales). customer+đơn là dữ liệu
> người nhập tại quầy, không suy ra từ event nền → auto-ghi sổ sai chỗ về kiến trúc. Ledger giữ nguyên use-case tường minh
> `ComplianceService.record_controlled_entry` (nơi có đủ dữ liệu).

**⚠️ Điều kiện bắt buộc (yêu cầu của sếp, giống tiền lệ S4.4/S5.4):** **Dùng Opus**; làm **từng bước, dừng chờ duyệt** sau MỖI bước.

**Bước 5b đã làm (HEAD):** file mới `api/v1/compliance_cross.py` — `wire_compliance_sync(container)` subscribe `SaleCompleted`,
dựng `PushSyncInput(payload_type=SALE, client_uuid=event.client_uuid, payload=<serialize order_id+items>)` dưới system-context
(`_SYSTEM_USER=…5c05`, quyền `{"compliance.sync.push"}`), gọi `NationalSyncService.push_payload`. Idempotent theo `client_uuid`.
Nối trong `build_api_router` ngay sau `wire_national_sync`. `compliance` KHÔNG import `sales` (chỉ import class event `SaleCompleted`,
y như `wire_sale_dispensing`). Test: `tests/integration/test_cross_module_compliance_sync.py` (3 test: enqueue 1 log ACK · re-sync cùng
`client_uuid` không nhân đôi · 2 sale khác nhau ra 2 log).

**Bước 5c đã làm (đóng Sprint Compliance):** e2e thật `tests/integration/test_compliance_sync_e2e.py` qua `TestClient(create_app())`
— POST `/api/v1/sales` → `SaleCompleted` publish qua UoW (sau commit) → handler C.5 enqueue sync log (KHÔNG publish event thủ công như
5b). Kiểm trực tiếp trên SQLite (compliance chưa có HTTP router): bán thuốc → đúng 1 dòng `national_sync_logs` (`sale`, `ACK`);
re-sync `/api/v1/sync/sales` cùng `client_uuid` → vẫn 1 dòng (không nhân đôi). Không kiểm ledger (5a đã loại auto-ghi ledger).

**Nếu mở lại Compliance sau này (ngoài phạm vi Sprint đã đóng):** ứng viên kế tiếp — (a) HTTP router cho `compliance` (dược sĩ nhập tay
1 dòng sổ / xem sync log); (b) adapter `NationalDrugDbGateway` thật khi có đặc tả API DAV (`# BLOCKER: DAV API spec`, ~6/2026);
(c) nếu nghiệp vụ yêu cầu auto-ghi ledger từ bán hàng, cần quyết lại 5a: hoặc event `SaleCompleted` giàu hơn, hoặc 3 read-port cross-module.

**Hook code đã sẵn cho C.5 (không phải làm lại):**
- `ComplianceService.record_controlled_entry` (C.2) — đã validate rule C.3, đã persist `ControlledLedgerEntry`, sẵn để cross-module gọi.
- `NationalSyncService.push_payload` (C.4) — idempotent theo `client_uuid`, best-effort; đã đăng ký trong container qua
  `wire_national_sync(container)`, resolve được ở `build_api_router`. C.5 chỉ cần subscribe event và gọi nó.
- `MockNationalDrugDbGateway` (C.4, `api/v1/national_sync.py`) — trả ACK giả, `# BLOCKER: DAV API spec`; C.5 KHÔNG cần đụng, chỉ dùng lại.
- `DrugMasterProvider` port (C.1) — sẵn để composition root cấp adapter đọc `catalog.registration_no`/`base_unit`, giống tiền lệ
  `DrugInfoProvider`/`CatalogDrugInfoProvider` ở Sprint 4 S4.5 (nếu C.5 cần build `NationalDrugRecord` từ catalog).
- `to_national_drug_record_export` (C.3) — sẵn để dựng payload 23-field gửi đi.
- `EtcPrescriptionPolicy.require_etc_prescription_fields` (mặc định `False`) — nguồn rule C.3.1 vẫn CHƯA xác định, KHÔNG bật cờ này
  trừ khi có văn bản kê đơn ngoại trú hiện hành xác nhận (xem cảnh báo đầu docs/13_COMPLIANCE_SPEC.md).

**Nợ/GAP chưa gỡ (không chặn C.5 nhưng cần biết):**
- 4 văn bản còn thiếu (đặc tả API DAV, TT11/2025, NĐ163/2025, NĐ90/2026, văn bản kê đơn ngoại trú) — xem cảnh báo đầu docs/13.
- Chưa có router/endpoint HTTP cho `compliance` — nếu C.5 hoặc sau đó cần expose thao tác thủ công (VD dược sĩ tự nhập tay 1 dòng sổ),
  phải thêm `interface/router.py` + `register()` riêng, hiện chưa làm vì chưa có yêu cầu cụ thể.
- ✅ (đã gỡ ở 5b) System-context cho sync đã có: `_SYSTEM_USER=…5c05` + `_SYSTEM_PERMISSIONS={"compliance.sync.push"}` trong
  `api/v1/compliance_cross.py`. `compliance.ledger.write` KHÔNG cấp vì 5a đã loại auto-ghi ledger khỏi phạm vi.

**Khuôn mẫu bắt buộc giữ (kế thừa Sprint 3–5):**
- Cross-module **nối ở composition root** `api/v1/` — không để module import module.
- Mỗi bước = 1 commit chạy được, 4 cổng xanh (ruff + import-linter + mypy strict + pytest), cập nhật PROJECT_STATE sau mỗi commit.
- Bước rủi ro cao (cross-module, C.5) → dừng chờ duyệt sau bước đó.

---

## 7c. S5.5 Clinical AI (DONE mức MOCK — 5.5.1→5.5.3 xong; 5.5.4 blocker)

> **Trạng thái:** **5.5.1 (domain) + 5.5.2 (app+infra+migration) + 5.5.3 (interface HTTP) XONG — Sprint 5 DONE ở mức MOCK.**
> Còn **5.5.4 (cross-module auto-check)** = **BLOCKER** (chờ mô hình hoạt chất trong catalog, gộp Sprint 6). Working tree sạch sau
> commit 5.5.3. **239 test xanh, 10 contract kept/0 broken**, mypy 145 file, ruff sạch.

**Kế hoạch đã chốt (sếp duyệt qua 2 quyết định):**
- **Phạm vi lõi = A1** (kiểm tra tương tác thuốc chéo) **+ xương sống AI** (audit `ai_recommendations` + guardrail human-in-the-loop).
  Hoãn A2/A3/A4/A5/A6.
- **Khóa tương tác = ingredient-based, input hoạt chất tường minh** (đúng ERD). Map `drug_id→hoạt chất` là dependency riêng ở 5.5.4.
- **Mock LLM only** — không gọi API thật. LLM chỉ *diễn giải*; quyết định an toàn đến từ bảng `drug_interactions` (tất định).

**5.5.1 đã làm:** module `clinical/domain/` — `entities.py` (`InteractionSeverity`, `AiContextType`, `DrugInteraction` [cặp hoạt chất
canonical/order-independent], `AiRecommendation` [bất biến + `accept()` human-in-the-loop, guard `confidence∈[0,1]`]); `rules.py`
(engine thuần `find_interactions` xếp theo severity + guardrail `requires_pharmacist_review`: CONTRAINDICATED/MAJOR hoặc
`confidence<min` → cần dược sĩ duyệt); `ports.py` (`DrugInteractionRepository`, `AiRecommendationRepository`); `exceptions.py`.
Thêm contract import-linter `clinical-domain-innermost` + đưa `clinical` vào `module-independence` (9→10 contract; **không** đổi 9 cái cũ).
Test: `tests/unit/test_clinical_domain.py` (12). Domain **không** import LLM/framework.

**5.5.2 đã làm:** **app** `clinical/application/` — `ClinicalService.check_interactions` (engine tất định trên `drug_interactions`
→ LLM chỉ diễn giải → ghi 1 `AiRecommendation` bất biến, `requires_review` = guardrail), `get_recommendation`, `accept_recommendation`
(human-in-the-loop, 404/409); DTO. **infra** `clinical/infrastructure/` — ORM `DrugInteractionORM` (global, unique cặp canonical) +
`AiRecommendationORM` (tenant-scoped, `output`/`sources` = jsonb-variant, chỉ `accepted_by` mutate) + mapper + repo. **kernel**
`core/ai/MockLLMProvider` (KHÔNG gọi API, deterministic, `# BLOCKER: AI__API_KEY thật`). **migration** `0007_clinical` (2 bảng) —
autogenerate → apply **live Postgres** → `alembic check` sạch → downgrade → upgrade → **check sạch lại**. **seed** `seed_drug_interactions`
(5 cặp **mẫu**, source `SAMPLE …`, idempotent theo cặp — live PG: 5→0). Quyền `clinical.check`/`clinical.accept` thêm vào dev context +
system-permission test. Test: `test_clinical_flow.py` (8), `test_mock_llm_provider.py` (6), seed idempotent (+1). **Không** router/DI-wire (đó là 5.5.3).

**3 điểm BLOCKER (chưa gỡ — quyết định sau, đã ghi rõ TODO.md):**
- `# BLOCKER: AI__API_KEY thật` — `AnthropicProvider` thật (5.5.3+); nay `MockLLMProvider`.
- `# BLOCKER: catalog chưa có mô hình hoạt chất` (`active_ingredients`/`drug_ingredients` chưa implement) — chặn drug→ingredient ⇒
  auto-check ở sale/prescription (5.5.4). **KHÔNG tự thêm vào catalog** — chờ sếp chốt: thêm ngay vào `catalog` **hay** tách sprint riêng
  (chung mạch dị ứng KH Sprint 6). Giữ nguyên 10 contract.
- `# BLOCKER: nguồn tri thức dược thật + bản quyền` — RAG `drug_knowledge_chunks` **HOÃN, chưa tạo bảng ở `0007`**: cột `vector(1536)`
  phá test-harness SQLite (`create_all`) + bảng rỗng vô nghĩa cho A1. Tạo bảng+index+migration riêng khi làm RAG thật.

**5.5.3 đã làm (interface HTTP):** `clinical/interface/` — `schemas.py` (Pydantic `CheckInteractionsRequest` [validator strip/không rỗng]
+ `InteractionCheckResponse`/`DrugInteractionResponse`/`AiRecommendationResponse`), `router.py` (`POST /clinical/check-interactions`,
`GET /clinical/recommendations/{id}`, `POST /clinical/recommendations/{id}/accept`), `register.py`. **DI wiring:** `bootstrap` đăng ký
`LLMProvider → MockLLMProvider` (`# BLOCKER: AI__API_KEY thật` — chỗ swap `AnthropicProvider`); `api/v1` nối `register_clinical`.
Test **e2e HTTP thật** `test_clinical_api_e2e.py` (6): response có `source`+`confidence`, `model=mock-llm`, xếp severity, accept 200/lại 409,
schema 422. **DoD Sprint 5 đạt qua mock.**

**5.5.4 (cross-module auto-check) — BLOCKER, KHÔNG làm:** cần `drug_id→hoạt chất` (mô hình hoạt chất trong catalog chưa có).
Chốt: gộp vào **Sprint 6** cùng dị ứng KH. Nay client gọi `/clinical/check-interactions` với danh sách hoạt chất tường minh.

---

## 7d. Sprint 6 — Procurement & CRM (ĐANG MỞ — Bước 1 XONG hoàn toàn: domain + app+infra+migration)

> **Sprint 5 ĐÓNG ở mức MOCK (2026-07-22).** `clinical` A1 đủ 4 lớp + `MockLLMProvider`; DoD "có nguồn + confidence" đạt qua mock.
> **5.5.4 (auto-check cross-module) chính thức HOÃN sang Sprint 6 — KHÔNG quay lại trong Sprint 5.**

**Sprint 6 gồm (thứ tự đề xuất — chưa chốt):**
1. **Mô hình hoạt chất trong `catalog`** (`active_ingredients` + `drug_ingredients` theo docs/03) — gỡ blocker map `drug_id→hoạt chất`.
   Đây là nền cho cả (2) và (4). **XONG hoàn toàn (2026-07-22) — domain + app+infra+migration `0008`, xem dưới.**
2. **Auto-check tương tác 5.5.4** — nối `clinical.check_interactions` vào luồng sale/prescription (composition root, giữ module-independence).
   Phụ thuộc (1) đủ app+infra+migration — **điều kiện đã đủ**. Duyệt riêng vì là cross-module (rủi ro cao) — **cần Opus + phiên riêng, chưa mở**.
3. **Module `crm`** (Customer, dị ứng, bệnh nền, lịch sử) + nối **dị ứng KH** vào kiểm tra clinical (chung mạch với (2)).
4. **Feature flag AI theo tenant (SaaS)** — chuyển `AISettings.enable_clinical_ai` (và các cờ AI khác) từ cấu hình **toàn cục** sang
   **theo tenant** (bảng `settings` scope TENANT theo docs/03, hoặc `tenant_*_configs`). Lý do: SaaS đa tenant — mỗi nhà thuốc bật/tắt
   AI độc lập, không thể là 1 cờ chung. Liên quan nguyên tắc [[feedback_keep_unconfirmed_rules_as_flags]] (cờ mặc-định-tắt theo tenant).
5. **Module `procurement`** (Supplier, PO, GRN → inventory IN) — DoD gốc Sprint 6.

**Bước 1 — domain thuần (2026-07-22, xem changelog cùng ngày):** `ActiveIngredient` (hoạt chất — reference toàn cục, không tenant-scope,
giống tinh thần `AtcCode`; `id` + `name` + `name_en?`, guard tên không rỗng) + `DrugIngredient` (hàm lượng hoạt chất trong 1 thuốc —
`ingredient_id` + `amount: Decimal > 0` + `unit`, docs/03 `drug_ingredients`). `Drug` aggregate thêm field `ingredients: list[DrugIngredient]`
(default `[]`, tương thích ngược) + `add_ingredient()` chặn trùng `ingredient_id`. Exceptions: `InvalidIngredientError`,
`DuplicateIngredientError`. Port `ActiveIngredientRepository` (`add`/`get`/`find_by_name`/`list`) khai trong domain.

**Bước 1 tiếp — app+infra+migration (2026-07-22, cùng phiên):** `SqlAlchemyActiveIngredientRepository` (global, không tenant_id, session-only
— giống `SqlAlchemyDrugInteractionRepository` bên `clinical`) impl đủ `add`/`get`/`find_by_name`/`list`. ORM `ActiveIngredientORM`
(`active_ingredients`, **thêm unique constraint trên `name`** — quyết định kỹ thuật riêng, không phải yêu cầu spec: bảo vệ bất biến
"1 tên hoạt chất = 1 hàng" mà `find_by_name` giả định, tránh race-condition tạo trùng) + `DrugIngredientORM` (`drug_ingredients`, FK
`drugs.id` CASCADE + FK `active_ingredients.id`) + quan hệ `DrugORM.ingredients` (cascade delete-orphan, giống `units`). Mapper
`to_domain`/`to_orm` của `Drug` mở rộng để roundtrip `ingredients`; thêm `ingredient_to_domain`/`ingredient_to_orm`. `CatalogService`
nhận thêm `ingredient_repo_factory` (constructor 3 tham số — đã cập nhật cả `register.py` lẫn `tests/integration/conftest.py`);
`create_drug` validate mỗi `ingredients[].ingredient_id` **phải tồn tại** trong `active_ingredients` (else `NotFoundError`) trước khi
gọi `drug.add_ingredient()` (bắt `DuplicateIngredientError`/`InvalidIngredientError` → `ValidationError`, giống khuôn `DuplicateUnitError`
hiện có cho `units`). **Interface (mục tuỳ chọn đã làm):** `CreateDrugRequest`/`DrugResponse` mở rộng thêm `ingredients: list[...]`
(schema `DrugIngredientSchema` = `ingredient_id`+`amount:Field(gt=0)`+`unit`, giống khuôn `DrugUnitSchema`) — **không** thêm endpoint
CRUD `/active-ingredients` riêng (ngoài phạm vi "tuỳ chọn" đã giao; ingredient phải được tạo qua repo trực tiếp/seed script, chưa có
HTTP — ghi vào TODO.md). Migration `0008_catalog_ingredients`: autogenerate → apply **live Postgres** → `alembic check` sạch →
downgrade → upgrade lại → **check sạch lại**. Test: `tests/integration/test_catalog_repo.py` (+4: roundtrip tạo thuốc kèm hoạt chất có
thật, `NotFoundError` khi `ingredient_id` không tồn tại, `ValidationError` khi trùng hoạt chất trong cùng request, `find_by_name`/`list`
trên repo hoạt chất). **KHÔNG động vào clinical/compliance/10 contract.** Gate: ruff+format sạch, import-linter **10/0** (không đổi
contract), mypy strict **145 file**, pytest **249** (+4). **⇒ Sprint 6 Bước 1 (cả domain lẫn app+infra+migration) XONG hoàn toàn —
điều kiện phụ thuộc của Bước 2 đã đủ.**

**Nợ/gap mới ghi nhận (không chặn):** chưa có HTTP endpoint tạo/liệt kê `active_ingredients` — client hiện chỉ có thể *tham chiếu*
`ingredient_id` có sẵn khi tạo thuốc qua `POST /drugs`, không tự tạo hoạt chất mới qua API. Cần quyết định khi làm `crm`/`procurement`
hoặc khi có nhu cầu FE thật (xem TODO.md).

**Blocker mang sang (chưa gỡ, đã ghi TODO/ROADMAP):** `AI__API_KEY` thật (`AnthropicProvider`); nguồn tri thức dược + bản quyền
(RAG `drug_knowledge_chunks` — chưa tạo bảng); IAM thật thay dev-header context (`api/deps.py`).

**Bước kế (Bước 2 = 5.5.4 auto-check, KHÔNG tự mở):** nối `clinical.check_interactions` vào luồng sale/prescription ở composition root.
**Điều kiện bắt buộc trước khi mở (giữ như S5.4/C.5):** dùng **Opus 4.8** (không Sonnet), mở vào **phiên có hạn mức còn đầy**, làm
từng bước dừng chờ duyệt.

---

## 7e. Module `crm` (XONG HOÀN TOÀN — domain + app+infra+migration `0009` + interface HTTP, 2026-07-22)

> **Quyết định phạm vi trước khi code (sếp duyệt qua AskUserQuestion):** `crm.Customer` **độc lập hoàn toàn** với
> `compliance.CustomerDetail` — không tham chiếu/import qua lại, không có contract/port nối 2 module ở bước này. Lý do:
> `CustomerDetail` là value object bất biến, không id, gắn thẳng vào 1 dòng sổ kiểm soát (Phụ lục XXI) tại thời điểm bán —
> có thể là khách vãng lai chưa từng có trong CRM; `Customer` là master data có id, tái dùng qua sales/clinical, vòng đời
> khác hẳn. Gộp sẽ vi phạm nguyên tắc module-independence đã giữ xuyên suốt (compliance cố tình không phụ thuộc module
> nào). Nếu sau này cần tiện (VD tự điền tên/địa chỉ từ hồ sơ KH khi ghi sổ) — đó là quyết định cross-module riêng ở
> composition root (giống khuôn `DrugInfoProvider`/`CatalogDrugInfoProvider`), để dành cho khi thật sự làm crm↔compliance
> cross-module, không phải bây giờ.

**Đã làm (domain thuần, `crm/domain/`):** `Customer` (aggregate root — **không** tự mang `tenant_id` trong entity, giống
`Drug`: tenant gắn ở ranh giới repository) — `full_name` bắt buộc không rỗng, `weight_kg` optional > 0, cùng 3 collection con:
- `Allergy` — **theo hoạt chất** (`ingredient_id: UUID`, không phải tên thuốc tự do — đúng yêu cầu, để sau này khớp được với
  `catalog.ActiveIngredient` (Bước 1) và kiểu ingredient-based matching mà `clinical.DrugInteraction` đã dùng), `severity`
  (`AllergySeverity`: MILD/MODERATE/SEVERE), `note?`. `Customer.add_allergy()` chặn trùng `ingredient_id`
  (`DuplicateAllergyError`); `has_allergy_to(ingredient_id)` — query method thuần, chưa nối clinical.
- `Condition` — bệnh nền mã ICD-10 (`condition_code` bắt buộc không rỗng), `note?`. `add_condition()` chặn trùng mã
  (`DuplicateConditionError`).
- `MedicationHistoryEntry` — **tối giản** theo đúng yêu cầu: `drug_id` + `quantity: Decimal > 0` + `source`
  (`MedicationHistorySource`: SALE/PRESCRIPTION) + `ref_id` (UUID trỏ tới `SalesOrder`/`Prescription`, **không phải FK** —
  cùng khuôn `ref_type`/`ref_id` mà `inventory.StockMovement` đã dùng) + `occurred_at`. Đây chỉ là **hình dạng** một use-case
  có thể append vào — việc tự động ghi từ sự kiện `SaleCompleted`/`PrescriptionDispensed` (theo docs/08_MODULES.md "Events
  nghe") là bước cross-module riêng, **chưa làm** ở đây. `Customer.record_history_entry()` chỉ append, không dedup (dedup
  theo `ref_id` nếu cần là việc của use-case/infra, không phải domain).

Exceptions: `InvalidCustomerError`, `DuplicateAllergyError`, `InvalidConditionError`, `DuplicateConditionError`,
`InvalidMedicationHistoryEntryError`. Port `CustomerRepository` (`add`/`get`/`find_by_phone`/`list`/`update`) khai trong
domain, **chưa có impl**. Contract mới `crm-domain-innermost` + `crm` vào `module-independence` (10→**11** contract, không
đổi 10 cái cũ). Test: `tests/unit/test_crm_domain.py` (+9). **KHÔNG cross-module** — không đụng `clinical`/`sales`/`compliance`.

Gate (domain step): ruff+format sạch, import-linter **11/0**, mypy strict **150 file**, pytest **258** (+9).

**Đã làm tiếp — app+infra+migration+interface (cùng ngày, 2026-07-22):**
- **Infra:** `SqlAlchemyCustomerRepository` (tenant-scoped, giống khuôn `SqlAlchemyDrugRepository`) — `add`/`get`/
  `find_by_phone`/`list`/`update`. ORM `CustomerORM` (`customers`, tenant_id không branch — giống `DrugORM`) +
  `CustomerAllergyORM` (`customer_allergies`) + `CustomerConditionORM` (`customer_conditions`) +
  `CustomerMedicationHistoryORM` (`customer_medication_history` — tên tự đặt, ERD docs/03 chưa có tên chính thức) + mapper
  roundtrip đủ 3 collection con. `update()` reconcile theo id-diff (collection con chỉ insert-only, không sửa/xoá — khớp
  domain), tránh ghi đè dòng đã tồn tại.
  - **Quyết định kỹ thuật đáng chú ý:** `CustomerAllergyORM.ingredient_id` có **FK thật** tới `active_ingredients.id` (theo
    đúng yêu cầu) — **lần đầu tiên** trong codebase có FK **xuyên module** (mọi tham chiếu chéo module trước đây, VD
    `SaleLine.drug_id`/`PrescriptionItem.drug_id`, đều cố tình để UUID trần không FK). Vẫn AN TOÀN với `module-independence`:
    FK chỉ là tên bảng dạng string trong DDL, **không cần import class ORM của catalog** — import-linter không thấy được
    (vẫn 11/0). `active_ingredients` là bảng **global** (không tenant_id) nên không có rủi ro xuyên tenant, giống hệt
    `DrugIngredientORM.ingredient_id` đã làm trong catalog (Bước 1). **Lưu ý vận hành:** SQLite (test harness) KHÔNG enforce
    FK trừ khi bật `PRAGMA foreign_keys=ON` (dự án chưa bật) — nên constraint này **chỉ thật sự chặn trên Postgres sống**,
    test unit/integration không kiểm được nhánh "ingredient_id sai" (đã tránh viết test dựa vào việc này). `drug_id` trên
    `CustomerMedicationHistoryORM` vẫn giữ **không FK** (đúng khuôn cũ — cross-module ref tới dữ liệu tenant-scoped khác).
- **App:** `CrmService` (`create_customer`/`add_allergy`/`add_condition`/`get_customer`/`list_customers`), theo đúng khuôn
  `_get_or_404` + mutate-rồi-`repo.update()` của `PrescriptionService`. Quyền `crm.create`/`crm.read`/`crm.write`.
  `add_allergy`/`add_condition` **không** validate ingredient/mã tồn tại qua service khác — chỉ dựa FK (đã nói ở trên); đây
  là ranh giới đã nói rõ trong docstring, KHÔNG phải oversight.
- **Migration `0009_crm_customers`:** autogenerate → apply **live Postgres** → `alembic check` sạch → downgrade → upgrade
  lại → **check sạch lại**. 4 bảng mới, không đổi bảng cũ.
- **Interface (đã làm, không chỉ tuỳ chọn schema):** `interface/schemas.py`+`router.py`+`register.py` đủ — router
  `/customers` (POST tạo mới, GET list, GET theo id), `/customers/{id}/allergies` (POST), `/customers/{id}/conditions`
  (POST). Wiring: `api/v1/__init__.py` thêm `register_crm` (đơn giản — không cross-module như `register_sales`, không cần
  adapter/composition-root phức tạp); `api/deps.py` thêm quyền dev `crm.*`; `models_registry.py` đăng ký ORM crm.
- Test: `tests/unit/test_crm_domain.py` (9, không đổi) + `tests/integration/test_crm_repo.py` (+10: create/get, tenant
  isolation, permission, 404, allergy roundtrip + trùng bị chặn (422) + customer lạ (404), condition roundtrip + trùng bị
  chặn, list theo tên, cân nặng ≤0 bị chặn) + `tests/integration/test_crm_api_e2e.py` (+4: HTTP thật qua `TestClient` — tạo
  KH + thêm dị ứng/bệnh nền roundtrip, list, 404 problem+json, trùng dị ứng → 422). **KHÔNG cross-module** — không đụng
  `clinical`/`sales`/`compliance`, không tự nối dị ứng KH vào kiểm tra tương tác thuốc.

Gate cuối: ruff+format sạch, import-linter **11/0** (không đổi 10 contract cũ + `crm-domain-innermost`), mypy strict
**161 file**, pytest **272** (+14 so với domain-only). **⇒ Module `crm` XONG hoàn toàn (Hexagonal 4 lớp đủ).**

**Bước kế (Sprint 6 Bước 2 = 5.5.4 auto-check + nối dị ứng KH vào clinical, CHƯA mở):** nối `clinical.check_interactions`
vào luồng sale/prescription **và** nối `crm` dị ứng KH vào cùng luồng kiểm tra (composition root, giữ module-independence).
**Điều kiện bắt buộc trước khi mở (giữ như S5.4/C.5):** dùng **Opus 4.8** (không Sonnet), mở vào **phiên có hạn mức còn
đầy**, làm từng bước dừng chờ duyệt.

**✅ Gap đã gỡ (2026-07-22, cùng ngày):** `add_allergy` với `ingredient_id` sai từng trả `IntegrityError`/500 thô trên
Postgres (SQLite test không phát hiện được vì mặc định không enforce FK) — **đã sửa, KHÔNG cross-module**:
- Hỏi sếp trước (AskUserQuestion) vì cách sửa "đúng" (validate qua `ActiveIngredientRepository` của catalog) đòi cross-module
  read-port + adapter ở composition root — đúng loại bước mà quy tắc của sếp (S4.5/S5.4/C.5) luôn yêu cầu Opus + phiên riêng.
  Sếp chọn phương án Sonnet-an-toàn: bắt `sqlalchemy.exc.IntegrityError` ở `CrmService.add_allergy` (bọc quanh
  `repo.update(customer)`) và dịch thành `NotFoundError` → 404. Đáng tin cậy 100% trong ngữ cảnh này vì `customer_id` đã
  xác nhận tồn tại qua `_get_or_404` trước đó — FK `ingredient_id` là ràng buộc khả-vi-phạm duy nhất còn lại lúc insert.
  FK Postgres vẫn là nguồn enforcement thật (giữ nguyên, không bỏ) — code chỉ thêm lớp dịch lỗi.
- **Sửa kèm (bắt buộc để test được):** `core/db/session.build_engine()` bật `PRAGMA foreign_keys=ON` cho mọi kết nối SQLite
  (SQLite mặc định KHÔNG enforce FK) — nếu không, test chạy trên SQLite sẽ không bao giờ thấy `IntegrityError`, mù trước
  bug này y hệt lý do bug tồn tại (chỉ lộ trên Postgres sống). Áp dụng cho cả app thật (`build_engine`, dùng bởi e2e test
  qua `create_app`) lẫn `tests/integration/conftest.py` (`session_factory` fixture dùng listener tương tự trực tiếp trên
  engine của nó). Chỉ tác động dialect SQLite (`if url.startswith("sqlite")`) — Postgres không đổi hành vi.
  Chạy lại **toàn bộ** pytest sau khi bật để xác nhận không phá test nào khác do FK giờ được enforce thật (không có
  use-case xoá `Drug`/`Customer` nào tồn tại để cascade delete gây vỡ, nên an toàn) — xanh 274/274.
- **Xác nhận thủ công trên Postgres sống** (không chỉ tin SQLite): gọi qua ASGI app thật với `ingredient_id` ngẫu nhiên →
  `404` + body `problem+json` đúng (`type: not-found`, `detail: "Không tìm thấy hoạt chất <uuid>"`).
- Test mới: `test_crm_repo.py::test_add_allergy_unknown_ingredient_404_not_500` +
  `test_crm_api_e2e.py::test_unknown_ingredient_id_rejected_with_404_not_500` (+2, không đổi test cũ).
- `add_condition` **không** có gap tương tự — `condition_code` không có FK (ICD-10 không phải bảng tham chiếu trong hệ
  thống), nên không cần sửa.

Gate cuối (sau khi gỡ gap): ruff+format sạch, import-linter **11/0** (không đổi), mypy strict **161 file**, pytest **274**
(+2). **⇒ Module `crm` XONG hoàn toàn, gap 500↔404 đã gỡ.**

---

## 7f. Feature flag AI theo tenant (SaaS) — XONG HOÀN TOÀN, 2026-07-22

> Mục tiêu Sprint 6 (4): chuyển `AISettings.enable_clinical_ai` từ cấu hình **toàn cục** (chưa từng thật sự được đọc ở
> đâu trong code — cờ chết) sang **theo tenant**, để mỗi nhà thuốc (tenant) bật/tắt AI lâm sàng độc lập (đúng tinh thần
> SaaS đa tenant).

**Quyết định bảng lưu trữ (tự quyết theo đúng license "bạn quyết, báo lý do"):** **KHÔNG** tái dùng
`compliance.tenant_compliance_configs` — tạo bảng riêng `tenant_ai_settings` trong module `clinical`. Lý do:
1. Tái dùng bảng compliance nghĩa là `clinical` phải đọc dữ liệu do `compliance` sở hữu — dù chỉ đọc, vẫn là cross-module
   thật (cần import trực tiếp `compliance` — vi phạm `module-independence`; hoặc dựng read-port + adapter ở composition
   root — đúng loại bước quy tắc của sếp luôn bắt Opus + phiên riêng, S4.5/S5.4/C.5). Yêu cầu lần này ghi rõ **"Không
   cross-module mới"** — tái dùng bảng compliance sẽ trực tiếp vi phạm điều đó.
2. Hai khái niệm không liên quan: `ma_co_so_ban_le`/`ma_co_so_ban_buon` (compliance) là **mã pháp lý do Cục QLD cấp**,
   phục vụ liên thông CSDL Dược; `enable_clinical_ai` là **cờ tính năng sản phẩm**. Gộp chung 1 bảng làm giảm tính cố kết
   (cohesion), trộn 2 vòng đời/lý do thay đổi khác nhau vào 1 entity.
3. `TenantAiSettings` trong `clinical` theo đúng khuôn `TenantComplianceConfig` đã có (entity riêng, 1 dòng/tenant, upsert)
   — nhất quán kiến trúc, không phát minh pattern mới.

**Đã làm — domain (`clinical/domain/`):** `TenantAiSettings` (`tenant_id` + `enable_clinical_ai: bool = False` — mặc
định TẮT, fail-safe, "chưa cấu hình" đọc như đã tắt chứ không phải lỗi). Port `TenantAiSettingsRepository`
(`get`/`upsert`).

**Đã làm — infra:** `TenantAiSettingsORM` (`tenant_ai_settings`, unique `tenant_id`, giống khuôn
`TenantComplianceConfigORM`) + mapper + `SqlAlchemyTenantAiSettingsRepository` (get/upsert).

**Đã làm — app (`ClinicalService`):**
- `check_interactions` gọi `_ensure_ai_enabled(ctx)` **ngay sau** `require_permission` (trước khi chạm interaction
  repo/LLM) — đọc `TenantAiSettingsRepository.get(ctx.tenant_id)` (từ `RequestContext` đã có sẵn qua RBAC, **không**
  cross-module mới); `None` hoặc `enable_clinical_ai=False` → `FeatureDisabledError` (mới, `core/errors.py`, 403,
  `error_type: feature-disabled`). **Chỉ `check_interactions` bị chặn** — `get_recommendation`/`accept_recommendation`
  (đọc/duyệt bản ghi AI **đã có sẵn**) vẫn hoạt động dù tenant tắt AI sau đó, vì đó là tra cứu/audit, không phải "chạy AI".
- `get_tenant_ai_settings`/`set_tenant_ai_settings` (mới, quyền `clinical.settings.read`/`clinical.settings.write`) —
  `get` không 404 khi chưa cấu hình (luôn có câu trả lời rõ ràng: tắt), `set` upsert.

**Đã làm — interface:** `GET /clinical/settings`, `PUT /clinical/settings` (schemas
`SetTenantAiSettingsRequest`/`TenantAiSettingsResponse`), thêm vào router `/clinical/*` hiện có (không router mới).

**Đã dọn:** xoá `AISettings.enable_clinical_ai` khỏi `core/config.py` (cờ đã chuyển hẳn sang tenant, không giữ song song
2 nguồn sự thật gây nhầm lẫn). `min_confidence` **giữ nguyên** trong `AISettings` — đây là tham số tinh chỉnh LLM toàn
triển khai (deployment-wide), không phải cờ bật/tắt theo tenant, không thuộc phạm vi yêu cầu.

**Cập nhật test hiện có (vỡ do hành vi mặc định đổi từ "luôn chạy" sang "tắt trừ khi cấu hình"):**
- `test_clinical_flow.py`: thêm fixture `autouse=True` bật AI cho tenant của `ctx` trước mỗi test trong file (test này đo
  hành vi check chính, không đo cổng feature-flag) + thêm tham số `settings_repo_factory` vào `ClinicalService(...)` dựng
  tay trong `test_no_findings_low_confidence_still_requires_review`.
- `test_clinical_api_e2e.py`: fixture `client` bật AI sẵn qua `PUT /clinical/settings` (đa số test đo hành vi check);
  fixture mới `client_ai_off` (chưa cấu hình) cho 3 test riêng đo đúng cổng feature-flag.

**Test mới (+9):** domain (+2: mặc định tắt, bật được) · `test_clinical_flow.py` (+4: get/set roundtrip, tenant chưa
cấu hình đọc ra tắt, chặn khi tắt, chặn tenant chưa cấu hình) · `test_clinical_api_e2e.py` (+3: chặn tenant chưa cấu
hình → 403 problem+json đúng `type`, chặn khi tắt tường minh, roundtrip get/set/check qua HTTP thật).

**Migration `0010_clinical_tenant_ai_settings`:** autogenerate → apply **live Postgres** → `alembic check` sạch →
downgrade → upgrade lại → **check sạch lại**. Xác nhận thủ công qua ASGI app trên Postgres sống: mặc định tắt (403) →
bật (200) → tắt lại (dọn dữ liệu demo, không để tenant dev bị bật ngầm cho phiên sau).

Gate: ruff+format sạch, import-linter **11/0** (không đổi 11 contract — không có cross-module mới), mypy strict
**161 file**, pytest **283** (+9). **⇒ Feature flag AI theo tenant XONG hoàn toàn.**

---

## 7g. Điểm bắt đầu tiếp theo — chỉ còn `procurement` (2026-07-22, resume point)

> **Trạng thái tại đây:** code Bước 2 dừng ở `2de9d2b` (+1 commit tài liệu ngay sau), working tree sạch, **304 test xanh, 11 contract kept/0**. Nhánh B
> (**Sprint 6 Bước 2 = 5.5.4 auto-check + nối dị ứng KH**) đã **XONG** trong phiên này (xem §7h + changelog). Hạng mục
> DoD gốc còn lại duy nhất của Sprint 6 là **`procurement`**. Docker compose (postgres+redis) — **luôn `docker compose ps`
> để xác nhận thực tế**, xem lưu ý đầu file.

**Nhánh A — `procurement` (Supplier, PO, GRN → inventory IN) — CÒN LẠI DUY NHẤT:**
- Không phụ thuộc `crm`/`clinical`, chỉ cần `catalog`+`inventory` (đã có từ Sprint 3).
- **Sonnet làm được ngay**, không cần Opus/phiên riêng — theo đúng khuôn stepped-commit cũ (domain → app+infra+migration →
  interface, mỗi bước 1 commit, 4 cổng xanh).
- Đây là hạng mục DoD gốc còn lại cuối cùng của Sprint 6 (xem ROADMAP.md §Sprint 6).

**Nợ còn treo (không chặn `procurement`, ghi để không quên):**
- Ghi `MedicationHistoryEntry` (crm) từ event `SaleCompleted`/`PrescriptionDispensed` — cross-module, chưa làm.
- Nối dị ứng cho **bán lẻ OTC** — cần thêm `customer_id` vào `SalesOrder` + migration (sếp chốt hoãn).
- Mặt hiển thị cảnh báo (UI dashboard dược sĩ) + bảng audit dị ứng riêng — chờ spec UI.

## 7h. Sprint 6 Bước 2 — 5.5.4 auto-check tương tác + nối dị ứng KH (XONG HOÀN TOÀN, 2026-07-22)

> Cross-module ở composition root `api/v1/cross_module.py`, **cảnh báo không chặn** (cả 2 event đều hậu-commit; quyết định
> chặn-vs-cảnh-báo là nghiệp vụ/pháp lý — **sếp chốt cảnh báo**). `module-independence` GIỮ NGUYÊN (11 kept/0): `api` compose
> catalog+clinical+crm+prescription, các module không import nhau.

**4 bước con (mỗi bước 4 cổng xanh, 1 commit):**
- **B1 `68a0d74`** — `catalog.get_drug_ingredients(drug_id) -> [(ingredient_id, name)]` (hạ tầng chung nội bộ catalog; trả
  cả UUID lẫn tên vì tương tác khớp theo tên, dị ứng khớp theo `ingredient_id`). +5 test.
- **B2 `aeea74d`** — `wire_safety_checks`: bắt `SaleCompleted`+`PrescriptionDispensed` → resolve hoạt chất qua catalog →
  `clinical.check_interactions`; audit `AiRecommendation`; **tenant-gated** (`TenantAiSettings`, default OFF —
  `FeatureDisabledError` nuốt im lặng); bỏ qua giỏ <2 hoạt chất phân biệt (tránh audit rỗng). +6 test.
- **B3a `f0281f2`** — `clinical.check_allergies` **thuần** (domain `AllergyAlert`+`find_allergy_alerts`, khớp theo
  `ingredient_id`; nhận id tường minh nên clinical KHÔNG import crm/catalog). **Sếp chốt: KHÔNG cổng AI, KHÔNG persist** —
  dị ứng là an toàn tất định, chạy mọi tenant. +7 test.
- **B3b `2de9d2b`** — nối dị ứng vào handler dispense: đọc `crm.get_customer(customer_id).allergies` (**chỉ luồng
  prescription** — sale không có `customer_id`); log `allergy_warning_raised`. Đổi tên `wire_interaction_safety_check`→
  `wire_safety_checks`; thêm `crm.read` vào system-permission. Đổi tên file test → `test_cross_module_safety_checks.py`,
  +3 test dị ứng (dùng `structlog.testing.capture_logs` vì log-only). Tổng **304 test**.

**3 quyết định nghiệp vụ/pháp lý — đều do sếp chốt (Claude không tự quyết):** (1) cảnh báo không chặn; (2) dị ứng chỉ luồng
prescription, OTC hoãn; (3) dị ứng luôn chạy, không cổng AI, không persist audit.

---

## 7i. `procurement` — domain thuần XONG (2026-07-22, DỪNG trước app+infra)

> **Trạng thái:** chỉ mới **domain thuần** — chưa app/infra/migration/interface. Đây là hạng mục DoD gốc cuối cùng còn lại
> của Sprint 6 (§7g). Không phải bước cross-module rủi ro cao (khác S4.4/S4.5/S5.4/C.5/Sprint 6 Bước 2) — **Sonnet làm
> được, không cần Opus** — nhưng vẫn dừng theo đúng khuôn stepped-commit (domain → app+infra+migration → interface, mỗi
> bước 1 commit) theo yêu cầu tường minh của sếp phiên này.

**Đã làm (`procurement/domain/`):**
- `Supplier` — entity đơn giản (không state machine), không tự mang `tenant_id` trong chuỗi bất biến quan trọng (giữ khuôn
  `Drug`/`Customer`: tenant gắn ở ranh giới repository), guard `name` không rỗng, `deactivate()`.
- `PurchaseOrder` (aggregate root) + `PurchaseOrderItem` — state machine đúng docs/07_UML.md §6: `DRAFT` → `ORDERED` →
  (`PARTIALLY_RECEIVED` | `RECEIVED`) → `CLOSED`, hoặc `DRAFT` → `CANCELLED`. `add_item()` chỉ khi `DRAFT`; `place_order()`
  chặn đơn rỗng; `cancel()` chỉ từ `DRAFT`; `close()` chỉ từ `RECEIVED`.
- `GoodsReceiptNote` (aggregate root **riêng**, không lồng vào `PurchaseOrder`) + `GoodsReceiptItem` — lifecycle
  `DRAFT`→`CONFIRMED` (không có un-confirm: sửa sai bằng cách lập GRN mới, vì confirm là điểm sẽ kích hoạt bước
  cross-module tạo lô kho ở bước sau). `GoodsReceiptItem` mang đủ `lot_no`/`expiry_date`/`unit_cost`/`quantity_received`
  — đúng dữ liệu docs/06_WORKFLOWS.md §4 cần để tạo `product_batches` (ERD chỉ liệt kê bảng `goods_receipts` không có
  `goods_receipt_items` tường minh — đây là mở rộng thiết kế hợp lý theo đúng workflow, không phải lệch spec).
- **`PurchaseOrder.apply_receipt(items)`** — nối 2 aggregate qua `po_item_id` (tham chiếu phẳng, giống khuôn
  `SalesOrder.prescription_ref`), fold số lượng đã nhận vào từng dòng PO, tự tính lại status (`RECEIVED` nếu mọi dòng đủ,
  ngược lại `PARTIALLY_RECEIVED`). Đây **không phải** cross-module (2 aggregate cùng module `procurement`) — application
  layer (bước sau) sẽ gọi `grn.confirm()` rồi `po.apply_receipt(grn.items)` trong cùng use-case, lưu cả 2 lại.
  `OverReceiptError` chặn nhận vượt số đặt hàng; `UnknownPurchaseOrderItemError` chặn dòng GRN trỏ sai PO.
- Exceptions: `ProcurementError` + 9 lớp con (`InvalidSupplierError`, `InvalidPurchaseOrderItemError`,
  `EmptyPurchaseOrderError`, `InvalidPurchaseOrderStateError`, `UnknownPurchaseOrderItemError`, `OverReceiptError`,
  `InvalidGoodsReceiptItemError`, `EmptyGoodsReceiptError`, `InvalidGoodsReceiptStateError`).
- Events: `PurchaseOrdered` (docs/08 §2.4) + `GoodsReceived` mang `tuple[ReceivedItem, ...]` (đúng khuôn
  `SaleCompleted`+`SoldItem`) — **`GoodsReceived` là điểm nối cho bước cross-module sau này** (inventory subscribe để tạo
  `ProductBatch`+`StockMovement` IN, `grn_id` làm khoá idempotent giống `StockMovement.ref_type/ref_id`). Domain **không**
  tự publish event (giữ khuôn `prescription`/`crm` — publish là việc của application service).
- Ports: `SupplierRepository` (`add`/`update`/`get`/`list`), `PurchaseOrderRepository` (`add`/`update`/`get`),
  `GoodsReceiptRepository` (`add`/`get`) — khai trong domain, **chưa impl**.

Contract mới `procurement-domain-innermost` + `procurement` vào `module-independence` (**11 → 12** contract, không đổi 11
cái cũ). Test: `tests/unit/test_procurement_domain.py` (+28: Supplier guard/deactivate; PurchaseOrderItem guard; PO
lifecycle đủ nhánh (draft→ordered→partial→received→closed, cancel chỉ từ draft, add_item chặn sau ordered); apply_receipt
(partial, full, tích luỹ qua nhiều GRN, chặn trước ordered, chặn vượt số đặt, chặn dòng lạ); GoodsReceiptItem guard;
GoodsReceiptNote lifecycle (draft→confirmed, chặn confirm rỗng/2 lần, chặn add_item sau confirm)). **KHÔNG đụng
`catalog`/`inventory`/module nào khác** — cross-module (GRN xác nhận → tạo lô inventory) để dành bước sau, theo đúng yêu
cầu tường minh của sếp phiên này ("đặt ở composition root theo khuôn cũ, giữ module-independence").

Gate: ruff+format sạch, import-linter **12/0**, mypy strict **170 file**, pytest **332** (+28).

**Đã làm tiếp — app+infra+migration `0011` (cùng ngày, 2026-07-22, DỪNG trước interface HTTP):**
- **Sửa nhỏ trong domain (cùng module, không phải contract mới):** thêm `update()` vào `GoodsReceiptRepository` (domain step
  trước chỉ có `add`/`get`) — cần thiết để persist thay đổi `status` sau `grn.confirm()`; không phải cross-module, không đổi
  12 contract.
- **Infra:** `SqlAlchemySupplierRepository` (tenant-scoped, `add`/`update`/`get`/`list`, giống khuôn
  `SqlAlchemyCustomerRepository`) + `SqlAlchemyPurchaseOrderRepository` (`add`/`update`/`get` — `update()` sync status +
  từng dòng `quantity_received` theo id, **không** cần diff insert-only như crm vì item không bị xoá, chỉ cộng dồn) +
  `SqlAlchemyGoodsReceiptRepository` (`add`/`update`/`get` — `update()` sync status + append dòng mới theo id-diff, giống
  khuôn crm). ORM `SupplierORM` (tenant-scoped, không branch — giống `CustomerORM`) + `PurchaseOrderORM`/
  `PurchaseOrderItemORM` (`TenantScopedMixin` đủ tenant+branch) + `GoodsReceiptORM`/`GoodsReceiptItemORM`.
  **Quyết định kỹ thuật:** `GoodsReceiptItemORM.po_item_id` có FK thật tới `purchase_order_items.id` — khác FK xuyên module
  của `crm.CustomerAllergyORM.ingredient_id` (S6 trước), đây là FK **cùng module** (`procurement`) nên an toàn tuyệt đối
  với `module-independence`, không cần lớp dịch lỗi 404 như crm. `drug_id` trên mọi bảng **không FK** (đúng khuôn cũ — tham
  chiếu chéo module tới `catalog`, giống `SaleLine.drug_id`).
- **App:** `ProcurementService` (3 repo factory, theo khuôn `ComplianceService`): `create_supplier`/`get_supplier`/
  `list_suppliers`; `create_purchase_order`(kèm dòng ban đầu, theo khuôn `create_prescription`)/`add_po_item`/
  `mark_ordered`(phát `PurchaseOrdered`)/`cancel_purchase_order`/`close_purchase_order`/`get_purchase_order`;
  `create_goods_receipt`(load PO trước để lấy đúng `tenant_id`/`branch_id`)/`confirm_goods_receipt`(gọi `grn.confirm()` rồi
  `po.apply_receipt(grn.items)` trong cùng transaction, lưu cả 2 qua 2 repo cùng 1 `uow`, phát `GoodsReceived` sau commit
  với `items: tuple[ReceivedItem,...]` đủ dữ liệu cho bước cross-module sau)/`get_goods_receipt`. Quyền mới:
  `procurement.supplier.{create,read}`, `procurement.po.{create,read,write}`, `procurement.grn.{create,read,confirm}` —
  tách `grn.confirm` riêng khỏi `grn.create` (như `rx.approve` tách khỏi `rx.create`) vì confirm là điểm sẽ kích hoạt tạo lô
  kho ở bước cross-module sau, rủi ro cao hơn tạo nháp.
- **Migration `0011_procurement`:** autogenerate (rev-id đặt tay `0011_procurement` để filename khớp revision, giống khuôn
  `0009_crm_customers`) → apply **live Postgres** → `alembic check` sạch → downgrade → upgrade lại → **check sạch lại**.
  5 bảng mới (`suppliers`, `purchase_orders`, `purchase_order_items`, `goods_receipts`, `goods_receipt_items`), không đổi
  bảng cũ. **Xác nhận thêm thủ công qua script chạy trực tiếp trên Postgres sống** (ngoài SQLite test-harness, vì
  `procurement` chưa có router để test qua ASGI app): supplier→PO(kèm dòng)→`mark_ordered`→GRN(kèm dòng)→
  `confirm_goods_receipt` → PO **RECEIVED** → `close_purchase_order` → **CLOSED**, `GoodsReceived` phát đúng 1 lần với
  `lot_no` khớp — dọn dữ liệu demo sau khi xác nhận (không để sót trên DB dev).
- Test: `tests/integration/test_procurement_flow.py` (+19: supplier CRUD+tenant-isolation+permission+list-order-by-name;
  PO create-with-items/add-item-while-draft/mark_ordered-emits-event-blocks-add-item/place-order-empty-rejected/
  cancel-from-draft/cancel-after-ordered-rejected; GRN confirm-partial→PARTIALLY_RECEIVED, confirm-full→RECEIVED+event+
  close→CLOSED, over-receipt rejected, confirm-before-ordered rejected, create-against-unknown-po 404, confirm-empty
  rejected, get-unknown-grn 404). `conftest.py` thêm fixture `procurement_service` (3 repo factory) + quyền
  `procurement.*` vào `ctx`.

**KHÔNG làm interface HTTP** (router/schemas/`register()`) — theo đúng yêu cầu, dừng ở đây. **KHÔNG cross-module**
(GRN confirmed → inventory ProductBatch/StockMovement) — `GoodsReceived` đã phát đủ dữ liệu (`items` mang `drug_id`/
`lot_no`/`expiry_date`/`unit_cost`/`quantity`) nhưng chưa có subscriber, giống tiền lệ `SaleCompleted` trước khi S4.4 nối
inventory.

Gate cuối: ruff+format sạch, import-linter **12/0** (không đổi 12 contract, không có cross-module mới), mypy strict
**175 file**, pytest **351** (+19). **⇒ `procurement` domain+app+infra+migration XONG hoàn toàn.**

**Đã làm tiếp — interface HTTP (cùng ngày, 2026-07-22, DỪNG trước cross-module GRN→inventory):**
- **Gap phát hiện + sửa trước khi làm interface:** `create_goods_receipt` nhận `po_item_id` từ client nhưng không kiểm tra
  gì trước khi build `GoodsReceiptItem` — `GoodsReceiptItemORM.po_item_id` có FK thật tới `purchase_order_items.id` (từ
  bước app+infra trước), nên `po_item_id` sai sẽ vỡ `IntegrityError`/500 thô khi insert, **đúng dạng bug đã gặp và sửa ở
  `crm.add_allergy`** (S6, xem §7e) — nhưng ở đây tốt hơn: PO đã được load sẵn trong cùng use-case (cùng module, không
  cross-module như crm→catalog), nên sửa bằng validate tường minh `po_item_id ∈ {po.items[].id}` **trước khi** build item,
  ném `UnknownPurchaseOrderItemError` (domain exception đã có sẵn từ `apply_receipt`, tái dùng) → 422 — sạch hơn cách dịch
  lỗi FK của crm, không cần bắt `IntegrityError`. Test: `test_create_goods_receipt_unknown_po_item_rejected_not_500` (flow)
  + `test_unknown_po_item_id_rejected_with_422_not_500` (e2e).
- **Schemas:** `interface/schemas.py` — `CreateSupplierRequest`/`SupplierResponse`; `PurchaseOrderItemRequest`/
  `CreatePurchaseOrderRequest`/`PurchaseOrderItemResponse`/`PurchaseOrderResponse`; `GoodsReceiptItemRequest`/
  `CreateGoodsReceiptRequest`/`GoodsReceiptItemResponse`/`GoodsReceiptResponse` — validation ở boundary (`quantity_ordered`/
  `quantity_received` `Field(gt=0)`, `unit_price`/`unit_cost` `Field(ge=0)`, `lot_no` không rỗng), theo khuôn `crm`/
  `prescription` schemas.
- **Router:** `interface/router.py` — 3 sub-router (`/suppliers`, `/purchase-orders`, `/goods-receipts`) gộp vào 1
  `build_router()`, vì docs/11 §procurement liệt kê 3 nhóm tài nguyên khác prefix (khác `clinical` chỉ 1 prefix). Route
  vượt khỏi 3 route docs/11 nêu tối thiểu (`GET/POST /suppliers`, `POST /purchase-orders`, `POST /goods-receipts`): thêm
  `GET /suppliers/{id}`, `GET/POST /purchase-orders/{id}`+`/items`+`/place`+`/cancel`+`/close`, `GET /goods-receipts/{id}`+
  `/confirm` — cần thiết để expose state machine qua HTTP, theo đúng tiền lệ `/prescriptions/{id}/{validate,reject,
  dispense}` (S5.3) đã mở rộng ngoài bản phác thảo gốc docs/11.
- **Wiring:** `interface/register.py` (3 repo factory, theo khuôn app-layer) + `api/v1/__init__.py` thêm `register_procurement`
  (đơn giản, không cross-module — đặt ngay sau `register_crm`) + `api/deps.py` thêm quyền dev `procurement.*` (8 quyền, khớp
  `ctx` fixture test).
- Test: `tests/integration/test_procurement_api_e2e.py` (+14, HTTP thật qua `TestClient(create_app())`, **thay cho script
  chạy tay trên Postgres sống** dùng ở bước trước) — supplier CRUD+list-order-by-name+404+422 schema; PO
  create-with-items/add-item/place/cancel/state-guards (chặn add-item & cancel sau khi ORDERED)/place-empty-rejected; full
  flow GRN tạo→confirm→PO RECEIVED→close CLOSED; partial receipt→PARTIALLY_RECEIVED; over-receipt 422; **po_item_id lạ →
  422 không phải 500**; GRN với PO lạ → 404; get GRN lạ → 404.

**KHÔNG làm cross-module** (GRN confirmed → inventory `ProductBatch`/`StockMovement`) — theo đúng yêu cầu, đây là bước
riêng cuối cùng của Sprint 6, để dành.

Gate cuối: ruff+format sạch, import-linter **12/0** (không đổi 12 contract, không có cross-module mới), mypy strict
**178 file**, pytest **366** (+15). **⇒ `procurement` đủ 4 lớp Hexagonal — chỉ còn cross-module GRN→inventory.**

**Đã làm — cross-module GRN confirmed → inventory tạo lô (2026-07-22, Opus, thiết kế duyệt trước; ĐÓNG Sprint 6):**
> Thiết kế được sếp duyệt trước khi code, chốt 2 quyết định: **PA A** (va chạm lô → bỏ qua dòng, không gộp — nhất quán với
> `receive_stock` thủ công + `uq_batch_lot`; gộp lô để dành enhancement riêng cho cả 2 luồng sau) và **bản ghi bù nhẹ** (bảng
> nhỏ ghi MỌI ca GRN confirmed mà không tạo được lô, không phải outbox/retry đầy đủ).
- **Trigger:** `wire_goods_receipt_stock_in(container)` ở `api/v1/cross_module.py` subscribe `GoodsReceived` (khuôn
  `wire_sale_dispensing`), nối trong `build_api_router` ngay sau `wire_sale_dispensing`. Handler map `ReceivedItem` →
  `inventory.GoodsReceiptLine` (DTO **của inventory**) → `InventoryService.receive_from_goods_receipt(lines, grn_id, ctx)`.
  Chạy dưới system-ctx `_GRN_STOCK_IN_PERMISSIONS={"inventory.receive"}`, `branch_id` lấy thẳng từ `GoodsReceived` (event
  mang branch thật). `procurement`/`inventory` KHÔNG import nhau — chỉ `api` import cả hai. **12 contract giữ nguyên.**
- **Use-case mới `InventoryService.receive_from_goods_receipt`** (bản sao đối xứng `dispense_for_sale`, additive — không đụng
  `receive_stock` thủ công): 1 transaction cho cả GRN; idempotent đầu vào `exists_for_ref("grn", grn_id)` (mọi IN-movement
  mang `ref_type="grn"`+`ref_id=grn_id`, chữ thường — **không** va `ref_type="GRN"` hoa + `ref_id` null của receive thủ
  công); mỗi dòng: **pre-check `BatchRepository.find_by_lot`** (port mới) để tránh `IntegrityError` làm hỏng transaction —
  trùng `(drug,branch,lot)` → **bỏ qua + ghi `StockReconciliationNeeded`** (kèm `po_item_id` dòng đó), ngược lại tạo
  `ProductBatch`(cost_price=unit_cost)+`StockMovement` IN+`balances.adjust`+collect `StockMovedIn`. Lỗi bất ngờ (race
  `IntegrityError`, DB down…) → transaction rollback, **best-effort ghi 1 bản ghi bù toàn-GRN** (`po_item_id=None`) ở
  transaction riêng + log ERROR, KHÔNG ném ra (bus đã cô lập; degrade có vết thay vì mất tồn im lặng).
- **Bảng `stock_reconciliation_needed`** (đặt ở **`inventory`** — nơi phát hiện lỗi; `grn_id`/`po_item_id` là UUID trần
  **không FK** tới procurement → giữ module-independence): `tenant_id`+`branch_id` (TenantScopedMixin), `grn_id`,
  `po_item_id?`, `reason`, `occurred_at`, `resolved`(default False). **Không API resolve** (đủ cho DoD — chỉ ghi để tra
  cứu). Domain entity `StockReconciliationNeeded` + port `StockReconciliationRepository` + ORM + repo, đủ 4 lớp.
- **Thread `po_item_id`:** thêm `po_item_id` vào `procurement.ReceivedItem` (event) → `confirm_goods_receipt` truyền từ
  `GoodsReceiptItem.po_item_id` → handler → `GoodsReceiptLine` → bản ghi reconciliation (để biết *dòng nào* va chạm).
- **Migration `0012_stock_reconciliation`** (1 bảng): autogenerate → apply **live Postgres** → `alembic check` sạch →
  downgrade → upgrade lại → **check sạch lại**. **Constructor `InventoryService` thêm 1 repo factory** (reconciliation) —
  cập nhật 2 chỗ dựng: `inventory/interface/register.py` + `tests/integration/conftest.py`.
- Test: `test_cross_module_goods_receipt.py` (+4 service-level: tạo lô/dòng, idempotent theo `grn_id`, va chạm lô → bỏ qua +
  ghi reconciliation đúng `po_item_id`, dòng qty≤0 bỏ qua) + `test_procurement_inventory_e2e.py` (+2 e2e HTTP thật qua
  `TestClient`: GRN confirm → on-hand tăng; 2 GRN từng phần lô khác nhau → tồn cộng dồn). **Smoke live Postgres** qua ASGI
  (tenant tạm, dọn sạch sau) xác nhận on-hand=100 sau confirm.
- Gate cuối: ruff+format sạch, import-linter **12/0** (không đổi — cross-module ở `api`), mypy strict **178 file**, pytest
  **372** (+6). **⇒ DoD gốc Sprint 6 "Nhập PO→GRN tạo lô" ĐẠT — Sprint 6 ĐÓNG.**

**Nợ mang sang Sprint 7 (đã biết, không chặn đóng Sprint 6):** (1) enhancement **gộp lô** (PA B) cho cả 2 luồng
receive_stock + GRN; (2) ghi `MedicationHistoryEntry` từ event `SaleCompleted`/`PrescriptionDispensed` (DoD Sprint 6 có
nhắc "lịch sử KH", sếp đã hoãn — cross-module riêng); (3) dị ứng OTC (cần `customer_id` trên `SalesOrder`); (4) outbox/retry
bền thay best-effort reconciliation; (5) API tra cứu/resolve `stock_reconciliation_needed`.

---

## 7j. Điểm bắt đầu tiếp theo — tính năng thương mại qua cổng `docs/14` (2026-07-23, resume point)

> **Trạng thái tại đây:** Sprint 6 ĐÓNG. **In bill (S7) XONG** đủ 4 lớp (commit `4a5bc0b`→`53e31b3`, xem entry changelog 2026-07-23 đầu). Còn **hồ sơ KH · tích điểm KH** (2/3 tính năng thương mại ngoài ROADMAP) — cả hai vẫn NGOÀI ROADMAP gốc → **bắt buộc đi qua Bước 0-4 của docs/14 trước khi code.**

**2 blocker nền:**
1. **RBAC/IAM (Bước 1.5) — ✅ ĐÃ THỎA (2026-07-23).** Module `iam` thật đã xong 4/4 bước, xem §7k.
   Còn 1 điểm liên quan trực tiếp tới 2 tính năng này: `crm.read` vẫn gộp cả dữ liệu thường lẫn dị
   ứng/bệnh nền — NĐ356 Điều 4.2 đòi phân quyền riêng cho dữ liệu nhạy cảm. Hiện thu ngân không
   được cấp quyền crm nào (an toàn), nhưng khi làm **hồ sơ KH** phải tách `crm.sensitive.read`.
2. **Văn bản pháp lý (Bước 1.1/1.8) — ĐÃ ĐỦ (2026-07-23).** Sếp đã thả đủ **Luật BVDLCN 91/2025/QH15**, **NĐ 356/2025/NĐ-CP**, **GPP** (TT02/2018 + TT11/2025 + TT29/2020), **Luật Dược 105/2016/QH13** + **Luật sửa đổi 44/2024/QH15**. Đã đọc + tóm tắt 10 file `docs/legal/*.SUMMARY.md` (xem `docs/legal/README.md`). **Traceability `docs/13_COMPLIANCE_SPEC.md` đã cập nhật (commit `aedd005`, sếp duyệt)** — dòng 14 (C.3 rule 1 ETC) nay dẫn Luật Dược Điều 2.27-28+6.5.h; dòng 17 (D.1 liên thông) nay có thêm Điều 75.2. Câu hỏi pháp lý mở còn treo (cần luật sư, không chặn IAM): (a) BeraLLC có cần Giấy chứng nhận kinh doanh dịch vụ xử lý DLCN (NĐ356 Điều 21-27) không.

**4 lệch đã báo cáo (sếp chốt sửa SAU khi xong 3 tính năng — vẫn hoãn, chỉ mới 1/3 xong):** demo_preview.py lỗi thời (2 constructor thiếu tham số); TODO:158 procurement chưa tick; TODO:73 C.5 chưa tick; cây rỗng untracked `backend/backend/`.

## 7k. Module IAM thật (users/roles/JWT) — ✅ XONG 4/4 bước (2026-07-23)

> **Trạng thái cuối:** sếp duyệt trọn 11 điểm thiết kế (`docs/15_IAM_DESIGN.md` §8) trong 1 lượt,
> thi công xong 4 bước, mỗi bước 1 commit + 4 cổng xanh: `3bc148f` (domain) → `5c3bc08`
> (application+infra+migration 0013) → `4c64a4c` (interface + `api/deps.py` + CLI bootstrap).
> **Blocker RBAC/IAM ở §7j mục 1 nay ĐÃ GỠ.**

| Hạng mục | Kết quả |
|----------|---------|
| Lỗ hổng `X-Branch-Id` (F1) | **ĐÃ ĐÓNG** — `branch_id` nằm trong claim JWT đã ký, header bị bỏ qua; có test e2e chốt |
| Dev-header | Giữ nhưng **fail-closed**: cần `SECURITY__ALLOW_DEV_AUTH=true` (mặc định **false**) + `Settings` từ chối boot nếu prod bật |
| `_DEV_PERMISSIONS` lệch 26/32 (F3) | **ĐÃ VÁ** — lấy thẳng từ `iam.domain.ALL_PERMISSIONS` (38 = 32 business + 6 `iam.*`) |
| Refresh token | Revocable + xoay vòng + phát hiện tái sử dụng (replay → thu hồi toàn bộ session của user) |
| Role 2 cấp | `user_roles.branch_id` NULL = toàn chuỗi; **2 partial unique index** (UNIQUE 3 cột không chặn trùng vì Postgres coi NULL là khác nhau) |
| Seed role | 5 role: `system_admin` 38 · `chain_pharmacist` 34 · `branch_pharmacist` 28 · `warehouse` 11 · `cashier` 6 (đã xác nhận trên Postgres thật) |
| Bootstrap | CLI `python -m seeds.bootstrap_tenant`, mật khẩu stdin/env, không mặc định; đã chạy thật rồi dọn tenant thử nghiệm |
| Cổng cuối | ruff sạch · mypy strict **201 file** · import-linter **13/0** · pytest **465** (+51) |

**Nợ ghi rõ, KHÔNG báo là xong:**
1. **Thu hồi quyền trễ ≤60 phút** — access token TTL giữ 60 (D2). Refresh mới tính lại quyền. Cần
   tức thì thì phải vô hiệu hóa user (thu hồi luôn session).
2. **Auth cho POS offline dài hạn CHƯA GIẢI** — lý do giữ TTL 60 thay vì hạ 15. Bài toán riêng.
3. ~~**`audit_logs` vẫn chỉ ghi structlog**~~ — **ĐÃ GỠ 2026-07-23, xem §7l.**
4. **Tách `crm.read` → `crm.sensitive.read` chưa làm** (D8 chọn phương án a). Thu ngân hiện không
   có quyền crm nào; khi `SalesOrder` có `customer_id` thì phải quay lại tách.
5. **Chưa gỡ hẳn dev-header** — 11 file test cũ vẫn opt-in `allow_dev_auth=True`. Chuyển hết e2e
   sang login thật rồi mới xóa được.
6. **Chưa có use-case tạo chi nhánh/tenant qua API** (quản lý chuỗi ngoài phạm vi, docs/15 §1) —
   test hai chi nhánh phải dựng branch thẳng qua repository.
7. **Module `compliance` vẫn chưa mount router** (F4) — không sửa ở bước này.
8. Chưa làm: 2FA (`require_2fa_roles` có field nhưng chưa dùng), SSO, hiệu lực role theo thời gian.

---

## 7l. `audit_logs` — persist nhật ký truy vết (gỡ nợ F8) — ✅ XONG 3/3 bước (2026-07-23)

> **Điều kiện đã chốt để mở `docs/14` cho Hồ sơ KH — nay ĐÃ THỎA.** 3 commit, mỗi bước 4 cổng xanh:
> `8435b42` (hình dạng) → `05b7857` (persist + migration `0014`) → `aa521ec` (đọc + vá bug drift).

| Hạng mục | Kết quả |
|----------|---------|
| Bảng `audit_logs` | `id`, `tenant_id`, `actor_user_id` (nullable), `action`, `target_type`, `target_id` (nullable), `occurred_at`, `context` (JSONB/JSON). 2 index: `(tenant_id, occurred_at)`, `(tenant_id, actor_user_id)` |
| Append-only | Repository **không có** `update`/`delete` — ràng buộc cấu trúc, không phải quy ước. Có test khẳng định |
| `AuditAction` | **11** giá trị (9 theo yêu cầu + `USER_ACTIVATED` + `PASSWORD_RESET` — IAM gọi thật, gom lại là mất thông tin) |
| Ghi | DB (bắt buộc, transaction riêng) **+** structlog song song, không thay thế nhau |
| `context` | CHỈ `client_ip` + `branch_id`. Có test khẳng định không lọt mật khẩu/token |
| Đọc | `GET /api/v1/audit-logs` — lọc thời gian/actor/action + phân trang, quyền mới `audit.read` (chỉ `system_admin` + `chain_pharmacist`) |
| Migration `0014_audit_logs` | up → check sạch → downgrade → up → check sạch lại. pg_dump trước: `~/backup_pre_migration_20260723_1244.sql` |
| Cổng cuối | ruff sạch · mypy strict **208 file** · import-linter **13/0** · pytest **505** (+40) |

**2 phát hiện khi kiểm chứng thật (không phải bug vặt — ghi lại vì đáng nhớ):**
1. **Role hệ thống chỉ seed MỘT LẦN, không bao giờ cập nhật.** Deployment cài từ bản trước giữ
   nguyên bộ permission cũ vĩnh viễn ⇒ admin gọi `/audit-logs` bị **403** dù code đã cấp quyền.
   **Test suite không bắt được** vì luôn khởi tạo DB rỗng nên luôn đi nhánh insert; chỉ lộ khi chạy
   CLI thật trên Postgres đã có dữ liệu. Đã sửa: `sync_system_roles()` (thêm mới + **cập nhật cái
   đã lệch**), gọi trong bootstrap và thêm vào `seeds/run.py` ⇒ `make seed` sau nâng cấp là đủ.
   Role riêng của tenant không bị đụng. +4 test hồi quy.
2. **Cổng import-linter bắt vi phạm layers thật**: đặt `client_ip` ở `api/deps.py` khiến router
   của `iam` import ngược lên tầng `api`. Đã hạ helper xuống `core/http.py`.

**Nợ còn lại của phần audit (ghi rõ, không overclaim):**
1. **Chỉ phủ 11 hành vi của `iam`.** Nghiệp vụ khác (bán hàng, cấp phát thuốc, đọc hồ sơ KH) **chưa
   ghi audit** — khi làm Hồ sơ KH phải thêm action cho việc *đọc* dữ liệu nhạy cảm, vì đó mới đúng
   là thứ NĐ356 Điều 4.2 quan tâm nhất.
2. **`client_ip` sau reverse proxy sẽ ghi IP của proxy.** Cố ý không đọc `X-Forwarded-For` (client
   gửi được ⇒ giả mạo được đúng chỗ không được phép giả mạo). Cần danh sách trusted-proxy.
3. **Không có retention/xóa theo hạn.** GPP TT02/2018 II.4.d nói lưu tối thiểu; chưa có chính sách
   xóa sau hạn, cũng chưa có ai hỏi.
4. **Dashboard/analytics audit vẫn là việc Sprint 7** — cố ý chỉ làm mức tối thiểu, tránh trùng công.
5. `GET /compliance/audit-logs` trong `docs/11` đã bị thay bằng `GET /audit-logs` (không làm 2
   endpoint trùng chức năng).

---

## 7n. ✅ CHỐT PHIÊN 2026-07-23 (Opus) — ĐỌC MỤC NÀY TRƯỚC KHI LÀM GÌ Ở PHIÊN SAU

> **Trạng thái khi đóng phiên (đã xác nhận bằng lệnh, không tin tài liệu):**
> `docker compose ps` postgres+redis **healthy** · `alembic current` = **`0015_customer_consents`
> (head)** · `git status` **sạch** · ruff sạch · mypy strict **210 file** · import-linter **13/0** ·
> pytest **560 passed**. **20 commit** trong phiên, từ `3bc148f` đến `7ae3947`.

### Phiên này làm được gì

| Việc | Kết quả | Mục chi tiết |
|------|---------|--------------|
| **Module `iam` thật** (thay dev-header) | ✅ XONG 4/4 bước | §7k |
| **`audit_logs` persist** (gỡ nợ F8) | ✅ XONG 3/3 bước | §7l |
| **Hồ sơ sức khỏe KH** qua cổng `docs/14` | 🟡 Bước 0-3 xong, **Bước 4 còn 5 việc** | §7m |
| **Thương hiệu BERAS + nguyên tắc UI** | ✅ `docs/16_BRAND_UI_GUIDE.md` | docs/16 |

### 🔜 Phiên sau bắt đầu từ đâu — theo đúng thứ tự này

1. **Đóng Bước 4 của Hồ sơ sức khỏe KH** (§7m có tên file cụ thể cho cả 5 việc). Nhỏ, cơ học,
   không thiết kế mới, không migration, không cross-module. **Cẩn thận cái bẫy đã ghi ở §7m mục 2:
   test e2e thu ngân đang khẳng định 403, nếu quên sửa thì test vẫn xanh.**
2. **Mount router `compliance`** — module đã code xong sổ thuốc kiểm soát + liên thông nhưng chưa
   có mặt HTTP nào. Đây là việc **vài phút** đang chặn cả một trụ cột thương hiệu (docs/16 §5 trụ 2).
3. **Audit cho `prescription` + `compliance`** — GĐ khuyến nghị làm trước mọi tính năng thương mại
   khác. Hiện 2/9 module có audit; thiếu nặng nhất là **cấp phát thuốc kê đơn** và **sổ thuốc kiểm
   soát**, tức đúng hai thứ thanh tra dược hỏi đầu tiên. Hạ tầng đã sẵn, mở rộng là việc cơ học.

### Quyết định sếp đã chốt trong phiên (không cần hỏi lại)

| Nhóm | Chốt |
|------|------|
| IAM (11 điểm, duyệt 1 lượt) | Refresh revocable + xoay vòng · TTL 60 phút · bootstrap bằng CLI · email unique toàn hệ thống · dev-header fail-closed · branch trong token đã ký · 5 role theo chức danh · IAM sở hữu `tenants`+`branches` · sửa contract import-linter |
| Hồ sơ sức khỏe KH (7 câu) | Đồng ý 2 mức BASIC/HEALTH · **khử nhận dạng** thay xóa cứng · audit luồng máy dùng action riêng · thu ngân được `crm.read`+`create`+`consent.manage` · `SalesOrder.customer_id` **ngoài phạm vi** · DPIA: mẫu + endpoint, khách tự nộp · `MedicationHistoryEntry` tự động **ngoài phạm vi** |
| Vận hành | Kỷ luật #7 (thử trên CSDL có dữ liệu sẵn) · `CLAUDE.md` vào git · "bấm có là đồng ý" (không dựng cổng văn bản điều khoản) |
| Thương hiệu | **BERAS** + tagline + tông màu Eco-Tech + 3 trụ cột + 2 nguyên tắc UI |

### Quyết định Claude TỰ CHỐT trong full-auto (theo kỷ luật full-auto #3 — sếp đọc lướt khi rảnh)

| # | Tự quyết | Lý do |
|---|----------|-------|
| 1 | Lỗi ghi audit **không bị nuốt**, ném lên | Bảng audit cùng CSDL với dữ liệu nghiệp vụ ⇒ insert audit hỏng nghĩa là ghi nghiệp vụ cũng đang hỏng; nuốt lỗi chỉ giấu việc nhật ký bị thủng |
| 2 | Audit ghi trên **transaction riêng** | Nhiều điểm gọi nằm sau khi giao dịch nghiệp vụ đã commit |
| 3 | Gộp Bước 1 Hồ sơ KH (domain+infra+app+1 endpoint) | Ràng buộc đồng ý ở domain làm 9 test đỏ; commit domain-thuần sẽ vi phạm kỷ luật #1 |
| 4 | Enum audit **11 action** thay vì 9 sếp nêu | Thêm `USER_ACTIVATED` + `PASSWORD_RESET` vì IAM gọi thật; gom lại là mất thông tin |
| 5 | Thêm `CUSTOMER_SENSITIVE_WRITE` ngoài action sếp giao | `docs/14` mục 4 đòi audit cả ghi/sửa, không chỉ đọc |
| 6 | Luồng máy đọc dị ứng **không** chắn bằng `crm.sensitive.read` | Chắn lại = cảnh báo dị ứng lặng lẽ ngừng kêu đúng với thu ngân — nhóm ít khả năng tự phát hiện nhất. Trả giá bằng dữ liệu tối thiểu + action audit riêng |
| 7 | Thiếu quyền nhạy cảm → **giấu trường**, không 403 | Thu ngân gắn khách vào đơn là việc hợp lệ |
| 8 | `list_customers` **không bao giờ** trả dữ liệu sức khỏe | 50 hồ sơ/trang không phải tra cứu; audit thành 50 lượt đọc sẽ làm ngập nhật ký |
| 9 | Xuất dữ liệu **không** phụ thuộc đồng ý | Quyền được biết không điều kiện hóa theo đồng ý xử lý |
| 10 | `POST .../anonymise` chứ không `DELETE` | Dòng dữ liệu vẫn sống vì mang nghĩa vụ lưu trữ GPP |
| 11 | `granted` **không** có giá trị mặc định (dù sếp chốt "bấm có là xong") | Mặc định = "im lặng là đồng ý", đúng thứ Luật 91 Điều 9 cấm thẳng. Chỉ cho `terms_version` mặc định |
| 12 | Tạo `backend/.env` (máy này trước đó **không có**) | Phục vụ đúng ý sếp: mở máy demo chạy được |
| 13 | H1 README đổi thành `BERAS` | "Nhất quán thương hiệu" mà tiêu đề vẫn tên cũ thì mâu thuẫn ngay 3 dòng đầu |
| 14 | Thêm `docs/16` §5 (trạng thái backend thật) + §4.3 (hệ quả UI) | Nguyên tắc "không quảng bá tính năng chưa sẵn sàng" cần bảng tra mới dùng được |

### Bug thật phát hiện & vá trong phiên (không phải bug vặt)

| # | Bug | Vì sao đáng nhớ |
|---|-----|-----------------|
| 1 | `api/deps.py` tin `X-Branch-Id` không kiểm tra ⇒ đổi header là truy cập chi nhánh khác với nguyên bộ quyền | **Lỗ hổng thật đang chạy**. IAM đã đóng bằng cách ký branch vào JWT |
| 2 | Role hệ thống chỉ seed **một lần**, không bao giờ cập nhật ⇒ deployment cũ mãi thiếu permission mới, admin bị 403 | **505 test đều xanh** trong khi tính năng hỏng trên máy thật. Sinh ra kỷ luật #7 |
| 3 | `.env.example` còn `AI__ENABLE_CLINICAL_AI` (đã bỏ khỏi `AISettings`) ⇒ làm đúng README (`cp .env.example .env`) là app **không khởi động nổi** | Hướng dẫn cài đặt không ai chạy lại thì mục dần trong im lặng |
| 4 | `_DEV_PERMISSIONS` lệch còn 26/32 permission | Khiến use-case `compliance` không gọi được trong dev |
| 5 | `repository.update()` chỉ insert ⇒ dị ứng/bệnh nền **sống sót qua chính lệnh xóa** | Test domain vẫn xanh vì entity trong bộ nhớ đã sạch |

### Việc còn treo chờ sếp (không chặn code)

| Việc | Ghi chú |
|------|---------|
| Ghi quyết định thương hiệu BERAS vào `BeraLLC/ChienLuoc/` | Hiện chỉ nằm trong `README`/`docs/16` của thư mục lập trình — sai chỗ theo quy tắc của chính sếp |
| Bán cho nhà thuốc lẻ hay chuỗi trước · màn hình đầu tiên xây là màn nào | GĐ đã hỏi 2 lần, ảnh hưởng cả UI lẫn thứ tự tính năng |
| Luật sư: rà lại Q2 (khử nhận dạng) · văn bản điều khoản cho `terms_version` · phần pháp lý mẫu DPIA | Ba việc, gộp một lần hỏi |
| Tagline README ≠ tagline chính thức `docs/16` | Sếp quyết dùng câu nào ở dòng đầu README |
| Badge `domain coverage 97%` chưa kiểm chứng lại từ Sprint 3 | Đo lại mất ~5 phút |
| Bộ test **1:27 → 4:09** trong một phiên | Chưa cần xử lý; cách rẻ nhất là hạ vòng bcrypt trong test |

---

## 7m. Hồ sơ sức khỏe khách hàng — qua cổng `docs/14` Bước 0-4, ĐÃ DUYỆT, CHƯA CODE (2026-07-23)

> **Điểm bắt đầu tiếp theo.** Tài liệu đầy đủ: `docs/features/ho-so-suc-khoe-khach-hang/01_DECISIONS.md`
> (commit `54db5ec`). Bước 0-3 xong, 7/7 câu hỏi mở sếp đã quyết, Bước 4 (ROADMAP+PROJECT_STATE) xong.
> **Chưa code dòng nào** — chờ sếp cho lệnh bắt đầu.

**2 blocker nền của §7j nay ĐỀU ĐÃ GỠ:** RBAC/IAM (§7k) · văn bản pháp lý (đủ 10 file `docs/legal`).
Cộng thêm `audit_logs` (§7l) là điều kiện sếp tự đặt thêm — cũng đã thỏa.

| Quyết định | Chốt |
|-----------|------|
| Q1 đồng ý | 2 mức `BASIC` (tên/SĐT) + `HEALTH` (dị ứng/bệnh nền/lịch sử) |
| Q2 rút đồng ý/xóa | **Khử nhận dạng, giữ dòng lịch sử** — không xóa cứng |
| Q3 audit luồng máy | Có, action riêng `CUSTOMER_SENSITIVE_AUTO_CHECK` |
| Q4 thu ngân | Được `crm.read` + `crm.create` + `crm.consent.manage` (**đảo D8**, tiền đề đã đổi) |
| Q5 `SalesOrder.customer_id` | **Ngoài phạm vi**, tách bước riêng sau |
| Q6 DPIA | Mẫu hồ sơ + endpoint trích xuất metadata; khách tự nộp |
| Q7 `MedicationHistoryEntry` tự động | **Ngoài phạm vi** (nợ cross-module cũ §7i) |

**3 phát hiện pháp lý đáng nhớ (chi tiết trong tài liệu tính năng):**
1. **Cơ sở pháp lý để lưu dữ liệu sức khỏe KH là DUY NHẤT một thứ: đồng ý** (Luật 91 Điều 26.1).
   Không tìm thấy văn bản nào *bắt buộc* nhà thuốc lưu dị ứng/bệnh nền ⇒ rút đồng ý phải thật sự
   làm được, không viện được "luật bắt tôi giữ". Khác hẳn dữ liệu bán thuốc kê đơn.
2. **Mâu thuẫn pháp lý thật giữa 2 văn bản còn hiệu lực:** quyền xóa (Luật 91 Điều 13-14) vs nghĩa
   vụ lưu ≥1 năm (GPP TT02 I-1a.II.4.d). GĐ đề nghị hỏi luật sư; **sếp chọn tự quyết** phương án khử
   nhận dạng. Hậu quả **không đảo ngược bằng `git revert`** — ghi mốc để rà lại khi có luật sư.
3. **NĐ356 Điều 41.2:** miễn DPIA cho hộ kinh doanh/DN siêu nhỏ **KHÔNG áp dụng** khi xử lý dữ liệu
   nhạy cảm ⇒ mọi tenant, kể cả nhà thuốc lẻ nhỏ nhất, đều phát sinh nghĩa vụ DPIA khi bật tính năng.

**Phạm vi 9 hạng mục / kế hoạch 4 bước stepped-commit:** xem tài liệu tính năng.

### ⏸️ ĐIỂM DỪNG (2026-07-23) — sếp cho tạm dừng để bàn UI + thương hiệu trước

> **Dừng ở ranh giới sạch:** Bước 1-3 xong, mỗi bước 1 commit 4 cổng xanh. Working tree **sạch**,
> không có việc dở dang. Cổng lúc dừng: ruff sạch · mypy strict **210 file** · import-linter **13/0**
> · pytest **560**. Resume = làm tiếp Bước 4, không cần đọc lại gì ngoài mục này.

| Bước | Commit | Trạng thái |
|------|--------|-----------|
| 1 — cổng đồng ý (domain+infra+app, migration `0015`) | `52ab50d` | ✅ (gộp so với kế hoạch, lý do ghi trong commit) |
| 2 — tách quyền đọc nhạy cảm + wiring 6 action audit | `10f2a73` | ✅ |
| 3 — xuất/khử nhận dạng + `GET /privacy/processing-record` | `96b5b9b` | ✅ |
| 4 — cập nhật role + tài liệu | `<xem commit kế tiếp>` | ✅ **XONG 2026-07-23** (phiên sau §7p) |

**Bước 4, 5 việc — cả 5 đã xong:**
1. ✅ Cấp `crm.read` + `crm.create` + `crm.consent.manage` cho role `cashier` (Q4) —
   `_CASHIER_PERMISSIONS` trong `modules/iam/domain/system_roles.py`.
2. ✅ Sửa `test_a_cashier_sees_the_person_but_not_the_diagnoses` — nay khẳng định 200 + thấy
   tên/SĐT + `allergies == []`, không còn 403. **3 test khác cùng lệch giả định** (đã sửa cùng lúc
   vì cùng nguyên nhân): `test_iam_api_e2e.py::test_admin_creates_a_cashier_...` +
   `::test_cashier_is_refused_a_pharmacist_only_endpoint` (đổi sang thử `crm.sensitive.write` qua
   endpoint allergy, vì tạo khách nay hợp lệ) + `test_iam_flow.py::test_branch_scoped_role_grants_only_that_branch`
   + `test_iam_domain.py::test_cashier_has_no_customer_data_access` (đổi tên +
   đảo assertion). Không phát hiện trong lúc sửa mục 1 — bị bắt bởi pytest full suite, đúng lý do
   kỷ luật "4 cổng xanh trước mỗi commit" tồn tại.
3. ✅ Chạy `python -m seeds.run` trên Postgres dev đang chạy (kỷ luật #7) — **xác nhận bằng SQL
   thật**: trước khi chạy, `cashier` chỉ có 6 permission cũ; sau khi chạy, có thêm
   `crm.consent.manage`+`crm.create`+`crm.read` (`system_roles_updated=1`, khớp SQL).
4. ✅ `docs/features/ho-so-suc-khoe-khach-hang/02_CHINH_SACH_LUU_TRU.md`.
5. ✅ `docs/features/ho-so-suc-khoe-khach-hang/03_MAU_DPIA_KY_THUAT.md` (phần kỹ thuật; phần pháp
   lý còn `[TENANT + LUẬT SƯ ĐIỀN]`, xem mục C §7p).

**4 cổng lúc đóng Bước 4:** ruff (scope `src tests`) sạch · mypy strict 210 file (package
`pharmacy_os`, không tính `tests/`) · import-linter 13/13 · pytest full suite exit 0 (dòng tổng số
không hiện trong output bị cắt, nhưng exit code xác nhận không có test đỏ).

⚠️ **Vẫn còn treo, không giải quyết ở đây:** role `cashier` giờ có `crm.read` nhưng
`SalesOrder.customer_id` vẫn ngoài phạm vi (Q5) — thu ngân tra được khách, vẫn **chưa gắn được**
khách vào đơn bán. Xem mục C.

**Trạng thái audit lúc dừng — 17/17 action đều phát thật, nhưng chỉ 2/9 module có audit:**

| Có audit | Không có audit (việc nhạy cảm chưa để lại dấu vết) |
|----------|----------------------------------------------------|
| `iam` (11 action) · `crm` (6 action) | `prescription` (**duyệt đơn, cấp phát thuốc kê đơn**) · `compliance` (**sổ thuốc kiểm soát, liên thông**) · `sales` · `inventory` · `procurement` · `clinical` · `catalog` |

⚠️ **GĐ ghi nhận lệch ưu tiên:** `docs/11` §6 viết "mọi POST/PUT/DELETE nhạy cảm ghi `audit_logs`" —
hiện thực chưa tới. Chỗ thiếu nặng nhất là **cấp phát thuốc kê đơn** và **sổ thuốc kiểm soát** —
thanh tra dược hỏi "ai đã bán lô thuốc hướng thần này" trước khi hỏi "ai đã xem dị ứng của khách".
Hạ tầng đã sẵn, mở rộng là việc cơ học. **GĐ khuyến nghị làm ngay sau Bước 4, trước mọi tính năng
thương mại khác** — chưa được sếp chốt.

**Cảnh báo xu hướng (chưa cần xử lý):** bộ test từ **1:27 → 4:09** trong một phiên (560 test).
Nguyên nhân chính: các suite e2e dựng app + bootstrap tenant + bcrypt hash thật cho từng test. Nếu
giữ nhịp này thêm vài tính năng, mỗi lượt cổng thành 8-10 phút và kỷ luật "4 cổng xanh trước mỗi
commit" sẽ bắt đầu bị lách. Cách rẻ nhất: hạ vòng bcrypt trong test.

✅ **Cảnh báo vận hành ở trên đã hết hạn:** Bước 4 nay đã xong (2026-07-23), role `cashier` đã đúng
thiết kế Q4. Vẫn còn giới hạn thật: `SalesOrder.customer_id` ngoài phạm vi (Q5) nên thu ngân tra
được khách nhưng chưa gắn được vào đơn bán — không phải lỗi, là phạm vi đã chốt.

---

## 7k-cũ. Thiết kế IAM thật — điểm dừng chờ phiên Opus (lưu lại làm bối cảnh)

> **Lệnh sếp:** thiết kế module `iam` thật (users/roles/JWT) thay `api/deps.py` dev-header, theo
> khung đã phác ở `docs/02_ARCHITECTURE.md`/`docs/08_MODULES.md` §2.1 (Sprint 1, mới chỉ là
> khung sơ bộ — `User`/`Role` aggregate, port `UserRepository`/`TokenService`, event
> `UserRegistered`/`RolesChanged`, endpoint `/auth/login`+`/users`+`/roles`). **Cross-module ảnh
> hưởng toàn hệ thống — CHỈ THIẾT KẾ TRƯỚC, dừng chờ sếp duyệt phạm vi 1 lần** (không tự chạy full-auto
> toàn bộ dù cơ chế full-auto đang bật, vì đây là thiết kế nền tảng mới hoàn toàn, sếp muốn xác nhận
> trước). Khi thiết kế role: **ghi nhận** 2 cấp "chuyên môn cấp chuỗi" (tenant-wide) và "chuyên môn cấp
> nhà thuốc" (branch-scoped) — phát hiện từ Luật 44/2024 (chuỗi nhà thuốc, xem `Luật-44-2024-QH15.SUMMARY.md`)
> — **chỉ đưa vào thiết kế RBAC, KHÔNG code quản lý chuỗi nhà thuốc** (ngoài phạm vi hiện tại).

**⏸️ ĐÃ DỪNG (2026-07-23) — hỏi sếp có tiếp tục ở Sonnet phiên này hay mở phiên Opus mới, sếp chọn
"mở phiên Opus mới" (đúng quy tắc chọn model của dự án cho thiết kế mới hoàn toàn ảnh hưởng toàn hệ
thống).** Chưa viết bất kỳ dòng thiết kế/code nào — chỉ mới khảo sát hạ tầng sẵn có bên dưới, để phiên
Opus kế tiếp không phải dò lại từ đầu.

**Hạ tầng đã có sẵn (Sprint 2), KHÔNG cần dựng lại — chỉ cần nối vào module `iam` mới:**
- `core/security/jwt.py` — `JwtService.issue(TokenPayload)`/`.decode(token)` đã chạy được, `TokenPayload(user_id, tenant_id, permissions: frozenset[str])`. **Thiếu:** cơ chế refresh token (docs/11 dòng 57 `/auth/refresh` đã cam kết endpoint nhưng chưa thiết kế — stateless (JWT thứ 2 TTL dài) hay revocable (bảng DB) là quyết định mở, xem bên dưới).
- `core/security/password.py` — `hash_password`/`verify_password` (bcrypt) đã có.
- `core/security/rbac.py` — `require_permission(context, permission)` đã có, dùng khắp các module hiện tại.
- `core/context.py` — `RequestContext(tenant_id, branch_id, user_id, permissions: frozenset[str])` — đã có sẵn field `branch_id` tách biệt `tenant_id`, khớp đúng nhu cầu phân biệt role cấp chuỗi/cấp nhà thuốc.
- `core/db/base.py` — `TenantScopedMixin` (tenant_id+branch_id cùng bắt buộc), `PkUuidMixin`, `TimestampMixin`, `Base` — dùng chung mọi module.
- **26 permission string đã dùng thật** trong `api/deps.py` (`_DEV_PERMISSIONS`) trải 6 module (`catalog.*`, `inventory.*`, `sales.*`, `rx.*`, `clinical.*`, `crm.*`, `procurement.*`) — đây là **danh sách permission cần model hóa thành Role thật**, không phải đoán mới.
- `docs/11_API_DESIGN.md` §3 mục `iam` — đã có khung endpoint: `POST /auth/login` (public), `POST /auth/refresh` (public), `GET/POST /users` (`iam.user.read`/`iam.user.create`), `GET/PUT /roles`, `/roles/{id}` (`iam.role.*`).

**Câu hỏi thiết kế còn mở — Opus cần quyết định/đề xuất phương án kèm rủi ro, KHÔNG tự chốt khi có
nhiều đánh đổi:**
1. **Refresh token**: stateless (JWT thứ 2, không revoke được sớm) vs bảng DB lưu refresh token (revocable, cần dọn/cleanup định kỳ).
2. **Bootstrap chicken-and-egg**: cần ít nhất 1 user admin để tạo user/role khác — seed thế nào (migration data seed cố định, hay CLI riêng, hay endpoint đặc biệt chỉ chạy lần đầu)?
3. **Có giữ dev-header fallback không** (hiện `api/deps.py` dùng cho non-prod) — bỏ hẳn ngay khi có IAM thật, hay giữ song song cho tiện dev/test cục bộ (nếu giữ, cần rào chắn rõ không lọt sang prod — hiện đã có check `settings.app.env == "prod"` chặn).
4. **Mô hình gán role 2 cấp chuỗi/nhà thuốc**: đề xuất sơ bộ (Opus xác nhận/sửa) — bảng `user_roles(user_id, tenant_id, branch_id NULLABLE, role_id)`; `branch_id IS NULL` = role áp dụng toàn chuỗi (mọi branch trong tenant), `branch_id` cụ thể = chỉ áp dụng nhà thuốc đó. Khi dựng `RequestContext` cho 1 request (biết `branch_id` cụ thể từ `X-Branch-Id`), permission set = hợp của mọi role có `branch_id IS NULL OR branch_id = branch hiện tại`.
5. **Role nào set sẵn (seed) ban đầu** — tối thiểu cần đủ để map 26 permission hiện có; có set role theo tên nghiệp vụ thật (dược sĩ/thu ngân/quản lý chuỗi) hay chỉ theo nhóm permission kỹ thuật?

> **Đầu phiên Opus kế tiếp:** `docker compose ps` + `git log --oneline -5` + `git status` xác nhận
> trạng thái thật trước khi thiết kế (đừng tin nội dung tài liệu).

---

## 7o. S4.6 — FE POS tối thiểu, 4/5 bước (2026-07-23, phiên Sonnet)

> **Trạng thái:** `frontend/` mới hoàn toàn, 4 commit (`cb3809e` CORS · `2bcea7f` scaffold ·
> `c642c34` auth · `ba547c4` POS). Không sửa module backend nào ngoài `main.py`/`config.py` cho
> CORS — sếp duyệt riêng trước khi làm. **Bước 5 (Dexie offline queue) chưa làm**, tách đợt sau
> theo đúng đề xuất đã duyệt.

**Đã chạy được:** đăng nhập JWT thật (không dev-header) → chọn chi nhánh nếu nhiều → tra thuốc →
giỏ hàng → `POST /sales` thanh toán. Theme Eco-Tech (mã hex tạm), mascot placeholder (emoji, có ghi
chú rõ chưa phải art thật).

**3 phát hiện lệch tài liệu-thực tế khi build (không tự sửa docs, chỉ ghi vào code + báo cáo):**
1. `docs/11_API_DESIGN.md` mô tả `POST /sales-orders` + `Idempotency-Key` header + endpoint
   `/payments`/`/complete` riêng — **API thật** là `POST /sales` (1 lệnh gộp), idempotent qua
   `client_uuid` trong body, không có endpoint tách. FE viết theo code thật.
2. `docs/11` ghi `GET /drugs?query=&cursor=` — **API thật không có tham số tìm kiếm nào**, chỉ
   `limit`/`offset`. FE lấy 1 trang rồi lọc phía client.
3. **Không có nguồn giá bán ở đâu trong backend** — `catalog` không có trường giá, `inventory` chỉ
   có `cost_price` (giá vốn). Thu ngân phải nhập tay đơn giá từng dòng. Đây là khoảng trống sản
   phẩm thật, không phải chỗ FE thiếu code — cần quyết định có xây `pricing` hay không.

**Kiểm chứng đã làm (không chỉ build sạch):** `tsc`/`eslint`/`next build` sạch; bootstrap tenant
thật + tạo thuốc qua CLI; curl mô phỏng đúng request FE gửi (login, CORS preflight, `GET /drugs`,
`POST /drugs`, `POST /sales`) trên backend live — khớp 100% với type TypeScript đã viết; `next dev`
thật chạy, 2 route trả 200, không lỗi runtime trong log server.

**⚠️ Giới hạn kiểm chứng — không overclaim:** môi trường không có trình duyệt/công cụ browser. Đã
xác nhận hợp đồng API đúng và server không crash, **chưa từng click-through UI thật** (focus, resize,
lỗi hydration chỉ lộ khi chạy JS thật, trải nghiệm nhập liệu...). Sếp cần tự mở `http://localhost:3000`
kiểm tra trước khi coi tính năng là dùng được.

**Tài khoản demo còn để lại trên Postgres (cố ý không dọn, để sếp login thử ngay):**
`fe-demo@beral.vn` / `MatKhauFeDemo2026` — tenant "Nhà thuốc FE Demo", 1 thuốc OTC mẫu
("Paracetamol 500mg"), 1 đơn bán mẫu đã tạo lúc kiểm chứng. Dọn sau khi sếp xem xong.

**Nợ ghi rõ:**
1. Dexie offline queue (Bước 5) — S4.6 vẫn **chưa thật sự offline-first**.
2. Chưa có bộ test tự động phía FE (vitest/playwright) — ghi trong `frontend/README.md`.
3. Mã hex Eco-Tech là tạm, chờ thiết kế chính thức (docs/16 §6).
4. Luồng đơn thuốc (ETC) chưa xây — bán ETC không kèm `prescription_ref` bị 422, FE chỉ hiện lỗi
   server trả về, không tự chặn phía client.
5. `localStorage` cho token (chốt của sếp, đánh đổi XSS đã ghi nhận trong code).

---

## 7p. ⏸️ ĐIỂM DỪNG TOÀN PHIÊN (2026-07-23) — chờ sếp + GĐ sắp xếp lại ưu tiên

> Sếp yêu cầu dừng để phiên sau bàn thứ tự làm việc với GĐ. Mục này liệt kê **trung lập, không xếp
> hạng ưu tiên** — mọi quyết định "làm gì trước" để dành cho buổi bàn đó, không phải Claude tự chọn.
> Đọc cùng §7n (chốt phiên Opus trước) và §7o (S4.6) — mục này chỉ gom lại thành 1 chỗ tra, không
> lặp lại chi tiết đã có.

### A. Trạng thái kỹ thuật lúc dừng (xác nhận bằng lệnh)

| Hạng mục | Trạng thái |
|----------|-----------|
| Git | Sạch, HEAD = `a11ac5a` |
| Backend 4 cổng | ruff sạch · mypy strict 210 file · import-linter 13/0 · pytest 560 (chưa chạy lại full sau `a11ac5a` vì chỉ sửa `.md`, không sửa code) |
| Frontend | `tsc`/`eslint`/`next build` sạch lúc commit `ba547c4`; chưa test bằng trình duyệt thật |
| **Tiến trình nền còn chạy** | `uvicorn` cổng 8000 (PID 236376) · `next dev` cổng 3000 (PID 237023/237036) — do Claude khởi động để kiểm chứng S4.6, **chưa dừng**, sếp tự quyết dừng hay giữ để bấm thử trình duyệt |
| Dữ liệu demo còn trên Postgres | Tenant "Nhà thuốc FE Demo" (`fe-demo@beral.vn` / `MatKhauFeDemo2026`) + 1 thuốc + 1 đơn bán mẫu — cố ý chưa dọn |

### B. Việc đang dở dang theo tính năng (mở trong phiên này hoặc phiên trước, chưa đóng)

| Tính năng | Bước đã xong | Còn lại | Chi tiết ở |
|-----------|--------------|---------|-----------|
| S4.6 FE POS | ✅ **5/5 XONG** (CORS, scaffold, auth, tra thuốc+giỏ+thanh toán, hàng đợi offline Dexie) | Chưa click-through trình duyệt thật (môi trường không có browser tool) — sếp tự kiểm trước khi coi "offline-first" là dùng được thật | §7s |
| Hồ sơ sức khỏe KH | ✅ **4/4 XONG** (cổng đồng ý, tách quyền+audit, quyền chủ thể dữ liệu+DPIA, cập nhật role+tài liệu) | Không còn — vẫn treo `SalesOrder.customer_id` (Q5, cross-module riêng, không phải nợ Bước 4) | §7m |
| Module `compliance` | ✅ **Router đã mount 2026-07-23** — 6 endpoint (`controlled-ledger` POST/GET, `tenant-config` PUT/GET, `sync-logs` POST/GET), 5 test e2e mới | Không còn — trụ cột 2 thương hiệu đã có API để UI gọi | §7q |
| Audit coverage | ✅ `iam` (11) + `crm` (6) + `prescription` (4, mới) + `compliance` (2, mới) = **23 action, 4/9 module** | Còn 5/9 module chưa ghi audit: `sales`, `inventory`, `procurement`, `clinical`, `catalog` — không thuộc nhóm ưu tiên đã duyệt phiên này | §7r |
| Nguồn giá bán (pricing) | ✅ **CHỐT 2026-07-23: KHÔNG xây module `pricing`.** Giữ nguyên: thu ngân nhập tay đơn giá từng dòng bán, như FE S4.6 đang làm | Quyết định sếp — không phải nợ, là phạm vi đã chọn. Xem lại nếu sau này có yêu cầu bán buôn/giá theo hợp đồng | §7o |
| Test tự động phía FE | — | Chưa có vitest/playwright nào | `frontend/README.md` |

### C. Việc treo ngoài phạm vi code — cần sếp / GĐ / luật sư, không phải Claude tự quyết

| # | Việc | Trạng thái |
|---|------|-----------|
| 1 | Ghi quyết định thương hiệu BERAS vào `01-WikiHub/BeraLLC/ChienLuoc/` theo mẫu T-QuyetDinh | ✅ **XONG 2026-07-23**: `BeraLLC/ChienLuoc/2026-07-23-thuong-hieu-BERAS.md` |
| 2 | Bán cho nhà thuốc lẻ hay chuỗi trước | ✅ **CHỐT 2026-07-23: nhà thuốc lẻ trước.** Ghi tại `BeraLLC/ChienLuoc/2026-07-23-phan-khuc-khach-hang-le-truoc.md`. Hệ quả: FE Bước 5 Dexie offline queue (A4) ưu tiên cao hơn (mạng yếu ở nhà thuốc lẻ), UI đầu tiên theo luồng 1 điểm bán |
| 3 | Tagline `README.md` (dòng đầu) ≠ tagline chính thức trong `docs/16_BRAND_UI_GUIDE.md` | ✅ **CHỐT 2026-07-23**: dùng câu định vị dài docs/16 ("BERAS là sổ điện tử quản lý nhà thuốc chuẩn Cloud/SaaS thế hệ mới, tích hợp AI...") cho cả 2 nơi |
| 4 | Gộp 1 lần hỏi luật sư: (a) rà lại quyết định Q2 khử nhận dạng (mâu thuẫn Luật 91 Điều 13-14 vs GPP II.4.d), (b) soạn văn bản điều khoản thật cho `terms_version` (hiện chỉ có chuỗi `"v1"`, không có nội dung), (c) hoàn thiện phần pháp lý của mẫu DPIA (Claude chỉ soạn được phần kỹ thuật) | Chưa đặt lịch |
| 5 | Câu hỏi pháp lý cũ hơn, vẫn treo: BeraLLC có cần Giấy chứng nhận kinh doanh dịch vụ xử lý DLCN không (NĐ356 Điều 21-27)? | Ghi từ phiên trước §7j, chưa có kết luận — cần luật sư, không tự suy diễn |
| 6 | Badge `domain coverage 97%` trong README | ✅ **ĐO LẠI 2026-07-23: 99%** (`coverage report --include="*/domain/*"`, 1393 statement, 6 miss — 9 module domain, không tính `infra`/`interface`). Badge cũ thấp hơn thực tế, không phải cao hơn. Cập nhật badge README |
| 7 | Bộ test backend chậm dần trong phiên (1:27 → 4:09) | Chưa cần xử lý ngay; cách rẻ nhất đã biết là hạ vòng bcrypt trong test |

### D. `TODO.md` — ✅ ĐÃ RÀ LẠI (2026-07-23, mục A6 danh sách ưu tiên đã duyệt)

8 mục lệch đã sửa (xem commit `3d7a9be`): dev-header/IAM, S4.6 FE 5/5, Compliance C.5+router+audit,
Sprint 6 backend đóng, audit `prescription`, TT11/2025 đã có trong `docs/legal`. **Không rà toàn
bộ file** — chỉ sửa dòng xác nhận được bằng lệnh thật hoặc đối chiếu PROJECT_STATE, đúng cảnh báo
thận trọng đã ghi khi mở mục này. Nợ sau **vẫn còn, đã xác nhận lại còn đúng** (không phải bỏ sót):
FK `drugs.atc_code → atc_codes` chưa bật · persist trả hàng (`register_return`) chưa nối tồn ·
HTTP endpoint tạo/liệt kê `active_ingredients` · nối `LLMProvider` → Claude thật (`AnthropicProvider`,
vẫn `# BLOCKER: AI__API_KEY thật`).

---

## 7q. Mount router `compliance` — XONG (2026-07-23, phiên bàn ưu tiên GĐ+Code)

> Việc mục #3 trong danh sách ưu tiên §7p đã duyệt. Module `compliance` đã có domain+app+infra
> đầy đủ từ trước (§3f) nhưng chưa có mặt HTTP nào — phiên này chỉ mount, **không đổi logic
> nghiệp vụ nào**.

**6 endpoint mới**, `backend/src/pharmacy_os/modules/compliance/interface/{router,register}.py`:

| Endpoint | Quyền | Use-case đã có sẵn |
|---|---|---|
| `POST /compliance/controlled-ledger` | `compliance.ledger.write` | `ComplianceService.record_controlled_entry` |
| `GET /compliance/controlled-ledger/{id}` | `compliance.ledger.read` | `ComplianceService.get_ledger_entry` |
| `PUT /compliance/tenant-config` | `compliance.config.write` | `ComplianceService.set_tenant_config` |
| `GET /compliance/tenant-config` | `compliance.config.read` | `ComplianceService.get_tenant_config` |
| `POST /compliance/sync-logs` | `compliance.sync.push` | `NationalSyncService.push_payload` (đẩy thủ công; luồng chính vẫn tự động qua `SaleCompleted`) |
| `GET /compliance/sync-logs/{id}` | `compliance.sync.read` | `NationalSyncService.get_sync_log` |

**Quyết định tự chọn khi mount (cơ học, không phải thiết kế mới):** `NationalSyncService` đã được
`wire_national_sync` đăng ký sẵn trong container cho C.5 (cross-module reaction) — di chuyển lời
gọi `wire_national_sync(container)` lên trước khi mount router `compliance` trong
`api/v1/__init__.py`, để router resolve đúng **cùng một instance**, không tạo instance thứ hai.

**Kiểm chứng:** 5 test e2e mới `test_compliance_api_e2e.py` (real token, real DI, cả đường
allow lẫn deny — thu ngân bị 403 khi ghi sổ). 4 cổng xanh: ruff · mypy strict 212 file ·
import-linter 13/13 · pytest full suite exit 0.

⚠️ **Lệch tài liệu phát hiện, không tự sửa:** `docs/11_API_DESIGN.md` §compliance ghi permission
`compliance.read`/`compliance.submit` và endpoint `GET /compliance/controlled-ledger` (không có
`/{id}`) + `POST /compliance/submissions/retry` — khác tên thật đang chạy
(`compliance.ledger.*`/`compliance.config.*`/`compliance.sync.*`, path `/sync-logs`). Router mount
theo đúng permission **thật** đã seed trong `system_roles.py`, không theo docs/11 đã lỗi thời. Cần
rà `docs/11` một lượt riêng (cùng đợt với nợ `TODO.md` ở mục D phía trên).

⚠️ **Chưa có audit cho module này** — đúng như đã ghi ở §7n: `compliance` vẫn thuộc nhóm 7/9 module
chưa ghi `audit_logs`. Việc mục #4 (audit cho `prescription`+`compliance`) trong danh sách ưu tiên
đã duyệt vẫn còn nguyên, mount router không tự động thêm audit.

---

## 7r. Audit cho `prescription` + `compliance` — XONG (2026-07-23, mục #4 danh sách ưu tiên đã duyệt)

> GĐ đã đề xuất việc này trước đó (§7n): 2 module chưa có audit lại đúng 2 thứ thanh tra dược hỏi
> đầu tiên — cấp phát thuốc kê đơn và sổ thuốc kiểm soát. Hạ tầng `AuditLogger`/`AuditEntry` đã có
> sẵn (§7l), phiên này chỉ mở rộng — không dựng lại, không cross-module (audit gọi `core`, chiều
> hợp lệ đã xác nhận từ trước ở `01_DECISIONS.md`).

**6 action mới trong `core/audit/entry.py::AuditAction`:**

| Module | Action | Phát khi nào |
|---|---|---|
| `prescription` | `PRESCRIPTION_CREATED` | Tiếp nhận đơn (DRAFT) |
| `prescription` | `PRESCRIPTION_APPROVED` | Dược sĩ duyệt đơn |
| `prescription` | `PRESCRIPTION_REJECTED` | Dược sĩ từ chối đơn |
| `prescription` | `PRESCRIPTION_DISPENSED` | Cấp phát thuốc kê đơn — đúng câu hỏi thanh tra hay hỏi nhất |
| `compliance` | `CONTROLLED_LEDGER_ENTRY_RECORDED` | Ghi 1 dòng sổ thuốc kiểm soát đặc biệt |
| `compliance` | `TENANT_COMPLIANCE_CONFIG_SET` | Đổi mã cơ sở Cục QLD cấp |

**Không audit đọc (`get_prescription`/`get_ledger_entry`/`get_tenant_config`):** cùng nguyên tắc đã
áp dụng cho `crm.list_customers` — đọc đơn lẻ theo id không phải tra cứu hàng loạt nhạy cảm ở mức
cần audit riêng; nếu sau này cần, mở rộng thêm không phải thiết kế lại.

**Nội dung `context` — chỉ metadata, không chép dữ liệu:** đã tự kiểm bằng test riêng — lý do từ
chối `reject_prescription` và tên/địa chỉ bệnh nhân trong `record_controlled_entry` **không** xuất
hiện trong `context` (cùng nguyên tắc đã khóa ở §7m cho `crm`).

**Kiểm chứng bằng lệnh thật, không tin việc gọi hàm suông:** thêm test đọc ngược `audit_logs` sau
khi gọi use-case thật (`test_prescription_flow.py`, `test_compliance_flow.py`) — đúng dạng bài học
từ §7l: chỉ audit_logs sạch trên giấy không có nghĩa call site thật sự chạy tới. Cập nhật
`_COVERED_ELSEWHERE`/`expected` trong 2 bộ test đóng ("mọi action đều có test") để bộ test không
lặng lẽ hết còn đúng nữa.

**4 cổng:** ruff sạch · mypy strict 212 file · import-linter 13/13 · pytest full suite exit 0.

⚠️ **Còn treo, ghi rõ không giấu:** `sales`/`inventory`/`procurement`/`clinical`/`catalog` (5/9
module) vẫn chưa có audit — không thuộc phạm vi đã duyệt phiên này, để riêng cho lần rà tiếp theo
nếu sếp/GĐ quyết định mở rộng thêm.

---

## 7s. S4.6 Bước 5 — Dexie offline queue: XONG (2026-07-23, mục #7 danh sách ưu tiên đã duyệt)

> Backend `/sync/sales` đã có sẵn từ Sprint 4 (idempotent theo `client_uuid`) — phiên này chỉ xây
> phần FE dùng nó. Không sửa module backend nào.

**3 file mới** trong `frontend/src/shared/offline/`:

| File | Vai trò |
|---|---|
| `db.ts` | Bảng Dexie `pendingSales`, khóa = chính `client_uuid` của đơn (không thể lưu trùng) |
| `sync-queue.ts` | `enqueueSale` (lưu khi mất mạng) · `flushQueue` (phát lại qua `POST /sync/sales` theo đúng thứ tự đã lưu) |
| `use-offline-sync.ts` | Hook tự flush khi mount + khi có sự kiện `online`, gắn ở `(pos)/layout.tsx` nên chạy trên mọi màn POS |

**`useCheckout` sửa để phân 2 loại lỗi:** `ApiError` (server đã trả lời — từ chối thật, VD thiếu
tồn) → ném lại, hiện lỗi cho thu ngân, **không** lưu vào hàng đợi. Lỗi khác (bản thân `fetch` không
kết nối được) → lưu vào hàng đợi, trả về "đã lưu tạm, chưa mất". Đơn bị server từ chối trong lúc
`flushQueue` phát lại thì bị bỏ khỏi hàng đợi ngay — không giữ lại retry vô hạn (sẽ chặn mọi đơn
xếp sau nó trong cùng hàng đợi).

**UI:** header POS hiện huy hiệu "N đơn chờ đồng bộ" khi hàng đợi không rỗng; thông báo sau thanh
toán phân biệt rõ "đã bán thành công" (server xác nhận) vs "không có mạng — đã lưu tạm" (đang chờ
đồng bộ) — không đánh đồng 2 trạng thái để thu ngân khỏi tưởng nhầm.

**Kiểm chứng đã làm:** `tsc`/`eslint`/`next build` sạch; `next dev` thật chạy, `/login` và `/` trả
200, không lỗi runtime trong log server.

⚠️ **Giới hạn kiểm chứng, không overclaim:** môi trường không có trình duyệt/công cụ browser —
**chưa từng** tự tay ngắt mạng (DevTools Offline hoặc tắt Wi-Fi thật), gõ đơn, bật mạng lại xem đơn
có tự đồng bộ đúng không. Logic đã review kỹ (phân biệt `ApiError` vs lỗi mạng, thứ tự phát lại,
dequeue khi bị từ chối thật) nhưng **hành vi IndexedDB + sự kiện `online` thật trong trình duyệt
chưa được diễn tập**. Sếp cần tự mở `http://localhost:3000`, tắt mạng thử thanh toán, bật lại mạng
xem huy hiệu "chờ đồng bộ" có tự về 0 không, trước khi coi Bước 5 là dùng được thật.

**Giới hạn thiết kế đã biết (ghi trong code + README):** phân biệt "mất mạng" vs "lỗi JS khác" chỉ
dựa vào việc lỗi có phải `ApiError` hay không — đơn giản, đủ cho MVP, nhưng không phân biệt được
mất mạng thật với các lỗi runtime hiếm khác không phải bị server từ chối.

**Chưa có bộ test tự động (vitest/playwright)** cho luồng offline — cùng nợ đã ghi ở §7o cho toàn
bộ `frontend/`, không phải nợ riêng của Bước 5.

---

## 7t. ✅ CHỐT PHIÊN 2026-07-23 (buổi bàn ưu tiên GĐ+Code, 11/11 mục đã duyệt XONG)

> Đóng phiên toàn bộ theo lệnh sếp. Đọc mục này trước khi làm gì ở phiên sau — không cần đọc lại
> §7n–§7s chi tiết trừ khi cần tra cứu sâu hơn.

**Trạng thái khi đóng phiên (xác nhận bằng lệnh, không tin tài liệu):** `docker compose stop` đã
chạy — postgres+redis **đã dừng**, không còn tiến trình nền nào chạy (không có `uvicorn`/`next dev`
sót lại). `git status` sạch ở cả 2 repo (root vault + `AI_Pharmacy_OS`). 13 commit trong phiên.

### 11/11 mục đã duyệt — tất cả XONG

| # | Mục | Commit |
|---|---|---|
| C1 | Phân khúc KH: nhà thuốc lẻ trước | `5ae5c83` (root) |
| A1 | Hồ sơ sức khỏe KH Bước 4/4 | `38b1ec6` |
| A2 | Mount router `compliance` (6 endpoint) | `92baa56` |
| A3 | Audit `prescription`+`compliance` (6 action) | `643de5a` |
| C4 | Bản gộp câu hỏi luật sư | `3eddb19` (root) |
| A5 | Không xây module `pricing` | `f0fe490` |
| A4 | FE Dexie offline queue (S4.6 5/5) | `571e578` |
| A6 | Rà lại `TODO.md` (8 mục lệch) | `3d7a9be`, `372b44f` |
| C2 | Ghi quyết định BERAS vào `ChienLuoc/` | `0b8c38e` (root) |
| C3 | Thống nhất tagline README↔docs/16 | `f1f537a` |
| C5 | Đo lại badge domain coverage: 97%→99% | `d520d61` |

### 🔜 Phiên sau bắt đầu từ đâu

Không còn việc kỹ thuật nào đang dở dang từ danh sách ưu tiên đã duyệt. Việc treo thật sự, không
phải bỏ sót:
1. **Chờ sếp gửi bản câu hỏi luật sư** (`BeraLLC/PhapLy/2026-07-23-cau-hoi-luat-su-AI-Pharmacy-OS.md`)
   và chờ trả lời — đặc biệt Q2 (khử nhận dạng) có thể cần sửa code nếu luật sư kết luận khác hướng
   đã chọn.
2. **Sếp tự click-through FE trên trình duyệt thật** — cả S4.6 (POS) lẫn Bước 5 (Dexie offline) mới
   chỉ kiểm chứng qua code review + curl/`next dev`, chưa có browser tool trong môi trường này.
3. Nợ kỹ thuật cũ còn nguyên, không đổi: FK `atc_code`, persist trả hàng (`register_return`),
   endpoint `active_ingredients`, `AnthropicProvider` thật, audit cho 5/9 module còn lại
   (`sales`/`inventory`/`procurement`/`clinical`/`catalog`).
4. Đầu phiên sau: `docker compose up -d` (đã dừng khi đóng phiên này) trước khi thử API/FE.

### Quyết định Claude tự chốt trong phiên (kỷ luật full-auto #3)

| # | Tự quyết | Lý do |
|---|----------|-------|
| 1 | Sửa thêm 3 test integration (ngoài 1 test đã biết trước) khi cấp quyền `crm.*` cho `cashier` | Bắt bởi pytest full suite, không phải chỉ file định sửa — cùng giả định cũ bị đảo bởi Q4 |
| 2 | Thiết kế 6 action audit mới (4 prescription + 2 compliance) — tên, target_type, nội dung context | GĐ chỉ đề xuất "cần audit", không nêu action cụ thể; theo đúng khuôn `crm`/`iam` đã có (metadata only, không chép nội dung nhạy cảm) |
| 3 | Không audit các use-case đọc đơn lẻ (`get_prescription`/`get_ledger_entry`/`get_tenant_config`) | Cùng nguyên tắc đã áp dụng cho `crm.list_customers` — đọc đơn lẻ theo id không phải tra cứu hàng loạt |
| 4 | Dời `wire_national_sync` lên trước khi mount router `compliance` trong `api/v1/__init__.py` | Để router và cross-module C.5 dùng chung 1 instance `NationalSyncService`, không tạo instance thứ 2 |
| 5 | Phân biệt lỗi mạng vs lỗi server thật trong `useCheckout` bằng `instanceof ApiError` | Đơn giản, đủ cho MVP; giới hạn đã ghi rõ trong code+README, không giấu |
| 6 | Đơn bị server từ chối thật trong `flushQueue` thì dequeue ngay, không giữ lại retry vô hạn | Retry vô hạn sẽ chặn mọi đơn xếp sau nó trong cùng hàng đợi |

---

## 7u. Endpoint HTTP `active_ingredients` — XONG (2026-07-23, nợ kỹ thuật đơn module, tiếp phiên sau §7t)

> Phiên trước (§7t) đóng toàn bộ danh sách ưu tiên đã duyệt, không còn việc dở dang — chỉ còn nợ kỹ
> thuật chưa ai chọn ưu tiên (TODO.md). Phiên này (full-auto, sếp bận HoSoCongTrinh) tự chọn việc rủi
> ro thấp nhất trong danh sách đó: `catalog` đã có domain+infra cho `ActiveIngredient` từ Sprint 6
> Bước 1 nhưng chưa có endpoint HTTP tạo/liệt kê — TODO.md từng ghi "quyết định khi có nhu cầu FE
> thật"; nay làm vì không cross-module, không migration, đúng khuôn Sonnet.

**Đã làm:** `POST /api/v1/active-ingredients` (201, chặn trùng `name` → 409) + `GET
/api/v1/active-ingredients` (danh sách, không cross-module, không migration — bảng `active_ingredients`
đã có từ migration `0008`). Tái dùng đúng 2 quyền có sẵn `catalog.create`/`catalog.read` (giống cách
`get_drug_ingredients` đã dùng `catalog.read`) — không cần đổi role/permission trong `iam`.

- `application/dto.py`: `CreateIngredientInput`, `ActiveIngredientOutput`.
- `application/service.py`: `CatalogService.create_ingredient`/`list_ingredients` (dùng
  `ActiveIngredientRepository` đã có sẵn từ Sprint 6 Bước 1, không đổi port).
- `interface/schemas.py`: `CreateIngredientRequest`/`ActiveIngredientResponse`.
- `interface/router.py`: tách `_build_drugs_router`/`_build_ingredients_router`, `build_router` gộp
  cả 2 qua `include_router` — `register.py`/`api/v1/__init__.py` không đổi (vẫn gọi `build_router`
  như cũ, ghép router lồng nhau minh bạch với FastAPI).
- Test mới `test_active_ingredients_crud` (`tests/integration/test_api_e2e.py`): tạo hoạt chất → trùng
  tên → 409 → liệt kê → tạo thuốc tham chiếu `ingredient_id` vừa tạo → 201.

**Bằng chứng:** `ruff` sạch (check+format) · `mypy --strict` **212 file, không lỗi** · `import-linter`
**13 kept/0 broken** (không đổi contract nào — thuần interface layer 1 module) · `pytest` **570 test
collected, exit code 0 (toàn bộ xanh)** — chạy 2 lần độc lập để xác nhận, không chỉ tin 1 lần chạy.
Không có migration mới (bảng đã tồn tại từ `0008`).

**Quyết định tự chọn trong phiên (full-auto #3):** không thêm audit action cho việc tạo hoạt chất —
đây là dữ liệu tham chiếu toàn cục (không tenant-scope, giống `atc_codes`), không phải hành vi nghiệp
vụ của một tenant cụ thể; khớp nguyên tắc audit hiện có (chỉ ghi hành vi tenant-scoped). Nếu sếp muốn
audit cả thay đổi dữ liệu tham chiếu toàn cục, cần bàn riêng — chưa tự quyết thêm.

**Nợ không đổi:** vẫn còn 5/9 module chưa có audit (`sales`/`inventory`/`procurement`/`clinical`/
`catalog`), FK `atc_code`, persist trả hàng, `AnthropicProvider` thật — xem §7t mục 3, TODO.md.

---

## 7v. Audit cho `sales` — XONG (2026-07-23, GĐ chọn ưu tiên: audit 5 module còn lại, bắt đầu từ sales)

> GĐ chọn thứ tự **sales → inventory → procurement → clinical → catalog** (giảm dần theo mức nhạy
> cảm pháp lý — sales là nơi bán thuốc kiểm soát/kê đơn ra cửa hàng, thanh tra hay hỏi đầu tiên "ai
> bán, lúc nào"), theo đúng khuôn đã dùng cho `prescription`/`compliance`/`crm` (§7r).

**Đã làm:** `AuditAction.SALE_COMPLETED` mới (`core/audit/entry.py`). `SalesService` nhận thêm
`audit: AuditLogger | None = None` (optional — giữ nguyên chữ ký cũ cho 3 file test dựng
`SalesService` trực tiếp không cần sửa, giống cách `drug_info`/`prescription_info` đã optional).
`complete_sale` ghi 1 dòng audit **sau khi hoàn tất thật** — **không** ghi khi trả lại kết quả replay
idempotent (cùng `client_uuid` sync lại) để không nhân đôi vết. `interface/register.py` resolve
`AuditLogger` từ container (giống `prescription/interface/register.py`). Cập nhật fixture
`sales_service` trong `tests/integration/conftest.py` để có audit thật trong test.

**Va chạm phát hiện khi chạy pytest (không phải lỗi code sales):** 2 test "exhaustiveness" có sẵn
(`test_audit_entry.py::test_every_action_the_codebase_emits_has_a_member`,
`test_audit_persistence.py::test_every_action_emitted_by_iam_reaches_the_table`) hard-code danh sách
`AuditAction` — thêm member mới làm cả 2 đỏ ngay, đúng như docstring của chúng mô tả ("guards against
drift"). Đã cập nhật cả 2 danh sách (`expected` set + `_COVERED_ELSEWHERE`) thêm `SALE_COMPLETED`,
trỏ về `test_sales_flow.py` là nơi test thật. Không tự ý nới lỏng hay xoá 2 test này.

**Test mới** (`tests/integration/test_sales_flow.py`): `test_complete_sale_leaves_an_audit_row` (đọc
lại bảng `audit_logs`, không tin call site) + `test_idempotent_resync_leaves_a_single_audit_row` (sync
lại cùng `client_uuid` → vẫn đúng 1 dòng, không nhân đôi).

**Bằng chứng:** `ruff` sạch · `mypy --strict` **212 file** · `import-linter` **13/0** (không đổi
contract) · `pytest` **exit code 0** (chạy 2 lần: lần 1 lộ 2 test exhaustiveness đỏ như trên, lần 2
sau khi sửa — xanh toàn bộ). Không có migration mới (bảng `audit_logs` đã có từ §7l).

**Nợ còn lại:** audit cho `inventory`/`procurement`/`clinical`/`catalog` (4/9 module) — tiếp theo
theo đúng thứ tự GĐ đã chọn.

---

## 7w. Audit cho `inventory` — XONG (2026-07-23, tiếp thứ tự GĐ đã chọn sau §7v)

**Đã làm:** 2 action mới `INVENTORY_STOCK_RECEIVED`/`INVENTORY_STOCK_DISPENSED` (`core/audit/entry.py`).
`InventoryService` nhận `audit: AuditLogger` — **bắt buộc** (không optional như `sales`), vì chỉ 1 nơi
dựng service trực tiếp ngoài `register.py` (fixture test) nên không có rủi ro phải sửa nhiều call site,
giống khuôn `prescription`. `receive_stock` ghi `INVENTORY_STOCK_RECEIVED` (target = `batch_id`);
`dispense_stock` ghi `INVENTORY_STOCK_DISPENSED` (target = `drug_id`, vì thao tác này không có 1 entity
id duy nhất — có thể phân bổ nhiều lô).

**Quyết định phạm vi (tự chọn, full-auto #3):** **KHÔNG** audit 2 use-case cross-module
`dispense_for_sale`/`receive_from_goods_receipt` — đây là phản ứng tự động theo `SaleCompleted`/GRN
xác nhận, đã có vết riêng ở nơi phát sinh thật (`SALE_COMPLETED` bên `sales`; `procurement` sẽ có vết
riêng khi tới lượt). Ghi audit ở cả 2 đầu cho cùng 1 sự kiện thật sẽ nhân đôi số dòng mà không thêm
thông tin — cùng logic đã dùng khi quyết định C.5 không tự ghi `ControlledLedgerEntry` từ `SaleCompleted`
(§7b). Chỉ audit 2 endpoint HTTP **con người gõ tay trực tiếp** (`/inventory/receive`, `/inventory/dispense`).

**Test mới** (`tests/integration/test_inventory_flow.py`):
`test_receive_and_dispense_each_leave_an_audit_row` (đọc lại bảng `audit_logs`, không tin call site,
xác nhận đúng target_id cho cả 2 action).

**Bằng chứng:** `ruff` sạch · `mypy --strict` **212 file** · `import-linter` **13/0** (không đổi
contract) · `pytest` **exit code 0** (2 test exhaustiveness cập nhật thêm ngay từ đầu, không phải sửa
lại lần 2 như sales — rút kinh nghiệm). Không có migration mới.

**Nợ còn lại:** audit cho `procurement`/`clinical`/`catalog` (3/9 module).

---

## 7x. Audit cho `procurement` — XONG (2026-07-23, tiếp thứ tự GĐ đã chọn sau §7w)

**Đã làm:** 2 action mới `PROCUREMENT_PO_ORDERED`/`PROCUREMENT_GRN_CONFIRMED` (`core/audit/entry.py`).
`ProcurementService` nhận `audit: AuditLogger` bắt buộc (chỉ 1 call site ngoài `register.py`, giống
`prescription`/`inventory`). `mark_ordered` (DRAFT→ORDERED, cam kết tài chính thật với NCC) ghi
`PROCUREMENT_PO_ORDERED` (target = `po.id`); `confirm_goods_receipt` (xác nhận nhận hàng, kích hoạt
nhập kho thật) ghi `PROCUREMENT_GRN_CONFIRMED` (target = `grn.id`).

**Phạm vi đã chọn (tự quyết, full-auto #3):** chỉ 2/7 use-case của module — bỏ qua CRUD hành chính
(`create_supplier`/`create_purchase_order` DRAFT/`add_po_item`/`cancel_purchase_order`/
`close_purchase_order`) vì đây không phải "sự kiện thật không thể đảo ngược" mà thanh tra/kiểm toán
cần truy vết — cùng logic độ nhạy cảm đã áp dụng cho `inventory` (§7w: chỉ audit hành vi tạo/xác nhận
sự kiện thật, không audit mọi CRUD). Không audit lại bước cross-module tạo lô tồn kho từ GRN (đã có ở
phía `inventory` khi làm module đó, tránh nhân đôi — xem §7w).

**Test mới** (`tests/integration/test_procurement_flow.py`):
`test_mark_ordered_and_confirm_receipt_each_leave_an_audit_row` (đọc lại bảng `audit_logs`, không tin
call site, xác nhận đúng target_id cho cả 2 action, luồng đầy đủ supplier→PO→ordered→GRN→confirm).

**Bằng chứng:** `ruff` sạch · `mypy --strict` **212 file** · `import-linter` **13/0** (không đổi
contract) · `pytest` **exit code 0** (2 test exhaustiveness cập nhật ngay từ đầu, xanh ngay lần chạy
đầu). Không có migration mới.

**Nợ còn lại:** audit cho `clinical`/`catalog` (2/9 module).

---

## 7y. Audit cho `clinical` — XONG (2026-07-23, tiếp thứ tự GĐ đã chọn sau §7x)

**Đã làm:** 2 action mới `CLINICAL_INTERACTION_CHECKED`/`CLINICAL_RECOMMENDATION_ACCEPTED`
(`core/audit/entry.py`). `ClinicalService` nhận `audit: AuditLogger | None = None` — **optional**
(khác `inventory`/`procurement` bắt buộc) vì có 2 nơi dựng service trực tiếp ngoài `register.py`
(`conftest.py` + `test_clinical_flow.py` tự dựng riêng để test guardrail confidence) — giữ optional
để không phải sửa test không liên quan đến audit, giống lý do đã chọn cho `sales`.

`check_interactions` ghi `CLINICAL_INTERACTION_CHECKED` sau khi persist `AiRecommendation` — bù đắp
1 khoảng trống thật: bản thân `AiRecommendation` là "audit bất biến" theo thiết kế (model/confidence/
output) nhưng **không** lưu ai đã yêu cầu kiểm tra (chỉ `accepted_by` cho bước duyệt sau), nên audit_logs
là nơi duy nhất trả lời được "ai yêu cầu kiểm tra này". `accept_recommendation` ghi
`CLINICAL_RECOMMENDATION_ACCEPTED` — đúng hành vi human-in-the-loop docs/12 mục 6 yêu cầu.

**Quyết định phạm vi (tự chọn, full-auto #3):** không audit `check_allergies` — domain thuần, không
gọi AI, không persist gì (theo đúng docstring có sẵn của use-case này), nên không có gì để ghi vết;
không audit `get_tenant_ai_settings`/`set_tenant_ai_settings` — cấu hình tenant tần suất thấp, không
phải sự kiện lâm sàng, tương tự đã bỏ qua CRUD hành chính ở `procurement`.

**Test mới** (`tests/integration/test_clinical_flow.py`):
`test_check_and_accept_each_leave_an_audit_row` (đọc lại bảng `audit_logs`, không tin call site, xác
nhận đúng target_id cho cả 2 action trên cùng 1 `AiRecommendation`).

**Bằng chứng:** `ruff` sạch · `mypy --strict` **212 file** · `import-linter` **13/0** (không đổi
contract) · `pytest` **exit code 0** (2 test exhaustiveness cập nhật ngay từ đầu). Không có migration
mới.

**Nợ còn lại:** audit cho `catalog` — module cuối cùng trong 5 module đã chọn, còn lại 1/9.

---

## 7z. Audit cho `catalog` — XONG (2026-07-23) — **MẠCH 5 MODULE ĐÃ ĐÓNG, 9/9 MODULE CÓ AUDIT**

**Đã làm:** 1 action mới `CATALOG_DRUG_CREATED` (`core/audit/entry.py`). `CatalogService` nhận
`audit: AuditLogger` bắt buộc (chỉ 1 call site ngoài `register.py`, giống `prescription`/`inventory`/
`procurement`). `create_drug` ghi `CATALOG_DRUG_CREATED` (target = `drug.id`) — chỉ 1 action vì đây là
use-case ghi duy nhất của module (chưa có `update_drug`); `rx_class` (OTC/ETC/CONTROLLED) là phân loại
thẩm quyền mọi luồng kiểm soát downstream (`sales` Rx gate, `compliance` ledger) tin theo, nên "ai đã
thêm/phân loại thuốc này" đáng ghi vết dù `catalog` bản thân không có rủi ro pháp lý cao như sales/
inventory.

**Phạm vi đã chọn (tự quyết, full-auto #3):** không audit `create_ingredient`/`list_ingredients` —
đã quyết định ở §7u (dữ liệu tham chiếu toàn cục, không phải hành vi tenant); không audit `get_drug`/
`list_drugs`/`get_drug_ingredients` — đọc đơn thuần, cùng nguyên tắc đã áp dụng xuyên suốt các module
trước (`crm.list_customers`, `prescription.get_prescription`, v.v. — §7t quyết định #3).

**Test mới** (`tests/integration/test_catalog_repo.py`): `test_create_drug_leaves_an_audit_row` (đọc
lại bảng `audit_logs`, không tin call site).

**Bằng chứng:** `ruff` sạch · `mypy --strict` **212 file** · `import-linter` **13/0** (không đổi
contract) · `pytest` **exit code 0** (2 test exhaustiveness cập nhật ngay từ đầu). Không có migration
mới.

### Tổng kết mạch audit 5 module (GĐ chọn ưu tiên 2026-07-23, §7v→§7z)

| Module | Action mới | Bắt buộc/optional | PROJECT_STATE |
|---|---|---|---|
| `sales` | `SALE_COMPLETED` | optional (3 test tự dựng service) | §7v |
| `inventory` | `INVENTORY_STOCK_RECEIVED`, `INVENTORY_STOCK_DISPENSED` | bắt buộc | §7w |
| `procurement` | `PROCUREMENT_PO_ORDERED`, `PROCUREMENT_GRN_CONFIRMED` | bắt buộc | §7x |
| `clinical` | `CLINICAL_INTERACTION_CHECKED`, `CLINICAL_RECOMMENDATION_ACCEPTED` | optional (2 test tự dựng service) | §7y |
| `catalog` | `CATALOG_DRUG_CREATED` | bắt buộc | §7z |

**9 action mới, 5 commit riêng** (`56fb349`, `6cbe37f`, `5dae48e`, `02232d0`, và commit của §7z) —
cộng với 6 module đã có audit từ trước (`iam`, `prescription`, `compliance`, `crm` — xem §7l/§7r) ⇒
**toàn bộ 9/9 module nghiệp vụ nay đều có audit trail** cho ít nhất hành vi cốt lõi nhất của module đó.
Nguyên tắc xuyên suốt cả 5 module: chỉ audit **sự kiện thật/không đảo ngược** (hoàn tất, xác nhận,
duyệt) — không audit CRUD hành chính, đọc đơn lẻ, hay dữ liệu tham chiếu toàn cục; không audit trùng
lặp giữa module gốc phát sinh sự kiện và module phản ứng cross-module (đã nêu rõ ở từng mục §7v-§7z).

**Nợ kỹ thuật còn lại (không đổi, xem §7t mục 3):** FK `atc_code`, persist trả hàng (`register_return`,
cross-module), `AnthropicProvider` thật (chặn — cần `AI__API_KEY`).

---

## 7aa. Persist trả hàng (`register_return`) — XONG use-case, KHÔNG auto-restock tồn kho (2026-07-23)

> Sau khi đóng mạch audit 5 module (§7v-§7z), sếp cho phép tiếp tục full-auto không dừng hỏi từng lệnh.
> Đã kiểm tra FK `atc_code` trước — **quyết định KHÔNG bật**: chỉ 10 mã ATC được seed làm dữ liệu khởi
> động (`seeds/reference_data.py` tự ghi "small starter set... full import job is a later concern");
> bật FK bây giờ sẽ chặn tạo bất kỳ thuốc nào có mã ATC thật ngoài 10 mã đó — vẫn là blocker (thiếu
> nguồn ATC đầy đủ), không phải chỉ là nợ kỹ thuật rẻ để sửa. Chuyển sang việc còn lại: **persist trả
> hàng**, domain đã có từ Sprint 4 (`SalesOrder.register_return`), chỉ thiếu tầng use-case.

**[GĐ]:** Đây là mục có yếu tố pháp lý cần nêu rõ, không chỉ báo cáo kỹ thuật thuần — **quyết định
KHÔNG tự động phục hồi tồn kho (auto-restock) khi có trả hàng**, dù kỹ thuật hoàn toàn làm được. Lý
do: thuốc đã bán ra rồi trả lại (nhất là thuốc kê đơn/kiểm soát) cần dược sĩ kiểm tra tình trạng bao bì/
chất lượng trước khi quyết định có bán lại được không — tự động cộng lại vào tồn kho bán được ngay khi
khách trả hàng là rủi ro an toàn dược phẩm thật, có thể vướng quy định GPP về đảm bảo chất lượng thuốc.
Không tìm thấy đặc tả nghiệp vụ trả hàng nào trong `docs/06_WORKFLOWS.md` để đối chiếu — đây là khoảng
trống thiết kế từ đầu, không phải tôi bỏ sót. Đề xuất: sếp xác nhận lại chính sách trả hàng thật (có
cho trả OTC còn nguyên bao bì tự động lên kệ không, ETC/CONTROLLED có luôn cấm resell không) — hiện tại
hệ thống chỉ ghi nhận **sự kiện trả hàng đã xảy ra** (đơn bán, dòng hàng, số lượng), việc đưa hàng vật
lý trở lại tồn kho bán được vẫn là thao tác tay qua `POST /inventory/receive` sẵn có, không tự động.

**Đã làm (sales side, an toàn — chỉ ghi nhận sự kiện, không đụng tồn kho):**
- `domain/events.py`: event mới `SaleReturned` (`return_id`/`order_id`/`branch_id`/`line_id`/`drug_id`/
  `quantity`) — chưa có subscriber (để sẵn cho sau này nếu sếp chốt chính sách restock tự động).
- `domain/ports.py` + `infrastructure/repository.py`: thêm `SalesRepository.update()` (trước đây
  `SalesOrder` chỉ từng được `add()` 1 lần, chưa từng cần sửa lại sau khi tạo).
- `application/service.py`: `SalesService.register_return(order_id, RegisterReturnInput, ctx)` — gọi
  domain method có sẵn, `repo.update`, phát `SaleReturned`, ghi audit.
- `interface`: `POST /sales/{order_id}/returns` (200, trả về đơn đã cập nhật `returned_quantity`/
  `status`); quyền mới `sales.return` (thêm vào `SALES_PERMISSIONS`, tự động có ở mọi vai đã có quyền
  bán hàng — cashier/dược sĩ/admin).
- Audit: action mới `SALE_RETURN_REGISTERED` (`core/audit/entry.py`), ghi kèm `return_id` trong context.

**Test mới:** unit-app (`test_sales_flow.py`: partial→full return, quá số lượng bị chặn 422/
`ValidationError`, đơn không tồn tại 404, event `SaleReturned` phát đúng, audit ghi đúng 1 dòng) + e2e
HTTP (`test_sales_api_e2e.py`: partial→full qua API thật, quá số lượng, đơn không tồn tại).

**Bằng chứng:** `ruff` sạch · `mypy --strict` **212 file** · `import-linter` **13/0** (không đổi
contract — thuần nội bộ `sales`, không cross-module mới) · `pytest` **exit code 0**. Không có migration
mới (`returned_quantity` đã có cột từ migration `0003_sales`).

**Nợ còn lại:** "trả tồn" (auto-restock) vẫn CHƯA làm — chờ sếp/GĐ chốt chính sách trả hàng thật trước
khi thiết kế cross-module (nếu chốt có auto-restock, đây sẽ là cross-module thật cần Opus + từng bước
duyệt, theo đúng tiền lệ S4.4/S4.5/S5.4/C.5).

### Chính sách trả hàng — sếp đã DUYỆT khung phân loại (2026-07-23)

GĐ đề xuất, sếp duyệt phần **(a) khung phân loại lý do trả hàng**; phần (b) — thêm trường "lý do trả"
vào hệ thống — **chưa duyệt**, để ngỏ khi sếp cần.

| Lý do trả | Cho lên kệ bán lại? | Ghi chú |
|---|---|---|
| Lỗi từ tiệm (bán nhầm, thiếu/thừa, bấm nhầm) | ✅ Có, nhưng dược sĩ phải xác nhận bao bì nguyên vẹn bằng tay | Trách nhiệm thuộc tiệm, thuốc chưa thật sự rời tầm kiểm soát |
| Thuốc lỗi từ nhà sản xuất | ❌ Không lên kệ — trả NCC hoặc huỷ | Vấn đề chất lượng, không phải tồn kho |
| Khách đổi ý | ❌ **Mặc định KHÔNG nhận trả thuốc dạng này** | Ra khỏi tiệm là mất kiểm soát bảo quản — chuẩn ngành các chuỗi lớn |
| Thuốc kiểm soát đặc biệt (mọi lý do) | ❌ Không bao giờ tự động lên kệ | TT20/2017 — phải qua sổ kiểm soát riêng, không xử lý như thuốc thường |

**Áp dụng vào hệ thống hiện tại:** khớp đúng những gì đã code ở trên (§7aa) — `register_return` chỉ
ghi nhận sự kiện, không tự động cộng tồn kho; restock (khi đủ điều kiện "lỗi từ tiệm" + bao bì nguyên
vẹn) vẫn là thao tác tay qua `POST /inventory/receive`, không tự động cho bất kỳ trường hợp nào — **an
toàn hơn cả khung đã duyệt** (khung cho phép restock tay cho case "lỗi từ tiệm", hệ thống hiện tại đã
đáp ứng đúng, không cần sửa gì thêm). Không code thêm gì ở bước duyệt này vì (b) chưa được chốt.

---

## 7ab. Nhóm việc rủi ro thấp đã duyệt (2026-07-23) — 3 việc độc lập, mỗi việc 1 commit

> Sếp duyệt hướng ưu tiên GĐ đề xuất: làm ngay nhóm rủi ro thấp (#1 API resolve reconciliation, #9
> dọn deprecation warning, #10 sửa tài liệu lệch), các việc còn lại (gộp lô, `MedicationHistoryEntry`,
> dị ứng OTC, outbox, mở Sprint 7 analytics/report) chờ sếp mô tả thêm trước khi làm.

| # | Việc | Commit |
|---|---|---|
| 10 | `ROADMAP.md`: tick "Hồ sơ sức khỏe khách hàng" đã xong (lệch tài liệu, đã xong từ §7m/§7t) + tách rõ phần `compliance` đã xong (sổ kiểm soát) vs chưa xong (outbox, dashboard) | *(gộp cùng #9, xem dưới)* |
| 9 | `StarletteDeprecationWarning` — thêm `httpx2` vào dev deps (`pyproject.toml`), `starlette.testclient` tự ưu tiên dùng thay `httpx` cũ, không cần sửa code (không nơi nào trong `src/` import `httpx` trực tiếp) | *(gộp cùng #10)* |
| 1 | API resolve `stock_reconciliation_needed` — xem chi tiết dưới | riêng |

**#1 — API resolve `stock_reconciliation_needed` (đã làm):**
- Domain: `StockReconciliationNeeded.resolve()` (chặn resolve 2 lần →
  `ReconciliationAlreadyResolvedError`).
- Port `StockReconciliationRepository`: thêm `get`/`update`/`list` (trước đây chỉ có `add`, "chưa có
  resolve workflow" — nay có).
- Application: `InventoryService.list_reconciliations` (lọc theo `resolved`, phân trang) +
  `resolve_reconciliation` (404 nếu không có, 409 nếu đã resolve).
- Interface: `GET /inventory/reconciliations` + `POST
  /inventory/reconciliations/{id}/resolve`; quyền mới `inventory.reconcile` (thêm vào
  `INVENTORY_PERMISSIONS` + `_WAREHOUSE_PERMISSIONS` tường minh — `WAREHOUSE` không kế thừa trọn bộ
  `INVENTORY_PERMISSIONS`).
- Audit: action mới `INVENTORY_RECONCILIATION_RESOLVED` — **không thêm cột** `resolved_by`/
  `resolved_at` vào bảng (tránh migration), ai/khi nào xử lý nằm ở `audit_logs`, đúng nguyên tắc đã
  dùng xuyên suốt các module khác.

**Test mới** (`tests/integration/test_inventory_flow.py`): lọc theo `resolved` (mở/đóng/tất cả),
resolve thành công + audit row, resolve 2 lần → 409, id không tồn tại → 404.

**Bằng chứng:** `ruff` sạch (check+format) · `mypy --strict` **212 file** · `import-linter` **13/0**
(không đổi contract) · `pytest` **exit code 0**. Không có migration mới (bảng
`stock_reconciliation_needed` + cột `resolved` đã có từ migration `0012`).

**Nợ còn lại (chờ sếp mô tả thêm, chưa tự làm):** gộp lô (PA B), `MedicationHistoryEntry` tự động,
dị ứng OTC, outbox/retry bền, module `analytics` + report (Sprint 7 mới).

---

## 7ac. Gộp lô (PA B) — XONG cho cả 2 luồng (2026-07-23, GĐ tự chốt theo full-auto)

> Sếp: "tiếp tục theo GĐ cố vấn". Full-auto (§7k mục CHẾ ĐỘ FULL-AUTO) liệt kê rõ "Quyết định
> nghiệp vụ/pháp lý" là loại quyết định Claude được tự chốt khi sếp bận việc khác — kỷ luật #3 gốc
> của dự án còn nêu đích danh **"gộp lô hay bỏ qua"** làm ví dụ, nay full-auto cho phép tự quyết,
> ghi rõ ở đây để xem lại.

**Quyết định (tự chốt):** gộp lô khi **cùng** `(drug_id, branch_id, lot_no, expiry_date)` — thêm điều
kiện HSD khớp so với PA B gốc chỉ nói `(drug_id, branch_id, lot_no)`, vì cùng số lô từ nhà sản xuất
đương nhiên phải cùng HSD; nếu số lô trùng nhưng HSD khác nhau, đó là bất thường dữ liệu thật (nhập
nhầm số lô, hoặc 2 lô thật trùng số ngẫu nhiên), **không gộp** — xử lý khác nhau theo luồng:
- **`receive_stock` (nhập tay):** HSD khác → `ValidationError` (422), từ chối ngay, dược sĩ tự sửa lại
  ngay tại chỗ (đây là luồng tương tác, sửa được ngay, không cần bảng đối soát).
- **`receive_from_goods_receipt` (GRN xác nhận):** HSD khác → **giữ nguyên hành vi cũ** (bỏ qua dòng +
  ghi `stock_reconciliation_needed`) — GRN không sửa được tương tác, cần con người tra lại sau (nay có
  API resolve từ §7ab).

**Công thức gộp:** `quantity_received` cộng dồn; `cost_price` = bình quân gia quyền theo số lượng
(`(qty_cũ*giá_cũ + qty_mới*giá_mới) / (qty_cũ+qty_mới)`) — quy ước kế toán tồn kho chuẩn, không phải
số liệu tự suy đoán. Gộp vào **cùng 1 batch** (không tạo batch mới) — `StockMovement` mới vẫn ghi vào
đúng `batch_id` đã có, nên FEFO/on-hand không cần đổi gì.

**Đã làm:**
- Domain: `ProductBatch.merge_receipt(quantity, cost_price)` + `ensure_mergeable_expiry(expiry_date)`
  (raise `LotExpiryMismatchError` nếu khác HSD).
- Port `BatchRepository.update()` mới (trước đây chỉ `add`, chưa từng cần sửa batch đã tồn tại).
- `receive_stock`: kiểm tra `find_by_lot` trước — có rồi + khớp HSD → gộp; có rồi + khác HSD → 422;
  chưa có → tạo batch mới như cũ. (Trước đây `receive_stock` **không hề kiểm tra trùng lô** — nhập
  trùng sẽ vỡ ở `uq_batch_lot` thành `IntegrityError` thô 500; nay đã có luồng xử lý tử tế.)
- `receive_from_goods_receipt`: cùng logic kiểm tra, nhánh khác HSD giữ nguyên hành vi flag cũ.

**Test mới:** `test_inventory_flow.py` (gộp cùng HSD giữ nguyên `batch_id`, khác HSD → 422, không ghi
gì khi bị từ chối) · `test_cross_module_goods_receipt.py` (đổi tên
`test_lot_collision_skips_line_and_flags_reconciliation` → 2 test: `..._same_expiry_merges` (xác nhận
giá vốn bình quân gia quyền đúng công thức) + `..._different_expiry_skips_and_flags_reconciliation`
(giữ nguyên hành vi cũ, chỉ đổi để dùng HSD thật sự khác thay vì trùng HSD như test cũ — test cũ vô
tình đặt cùng HSD nên giờ hành vi đổi từ "skip" sang "merge", phải viết lại cho đúng ý nghĩa mới).

**Bằng chứng:** `ruff` sạch (check+format) · `mypy --strict` **212 file** · `import-linter` **13/0**
(không đổi contract) · `pytest` **exit code 0**. Không có migration mới.

**Nợ còn lại (cross-module/kiến trúc lớn hơn — đề nghị phiên Opus riêng, không tiếp tục Sonnet):**
`MedicationHistoryEntry` tự động, dị ứng OTC (+ migration `SalesOrder.customer_id`), outbox/retry bền,
module `analytics` + report (Sprint 7 mới, cần sếp mô tả yêu cầu trước khi thiết kế).

---

## 7ad. MedicationHistoryEntry tự động + dị ứng OTC — XONG (2026-07-24, phiên Opus full-auto, 3 bước)

> Sếp chuyển sang model Opus + "tiếp tục như GĐ cố vấn". Full-auto (§7k CHẾ ĐỘ FULL-AUTO) bao gồm
> cross-module, nên làm liền không dừng chờ duyệt từng bước, nhưng giữ mỗi bước = 1 commit + 4 cổng
> xanh + ghi rõ mọi quyết định tự chốt (full-auto rule #3).

**Phát hiện thứ tự bắt buộc (nêu ngay đầu, không tự mở rộng phạm vi):** 2 việc `MedicationHistoryEntry`
tự động và dị ứng OTC **không độc lập** — cả hai bị chặn bởi cùng 1 thứ: `SalesOrder` không có
`customer_id` (bằng chứng ngay trong code cũ: comment `cross_module.py` "OTC sales carry no
customer_id, so only the drug–drug check runs here"). Nên phải làm `customer_id` **trước**. Đây đúng là
"bước tách riêng sau" mà sếp đã quyết ở **Q5 + Q7 §7m** (hồ sơ sức khỏe KH) — nhất quán với quyết định
cũ, KHÔNG đảo ngược.

| Bước | Nội dung | Commit |
|------|----------|--------|
| 1 | `SalesOrder.customer_id` (nullable) đủ 4 lớp + migration `0016` (add column + index, live/reversible/no-drift) | `05133cd` |
| 2a | `CrmService.record_medication_history` (use-case, crm-internal, không cross-module) + audit action `CUSTOMER_MEDICATION_HISTORY_RECORDED` | `0f5e352` |
| 2b | Wiring cross-module: `wire_medication_history` (mới) + dị ứng OTC trong `wire_safety_checks` | `9622bff` |

**Quyết định tự chốt (full-auto #3):**
1. **`customer_id` nullable vĩnh viễn, UUID trần KHÔNG FK sang `crm.customers`** — khách vãng lai OTC
   không có người mua là hợp lệ; sales phải độc lập crm (module-independence), cùng quy ước
   `prescription_ref`/`drug_id`.
2. **KHÔNG đổi contract `SaleCompleted`** (§7b ghi "cấm") — handler đọc `customer_id` qua
   `sales.get_sale(order_id)`, không nhét field vào event. Đọc thêm 1 lần/đơn — chấp nhận cho phản ứng
   nền hậu-commit.
3. **`record_medication_history` là phản ứng hệ thống, KHÔNG gate `crm.sensitive.write`** — giống
   `allergy_severities_for_safety_check` (§7m Q3): việc ghi do người hoàn tất đơn (thường thu ngân, không
   được tự tay ghi hồ sơ sức khỏe) kích hoạt, dữ liệu từ giao dịch chứ không phải họ gõ.
4. **Consent HEALTH là cơ sở pháp lý DUY NHẤT** (Luật 91/2025 Điều 26.1, §7m phát hiện #1) — không
   đồng ý → ghi 0 dòng, **không raise**, KH chưa opt-in đơn giản không có lịch sử, handler không vỡ.
   Domain `record_history_entry` còn enforce consent lần 2 (defense in depth).
5. **Idempotent theo `(source, ref_id)`** — phát lại cùng đơn/cấp phát không nhân đôi.
6. **Audit action riêng `CUSTOMER_MEDICATION_HISTORY_RECORDED`** — tách khỏi `CUSTOMER_SENSITIVE_WRITE`
   cùng lý do `CUSTOMER_SENSITIVE_AUTO_CHECK` tách khỏi read: máy-ghi mỗi đơn sẽ chôn vùi write người
   thật làm nếu gộp chung. Ghi 1 dòng/lần gọi (không phải mỗi thuốc).
7. **`wire_medication_history` TÁCH RIÊNG khỏi `wire_safety_checks`** — cái sau chỉ đọc+cảnh báo
   (warn-only), cái này GHI vào crm; trộn write vào handler read-only sẽ mờ ý định + permission set. Mỗi
   wire = 1 concern (khớp `wire_sale_dispensing`/`wire_goods_receipt_stock_in`). Đổi lại đọc source 2 lần.

**Dị ứng OTC:** `wire_safety_checks.on_sale_completed` nay đọc sale lấy `customer_id`, nếu có thì chạy
`run_allergy_check` cho luồng bán lẻ (trước chỉ luồng prescription). Thêm `sales.read` vào
`_SAFETY_PERMISSIONS`. Test cũ `test_sale_never_runs_allergy_check` đổi tên
`test_sale_without_a_customer_runs_no_allergy_check` + thêm positive `test_sale_to_allergic_customer_logs_allergy_warning`.

**Bằng chứng tổng:** 3 bước, mỗi bước 4 cổng xanh · `mypy --strict` **212 file** · `import-linter`
**13/0** (module-independence giữ nguyên — nối ở composition root) · migration `0016` live Postgres,
pg_dump backup trước (`~/backup_pre_migration_20260724_0314.sql`, full-auto rule #6). Test mới:
`test_cross_module_medication_history.py` (5) + crm use-case (4) + OTC allergy (2).

**Nợ còn lại Sprint 6→7:** outbox/retry bền (hạ tầng lõi event bus) — **Bước 1/3 (codec) đã XONG, xem
§7ae** — module `analytics` + report (Sprint 7 mới — cần sếp mô tả yêu cầu "dự báo nhu cầu" tính theo gì
trước khi thiết kế).

---

## 7ae. Outbox/retry — Bước 1/3: codec serialize/deserialize (domain thuần) — XONG (2026-07-24)

> Phiên bị tắt đột ngột trước đó (không qua nghi thức đóng phiên) sau §7ad. Resume phiên xác nhận theo
> đúng thứ tự bắt buộc (docker compose ps · process cũ · git status/log) — phát hiện working tree **không
> sạch**: `core/events/serialization.py` + `test_event_serialization.py` đã viết xong nhưng chưa commit
> (không có ghi chú "ĐIỂM DỪNG" giải thích tại sao dở dang — suy đoán hợp lý nhất: đây là Bước 1 outbox
> đang làm dở khi phiên bị cắt). Đã chạy đủ 4 cổng trên phần dở dang trước khi tin tưởng, xanh hết → commit
> nguyên trạng, không sửa logic.

**Nội dung:** `serialize_event`/`deserialize_event` — codec generic đi qua `dataclasses.fields()` +
`get_type_hints()` của bất kỳ `DomainEvent` nào, tự xử lý `Decimal`/`UUID`/`date`/`datetime`/tuple lồng
nhau mà không cần encoder riêng cho từng event. `EventRegistry` map tên `event_type` đã lưu về class —
sống ở composition root (kernel `core` không được biết business module nào tồn tại). Round-trip identity
test cho toàn bộ 17 `DomainEvent` hiện có trong hệ thống.

**Vì sao đúng là "domain thuần"/Bước 1:** codec chỉ import `core.events.base` — không đụng infra/DB,
khớp import-linter contract "Core kernel must not import business modules". Bảng outbox thật + relay
worker (Bước 2: app/infra/migration) và publish qua bảng đó thay vì `InMemoryEventBus` trực tiếp (Bước 3:
interface/wiring) **chưa làm** — không overclaim.

**Bằng chứng:** ruff sạch · `mypy --strict` sạch (file mới) · import-linter 13 kept/0 broken · pytest full
suite xanh (không hồi quy). 2 commit riêng: `a5862d6` (codec) + `c5b01f0` (sửa TODO.md lệch "2/9 module
chưa audit" — dòng cũ sai, §7y/§7z đã đóng mạch 9/9 từ 2026-07-23, phát hiện khi đối chiếu tài liệu lúc
resume).

**Tiếp theo (chưa hỏi vì không phải quyết định nghiệp vụ/pháp lý — nhưng SẼ hỏi tại điểm outbox chạm
migration/bảng mới, đúng kỷ luật cross-module/migration hiện có):** thiết kế bảng outbox (cột, index,
retention) + relay/retry worker.

---

## 7af. ⏸️ ĐIỂM DỪNG PHIÊN (2026-07-24) — chờ sếp đổi model sang Opus cho outbox Bước 2/3

> Phiên này resume sau khi phiên trước bị tắt đột ngột (không qua nghi thức đóng phiên) ngay sau §7ad.
> Đóng phiên đúng nghi thức lần này để tránh lặp lại tình huống đó.

**Trạng thái kỹ thuật lúc dừng (xác nhận bằng lệnh):**

| Hạng mục | Trạng thái |
|----------|-----------|
| Git | Sạch, HEAD = `19f2778` |
| Docker | `postgres` + `redis` healthy (Claude khởi động lại đầu phiên vì đã exit 255 từ 3 tiếng trước — nguyên nhân exit chưa điều tra, không phải lỗi phiên này) |
| Tiến trình nền | Không có `uvicorn`/`next dev` nào đang treo |
| Backend 4 cổng | ruff sạch · mypy --strict sạch · import-linter 13 kept/0 broken · pytest full suite xanh (chạy lại sau commit `a5862d6`) |

**Quyết định tự chốt trong phiên (full-auto rule #3):**
1. Phát hiện working tree không sạch lúc resume (codec outbox dở dang từ phiên bị cắt) — chạy đủ 4 cổng
   trước khi tin tưởng, xanh hết → commit nguyên trạng không sửa logic. Chi tiết §7ae.
2. Sửa `TODO.md` dòng lệch "còn 2/9 module chưa audit" (sai — §7y/§7z đã đóng mạch 9/9 từ 2026-07-23).
3. **KHÔNG tự thiết kế outbox Bước 2/3 (bảng + relay) trên Sonnet** — tự nhận đây là "thiết kế mới hoàn
   toàn chưa có khuôn mẫu" theo CLAUDE.md mục "Chọn model" (rule chỉ định Opus cho loại việc này), dừng
   hỏi sếp thay vì lặng lẽ làm trên Sonnet dù full-auto miễn bước duyệt thiết kế. Sếp đã chọn: đổi sang
   Opus.

**Việc tiếp theo khi resume:** sếp `/model` chọn Opus → tiếp tục thiết kế + code outbox Bước 2/3 (bảng
outbox trong cùng transaction với dữ liệu nghiệp vụ + relay đọc bản ghi PENDING, retry, đánh dấu
PUBLISHED/FAILED). Không có việc nào khác đang treo giữa chừng. Nợ Sprint 6→7 còn lại đúng như §7ad đã
ghi: outbox Bước 2-3, module `analytics` (dừng hỏi sếp mô tả yêu cầu trước khi thiết kế — **không tự làm**).

---

## 7ag. Outbox/retry — Bước 2/3: machinery (bảng + repo + relay) NGỦ, flag OFF — XONG (2026-07-24)

> Phiên Opus. Sếp duyệt thiết kế §7af (3 điểm: công tắc sync/async · chia Bước 2 machinery-ngủ /
> Bước 3 flip-nguyên-tử · cổng idempotency) và **mở rộng cổng #3**: liệt kê TOÀN BỘ subscriber đang
> nối EventBus, xác nhận idempotent khi nhận event trùng, **không flip** cho tới khi sếp xác nhận danh
> sách. Bước 2 được phép bắt đầu ngay sau khi có bảng đó.

**Bảng idempotency đầy đủ (10 subscription / 7 handler, xác minh bằng code thật):** tất cả đường ghi dữ
liệu nghiệp vụ đều đã có khoá idempotent sẵn — dispense `exists_for_ref("sale",order_id)`, GRN
`exists_for_ref("grn",grn_id)`, medication_history `(source,ref_id)`, national_sync `client_uuid`, 3
handler nội-inventory chỉ log, allergy check read-only. **DUY NHẤT không idempotent: interaction check
trong `wire_safety_checks`** — ghi `AiRecommendation` + audit mỗi lần chạy ⇒ event trùng tạo bản ghi/audit
trùng (không hư tồn/tiền). Đây là điểm phải quyết trước khi flip (Bước 3), **đang chờ sếp xác nhận danh
sách**.

**Đã xây (machinery NGỦ — chưa đấu vào đường publish, `UoW.commit()` KHÔNG đổi):**
- `core/outbox/record.py` — `OutboxRecord` (frozen, slots) + `OutboxStatus` (PENDING/PUBLISHED/FAILED),
  framework-free như `audit/entry.py`; `payload` là dict đã qua codec §7ae, không biết event class.
- `core/outbox/models.py` — `OutboxEventORM` bảng `event_outbox` (cấp `core` như `audit_logs`, không FK).
  Unique `event_id`, index `(status,next_attempt_at)` + `(tenant_id,occurred_at)`.
- `core/outbox/ports.py` + `repository.py` — `add` (ghi PENDING trong txn nghiệp vụ) · `claim_pending`
  (oldest-first, due-filter, `FOR UPDATE SKIP LOCKED` — no-op trên SQLite) · `mark_published/retry/failed`.
- `core/outbox/relay.py` — `OutboxRelay.drain_once()`: claim → `deserialize_event` → `event_bus.publish`
  → stamp; backoff `base*2^(n-1)`, dead-letter khi `retry_count>=max_retries`.
- Migration `0017_event_outbox` (autogenerate). `models_registry.py` +1 import.

**Ranh giới quan trọng (ghi rõ để Bước 3 không hiểu nhầm):** `InMemoryEventBus.publish` cô lập lỗi
subscriber (log+nuốt) ⇒ outbox đảm bảo *event tới bus ít nhất 1 lần* (đóng cửa sổ "committed nhưng chưa
dispatch"), **không** đảm bảo subscriber thành công. Retry/FAILED của relay chỉ kích hoạt khi
deserialize/unknown-type/lỗi DB, không phải lỗi trong handler.

**Bằng chứng (4 cổng + live migration):** ruff sạch · `mypy --strict` 219 file sạch · import-linter
**13 kept/0 broken** (không thêm/xóa contract — outbox ở `core` nên không đụng module-independence) ·
pytest **633 passed** (+13 test outbox: 7 unit relay logic với fake repo, 6 integration repo SQLite).
Live migration trên Postgres (đã pg_dump backup trước, rule #6): `upgrade`→`alembic check` no-drift→
`downgrade -1` (xác nhận bảng biến mất bằng `to_regclass` NULL)→`upgrade`→check sạch; `\d event_outbox`
khớp 100% thiết kế (12 cột, jsonb, 2 index + PK + unique).

**Quyết định tự chốt trong phiên (full-auto rule #3):** không có quyết định nghiệp vụ/pháp lý tự chốt —
mọi quyết định lớn (sync/async, chia bước, idempotency) đều đã trình sếp duyệt ở §7af. Nợ tồn-âm khi
eventual-consistency (GĐ nêu) đã ghi vào `TODO.md` mục Nợ kỹ thuật (Sprint sau, gộp p95 NFR Sprint 8).

**Bước 3 (flip) CHƯA làm.** Khi làm: đổi `UoW.commit()` ghi outbox in-txn + công tắc `SYNC_DRAIN` ·
populate `EventRegistry` 17 event ở composition root · khởi `OutboxRelay` nền trong lifespan.

**SẾP ĐÃ DUYỆT (2026-07-24, cuối phiên §7ag):** (1) xác nhận bảng idempotency đầy đủ ở trên; (2) chọn
**phương án (a) — CHẶN TRÙNG cho interaction-check** trong `wire_safety_checks`: thêm khoá idempotent
`(context_type, context_id)` trước khi ghi `AiRecommendation`/audit, để redelivery không tạo bản ghi
tuân thủ trùng (GĐ khuyến nghị (a): audit/recommendation là bằng chứng NĐ356 + vết quyết định lâm sàng
docs/12, trùng lặp làm hồ sơ mất tin cậy khi thanh tra; chi phí chỉ 1 khoá idempotent). **Đây là việc
BẮT BUỘC làm TRƯỚC khi flip** — nếu không, giai đoạn chuyển tiếp at-least-once sẽ phình audit/recommendation.

---

## 7ah. ⏸️ ĐIỂM DỪNG PHIÊN (2026-07-24) — Bước 2 xong, sếp chốt (a), tạm dừng

**Trạng thái kỹ thuật lúc dừng (xác nhận bằng lệnh):**

| Hạng mục | Trạng thái |
|----------|-----------|
| Git | Sạch, HEAD = `48e40c0` (outbox machinery Bước 2/3) |
| Docker | `postgres` + `redis` **Up (healthy)** — Claude bật lại đầu phiên (đã TẮT lúc resume, §7af "healthy" đã lỗi thời) |
| Tiến trình nền | Không có `uvicorn`/`next dev`/`pytest` treo |
| 4 cổng | ruff sạch · mypy --strict 219 file · import-linter 13/0 · pytest **633** (chạy 2 lần độc lập, đều exit 0) |
| Migration | head = `0017_event_outbox`, đã apply live PG (round-trip verified) |

**Việc tiếp theo khi resume (Bước 3 — flip, thiết kế đã duyệt trọn):**
1. **TRƯỚC TIÊN** vá interaction-check theo **phương án (a)** sếp đã chốt: khoá idempotent
   `(context_type, context_id)` trong `wire_safety_checks` trước khi ghi `AiRecommendation`/audit
   (đây là điều kiện tiên quyết của flip — xem §7ag).
2. Đổi `SqlAlchemyUnitOfWork.commit()`: ghi outbox in-txn (dùng `serialize_event` + `OutboxRecord`) thay
   vì publish inline; thêm công tắc `SECURITY`/`OUTBOX__SYNC_DRAIN` (test+dev = sync drain giữ 633 test
   xanh; prod = relay nền async).
3. Populate `EventRegistry` 17 event ở composition root (`api/v1/__init__.py`), đăng ký vào container.
4. Khởi `OutboxRelay` nền trong `main.py` `_lifespan` (hủy khi shutdown); đấu sync-drain cho TestClient.
5. Flip là **1 commit nguyên tử** (rule: 4 cổng xanh mọi commit — sync-drain giữ suite xanh).

Nợ khác không đổi (§7ad): module `analytics` + report (chờ sếp mô tả yêu cầu). Nợ tồn-âm eventual-
consistency đã ở `TODO.md` (Sprint sau + p95 NFR Sprint 8).

---

## 7ai. ✅ OUTBOX BƯỚC 3/3 — FLIP XONG (2026-07-24, phiên Opus full-auto)

**Kết quả:** mọi `UnitOfWork` nay ghi sự kiện vào `event_outbox` **ngay trong giao dịch nghiệp vụ**.
Cửa sổ mất sự kiện (commit xong → tiến trình chết → `SaleCompleted` bốc hơi) đã đóng. Machinery ngủ từ
§7ag nay đã được đấu điện thật.

### 3 commit

| Commit | Nội dung |
|--------|----------|
| `50ea91c` | **Điều kiện tiên quyết** — chặn trùng interaction-check theo `(context_type, context_id)` (phương án (a) sếp chốt §7ag). Port + repo `find_for_context`, index `0018` (KHÔNG unique), `ClinicalService.find_recommendation_for_context()` chỉ đọc, cổng chặn đặt trong `wire_safety_checks`. Re-check thủ công qua API vẫn chạy được — khoá chỉ áp cho phản ứng tự động |
| *(chore)* | `ruff format` 5 file trôi định dạng có sẵn từ trước (3 migration 0013–0015 + 2 test e2e) — xem mục "Phát hiện lệch" bên dưới |
| *(flip)* | Bước 3 nguyên tử: UoW ghi outbox in-txn · `OutboxEventSink` · `OutboxSettings` · `EventRegistry` 14 event ở composition root · relay nền trong lifespan · 12 điểm dựng UoW gom về `UnitOfWorkFactory` |

### Thiết kế đã chọn (khác đôi chỗ so với phác thảo §7ah — đều là chọn kỹ hơn, không cắt bớt)

| Điểm | Phác thảo §7ah | Đã làm | Vì sao |
|------|----------------|--------|--------|
| Seam giữa UoW ↔ outbox | UoW gọi thẳng repo outbox | Protocol `OutboxSink` khai **trong `core/db/uow.py`**, cài đặt `OutboxEventSink` ở `core/outbox/sink.py` | `core.outbox.relay` đã phụ thuộc `core.db`; nếu `core.db` import ngược `core.outbox` thì vòng lặp import. Khai protocol tại chỗ dùng = cắt vòng, không cần TYPE_CHECKING lắt léo |
| Chế độ sync-drain | Gọi lại `relay.drain_once()` | Publish đúng những dòng UoW này vừa ghi, rồi `mark_published` | Gọi lại relay sẽ **đệ quy vô hạn** trên SQLite: `FOR UPDATE SKIP LOCKED` là no-op, nên drain lồng nhau claim lại chính dòng đang xử lý dở. Cách đã làm không tái nhập được vì chỉ đụng id của chính mình |
| Số event | "17 event" | **14** | Đếm thật bằng `class X(DomainEvent)`: sales 2, prescription 3, procurement 2, inventory 4, iam 3. Con số 17 ở §7ah là ước lượng, không phải đếm |
| Nơi dựng UoW | Giữ nguyên 12 chỗ | Gom về `UnitOfWorkFactory` đăng ký 1 lần trong container | 12 chỗ tự dựng UoW = 12 cơ hội quên truyền sink; quên là **mất sự kiện im lặng**, không có test nào bắt được. Diff còn nhỏ hơn: xoá 4 dòng, thêm 1 |
| Công tắc | 1 cờ `OUTBOX__SYNC_DRAIN` | 2 cờ: `SYNC_DRAIN` + `RELAY_ENABLED` | Chúng là 2 việc khác nhau: publish inline (độ trễ) vs quét lại dòng còn PENDING (phục hồi sau sự cố). Prod cần cái thứ hai kể cả khi bật cái thứ nhất |

**Mặc định:** `SYNC_DRAIN=true`, `RELAY_ENABLED=false` (hình dạng dev/test — publish inline, không có
poller nền làm test mất tính tất định). **Prod đặt `SYNC_DRAIN=false` + `RELAY_ENABLED=true`.** Cả hai
`false` khi `APP__ENV=prod` ⇒ app **từ chối khởi động** (sự kiện sẽ nằm lại trong bảng vĩnh viễn).

### Bằng chứng — chạy thật trên Postgres, đúng hình dạng prod

Không chỉ pytest (SQLite). Script kiểm tra trực tiếp trên PG với `SYNC_DRAIN=false`:

| Bước | Quan sát |
|------|----------|
| Nhập 20 viên | tồn = 20 · outbox `[StockMovedIn PENDING]` |
| Bán 3 viên | tồn **vẫn 20** (async: chưa trừ) · outbox thêm `SaleCompleted PENDING` |
| `drain_once()` #1 | published=2 · **tồn 17** (FEFO dispense đã chạy) · sinh `StockMovedOut PENDING` |
| `drain_once()` #2 | published=1 · tất cả PUBLISHED |
| `drain_once()` #3 | processed=0 · tồn vẫn 17 (không trừ 2 lần) |

**Phát hiện đáng ghi:** ở chế độ async, **mỗi vòng quét chỉ đẩy được 1 mắt xích** của dây chuyền sự kiện
(bán → dispense → `StockMovedOut`). Dây chuyền N mắt cần N chu kỳ poll để lắng hẳn. Không phải lỗi —
nhưng là thứ phải biết khi chọn `POLL_INTERVAL_SECONDS` cho prod, và nó cộng dồn vào độ trễ tồn kho đã
ghi trong nợ tồn-âm ở `TODO.md`. Dữ liệu tenant thử nghiệm đã dọn sạch sau khi chạy.

### Phát hiện lệch tài liệu ↔ thực tế (đã sửa luôn, đều thuộc loại (a) rẻ)

| Lệch | Xử lý |
|------|-------|
| **Cổng `ruff` ĐANG ĐỎ tại HEAD trước phiên này** — 24 lỗi trên `migrations/0013–0015` + 2 file test e2e, có sẵn từ trước, không do phiên này | `ruff format` 5 file đó thành 1 commit riêng. Ghi rõ vì báo cáo "4 cổng xanh" các phiên trước dùng `ruff check` trên file mình sửa, không phải cổng `ruff check . && ruff format --check .` toàn repo như `make lint` |
| `docs/03` ghi bảng tên `outbox_events` | Thực tế là `event_outbox` (migration 0017) — sửa `docs/03` + `docs/06` theo thực tế |
| README ghi `alembic upgrade head # 0001 → 0013` | Nay tới `0018` — sửa |
| **Cách chạy pytest của chính Claude che mất exit code** — `pytest -q \| tail` trả về mã thoát của `tail` (luôn 0), nên 2 lần "suite xanh" giữa phiên là **không có căn cứ**; lần chạy đầy đủ đầu tiên có ghi mã thoát thật đã bắt được 1 test đỏ (`test_registry_covers_every_domain_event` — fake event trong test bị đếm nhầm là event thật) | Đã sửa test + từ nay ghi `EXIT=$?` ra file thay vì pipe. Commit `50ea91c` được xác nhận lại bằng chính lần chạy cuối (code của nó nằm trong HEAD) |
| **README §5 "Trạng thái dự án" đứng yên ở Sprint 3** ("HOÀN THÀNH", `pytest 46`, `import-linter 6/0`) trong khi thực tế đã qua Sprint 6 | **ĐÃ SỬA** — Chain chốt nội dung ngay sau khi được báo (2026-07-24): bảng Sprint 1–7, tách rõ "Sprint 7 đã xong / còn lại", số liệu cổng mới (`pytest 650` · `mypy 221` · `import-linter 13/0` · mig `0001`→`0018`). Giữ nguyên sắc thái không overclaim: Sprint 4 ✅ *(backend)*, Sprint 5 ✅ *(mức MOCK — còn `# BLOCKER: AI__API_KEY thật`)* |
| **ROADMAP.md Sprint 7 vẫn tick `[ ]` cho dòng "transactional outbox ... — CHƯA làm"** dù outbox hạ tầng lõi đã xong (§7ai) | **CHƯA sửa** — dòng đó gộp 2 việc (outbox + audit query dashboard) và mới xong 1; tách lại checkbox là sửa cấu trúc lộ trình, để Chain chốt. README §5 đã ghi đúng thực tế nên không có mâu thuẫn đối ngoại |

### Quyết định tự chốt trong phiên (full-auto rule #3)

Không có quyết định nghiệp vụ/pháp lý mới. Toàn bộ quyết định là **kỹ thuật**, đã liệt kê ở bảng thiết
kế trên. Quyết định gần nghiệp vụ nhất — mặc định `RELAY_ENABLED=false` — chỉ ảnh hưởng dev/test; prod
bị validator ép phải có ít nhất 1 đường giao hàng, và README/`.env.example` ghi rõ hình dạng prod.

### Còn nợ sau bước này

| Nợ | Ghi ở đâu |
|----|-----------|
| Cảnh báo/khoá tồn-âm khi eventual-consistency ở prod | `TODO.md` Sprint sau + gộp p95 NFR Sprint 8 |
| Quét dọn (retention) dòng PUBLISHED/FAILED trong `event_outbox` | **Mới** — chưa có cơ chế xoá, bảng sẽ phình vô hạn ở prod. Đã thêm vào `TODO.md` |
| Module `analytics` + report | Chờ sếp mô tả yêu cầu (§7ad) |

---

## 7aj. ✅ RETENTION `event_outbox` (2026-07-24, phiên Opus full-auto — GĐ chọn việc)

**Bối cảnh:** Chain giao "hạn mức còn 45%, tiếp tục code cho hợp lý đi GĐ". GĐ chọn retention chứ không
chọn audit dashboard / `analytics` / retry DAV — lý do: đây là nợ **do chính mạch flip đẻ ra** (§7ai),
là **blocker prod**, và là thứ duy nhất trong danh sách không cần Chain mô tả yêu cầu nghiệp vụ trước.
Cũng vừa cỡ hạn mức còn lại: đóng gọn được, không để lại module xây dở.

### Chính sách xoá — chỗ duy nhất bug ở đây có thể phá dữ liệu thật

| Trạng thái | Xử lý | Vì sao |
|-----------|-------|--------|
| `PUBLISHED` | Xoá sau **30 ngày** (`OUTBOX__RETENTION_PUBLISHED_DAYS`) | Dòng outbox là **hạ tầng giao hàng, không phải bằng chứng**: bản ghi nghiệp vụ nằm ở `sales_orders`/`stock_movements`…, vết kiểm toán nằm ở `audit_logs`. Hết hạn không mất thứ gì thanh tra hỏi tới |
| `FAILED` | **Giữ vĩnh viễn** theo mặc định (`retention_failed_days=None`) | Là dấu vết DUY NHẤT cho biết có sự kiện chưa bao giờ giao được. Xoá theo hẹn giờ = xoá im lặng. Chỉ đặt cửa sổ khi deployment có quy trình soát dead-letter thật |
| `PENDING` | **Không bao giờ**, ở mọi tuổi | Là việc chưa giao. Ràng buộc bằng **KIỂU** — `TerminalStatus = Literal[PUBLISHED, FAILED]` — nên mypy chặn ngay khi viết, không phụ thuộc người nhớ đọc docstring |

### Thiết kế

| Điểm | Chọn | Vì sao |
|------|------|--------|
| Nhịp chạy | Task nền **riêng**, mặc định 1 giờ/lượt, cờ `RETENTION_ENABLED` **độc lập với `RELAY_ENABLED`** | Dòng chất đống ở chế độ `sync_drain` y hệt chế độ relay. Buộc retention vào relay là bẫy: deployment chạy sync-drain sẽ không bao giờ được dọn |
| Xoá theo lô | `batch_size=500`/txn, `max_batches=20`/lượt | Mỗi lô 1 giao dịch ngắn → không khoá bảng. `max_batches` chặn 1 lượt biến thành bão giao dịch; tồn đọng lớn dọn dần qua nhiều lượt thay vì 1 lần |
| Câu SQL | `DELETE ... WHERE id IN (SELECT ... LIMIT n)` | Postgres không có `DELETE ... LIMIT`; cách này chạy được cả PG lẫn SQLite bằng đúng 1 câu |
| Index | Migration `0019` `(status, created_at)` | Index dispatch cũ `(status, next_attempt_at)` cũng dẫn đầu bằng status nhưng già theo `next_attempt_at` — không trả lời được câu hỏi tuổi. Thiếu index này thì mỗi lượt quét đọc toàn bộ dòng đã giao |
| Mặc định `RETENTION_ENABLED` | **false** | Hẹn giờ chạy trong bộ test làm test mất tính tất định (cùng lý do với relay). **Prod phải bật** — khởi động ở prod mà thiếu thì log `outbox_retention_disabled_in_prod` |

### Bằng chứng

**pytest 665** (+9 unit retention, +2 repo purge, +4 lifespan; `EXIT=0` ghi ra file) · ruff sạch ·
mypy --strict 222 file · import-linter 13/0 · migration `0019` round-trip verified trên PG thật.

**Chạy thật trên Postgres** (không chỉ SQLite): seed 4 dòng backdate — `PUBLISHED` 60 ngày,
`PUBLISHED` 1 ngày, `PENDING` 3650 ngày, `FAILED` 3650 ngày → 1 lượt `purge_once()` xoá **đúng 1 dòng**
(`PUBLISHED` quá hạn), giữ nguyên 3 dòng còn lại; lượt 2 = no-op. Dữ liệu thử nghiệm đã dọn.

**Test lifespan** (mới): xác nhận 2 task nền chỉ khởi khi bật đúng cờ của nó, retention chạy được khi
relay tắt, và **cả hai đều `cancelled()` sau khi app shutdown** — task rò rỉ giữ connection + hẹn giờ
suốt đời tiến trình.

### Quyết định tự chốt (full-auto rule #3)

Retention bao nhiêu ngày **không phải quyết định pháp lý** — đã lập luận ở bảng trên (outbox không phải
hồ sơ lưu trữ theo luật; `audit_logs` mới là). Nếu Chain thấy khác, đổi 1 biến môi trường là xong, không
phải sửa code. Việc giữ `FAILED` vĩnh viễn là chọn an toàn có chủ đích, không phải quên làm.

### Còn nợ sau bước này

Không phát sinh nợ mới. Mạch outbox nay đóng trọn: codec (§7ae) → machinery (§7ag) → flip (§7ai) →
retention (§7aj). Nợ Sprint 7 còn lại không đổi: audit query dashboard, `analytics`, report xuất khẩu
(2 cái sau chờ Chain mô tả yêu cầu), retry DAV vẫn kẹt `# BLOCKER: DAV API spec`.

---

## 7ak. ⏸️ ĐIỂM DỪNG PHIÊN (2026-07-24) — mạch outbox đóng trọn, chuyển sang Design

**Trạng thái kỹ thuật lúc dừng (xác nhận bằng lệnh, không tin tài liệu):**

| Hạng mục | Trạng thái |
|----------|-----------|
| Git | Sạch (0 file thay đổi), HEAD = `1415bb8` |
| Docker | `postgres` + `redis` **Up 5h (healthy)** |
| Tiến trình nền | **0** — không có `uvicorn`/`next dev`/`pytest` treo |
| 4 cổng | ruff check + format --check sạch (315 file) · mypy --strict **222 file** · import-linter **13/0** · pytest **665** (`EXIT=0` ghi ra file, không pipe qua `tail`) |
| Migration | head = `0019_outbox_retention_idx`, đã apply live PG (round-trip verified) |
| Dữ liệu thử nghiệm | Đã dọn — `event_outbox` = 0 dòng; 2 `sales_orders` còn lại là dữ liệu có sẵn từ 2026-07-23, không phải của phiên này |

**7 commit trong phiên:**

| Commit | Nội dung |
|--------|----------|
| `50ea91c` | Chặn trùng interaction-check `(context_type, context_id)` + mig `0018` — điều kiện tiên quyết flip |
| `5c84e22` | `ruff format` 5 file trôi định dạng — khôi phục cổng lint vốn đã đỏ tại HEAD |
| `2818452` | **FLIP outbox** — UoW ghi `event_outbox` trong txn nghiệp vụ (§7ai) |
| `af0c4bf` | README §5 "Trạng thái dự án" theo thực tế |
| `8e9e13f` | Tách checkbox ROADMAP Sprint 7 |
| `e758f6a` | Retention: logic + repo + mig `0019` (bước 1/2) |
| `1415bb8` | Retention: settings + lifespan (bước 2/2) — §7aj |

### Toàn bộ quyết định TỰ CHỐT trong phiên (full-auto rule #3 — gom 1 chỗ để Chain đọc lướt)

| # | Quyết định | Loại | Đảo ngược thế nào |
|---|-----------|------|-------------------|
| 1 | `OutboxSink` khai protocol trong `core/db/uow.py` thay vì import ngược `core.outbox` | Kỹ thuật (bắt buộc — nếu không thì vòng lặp import) | Sửa code |
| 2 | Sync-drain publish đúng dòng vừa ghi, KHÔNG gọi lại `relay.drain_once()` | Kỹ thuật (bắt buộc — tránh đệ quy vô hạn trên SQLite) | Sửa code |
| 3 | Gom 12 điểm dựng UoW về `UnitOfWorkFactory` | Kỹ thuật | Sửa code |
| 4 | Tách 2 cờ `SYNC_DRAIN` / `RELAY_ENABLED` thay vì 1 | Kỹ thuật | Env var |
| 5 | Mặc định `RELAY_ENABLED=false`, `RETENTION_ENABLED=false` | Vận hành | **Env var** |
| 6 | `RETENTION_ENABLED` độc lập `RELAY_ENABLED` | Kỹ thuật | Sửa code |
| 7 | Retention `PUBLISHED` = 30 ngày | Vận hành (**không phải pháp lý** — lập luận ở §7aj) | **Env var** |
| 8 | Retention `FAILED` = giữ vĩnh viễn | Vận hành, chọn an toàn có chủ đích | **Env var** |
| 9 | Sửa 1 mệnh đề trong câu Chain đọc cho ROADMAP (outbox thay cơ chế *phát sự kiện*, KHÔNG thay retry DAV) | Chính xác hoá, đã báo Chain ngay | Sửa 1 dòng md |

Không có quyết định **nghiệp vụ/pháp lý** nào tự chốt trong phiên. Việc gần nhất — chặn trùng
interaction-check — là do Chain chốt từ §7ag.

### Việc tiếp theo: **PHIÊN DESIGN**, không phải phiên code

Chain chuyển sang Design để lên ý tưởng cho 3 mục còn lại của Sprint 7. Cả 3 đều **chặn ở yêu cầu, không
chặn ở kỹ thuật** — bắt đầu code trước khi trả lời được các câu dưới là chắc chắn phải viết lại.

| Mục | Câu hỏi phải trả lời trong phiên Design |
|-----|------------------------------------------|
| **Audit query dashboard** | Ai được xem (chủ chuỗi / quản lý nhà thuốc / thanh tra)? Xem để trả lời câu hỏi gì (điều tra 1 vụ việc? soát định kỳ? chứng minh tuân thủ khi thanh tra)? Lọc theo chiều nào (người–thời gian–đối tượng–hành động)? Có xuất file không? **Lưu ý riêng:** `audit_logs` chứa vết "ai đã đọc hồ sơ sức khỏe của ai" — dashboard này tự nó là một bề mặt dữ liệu nhạy cảm, cần quyền riêng chứ không dùng chung `audit.read` |
| **Module `analytics`** | "Dự báo nhu cầu" tính theo gì — lịch sử bán bao lâu, có tính mùa vụ/dịch bệnh không, tới cấp thuốc hay cấp hoạt chất? "Đề xuất nhập" sinh PO nháp theo tồn tối thiểu hay theo dự báo? Dashboard hiển thị số liệu nào ở màn hình đầu? *(treo từ §7ad, chưa từng được mô tả)* |
| **Report xuất khẩu** | Mẫu nào ra trước, và theo biểu mẫu pháp lý có sẵn hay tự thiết kế? Xuất định dạng gì (Excel/PDF/XML liên thông)? Ai bấm xuất? |

**Điều kiện thuận lợi:** cả 3 đều nằm trong ROADMAP gốc → **không bắt buộc qua cổng `docs/14`** (cổng đó
dành cho tính năng NGOÀI ROADMAP gốc). Nhưng phần dashboard chạm dữ liệu nhạy cảm nên vẫn nên soát
Privacy by Design ở mức tối thiểu — đừng bỏ qua chỉ vì cổng không bắt buộc.

**Việc còn treo, không thuộc Sprint 7:** cảnh báo/khoá tồn-âm khi outbox chạy async (Chain đã chốt Sprint
sau, gộp đo tải p95 Sprint 8) · retry đẩy DAV vẫn best-effort riêng, kẹt `# BLOCKER: DAV API spec`.

---

## 7al. ✅ AUDIT DASHBOARD — XONG (2026-07-24, phiên Opus full-auto — GĐ giao 1/3 mục Sprint 7)

> GĐ (thay Chain đang bận HoSoCongTrinh, full-auto) chỉ giao **audit dashboard** — mục rủi ro pháp lý
> thấp nhất trong 3 mục còn lại (công cụ nội bộ, không phải biểu mẫu nộp cơ quan). **KHÔNG động** vào
> `analytics` / report xuất khẩu: 2 mục đó cần Chain trả lời trực tiếp (phương pháp dự báo · đúng biểu
> mẫu pháp lý mà `docs/legal/` đang thiếu) — đoán sai là rủi ro tuân thủ thật, xem §7ak.

### Giả định Design đã dùng (GĐ tự quyết thay Chain khi bận — full-auto rule #3, ghi lại để Chain đọc sau)

| # | Câu hỏi | Đã chọn |
|---|---------|---------|
| 1 | Ai được xem | Quyền RIÊNG `audit.dashboard.read` (KHÔNG dùng chung `audit.read`). Cấp: `system_admin` (qua `ALL_PERMISSIONS`) + `chain_pharmacist` (owner) + `branch_pharmacist` (quản lý nhà thuốc). KHÔNG cashier/warehouse. `branch_pharmacist` nhận dashboard nhưng **vẫn không có** `audit.read` thô — tách bề mặt nhạy cảm |
| 2 | Trả lời câu hỏi gì | Cả 3 (điều tra vụ việc + soát định kỳ + sẵn sàng thanh tra) → lọc linh hoạt, không truy vấn cố định |
| 3 | Lọc theo chiều | actor + from/to + `target_type` (entity) + action — tất cả optional, AND. `target_type` là chiều MỚI mà `/audit-logs` chưa có |
| 4 | Xuất file | CSV thuần (không phải biểu mẫu pháp lý — khác hẳn "report xuất khẩu" mục kia) |
| 5 | Phân trang | Bắt buộc. List: limit≤200/offset. Export: stream theo lô 500, phân trang nội bộ (không nạp cả bảng vào RAM) |

**Điều chỉnh kỹ thuật so với giả định (ghi rõ theo tinh thần "GĐ tự quyết, ghi lại"):** phát hiện đã có
sẵn `core/audit/query.py` (`AuditQueryService` + `/audit-logs`, quyền `audit.read`) — "bản tối thiểu chứng
minh trail truy vấn được". KHÔNG sửa/thay nó (giữ contract cũ, kỷ luật #5); dashboard là **bề mặt thứ 2**
giàu hơn (entity filter + CSV) với quyền riêng, đúng khuôn kernel-infra như audit cũ (đặt ở `core` + endpoint
ở `api/v1` composition root, không module-import-module).

### 3 commit (stepped-commit, mỗi bước 4 cổng xanh ở trạng thái cô lập)

| Commit | Bước | Nội dung |
|--------|------|----------|
| `7346dbe` | 1/3 đọc-thuần | `ports`+`repository` thêm filter `target_type` · `csv_export.py` thuần (CSV_HEADER + entry_to_row, context gộp 1 cột JSON deterministic) |
| `76ec94e` | 2/3 app+seed+migration | `AuditDashboardService` (list + export_rows: quyền/thời gian check EAGER trước stream, generator ở `_export_stream`) · quyền `audit.dashboard.read` vào 3 role + `ALL_PERMISSIONS` · index `(tenant_id, target_type, occurred_at)` model+mig `0020` |
| `adb38da` | 3/3 interface | endpoint `GET /audit-dashboard` + `/export` (StreamingResponse text/csv) · đăng ký router + container · e2e 11 test |

### Bằng chứng 4 cổng (mỗi commit kiểm cô lập bằng stash phần bước sau)

| Cổng | Kết quả |
|------|---------|
| ruff check + format --check | sạch (300 file) |
| import-linter | **13/0 KEPT** — không thêm/sửa contract (dashboard ở core, endpoint ở composition root) |
| mypy --strict | **225 file**, 0 lỗi (bẫy đã gỡ: `list[str]` trong annotation bị phân giải nhầm sang method `list` của class → alias `CsvRow` ở module scope) |
| pytest | **679** (665 + 3 csv unit + 11 dashboard e2e), EXIT=0 |

### Migration + kỷ luật #7 (chạy thật trên CSDL có dữ liệu sẵn, xác nhận bằng SQL — KHÔNG tin log)

- pg_dump backup trước upgrade: `~/backup_pre_migration_20260724_1914.sql` (full-auto rule #6).
- `alembic upgrade head`: `0019 → 0020_audit_target_type_idx` trên live PG. **Round-trip verified**:
  downgrade xoá index (count 0) → upgrade tạo lại (count 1).
- `python -m seeds.run` trên live PG (role đã tồn tại từ trước, thiếu quyền mới — đúng kịch bản sự cố
  §7l): 5 role **updated**. Xác minh bằng SQL thật trên `role_permissions`:

  | role | có `audit.dashboard.read` | có `audit.read` |
  |------|:---:|:---:|
  | system_admin | ✅ | ✅ |
  | chain_pharmacist | ✅ | ✅ |
  | branch_pharmacist | ✅ | ❌ |
  | cashier | ❌ | ❌ |
  | warehouse | ❌ | ❌ |

  Đúng 100% ý đồ Design #1. (Ghi chú: live DB còn drift nhẹ từ phiên trước — vài role thiếu 1-2 quyền
  cũ như `crm.consent.manage`; seed sync đã kéo về khớp code. Không phải quyền phiên này thêm.)

### ⏸️ ĐIỂM DỪNG PHIÊN (2026-07-24) — audit dashboard xong, 2 mục Sprint 7 còn chờ Chain

| Hạng mục | Trạng thái (xác nhận bằng lệnh) |
|----------|--------------------------------|
| Git | HEAD `adb38da`, cây sạch (3 commit trong phiên) |
| Docker | `postgres` + `redis` **Up (healthy)** — Claude bật lại đầu phiên (đã TẮT lúc resume) |
| Migration | head = `0020_audit_target_type_idx`, live PG round-trip verified |
| 4 cổng | ruff/format sạch · import-linter 13/0 · mypy --strict 225 file · pytest **679** EXIT=0 |
| Dữ liệu thử | Không tạo tenant/dữ liệu thử trên live PG (seed chỉ sync role — dữ liệu dùng chung, GIỮ); e2e chạy SQLite tmp, tự dọn |
| Tiến trình nền | 0 treo |

**Quyết định TỰ CHỐT trong phiên (full-auto rule #3):**

| # | Quyết định | Loại | Đảo ngược |
|---|-----------|------|-----------|
| 1 | Quyền riêng `audit.dashboard.read`, không dùng chung `audit.read` | Nghiệp vụ (Design #1, GĐ chốt) | Sửa seed + re-seed |
| 2 | `branch_pharmacist` được dashboard nhưng KHÔNG `audit.read` thô | Nghiệp vụ (tách bề mặt nhạy cảm) | Sửa seed |
| 3 | Dashboard là bề mặt thứ 2, KHÔNG thay `/audit-logs` cũ | Kỹ thuật (giữ contract cũ) | Sửa code |
| 4 | Export CSV stream theo lô 500, phân trang nội bộ | Kỹ thuật (RAM phẳng) | Sửa hằng |
| 5 | `context` gộp 1 cột JSON (không nở cột theo key) | Kỹ thuật (header ổn định, loss-free) | Sửa serializer |
| 6 | Index `(tenant_id, target_type, occurred_at)` cho chiều entity | Kỹ thuật | migration down |

**2 mục Sprint 7 còn lại — KHÔNG đụng, chờ Chain trả lời (đúng chỉ đạo phiên):**

| Mục | Câu hỏi Chain phải trả lời trước khi code |
|-----|-------------------------------------------|
| Module `analytics` | "Dự báo nhu cầu" tính theo gì (lịch sử bao lâu · mùa vụ/dịch bệnh · cấp thuốc hay hoạt chất)? "Đề xuất nhập" theo tồn tối thiểu hay dự báo? Màn hình đầu hiện số nào? |
| Report xuất khẩu | Mẫu nào ra trước · theo biểu mẫu pháp lý có sẵn hay tự thiết kế (`docs/legal/` đang thiếu)? Định dạng (Excel/PDF/XML liên thông)? Ai bấm xuất? |

---

## 7am. Yêu cầu `analytics` + `report xuất khẩu` — GĐ chốt (2026-07-24, Chain duyệt)

> Trả lời 2 câu hỏi treo ở §7al, dựa trên: (1) rà lại quy định hiện hành (web, không chỉ `docs/legal/`
> cũ), (2) tham khảo cách Long Châu/Pharmacity và các phần mềm nhà thuốc phổ biến (MISA eShop, Sapo,
> VNPT Pharmacy) vận hành thật. Đây LÀ quyết định nghiệp vụ tự chốt dưới full-auto (rule #3), Chain đã
> duyệt trực tiếp — không phải GĐ tự ý không xin phép.

**Căn cứ pháp lý (đã kiểm chứng, không suy đoán):** TT11/2025 (đã có ở `docs/legal/`) chỉ bắt nhà
thuốc **kết nối/cập nhật dữ liệu real-time** lên hệ thống thông tin dược (từ 1/1/2026) — đã làm xong
qua QĐ540/`NationalSyncLog`. **Không có văn bản nào** bắt nhà thuốc bán lẻ lập báo cáo định kỳ hay
dashboard thống kê nộp cơ quan quản lý (khớp đính chính docs/13 #21 — Phụ lục X/XI TT20/2017 không
áp dụng bán lẻ). Do đó rủi ro pháp lý của cả 2 module = **0** — thuần túy là công cụ quản trị nội bộ,
sai thì chỉ tốn công sửa lại, không phải rủi ro tuân thủ.

**Căn cứ thực tiễn ngành:** Long Châu dùng AI/big data dự báo real-time theo khu vực+nhóm sản phẩm
qua hệ thống USee riêng (giảm stockout >70%) — vượt quá quy mô/hạ tầng hiện tại của dự án này, không
sao chép nguyên bản. Các phần mềm nhà thuốc phổ biến (MISA eShop, Sapo, VNPT Pharmacy) đều có báo cáo
doanh thu theo ngày/nhân viên/chi nhánh + cảnh báo cận date + tồn kho theo lô — đây là mức MVP hợp lý
để bắt đầu.

### Module `analytics` (v1)

| Hạng mục | Quyết định |
|---|---|
| Cấp độ dự báo | Theo **thuốc × chi nhánh** (không phải hoạt chất — PO nháp cần trỏ đúng thuốc/NCC) |
| Phương pháp v1 | Trung bình trượt 90 ngày + mốc tái đặt hàng = (vận tốc bán bình quân/ngày × lead-time NCC) + tồn an toàn. KHÔNG làm AI/ML thật ở v1 |
| Đề xuất nhập | Sinh **PO nháp** trong `procurement` khi tồn dự kiến < mốc tái đặt — không tự gửi NCC, người duyệt (giữ triết lý "cảnh báo không chặn" đã dùng cho tương tác/dị ứng thuốc) |
| Dashboard đầu | Doanh thu theo ngày/chi nhánh · top thuốc bán chạy · số cảnh báo cận date+tồn thấp · số PO nháp chờ duyệt |
| Hoãn v2 | Phát hiện bất thường (doanh thu tụt, tồn quay chậm) + yếu tố mùa vụ/dịch bệnh — cần nhiều dữ liệu lịch sử hơn hệ thống hiện có |
| Model giao | **Opus** (thiết kế mới hoàn toàn + cross-module thật `sales`/`inventory` → `procurement`) |

### Module `report xuất khẩu`

| Hạng mục | Quyết định |
|---|---|
| Nội dung đợt 1 | Doanh thu (ngày/tuần/tháng, theo chi nhánh/nhân viên) + tồn kho hiện tại theo lô/HSD |
| Nội dung đợt 2 | Top thuốc bán chạy + xuất `ControlledLedgerEntry` (dữ liệu đã có từ Compliance C.1–C.5) |
| Định dạng | CSV (tái dùng `core/audit/csv_export.py` vừa dựng ở §7al) — Excel/PDF để sau nếu cần |
| Quyền | Tái dùng `sales.read`/`inventory.read` hiện có — KHÔNG tạo quyền mới (không phải dữ liệu nhạy cảm hơn UI đã hiển thị) |
| Model giao | **Sonnet** (tái dùng khuôn CSV đã có, không phải thiết kế mới) |

**Thứ tự triển khai:** `report xuất khẩu` (Sonnet) trước — nhanh, rủi ro thấp; đợi commit xong mới mở
`analytics` (Opus) — tránh 2 agent cùng chạy migration/commit song song trên cùng git tree + Postgres
sống (rủi ro đã lường trước ở phiên audit dashboard).

---

## 7an. `report xuất khẩu` đợt 1 XONG (Sonnet, 2026-07-24) — đợt 2 + `analytics` còn nợ

> Phiên Sonnet, làm đúng 1/2 mục Sprint 7 còn treo (§7am) — **KHÔNG đụng `analytics`**, để dành phiên
> Opus riêng như đã chốt. Docker đã Up (healthy) từ đầu phiên (Claude không cần bật lại — khác các
> phiên trước). HEAD lúc bắt đầu `a9fdf37`, git sạch.

### Đợt 1 (bắt buộc) — làm xong cả 2

| Report | Nội dung |
|---|---|
| Doanh thu | Gom theo ngày/tuần/tháng (`granularity`), lọc chi nhánh tùy chọn, theo tiền tệ — `GET /reports/revenue/export` |
| Tồn kho | Theo lô + HSD, sắp HSD gần nhất trước, lọc chi nhánh tùy chọn, tenant-wide mặc định — `GET /reports/inventory/stock/export` |

**Đợt 2 (top thuốc bán chạy + xuất `ControlledLedgerEntry`) KHÔNG làm** — đúng chỉ đạo "chỉ làm nếu
đợt 1 xong sớm và còn dư sức, không bắt buộc". Đợt 1 đã dùng phần lớn ngân sách phiên cho thiết kế +
live-test; ghi rõ là nợ, không phải "xong hết Sprint 7 report".

### Điều chỉnh kỹ thuật so với giả định ban đầu (ghi rõ theo tinh thần "GĐ tự quyết, ghi lại")

| # | Giả định ban đầu | Thực tế/điều chỉnh | Vì sao |
|---|---|---|---|
| 1 | Lọc doanh thu "theo chi nhánh và/hoặc nhân viên bán hàng" | **Bỏ lọc theo nhân viên bán hàng** — chỉ còn lọc theo chi nhánh | `SalesOrder`/`sales_orders` **không có cột** actor/thu ngân nào được lưu (đã đọc `domain/entities.py`, `infrastructure/models.py` xác nhận). Người hoàn tất đơn chỉ có trong audit trail (`AuditEntry.actor_user_id`, `target_type="sale"`) — đây là bề mặt mục đích **tuân thủ** (ai đọc/ghi gì), không phải nguồn dữ liệu nghiệp vụ chung, và không có index trên `target_id` để join hiệu quả với `sales_orders`. Thêm cột `sold_by_user_id` mới là thay đổi schema/nghiệp vụ (ai được coi là "người bán" khi có nhiều thao tác trên 1 đơn?) — vượt phạm vi "chỉ đọc dữ liệu có sẵn" của phiên này. **Cần Chain quyết định hướng** nếu muốn có lọc này: (a) thêm cột vào `sales_orders` (schema change, câu hỏi nghiệp vụ đi kèm), hoặc (b) chấp nhận join qua audit trail (rủi ro hiệu năng + lẫn mục đích compliance/business đã cố tình tách bạch trong dự án) |
| 2 | "Theo ngày/tuần/tháng" ngụ ý `GROUP BY` trong SQL | Gom nhóm chạy **ở Python** (bộ đệm nhỏ theo bucket `(period, branch, currency)`), không dùng `date_trunc` | `date_trunc` là hàm Postgres-only; models của dự án giữ nguyên tắc cross-dialect (Postgres prod + SQLite test, ghi rõ trong docstring `models.py`). Repo vẫn phân trang 500 đơn/lượt ở tầng SQL (bộ nhớ phẳng phía dữ liệu thô); chỉ có bộ gom-nhóm (nhỏ, bị chặn bởi số period×branch×currency, không phải số đơn) sống trong RAM |
| 3 | Không nói rõ doanh thu tính gộp hay trừ hàng trả | **Tính gộp tại thời điểm bán** (không trừ theo return sau đó) | Đơn giản, đúng nghĩa "doanh thu ghi nhận lúc bán" — MVP hợp lý; nếu Chain muốn "doanh thu ròng sau trả hàng" là một report khác, cần quyết định thêm |
| 4 | Tồn kho lọc theo chi nhánh (ngụ ý phạm vi giống các read khác của `inventory`) | **Tenant-wide mặc định** (branch_id lọc tùy chọn) — khác hẳn `on_hand`/`list_near_expiry` vốn luôn khoá theo `ctx.branch_id` | Đây là bề mặt báo cáo cấp chuỗi (như audit dashboard), không phải thao tác nghiệp vụ hàng ngày của 1 chi nhánh. Khớp với cách `sales.read` qua `get_sale`/`by_client_uuid` cũng đã đọc xuyên chi nhánh (chỉ lọc theo `tenant_id`) |

### Kiến trúc đã chọn

- **Không tạo module `reports` mới** — thêm 2 phương thức đọc trực tiếp vào `SalesService`
  (`revenue_report_rows`) và `InventoryService` (`stock_report_rows`), mỗi service tự viết SQL/aggregation
  trên bảng nó sở hữu (đúng khuôn `list_near_expiry`/`list_reconciliations` đã có). Composition root
  (`api/v1/reports.py`, giống `cross_module.py` nhưng cho đọc thay vì phản ứng sự kiện) gọi thẳng cả 2
  service (đã đăng ký sẵn trong container) để dựng 2 endpoint — `sales` và `inventory` **không** import
  lẫn nhau (import-linter xác nhận 13/0 KEPT suốt 3 bước).
- CSV shaping thuần theo đúng khuôn `core/audit/csv_export.py` (§7al): mỗi module một
  `*_CSV_HEADER` tuple + `*_to_row(...) -> list[str]` (`sales/application/csv_export.py`,
  `inventory/application/csv_export.py`).
- **Tách + tái dùng streaming helper:** `core/http.py` có `csv_stream_body(header, rows)` — kéo ra từ
  `_csv_body` cũ của `audit_dashboard.py` để mọi export CSV trong dự án dùng chung 1 chỗ. `audit_dashboard.py`
  chuyển sang gọi hàm này (hành vi giữ nguyên, 11 e2e test dashboard cũ vẫn xanh không sửa).
- Không quyền mới: `sales.read` cho report doanh thu, `inventory.read` cho report tồn kho (đúng chỉ đạo
  §7am — không phải dữ liệu nhạy cảm hơn UI hiện tại). Vì vậy **không cần** `seeds.run`/reseed role.
- Không migration (chỉ đọc dữ liệu có sẵn qua `JOIN`/`GROUP BY` trên bảng cũ, không thêm bảng/cột).

### 3 commit (stepped-commit, mỗi bước 4 cổng xanh cô lập bằng `git stash`)

| Commit | Bước | Nội dung |
|--------|------|----------|
| `4c45f88` | 1/3 đọc-thuần | `OrderRevenueRow`+`SalesRepository.completed_in_range` · `BatchStockRow`+`BatchRepository.stock_report` · DTO (`RevenueGranularity`/`RevenueRow`/`StockReportItem`) · CSV shaper thuần 2 module |
| `be9ada9` | 2/3 app | `SalesService.revenue_report_rows` (gom nhóm Python, phân trang 500) · `InventoryService.stock_report_rows` (phân trang 500) — cả 2 kiểm quyền+validate EAGER trước khi trả generator, giống `AuditDashboardService.export_rows` |
| `414269d` | 3/3 interface | `core/http.py:csv_stream_body` (tách từ audit dashboard) · `api/v1/reports.py` 2 endpoint · đăng ký router · 11 e2e test |

### Bằng chứng 4 cổng (mỗi commit kiểm cô lập bằng `git stash push --include-untracked` phần bước sau)

| Cổng | Kết quả |
|------|---------|
| ruff check + format --check | sạch (325 file) |
| import-linter | **13/0 KEPT** — không thêm/sửa contract, `sales`/`inventory` vẫn độc lập |
| mypy --strict | **228 file**, 0 lỗi |
| pytest | **690** (679 cũ + 11 mới), EXIT=0 cả 3 bước lẫn trạng thái cuối |

### Xác nhận trên Postgres sống (tinh thần kỷ luật #7 — không đổi permission/seed nhưng vẫn xác nhận thật
vì đây là SQL join/aggregate mới, hành vi có thể khác giữa SQLite (pytest) và Postgres (prod))

- `alembic current` = `0020_audit_target_type_idx` — **không migration mới**, khớp dự đoán ban đầu.
- Bootstrap tenant tạm (`Smoke Test Report Sprint7`) trên Postgres sống qua `uvicorn` thật (không phải
  TestClient/SQLite): login thật → 2 đơn bán (100.000đ + 30.000đ qua `POST /sales`) → 1 lô nhập 25 đơn vị
  (`POST /inventory/receive`) → gọi `GET /reports/revenue/export` và `GET /reports/inventory/stock/export`.
- Đối chiếu bằng SQL trực tiếp (`SUM(quantity*unit_price)` trên `sales_orders`/`sale_lines`): **130000.00000
  khớp 100% với CSV trả về**, `order_count=2` đúng. Tồn kho CSV đúng lô/HSD/số lượng nhập.
- **Dọn dữ liệu thử xong**, xác nhận lại bằng SQL = 0 dòng còn lại trên: `tenants`, `branches`, `users`,
  `sales_orders` (cascade `sale_lines`/`sale_payments`), `product_batches`, `stock_balances`,
  `stock_movements`, `audit_logs`, `event_outbox`, `national_sync_logs`, `user_roles`, `refresh_tokens`.
  (`roles` không xoá gì — role hệ thống trong DB dev này là hàng chia sẻ giữa các tenant từ trước, không
  phải dữ liệu phiên này tạo ra; xác nhận `system_roles_created=0`/`updated=0` ở log bootstrap khớp.)

### ⏸️ ĐIỂM DỪNG PHIÊN (2026-07-24) — report đợt 1 xong, đợt 2 + `analytics` còn nợ

| Hạng mục | Trạng thái (xác nhận bằng lệnh) |
|----------|--------------------------------|
| Git | HEAD `414269d`, cây sạch (3 commit trong phiên) |
| Docker | `postgres` + `redis` **Up (healthy)** suốt phiên — không cần bật lại |
| Migration | Không đổi, head vẫn `0020_audit_target_type_idx` |
| 4 cổng | ruff/format sạch · import-linter 13/0 · mypy --strict 228 file · pytest **690** EXIT=0 |
| Dữ liệu thử | Đã tạo trên Postgres sống để smoke-test, đã xoá sạch, xác nhận lại = 0 dòng |
| Tiến trình nền | 0 treo (uvicorn smoke-test đã kill) |

**Nợ lại cho phiên sau:**

| Mục | Trạng thái |
|-----|-----------|
| Report đợt 2 (top thuốc bán chạy + xuất `ControlledLedgerEntry`) | Chưa làm — không bắt buộc theo chỉ đạo, nhưng vẫn là nợ nếu Chain muốn đủ Sprint 7 report |
| Lọc doanh thu theo nhân viên bán hàng | Chặn ở thiếu dữ liệu (không có cột lưu), cần Chain quyết định hướng — xem bảng điều chỉnh #1 ở trên |
| Module `analytics` | **KHÔNG đụng** — giao Opus riêng như đã chốt §7am (thiết kế mới + cross-module `sales`/`inventory`→`procurement`) |

---

## 7ao. Lọc doanh thu theo nhân viên bán — cột `sold_by_user_id` XONG (Opus, 2026-07-25)

> Gỡ nợ còn treo ở §7an ("lọc theo nhân viên bán hàng — chặn ở thiếu dữ liệu"). Chain duyệt **PA (a)**
> ngày 2026-07-25: thêm cột lưu người bán, ghi từ JWT lúc chốt đơn; báo cáo nhân viên tính từ ngày
> triển khai, đơn cũ để `None`. GĐ đề xuất (a) vì MISA/Sapo/VNPT đều báo cáo theo nhân viên + là cơ sở
> tính hoa hồng về sau; rủi ro pháp lý = 0 (dữ liệu nội bộ). Chain gật.

### Đã làm — 3 commit stepped

| Bước | Commit | Nội dung |
|------|--------|----------|
| 1/3 domain | `cd98f7b` | `SalesOrder.sold_by_user_id` (nullable vĩnh viễn) + trường trên `OrderRevenueRow`; 2 unit test |
| 2/3 app/infra/mig | `8771234` | `complete_sale` ghi `ctx.user_id`; ORM cột+index; mappers; `repo.completed_in_range` nhận filter; `revenue_report_rows` thêm tham số; migration `0021` |
| 3/3 interface | `b76a99b` | `GET /reports/revenue/export?sold_by_user_id=…`; 3 e2e |

### Quyết định thiết kế tự chốt (full-auto)

| Điểm | Chọn | Vì sao |
|------|------|--------|
| Kiểu cột | `UUID | None`, plain (không FK tới `iam.users`) | Giữ module-independence, đúng khuôn `customer_id`/`prescription_ref` đã có |
| Đơn cũ / sync offline | `None`, KHÔNG rớt khỏi tổng | Doanh thu tổng không được co lại vì thiếu tên NV; báo cáo theo-NV đơn giản không thấy đơn cũ |
| Ý nghĩa filter rỗng | `None` = **mọi NV**, không phải "đơn không rõ NV" | Không mở đường tách riêng đơn vô danh — tránh lộ khe hiểu nhầm |
| `RevenueRow`/CSV | **Không đổi** — chỉ thêm *filter*, không thêm *chiều nhóm* | §7am/§7an nói "lọc theo nhân viên" (filter), không phải cột mới trong file; muốn per-NV thì gọi lọc từng người |
| Quyền | Tái dùng `sales.read`, KHÔNG quyền mới | Không nhạy cảm hơn UI POS hiện có (khớp §7am) |

### Xác nhận bằng lệnh thật

| Cổng / kiểm chứng | Kết quả |
|---|---|
| 4 cổng | ruff/format sạch · import-linter **13/0** · mypy --strict **228** file · pytest **695** EXIT=0 |
| Migration `0021` trên PG sống | `alembic upgrade head` chạy; `\d sales_orders` có `sold_by_user_id uuid` + index `ix_sales_orders_sold_by_user_id` (xác nhận qua `psql`); downgrade xoá cột → count=0, upgrade lại sạch; `alembic check` không drift |
| Backup trước migration | `~/backup_pre_migration_20260725_0239.sql` |
| Kỷ luật #7 (seed/permission) | **Không áp dụng** — thay đổi này là thêm cột, KHÔNG đụng seed data hay permission (không đi nhánh insert-vs-update của role/quyền). Ghi rõ để không nhầm là bỏ sót |

### Còn nợ (không đổi so với §7an)

| Mục | Trạng thái |
|-----|-----------|
| Report đợt 2 (top thuốc + `ControlledLedgerEntry`) | Chưa làm — không bắt buộc |
| Module `analytics` | **KHÔNG đụng** — chờ phiên Opus riêng (§7am) |

---

## 7ap. Module `analytics` XONG — Sprint 7 ĐÓNG (2026-07-25, Opus full-auto)

> Phiên bắt đầu ~06:00, **cúp điện lúc ~07:00 cắt ngang giữa bước 7/8**. Phiên này (Chain ủy quyền
> GĐ rà lại + hoàn thiện) nối tiếp: xác nhận việc dở, chạy cổng, phát hiện và vá 3 lỗi, đóng sprint.
> Thiết kế gốc: `docs/features/analytics/00_DESIGN_PROPOSAL.md` (Chain duyệt Q1–Q4 + quyền,
> 2026-07-25). Yêu cầu nghiệp vụ: §7am.

### Trạng thái lúc cúp điện vs sau khi rà

| Hạng mục | Lúc cúp điện (07:00) | Sau phiên rà |
|---|---|---|
| Bước 1–6/8 | Đã commit (`9b335b0`→`96ef714`) | Giữ nguyên |
| Bước 7/8 (wiring + quyền + e2e) | Viết xong, **chưa chạy cổng, chưa commit** | Chạy cổng → commit `a40de7e` |
| Cổng ruff tại HEAD | **ĐỎ** từ commit bước 4/8 (2 lỗi C408 lọt qua) | Vá, commit `0bfb41b` |
| Container docker | Chết theo điện | Đã bật lại, healthy |
| Migration `0022` | Đã áp lên PG trước khi mất điện | Xác nhận bằng `alembic current` |

### 3 lỗi phát hiện trong phiên rà (không phải do cúp điện)

| # | Lỗi | Mức | Vá tại |
|---|---|---|---|
| 1 | Cổng ruff đỏ tại HEAD từ bước 4/8 — commit lọt qua, vi phạm kỷ luật #1 | Thấp (chỉ lint test) | `0bfb41b` |
| 2 | **`audit_logs.action` là varchar(32) trong khi 3 giá trị `AuditAction` dài 33–36 ký tự** → Postgres 500. SQLite (nền test) bỏ qua độ dài nên **734 test vẫn xanh**. 2/3 action có từ §7ab/§7ad — **bug sống trên deployment thật từ trước, không phải do analytics** | **Cao** — audit là mặt tuân thủ | `77faa5e` (mig `0023` nới lên 64 + test đọc độ rộng cột từ model để chặn tái diễn) |
| 3 | **PO nháp ghi bằng system-user**, lệch thiết kế Chain đã duyệt (§6 bản thiết kế: phải dùng identity người bấm). Hệ quả: role chỉ có `analytics.reorder.run` mà không có `procurement.po.create` vẫn tạo được PO qua ngả analytics — **cửa sau leo thang quyền** | Trung bình–cao | `97a4560` (port nhận `actor_user_id`+`actor_permissions`; 4 adapter ĐỌC vẫn giữ system identity) |

> Lỗi #2 là ca mẫu cho kỷ luật #7: nếu chỉ tin pytest thì đã commit và đẩy đi một đường audit gãy
> trên Postgres. Nó **chỉ lộ ra khi bấm materialize thật bằng token thật trên DB có dữ liệu**.

### Kiến trúc đã dựng

| Lớp | Nội dung |
|---|---|
| domain | `ReorderSuggestion` (+`SuggestionStatus`), công thức reorder thuần, 5 read/write port (Protocol) |
| application | `AnalyticsService`: `run_reorder` · `list_suggestions` · `materialize` · `dismiss` · `dashboard` |
| infrastructure | Repo SQLAlchemy + bảng `reorder_suggestions` (mig `0022`) — dữ liệu RIÊNG của analytics |
| interface | Router `/api/v1/analytics/*` + schemas |
| composition root | `api/v1/analytics_wiring.py` — 5 adapter bọc `sales`/`inventory`/`procurement`. **`analytics` không import module nghiệp vụ nào**; 2 contract import-linter mới khoá điều đó (16 contract, 0 broken) |

**Công thức v1 (đúng §7am):** vận tốc = trung bình trượt 90 ngày; mốc tái đặt = vận tốc × lead-time
(7 ngày) + tồn an toàn (3 ngày); tồn ≤ mốc ⇒ đề xuất. NCC = NCC gần nhất từng cấp thuốc đó; chưa
từng mua ⇒ `can_materialize=false`, không vỡ. Chạy **on-demand**.

### Quyết định tự chốt trong phiên (full-auto — Chain đọc lướt sau)

| # | Quyết định | Lý do |
|---|---|---|
| 1 | Nới `audit_logs.action` lên 64 thay vì đổi tên 3 action cho ngắn | Đổi tên action là đổi từ vựng vết audit đã ghi trên DB thật; nới cột không mất dữ liệu, `target_type`/`target_id` vốn đã 64 |
| 2 | `downgrade` của mig `0023` thu về 32 và **để nó nổ** nếu đã có dòng dài | Audit append-only — thà rollback fail còn hơn cắt cụt vết tuân thủ |
| 3 | Sửa đường ghi PO nháp sang identity người bấm dù wiring cũ đã có docstring biện minh cho system-user | Thiết kế Chain duyệt nói rõ ngược lại, và cách cũ mở cửa hậu leo thang quyền |
| 4 | Gộp bước 8/8 (e2e + smoke live) vào commit bước 7 | File e2e đã do phiên trước viết sẵn, nằm chung trong đống chưa commit; tách ra sẽ là commit rỗng nghĩa |
| 5 | Đóng Sprint 7 dù report đợt 2 chưa làm | Đợt 2 đã được ghi "không bắt buộc" từ §7am/§7an; ghi thành nợ mang sang, không tính vào DoD |

### Kỷ luật #7 — đã chạy thật, không chỉ pytest

| Việc | Kết quả |
|---|---|
| `python -m seeds.run` trên PG có dữ liệu | Idempotent (`created=0, updated=0` — phiên trước đã sync trước khi mất điện) |
| Verify bằng SQL | Đúng 3 role (`system_admin`/`chain_pharmacist`/`branch_pharmacist`) có `analytics.read`+`analytics.reorder.run`; `cashier`/`warehouse` **không** có |
| Round-trip API bằng token thật | dashboard 200 (doanh thu khớp dữ liệu bán thật) · reorder/run 200 · materialize 200 sinh PO **DRAFT** thật (`unit_price=0`) · materialize khi chưa có NCC → **409 có kiểm soát**, không 500 · chạy lại run không nhân đôi dòng |
| Audit trên PG thật | `ANALYTICS_REORDER_RUN` + `ANALYTICS_SUGGESTION_MATERIALIZED` ghi đúng, `actor_user_id` = **người bấm thật**, không phải system-user |
| Migration `0023` | live upgrade→downgrade→upgrade sạch, `alembic check` không drift. Backup `~/backup_pre_migration_20260725_0938.sql` |
| Dọn dữ liệu thử | NCC thử + 3 PO + toàn bộ `reorder_suggestions` đã xoá; giữ lại tenant demo + vết audit (append-only, không xoá) |

### Cổng chất lượng cuối phiên

| Cổng | Kết quả |
|---|---|
| `ruff check` + `format --check` | sạch (351 file) |
| `mypy` (strict) | 245 file, 0 lỗi |
| `import-linter` | **16 contract / 0 broken** |
| `pytest` | **734 passed** |
| alembic | `0001`→`0023`, head khớp, không drift |

### Còn nợ sau khi đóng Sprint 7

| Mục | Trạng thái |
|-----|-----------|
| Report đợt 2 (top thuốc + xuất `ControlledLedgerEntry`) | Chưa làm — không bắt buộc từ đầu |
| Retry đẩy DAV của `NationalSyncService` lên outbox | Vẫn best-effort riêng (ghi từ §7ai) |
| Cảnh báo/khoá tồn-âm khi outbox chạy async | Nợ kỹ thuật, xem `TODO.md` |
| `analytics` v2 | Phát hiện bất thường · mùa vụ/dịch bệnh · override lead-time theo tenant · chạy nền định kỳ |
| Frontend cho analytics | Chưa có màn hình — backend-only như mọi module khác |

---

## 7aq. Rà toàn bộ độ rộng cột `varchar` — Chain duyệt sau §7ap (2026-07-25)

> GĐ đề xuất cuối §7ap, Chain duyệt ngay. Đích: bịt nốt loại điểm mù mà bug
> `audit_logs.action` vừa lộ ra — **cột hẹp hơn dữ liệu thật, mà SQLite không bắt được**.

### Phạm vi rà: 88 cột `varchar` có giới hạn trên 40 bảng

| Nhóm dữ liệu đổ vào cột | Cách kiểm | Kết quả |
|---|---|---|
| 24 enum chuỗi | So `max(len(value))` với độ rộng cột | ✅ Không cột nào tràn (sau mig `0023`). Sát nhất: `InteractionSeverity` 15/16 và `SyncStatus` 7/8 — **dư đúng 1 ký tự** |
| Permission (`role_permissions` 64) | `max(ALL_PERMISSIONS)` = 27 | ✅ dư nhiều |
| Role code (`roles.code` 64) | dài nhất `branch_pharmacist` = 17 | ✅ |
| Event type (`event_outbox` 100) | 14 event, dài nhất `StockShortfallDetected` = 22 | ✅ |
| `audit_logs.target_type` (64) | Chuỗi literal tại call site, dài nhất `stock_reconciliation_needed` = 27 | ✅ |
| `stock_movements.ref_type` (32) | literal, dài nhất 4 | ✅ |
| Các hash | bcrypt 60/128 · sha256 hex **64/64** | ⚠️ Đúng khít, dư 0 — đổi sang sha512 hoặc thêm tiền tố `sha256:` là gãy |
| **Input người dùng** | Thử thật bằng token thật | ❌ **Thủng hệ thống — xem dưới** |

### Lỗi tìm được: input người dùng không bị chặn độ dài ở cổng vào

Chỉ **17/159** trường chuỗi trong schema có `max_length`. Chuỗi dài hơn cột đi thẳng
xuống Postgres → `StringDataRightTruncationError` → **500**. Xác nhận trên PG thật, 6/7
endpoint thử đều 500:

| Request thử | Cột | Trước | Sau vá |
|---|---|---|---|
| `POST /customers` `full_name` 300 ký tự | 255 | **500** | 422 |
| `POST /customers` `phone` 40 | 32 | **500** | 422 |
| `POST /users` `email` 405 | 320 | **500** | 422 |
| `POST /users` `full_name` 300 | 255 | **500** | 422 |
| `POST /drugs` `name` 300 | 255 | **500** | 422 |
| `POST /suppliers` `phone` 40 | 32 | **500** | 422 |
| `POST /suppliers` `name` 300 | 255 | 422 *(vốn đã chặn)* | 422 |
| `POST /customers` `full_name` **đúng 255** | 255 | — | **201** (không chặn thừa) |

### Cách vá + 3 quyết định tự chốt

| # | Quyết định | Lý do |
|---|---|---|
| 1 | Chặn ở **tầng schema** (thêm `max_length` cho 29 trường / 8 module), KHÔNG bắt `DBAPIError` rồi đổi thành 4xx | Bắt kiểu đó sẽ **nuốt luôn** chuỗi quá dài do chính hệ thống sinh ra — mà đúng một ca như thế (`audit_logs.action`) chỉ lộ ra được vì nó nổ thành 500. Giữ cho lỗi nội bộ vẫn ồn |
| 2 | **Không** chặn mật khẩu / refresh token | Không lưu thô (bcrypt ra 60 ký tự, sha256 ra 64) nên không có cột để tràn. Chặn trên còn có hại: khoá cửa người đặt mật khẩu rất dài |
| 3 | **Không** chặn các cột `Text` (`note`, `diagnosis`, `address`, `instructions`) | Postgres không giới hạn `Text` → không có ca truncation. *Nhưng đây là nợ còn mở, xem dưới* |

**2 cổng chặn tái diễn:** (1) test cấu trúc — mọi trường chuỗi request phải có
`max_length` **hoặc** nằm trong danh sách miễn trừ **có ghi lý do**, kèm test phụ bắt
dòng miễn trừ đã chết; (2) test hành vi — đúng các endpoint từng 500 nay phải trả 422.

### Nợ còn mở sau đợt rà này

| Mục | Ghi chú |
|---|---|
| Cột `Text` không giới hạn đầu vào | Client vẫn post được `note`/`diagnosis`/`address` cỡ vài MB. Không phải 500, nhưng là đường DoS rẻ tiền. **Cần Chain chốt giới hạn nghiệp vụ** (bao nhiêu ký tự là hợp lý cho 1 ghi chú dị ứng?) — không tự đặt |
| 2 cột dư đúng 1 ký tự | `drug_interactions.severity` 16 và `national_sync_logs.status` 8. Thêm 1 giá trị enum dài hơn là gãy; test guard hiện chỉ phủ `AuditAction`, chưa phủ toàn bộ enum↔cột |
| Hash sha256 khít 64/64 | Đổi thuật toán băm hoặc thêm tiền tố là gãy ngay. Chưa có test chặn |

---

## 7ar. TT 18/2026/TT-BYT thay TT 20/2017 — Bước 1/3 (chỉ tài liệu) XONG (2026-07-25)

> Chain thả bookmark `Thông-tư-18-2026-TT-BYT.docx`, yêu cầu chuẩn bị đủ biểu mẫu cho phần
> "báo cáo thuốc danh mục đặc biệt đã bỏ qua trước đó", **chưa code, hỏi trình tự để duyệt**.

### Phát hiện

| # | Việc | Chi tiết |
|---|---|---|
| 1 | **TT20/2017 đã hết hiệu lực từ 16/7/2026** | TT18 Điều 16.4 bãi bỏ TT20/2017 + TT27/2024. Mục C của `docs/13` (spec đã khóa) đang trích văn bản chết **9 ngày** |
| 2 | Báo cáo định kỳ **vẫn không áp cho bán lẻ** | TT18 Điều 7 nằm ở Chương II, Điều 1.2 giới hạn Chương II cho cơ sở dược **không vì mục đích thương mại**. Kết luận đính chính 2026-07-24 không sai, chỉ đổi số mẫu (PL X/XI → **IX/X/XI**) |
| 3 | **Nhưng hạ mức chắc chắn** | Nghĩa vụ báo cáo của cơ sở **kinh doanh** dược nằm ở **NĐ 163/2025** (NĐ 54/2017 Điều 47 cũ), không nằm ở Thông tư. Chưa có NĐ163 ⇒ đọc là **"chưa kết luận được"**, không phải "không áp dụng" |
| 4 | **Cái thật sự bỏ sót không phải báo cáo** | (a) **Sổ PL XVI** — Điều 12.3 buộc bán lẻ lập sổ xuất/nhập/tồn cho thuốc **dạng phối hợp** + thuốc độc + danh mục cấm; **TT20 không có nghĩa vụ này**. (b) **Biên bản nhận lại PL XVIII** — trước bị gạt "ngoài phạm vi". (c) **Điều 15.1.d** buộc ký sổ điện tử bằng **chữ ký số/xác nhận điện tử** — hệ thống không có gì |
| 5 | Lưu trữ **mất căn cứ** | "≥2 năm sau hạn dùng" (TT20 Điều 18.1) biến mất; TT18 Điều 15.3 giao cho **TT 33/2025** + **TT 26/2025** — chưa có văn bản. Giữ hành vi hiện tại làm mức sàn |
| 6 | Số hiệu phụ lục dịch hết | PL XX→**XVIII**, PL XXI→**XIX** (PL XIX **thêm cột** số ĐKLH/GPNK); phân loại từ Điều 3 → **PL VII** |
| 7 | Danh mục hoạt chất | PL I 42 GN · PL II **72** HT (thêm **Carisoprodol, Etomidate** là hướng thần **từ 01/6/2026**) · PL III 8 TC + giới hạn nồng độ PL IV/V/VI |

### Quyết định Chain chốt cùng ngày

| # | Câu hỏi | Chốt |
|---|---|---|
| 1 | Phạm vi đợt này | **Bước 1–3** (tài liệu → seed danh mục → sổ PL XVI). Bước 4–6 đợt sau |
| 2 | Chữ ký số (Điều 15.1.d) | **Thiết kế trước, chưa code** |
| 3 | Spec đã khóa | **Sửa tại chỗ + changelog** (mục H cuối `docs/13`), không tách file v2 |
| 4 | Có bán thuốc độc / danh mục cấm? | **KHÔNG** ⇒ bước 3 chỉ dựng khung enum, không seed QĐ 3235 / danh mục thuốc độc |

### Đã làm ở bước 1 (chỉ tài liệu, không chạm code)

| File | Thay đổi |
|---|---|
| `docs/legal/Thông-tư-18-2026-TT-BYT.docx` | Copy từ bookmark vào kho pháp lý |
| `docs/legal/Thông-tư-18-2026-TT-BYT.SUMMARY.md` | Mới — trích nguyên văn cột của 5 biểu mẫu bán lẻ, bảng đối chiếu 19 phụ lục TT20↔TT18, 9 tiêu chí phân loại, bảng giới hạn nồng độ, 6 văn bản còn thiếu |
| `docs/13_COMPLIANCE_SPEC.md` | Mục C viết lại theo TT18; **thêm C.5** (sổ điện tử/chữ ký số) và **C.6** (biên bản nhận lại); enum thêm `THUOC_DOC`, `DANH_MUC_CAM`; ledger cần `book_type`; Traceability **#22–27**; changelog **mục H** |
| `docs/legal/README.md` | TT18 vào bảng tra (🔴), TT20 gạch "hết hiệu lực"; thêm 2 dòng việc chưa làm |
| `docs/features/tt18-kiem-soat-dac-biet/00_DE_XUAT_CAP_NHAT.md` | Mới — 6 bước, việc bị chặn, quyết định Chain, nhật ký thực thi |

### Bước 2 — seed danh mục pháp lý (2 commit)

| Commit | Nội dung |
|---|---|
| `8a4f49a` | Domain thuần: `ControlledSubstanceAppendix` + entity `ControlledSubstance` (ngưỡng PL IV/V/VI, `limit_note` cho 2 ngưỡng dạng câu điều kiện, `is_effective_on()` cho mốc riêng 01/6/2026) |
| `10691e7` | Bảng `controlled_substances` (mig `0024`, dùng chung không tenant-scoped) + `seeds/tt18_controlled_substances.py` **sinh tự động từ bản trích văn bản gốc**, không chép tay |

**Số liệu đã đối chiếu:** PL I 42 · PL II 72 · PL III 8 = **122 hoạt chất**; **62** chất có ngưỡng
(PL IV 13 · PL V 43 · PL VI 6) — khớp đủ, **không dòng ngưỡng nào mồ côi** (bẫy duy nhất: PL II ghi
`MEPROBAMATE`, PL V ghi `MEPROBAMAT`, đã map alias).

**Thử trên CSDL có dữ liệu sẵn (kỷ luật 7), xác nhận bằng SQL thật — không tin log:**

| Lần chạy | Kết quả |
|---|---|
| Lần đầu | `created=122`, đếm theo phụ lục 42/72/8 khớp |
| Ép nhánh cập nhật (sửa sai 2 dòng, xóa 1 dòng) | `created=1, updated=2` — TRAMADOL về đúng 37,5 mg, ETOMIDATE về đúng mốc 01/6/2026, tổng lại 122 |

Seed **có nhánh cập nhật**, không chỉ insert-nếu-thiếu — đúng bài học §7l: danh mục pháp lý sửa
ngưỡng thì deployment cũ phải được ghi đè, nếu không sẽ phân loại sai thuốc dạng phối hợp.

### Bước 3 — 2 mẫu sổ + kết xuất (2 commit)

| Commit | Nội dung |
|---|---|
| `be763d1` | Domain: enum **7 → 9 giá trị** (`THUOC_DOC`, `DANH_MUC_CAM`); `LedgerBookType` + `book_type_for()`; rule bán ra miễn thông tin khách hàng cho 2 nhóm mới (Điều 12.3 chỉ buộc sổ xuất/nhập/tồn) |
| `ea85d94` | Port `list_for_book()` + repo; `application/csv_export.py` (tồn lũy kế **reset theo từng thuốc** vì mẫu sổ bắt mỗi thuốc một sổ riêng); endpoint `GET /compliance/controlled-ledger/books/{book_type}/export` |

**3 quyết định tự chốt khi code:**

| # | Quyết định | Lý do |
|---|---|---|
| 1 | `book_type` **suy ra từ `category`**, KHÔNG lưu thành cột | Lưu thì có 2 nguồn sự thật cho cùng dữ kiện và lệch nhau được. Hệ quả tốt: bước 3 **không cần migration** |
| 2 | Route `books/...` khai báo **trước** `/{entry_id}` | FastAPI khớp theo thứ tự — để sau thì "books" bị bắt làm UUID, request kết xuất trả 422 thay vì file |
| 3 | Số lượng bỏ 0 thừa khi kết xuất (`100.000` → `100`, giữ `37.5`) | Sổ in ra để ký phải đọc như người ghi tay |

### Nợ phát sinh — KHÔNG tự làm, đã ghi rõ trong code lẫn tài liệu

| Nợ | Vì sao dừng |
|---|---|
| **Phần đầu sổ** (tên thuốc/nồng độ, số ĐKLH, đơn vị tính, nhà sản xuất) ⇒ CSV hiện là **phần bảng của sổ + `drug_id`**, chưa phải sổ hoàn chỉnh in ra ký | Trường thuộc `catalog`, phải mở rộng read-port `DrugMasterFacts` = **cross-module**, kỷ luật 2 buộc chờ duyệt |
| Tự động suy `category` từ công thức thuốc theo 9 tiêu chí PL VII | Cũng cross-module; ngoài 6 bước Chain đã duyệt |
| Xuất Excel đúng khuôn mẫu để in | Chưa ai yêu cầu — CSV mở được bằng Excel |
| Bước 4 (biên bản PL XVIII), 5 (kết xuất cuối ngày), 6 (chữ ký số) | Chain chốt để đợt sau; chữ ký số **chỉ thiết kế, chưa code** |

**Cổng chất lượng cuối mạch:** ruff · mypy --strict · import-linter (16 contract) · **pytest 782** ·
`alembic check` không drift.

### ⏸️ ĐÓNG PHIÊN 2026-07-25 — mạch TT18 bước 1–3 trọn vẹn

| Việc | Trạng thái |
|---|---|
| Bước 1–3 (tài liệu · 122 hoạt chất · sổ PL XVI + kết xuất CSV) | ✅ Xong, 5 commit `23ff6c1`→`ea85d94`, cây git sạch |
| Bước 6 — thiết kế ký sổ điện tử | ✅ Soạn xong (`92befaf`), **chờ Chain chọn A/B/C**. GĐ khuyến nghị **A** (xác nhận điện tử bằng tài khoản IAM + chuỗi hash): 0đ, không đổi thói quen dược sĩ, chuỗi hash dùng lại được nếu sau này phải nâng lên chữ ký số thật. Phát hiện then chốt: Điều 15.1.d cho **hai** lựa chọn — "kỹ thuật xác nhận điện tử" **hoặc** chữ ký số |
| Bước 4 (biên bản PL XVIII), 5 (kết xuất cuối ngày) | ⬜ Đợt sau. **Bước 4 không chờ văn bản nào** — nghĩa vụ đã rõ trong TT18, khởi động được ngay |
| NĐ 163/2025 · TT 33/2025 · TT 26/2025 | ❌ **Chưa tới máy.** Đã kiểm 2 lượt, quét cả máy: không file mới nào. Nhiều khả năng Chain đính kèm vào khung chat app Claude — file đó **không rơi xuống ổ đĩa** nên phiên CLI không đọc được. Cách chắc ăn: copy vào `/home/gau/Vault/00-Bookmark/` |
| Nhắc ghi sổ tay từ 16/7 | Chain chốt **không cần quan tâm** — khép lại, không nêu nữa |

**Việc đầu tiên phiên sau:** `ls /home/gau/Vault/00-Bookmark/` → có 3 văn bản thì trích và trả lời
2 câu còn treo (bán lẻ có phải báo cáo định kỳ không · thời hạn lưu trữ bao lâu); chưa có thì làm
bước 4 (biên bản nhận lại PL XVIII) vì nó độc lập hoàn toàn.

---

## 7as. Đọc xong NĐ163/2025 + TT33/2025 + TT26/2025 — ⭐ ĐẢO NGƯỢC KẾT LUẬN BÁO CÁO ĐỊNH KỲ (2026-07-25, GĐ dưới ủy quyền toàn quyền)

> Chain chép 3 văn bản còn thiếu lên bookmark, ủy quyền toàn quyền cho GĐ tiếp tục chỉ đạo code.

### 🔴 Phát hiện quan trọng nhất — KHÔNG PHẢI CODE, LÀ VIỆC THẬT NGOÀI ĐỜI

**NĐ 163/2025/NĐ-CP Điều 35.2** (hiệu lực **01/7/2025**): cơ sở **bán buôn, bán lẻ, tổ chức chuỗi
nhà thuốc** **PHẢI** báo cáo định kỳ **6 tháng** (trước 15/7) và **năm** (trước 15/01) về xuất/nhập/
tồn/sử dụng GN/HT/TC + thuốc dạng phối hợp, theo **Mẫu số 06 Phụ lục II NĐ163**, gửi **UBND cấp
tỉnh** nơi trụ sở chính. Không báo cáo đúng hạn (Điều 35.5) → bị ngừng tiếp nhận hồ sơ mua/XNK
thuốc cho tới khi báo cáo đầy đủ.

**Đây đảo ngược hoàn toàn** kết luận đã ghi 2 lần trước đó (2026-07-24 và đầu 2026-07-25): "bán lẻ
không phải báo cáo định kỳ" — kết luận đó **đúng riêng với TT18** (Điều 7 chỉ áp phần phi thương
mại) nhưng **sai khi coi đó là câu trả lời đầy đủ** — nghĩa vụ thật nằm ở Nghị định, không phải
Thông tư, đúng như nghi ngờ đã ghi ở `docs/legal/README.md` trước khi có văn bản.

⚠️ **NĐ163 không có lộ trình ân hạn cho khoản 2 Điều 35** (Điều 124 chỉ áp lộ trình cho khoản 1 —
sản xuất/XNK). Tính đến hôm nay đã qua **3 kỳ hạn nộp: 15/7/2025, 15/1/2026, 15/7/2026**.
**Việc cần làm ngay, không phải chờ code:** xác nhận với người chịu trách nhiệm chuyên môn dược
của BeraLLC xem đã từng nộp báo cáo này chưa. Nếu chưa, liên hệ Sở Y tế/UBND tỉnh xử lý trước.

### 2 phát hiện khác

| # | Văn bản | Kết luận |
|---|---|---|
| 1 | TT 33/2025 (lưu trữ hồ sơ) | Không có mục riêng cho sổ KSĐB bán lẻ. Mục gần đúng nhất (báo cáo định kỳ GN/HT/TC cấp phép NK/XK) = **20 năm**. GĐ quyết định (dưới ủy quyền): nâng sàn retention từ ≥2 năm sau hạn dùng lên **≥20 năm kể từ ngày phát sinh hồ sơ** — hướng an toàn hơn, không phải kết luận chắc tuyệt đối |
| 2 | TT 26/2025 (đơn thuốc & kê đơn) | Không phát sinh nghĩa vụ mới cho bán lẻ. Chỉ xác nhận 2 tham chiếu lỗi thời tự sửa trong chính nó: TT53/2017→TT33/2025, TT20/2017→TT18 Điều 15.4 (nguyên tắc "văn bản dẫn chiếu bị thay thế thì theo văn bản mới") |

### Đã cập nhật (chỉ tài liệu, chưa đổi code)

| File | Thay đổi |
|---|---|
| `docs/legal/Nghị-định-163-2025-NĐ-CP.SUMMARY.md` | Mới — trích Điều 35.2 (báo cáo), Mẫu số 06 12 cột, Điều 33/36 đối chiếu TT18 |
| `docs/legal/Thông-tư-33-2025-TT-BYT.SUMMARY.md` | Mới — không có mục riêng, nâng sàn 20 năm |
| `docs/legal/Thông-tư-26-2025-TT-BYT.SUMMARY.md` | Mới — không có nghĩa vụ mới, xác nhận 2 tham chiếu lỗi thời |
| `docs/legal/README.md` | Bảng tra cập nhật, đánh dấu NĐ54/2017 hết hiệu lực |
| `docs/13_COMPLIANCE_SPEC.md` | **Mục C.7 hoàn toàn mới** (báo cáo định kỳ); C.4 nâng sàn 20 năm; Traceability #27 đính chính lần 2, thêm #28; mục G bỏ báo cáo định kỳ ra khỏi "ngoài phạm vi"; changelog mục H |

### Việc mới cần làm — CHƯA CODE, cần qua cổng riêng

Tính năng "báo cáo định kỳ Mẫu số 06" (mục C.7 docs/13) là **tính năng hoàn toàn mới**, ngoài
phạm vi 6-bước đã duyệt cho mạch TT18. Cần `docs/14_FEATURE_PROCESS.md` Bước 0-3 trước khi code,
dù dữ liệu nguồn (`ControlledLedgerEntry`) đã có sẵn — việc mới là tổng hợp theo kỳ 6 tháng/năm +
kết xuất đúng Mẫu số 06 + (tùy chọn) nhắc lịch nộp.

**Ưu tiên đề xuất giữa 2 việc code đang chờ:** (a) bước 4 mạch TT18 đã duyệt trước (biên bản nhận
lại PL XVIII) — không khẩn về pháp lý nhưng đã sẵn sàng làm ngay; (b) báo cáo định kỳ Mẫu số 06 —
khẩn hơn về mặt tuân thủ (đã trễ hạn ngoài đời) nhưng cần qua cổng feature-process trước. **Hỏi
Chain ưu tiên việc nào trước khi tiếp tục code**, thay vì tự chọn dưới ủy quyền, vì đây là quyết
định phân bổ ưu tiên nghiệp vụ thật (không phải kỹ thuật) và ảnh hưởng tới việc có cần xử lý gấp
bên ngoài phần mềm trước không.

---

## 8. Nhật ký thay đổi (Changelog)

| Ngày | Thay đổi |
|------|----------|
| 2026-07-25 | **NĐ163+TT33+TT26 đọc xong — ĐẢO NGƯỢC kết luận báo cáo định kỳ (§7as)** — Chain chép 3 văn bản, ủy quyền toàn quyền GĐ chỉ đạo code. **NĐ163 Điều 35.2: bán lẻ CÓ nghĩa vụ báo cáo 6 tháng/năm gửi UBND cấp tỉnh (Mẫu số 06), đã trễ ≥3 kỳ (15/7/2025, 15/1/2026, 15/7/2026)** — đảo ngược kết luận cũ "TT18 không áp cho bán lẻ" (kết luận đó đúng riêng cho TT18, sai khi coi là câu trả lời đầy đủ). **Việc khẩn ngoài phần mềm:** xác nhận BeraLLC đã báo cáo chưa. TT33: không có mục riêng cho sổ KSĐB bán lẻ, nâng sàn retention lên ≥20 năm (suy diễn, an toàn hơn 2 năm cũ). TT26: không phát sinh nghĩa vụ mới, xác nhận 2 tham chiếu lỗi thời tự sửa. Cập nhật docs/13 (mục C.7 mới), docs/legal/README, 3 SUMMARY mới. **Chưa code** — tính năng báo cáo Mẫu số 06 cần qua docs/14_FEATURE_PROCESS trước; hỏi Chain ưu tiên việc này hay bước 4 (biên bản PL XVIII) đã duyệt trước đó. |
| 2026-07-25 | **TT 18/2026 THAY TT 20/2017 — bước 1/3, chỉ tài liệu (§7ar)** — Chain thả bookmark TT18, yêu cầu chuẩn bị biểu mẫu + hỏi trình tự trước khi code. Trích nguyên văn: TT18 **hiệu lực 16/7/2026, bãi bỏ TT20/2017 + TT27/2024** ⇒ mục C của `docs/13` đang dựa trên văn bản chết 9 ngày. Báo cáo định kỳ **vẫn không áp cho bán lẻ** (Điều 7 thuộc Chương II — cơ sở phi thương mại) nhưng **hạ mức xuống "chưa kết luận được"** vì nghĩa vụ báo cáo của cơ sở kinh doanh nằm ở **NĐ 163/2025** — chưa có văn bản. Cái thật sự bỏ sót là **3 nghĩa vụ khác**: sổ **PL XVI** (Điều 12.3, TT20 không có), **biên bản nhận lại PL XVIII** (trước gạt ngoài phạm vi), **chữ ký số Điều 15.1.d** (không có gì). Lưu trữ mất căn cứ (chờ TT 33/2025 + TT 26/2025). Chain chốt: làm **bước 1–3**, chữ ký số **chỉ thiết kế**, sửa spec **tại chỗ + changelog**, **không bán thuốc độc** ⇒ không seed QĐ 3235. Bước 1 xong: SUMMARY TT18 đầy đủ, `docs/13` mục C viết lại + C.5/C.6 mới + Traceability #22–27 + changelog mục H, `docs/legal/README.md`, bản đề xuất 6 bước. **Bước 2–3 xong cùng ngày:** 122 hoạt chất PL I/II/III + ngưỡng PL IV/V/VI vào bảng `controlled_substances` (mig `0024`; seed **có nhánh cập nhật**, đã ép chạy nhánh đó trên CSDL có dữ liệu sẵn — `created=1, updated=2`); enum **7→9 giá trị** (`THUOC_DOC`, `DANH_MUC_CAM`); `LedgerBookType` **suy từ `category`**, không lưu cột ⇒ không cần migration; endpoint `GET /compliance/controlled-ledger/books/{book_type}/export` kết xuất CSV 2 mẫu sổ, tồn lũy kế reset theo từng thuốc. **Nợ ghi rõ, không tự làm:** phần đầu sổ (tên thuốc, số ĐKLH, ĐVT, nhà sản xuất) chưa xuất được vì phải mở read-port `DrugMasterFacts` — cross-module, chờ duyệt. 4 cổng xanh, pytest **782**, `alembic check` không drift. |
| 2026-07-25 | **RÀ TOÀN BỘ ĐỘ RỘNG CỘT `varchar` (§7aq)** — GĐ đề xuất cuối §7ap, Chain duyệt. Rà 88 cột/40 bảng: từ vựng đóng (24 enum, permission, role code, event type, target_type, ref_type, hash) **không còn cột nào tràn** sau mig `0023`; nhưng **input người dùng thủng hệ thống** — chỉ 17/159 trường schema có `max_length`, xác nhận live 6/7 endpoint thử trả **500** (`/customers` full_name+phone, `/users` email+full_name, `/drugs` name, `/suppliers` phone). Vá bằng `max_length` khớp độ rộng cột cho 29 trường/8 module (`275cb9a`); verify live 6 request đó nay **422**, chuỗi dài đúng bằng cột vẫn 201 (không chặn thừa). **Cố ý KHÔNG bắt `DBAPIError` đổi thành 4xx** — sẽ nuốt mất lỗi nội bộ vốn cần nổ to. Không chặn mật khẩu/refresh token (không lưu thô) và cột `Text`. 2 cổng chặn tái diễn: test cấu trúc (mọi trường chuỗi request phải chặn hoặc miễn trừ có lý do) + test hành vi (endpoint từng 500 nay 422). 4 cổng xanh, pytest **741**. **Nợ còn mở:** cột `Text` chưa giới hạn (chờ Chain chốt mức nghiệp vụ) · 2 cột dư đúng 1 ký tự · hash sha256 khít 64/64. |
| 2026-07-25 | **MODULE `analytics` XONG — SPRINT 7 ĐÓNG (§7ap)** — nối phiên bị **cúp điện 07:00** cắt ngang giữa bước 7/8. Dự báo trung bình trượt 90 ngày + mốc tái đặt hàng cấp thuốc×chi nhánh, đề xuất sinh **PO nháp** DRAFT trong `procurement`, dashboard doanh thu/top thuốc/cảnh báo tồn. 8 bước, 4 commit trong phiên này (`0bfb41b`→`a40de7e`→`77faa5e`→`97a4560`). **3 lỗi phát hiện khi rà**: (1) cổng ruff đỏ tại HEAD từ bước 4/8; (2) **`audit_logs.action` varchar(32) trong khi 3 action dài 33–36 ký tự → Postgres 500, mà 734 test vẫn xanh vì SQLite bỏ qua độ dài** — 2/3 action có từ trước, bug sống trên deployment thật, vá bằng mig `0023` + test chặn tái diễn; (3) **PO nháp ghi bằng system-user** lệch thiết kế Chain duyệt, mở cửa hậu leo thang quyền — nay ghi bằng identity người bấm. Kỷ luật #7 chạy đủ: seed idempotent + verify SQL (3 role có quyền, cashier/warehouse không) + round-trip API token thật trên PG (materialize sinh PO DRAFT thật, audit ghi đúng người bấm), dữ liệu thử đã dọn. 4 cổng xanh, pytest **734**, import-linter **16/0**, mig `0001`→`0023`. **Nợ mang sang (không tính DoD):** report đợt 2, retry DAV lên outbox, tồn-âm async, `analytics` v2, FE analytics. |
| 2026-07-25 | **LỌC DOANH THU THEO NHÂN VIÊN XONG (§7ao)** — gỡ nợ §7an. Chain duyệt PA (a): thêm cột `sold_by_user_id` trên `sales_orders` (nullable vĩnh viễn, ghi từ JWT lúc chốt đơn), lọc `GET /reports/revenue/export?sold_by_user_id`. 3 commit stepped (`cd98f7b`→`8771234`→`b76a99b`), migration `0021` live+reversible (đã verify cột/index bằng `psql`, downgrade/upgrade sạch, `alembic check` không drift), backup `~/backup_pre_migration_20260725_0239.sql`. Tái dùng `sales.read` — KHÔNG quyền mới. 4 cổng xanh, pytest **695**. Kỷ luật #7 không áp dụng (thêm cột, không đụng seed/permission). `RevenueRow`/CSV giữ nguyên (chỉ thêm filter, không thêm chiều nhóm). **`analytics` vẫn chờ Opus.** |
| 2026-07-24 | **REPORT XUẤT KHẨU đợt 1 XONG (§7an)** — GĐ giao 1/2 mục Sprint 7 còn treo (Sonnet, full-auto). `GET /reports/revenue/export` (doanh thu ngày/tuần/tháng, lọc chi nhánh) + `GET /reports/inventory/stock/export` (tồn kho theo lô/HSD) — cả hai CSV stream, KHÔNG quyền mới (tái dùng `sales.read`/`inventory.read`), KHÔNG migration. `core/http.py:csv_stream_body` tách từ audit dashboard để dùng chung. 3 commit stepped (`4c45f88`→`be9ada9`→`414269d`), live PG smoke-test khớp 100% với SQL (kỷ luật #7 tinh thần), dữ liệu thử đã dọn sạch. 4 cổng xanh, pytest **690**. **Đợt 2 (top thuốc + `ControlledLedgerEntry`) KHÔNG bắt buộc, chưa làm; lọc "theo nhân viên bán hàng" chặn ở thiếu dữ liệu — cần Chain quyết định hướng. `analytics` KHÔNG đụng — chờ phiên Opus.** |
| 2026-07-24 | **AUDIT DASHBOARD XONG (§7al)** — GĐ giao 1/3 mục Sprint 7 (full-auto). Quyền RIÊNG `audit.dashboard.read` cấp cho admin+chain+branch (KHÔNG cashier/warehouse; branch có dashboard nhưng không `audit.read` thô). Filter actor+time+`target_type`+action (AND, optional) · export CSV stream theo lô. 3 commit stepped (`7346dbe`→`76ec94e`→`adb38da`), migration `0020` index entity, live PG round-trip + seed verify bằng SQL (kỷ luật #7). 4 cổng xanh, pytest **679**. **2 mục còn lại (`analytics`, report) KHÔNG đụng — chờ Chain trả lời yêu cầu.** |
| 2026-07-24 | **DỪNG PHIÊN đúng nghi thức (§7ak)** — mạch outbox đóng trọn 4 bước, 7 commit, HEAD `1415bb8`, git sạch, 4 cổng xanh, docker healthy, 0 tiến trình treo, dữ liệu thử đã dọn. Chain chuyển sang **phiên Design** cho 3 mục còn lại Sprint 7 (audit dashboard · `analytics` · report) — cả 3 chặn ở YÊU CẦU, không chặn kỹ thuật; câu hỏi cần trả lời đã liệt kê ở §7ak. Toàn bộ 9 quyết định tự chốt trong phiên gom 1 bảng tại §7ak. |
| 2026-07-24 | **Retention `event_outbox` (§7aj).** `OutboxRetention` quét nền: `PUBLISHED` quá 30 ngày xoá theo lô · `FAILED` giữ vĩnh viễn (mặc định) · `PENDING` không bao giờ, chặn bằng kiểu `TerminalStatus`. Cờ `OUTBOX__RETENTION_ENABLED` độc lập với relay (dòng chất đống ở cả 2 chế độ). Migration `0019` index `(status, created_at)`. pytest **665**, chạy thật trên PG. Mạch outbox đóng trọn 4 bước. |
| 2026-07-24 | **OUTBOX BƯỚC 3/3 — FLIP XONG (§7ai).** UoW ghi `event_outbox` in-txn; `OutboxEventSink` + 2 cờ `OUTBOX__SYNC_DRAIN`/`RELAY_ENABLED`; `EventRegistry` 14 event; relay nền trong lifespan; 12 điểm dựng UoW gom về `UnitOfWorkFactory`. Kèm điều kiện tiên quyết (chặn trùng interaction-check, mig `0018`) + 1 commit `ruff format` sửa cổng lint vốn đã đỏ tại HEAD. **Chạy thật trên Postgres đúng hình dạng prod** (async): bán → PENDING → drain → tồn trừ → PUBLISHED, drain lại = no-op. Phát hiện: async đẩy 1 mắt xích/vòng quét. |
| 2026-07-24 | **DỪNG PHIÊN đúng nghi thức (§7ah).** Sếp chốt **phương án (a)** — chặn trùng interaction-check bằng khoá `(context_type, context_id)`, là điều kiện tiên quyết TRƯỚC khi flip Bước 3. HEAD `48e40c0`, 4 cổng xanh, docker healthy, không tiến trình treo. Resume = làm Bước 3 (flip nguyên tử), 5 bước ghi ở §7ah. |
| 2026-07-24 | **Outbox Bước 2/3: machinery NGỦ (bảng `event_outbox` + repo + relay + migration 0017), flag OFF, `UoW` chưa đổi.** Sếp duyệt thiết kế §7af + mở rộng cổng idempotency (liệt kê TOÀN BỘ subscriber). Bảng idempotency đầy đủ: chỉ interaction-check không idempotent. 4 cổng xanh (pytest **633**, +13), live migration 0017 round-trip verified. **Bước 3 (flip) chờ sếp xác nhận danh sách idempotency.** Xem §7ag. |
| 2026-07-24 | **DỪNG PHIÊN đúng nghi thức** — outbox Bước 1/3 xong, Bước 2/3 chờ đổi model sang Opus (quy tắc chọn model, thiết kế mới chưa có khuôn mẫu). Xem §7af. |
| 2026-07-24 | Outbox Bước 1/3: codec serialize/deserialize DomainEvent (domain thuần) — resume phiên sau cắt đột ngột, xem §7ae. |
| 2026-07-24 | MedicationHistoryEntry tự động + dị ứng OTC (3 bước: customer_id/mig 0016 · use-case · wiring) — phiên Opus full-auto, xem §7ad. |
| 2026-07-23 | Endpoint HTTP `active_ingredients` (POST/GET) — nợ kỹ thuật đơn module, xem §7u. |
| 2026-07-23 | Audit `sales` (`SALE_COMPLETED`) — GĐ chọn ưu tiên, xem §7v. |
| 2026-07-23 | Audit `inventory` (`INVENTORY_STOCK_RECEIVED`/`DISPENSED`, chỉ 2 endpoint tay) — xem §7w. |
| 2026-07-23 | Audit `procurement` (`PO_ORDERED`/`GRN_CONFIRMED`, chỉ 2/7 use-case) — xem §7x. |
| 2026-07-23 | Audit `clinical` (`INTERACTION_CHECKED`/`RECOMMENDATION_ACCEPTED`) — xem §7y. |
| 2026-07-23 | Audit `catalog` (`DRUG_CREATED`) — **mạch 5 module đóng, 9/9 module có audit** — xem §7z. |
| 2026-07-23 | Persist trả hàng (`register_return`, sales-side only) — GĐ chốt KHÔNG auto-restock tồn kho, xem §7aa. |
| 2026-07-23 | Nhóm rủi ro thấp đã duyệt: httpx2 dep fix, ROADMAP checkbox fix, API resolve `stock_reconciliation_needed` — xem §7ab. |
| 2026-07-23 | Gộp lô (PA B) cho cả `receive_stock` + GRN — GĐ tự chốt theo full-auto, xem §7ac. |
| 2026-07-23 | **DỪNG PHIÊN theo yêu cầu sếp — gom điểm dừng toàn phiên vào §7p.** Sếp muốn phiên sau bàn sắp xếp lại ưu tiên với GĐ trước khi tiếp tục code. §7p liệt kê trung lập (không xếp hạng): trạng thái kỹ thuật lúc dừng (2 tiến trình nền còn chạy — uvicorn 8000, next dev 3000; tenant demo còn trên Postgres), 6 việc tính năng đang dở dang, 7 việc treo ngoài phạm vi code (thương hiệu chưa ghi vào `ChienLuoc/`, câu hỏi lẻ-hay-chuỗi, tagline lệch, gộp hỏi luật sư, badge chưa đo lại...), và cảnh báo `TODO.md` đã lỗi thời (đề 2026-07-22, một số dòng sai so với thực tế — cần rà lại riêng, không tự sửa hàng loạt ngay vì thiếu ngữ cảnh phiên cũ). |
| 2026-07-23 | **S4.6 FE POS tối thiểu — 4/5 bước (phiên Sonnet, xem §7o).** Hồi sinh từ nợ ROADMAP Sprint 4. `frontend/` mới hoàn toàn (Next.js+TS+TanStack Query+Zustand), theo `docs/04` §3 + `docs/16` brand guide. 4 commit: CORS (`cb3809e`, ngoại lệ backend duy nhất, xin phép trước) → scaffold (`2bcea7f`) → auth JWT thật (`c642c34`) → tra thuốc/giỏ hàng/thanh toán (`ba547c4`). **3 phát hiện lệch docs/11-thực tế**: API `sales` thật là `POST /sales` gộp 1 lệnh (không phải `/sales-orders`+`/payments`+`/complete` như doc); `GET /drugs` không có tham số tìm kiếm; **không nguồn giá bán nào trong backend** (chỉ có `inventory.cost_price` — giá vốn) nên thu ngân nhập tay giá — khoảng trống sản phẩm thật. Kiểm chứng bằng curl mô phỏng đúng request FE trên backend live (không chỉ đọc code) — khớp 100% type đã viết; `next dev` thật chạy sạch. **Giới hạn: không có trình duyệt trong môi trường, chưa từng click-through UI thật** — chỉ xác nhận hợp đồng API + server không crash. **Bước 5 (Dexie offline) chưa làm.** Để lại tài khoản demo `fe-demo@beral.vn`/`MatKhauFeDemo2026` trên Postgres để sếp login thử ngay. |
| 2026-07-23 | **CHỐT PHIÊN — 20 commit, xem §7n.** Phiên Opus dài: `iam` thật (4 bước) → `audit_logs` persist (3 bước) → Hồ sơ sức khỏe KH qua cổng docs/14 (Bước 0-3, còn Bước 4) → thương hiệu **BERAS** + `docs/16_BRAND_UI_GUIDE.md`. Cổng cuối: ruff sạch · mypy strict 210 file · import-linter 13/0 · pytest **560** · alembic `0015` (head) · git sạch. **5 bug thật** phát hiện và vá (nặng nhất: lỗ hổng `X-Branch-Id` đang chạy; role hệ thống không cập nhật khi nâng cấp mà 505 test vẫn xanh). **14 quyết định Claude tự chốt trong full-auto** liệt kê đủ ở §7n để sếp đọc lướt. Phiên sau bắt đầu: đóng Bước 4 → mount router `compliance` → audit cho `prescription`+`compliance`. |
| 2026-07-23 | **Thương hiệu BERAS + nguyên tắc UI.** Sếp chốt tên/mascot/tagline/tông màu Eco-Tech/3 trụ cột (`sales`/`compliance`/`clinical`)/2 nguyên tắc UI → `docs/16_BRAND_UI_GUIDE.md`. README đổi định vị từ "Hệ điều hành nghiệp vụ AI-native" sang "Sổ điện tử quản lý nhà thuốc chuẩn Cloud/SaaS thế hệ mới", H1 mang tên BERAS, dọn tàn dư "lấy AI làm lõi" ở §1, bổ sung docs 13-16 vào bản đồ tài liệu, sửa 2 badge sai (Sprint 3→7, tests 46→560). Bổ sung vào docs/16 phần **trạng thái backend thật của 3 trụ cột** (kiểm chứng bằng lệnh) để nguyên tắc "không quảng bá tính năng chưa sẵn sàng" có căn cứ dùng được: trụ 1 POS chạy được · trụ 2 tuân thủ **một nửa** (module `compliance` chưa mount router ⇒ chưa có API cho màn sổ kiểm soát) · trụ 3 AI **chưa thật** (`MockLLMProvider`; cảnh báo tương tác/dị ứng chạy thật nhưng bằng engine tất định, không phải AI). Không đụng code. |
| 2026-07-23 | **Hồ sơ sức khỏe KH — Bước 1-3/4 (`52ab50d`, `10f2a73`, `96b5b9b`).** Cổng đồng ý (đồng ý là cơ sở pháp lý DUY NHẤT nên ràng buộc đặt ở domain, không để caller tự nhớ) → tách `crm.sensitive.read`/`write` + wiring 6 action audit → xuất dữ liệu/khử nhận dạng + `GET /privacy/processing-record` (sinh từ code, trả kèm `known_gaps`). Migration `0015_customer_consents`. pytest 522→536→560. **Bước 4 chưa làm**, 5 việc còn lại ghi ở §7m. |
| 2026-07-23 | **`audit_logs` XONG 3/3 bước — gỡ nợ F8, mở đường cho Hồ sơ KH.** Sếp lệnh persist `AuditLogger` thay vì chỉ đẩy log stream. 3 commit (`8435b42` hình dạng → `05b7857` persist + migration `0014` → `aa521ec` đọc + vá bug). Bảng append-only (repository KHÔNG có update/delete), `context` chỉ metadata (`client_ip`+`branch_id`, có test khẳng định không lọt mật khẩu/token — chép dữ liệu bị truy cập vào audit là tự tạo kho DLCN thứ hai ít được canh hơn kho nó bảo vệ). Ghi DB **và** structlog song song. `GET /audit-logs` mức tối thiểu + quyền mới `audit.read` (chỉ admin + dược sĩ cấp chuỗi). **2 phát hiện khi kiểm chứng thật:** (1) **role hệ thống chỉ seed 1 lần, không bao giờ cập nhật** ⇒ deployment cũ mãi thiếu permission mới, admin bị 403 dù code đã cấp — **test suite không bắt được vì luôn khởi tạo DB rỗng**, chỉ lộ khi chạy CLI thật trên Postgres đã có dữ liệu; đã sửa thành `sync_system_roles()` + đưa vào `seeds/run.py`, +4 test hồi quy; (2) cổng import-linter bắt vi phạm layers thật (`modules.iam` import `api.deps`) → hạ helper xuống `core/http.py`. **Quyết định tự chốt (full-auto):** lỗi ghi audit KHÔNG bị nuốt, cứ ném lên — bảng audit cùng CSDL với dữ liệu nghiệp vụ nên insert audit hỏng nghĩa là ghi nghiệp vụ cũng đang hỏng; nuốt lỗi không giúp bán được hàng, chỉ giấu việc nhật ký bị thủng (structlog phát TRƯỚC insert nên sự kiện không mất hẳn). Cổng: ruff sạch · mypy strict 208 file · import-linter 13/0 · pytest **505** (+40). **5 nợ ghi rõ ở §7l** — nặng nhất: mới phủ 11 hành vi của `iam`, nghiệp vụ khác (đọc hồ sơ KH) chưa ghi audit. |
| 2026-07-23 | **Module IAM thật XONG 4/4 bước — blocker RBAC gỡ.** Phiên Opus: đọc §7k, khảo sát code thật, viết `docs/15_IAM_DESIGN.md` (thiết kế + trả lời 5 câu hỏi mở + 11 điểm chờ duyệt), **sếp duyệt trọn 11 điểm 1 lượt**, thi công 4 bước (`3bc148f` domain → `5c3bc08` app+infra+migration `0013_iam` → `4c64a4c` interface+deps+CLI). **6 phát hiện trong lúc khảo sát**: (F1 🔴) `api/deps.py` tin `X-Branch-Id` không kiểm tra → đổi header là truy cập chi nhánh khác trong tenant với nguyên bộ quyền — **đây là lỗ hổng thật đang chạy, IAM đã đóng bằng cách ký branch vào JWT**; (F2) thiếu header thì gán `branch_id = tenant_id`; (F3) `_DEV_PERMISSIONS` chỉ 26/32 permission thật, thiếu đúng 6 `compliance.*`; (F4) module `compliance` chưa mount router (chưa sửa); (F5) `TenantScopedMixin` ép `branch_id NOT NULL` nên iam phải tự khai cột; (F7) `crm.read` gộp cả dữ liệu nhạy cảm, ngược NĐ356 Điều 4.2. **Quyết định đáng nhớ**: refresh token revocable + xoay vòng + phát hiện replay (thay vì stateless — nhà thuốc có luân chuyển nhân sự thật, Luật 44/2024 Điều 47a.1.đ); giữ TTL access token 60 phút thay vì hạ 15 vì POS offline-first (đổi rủi ro lấy rủi ro, ghi nợ thay vì giả vờ giải xong); bootstrap bằng CLI chứ không endpoint (không mở thêm bề mặt tấn công); dev-header giữ nhưng mặc định TẮT (fail-closed); 5 role đặt tên theo chức danh nghiệp vụ bám Luật 44 Điều 17a; thu ngân không có `rx.approve`/`rx.dispense` (Luật Dược Điều 6.5.h) và không có `crm.*` (NĐ356 Điều 4.2 + GPP TT02 I-1a.III.4.a). Cổng cuối: ruff sạch · mypy strict 201 file · import-linter 13/0 (thêm `iam-domain-innermost`, thêm `iam` vào `module-independence` — sếp duyệt sửa contract cũ) · pytest **465** (+51). **8 nợ ghi rõ ở §7k, không overclaim** — nặng nhất: `audit_logs` vẫn chỉ ghi structlog nên chưa chứng minh được ai truy cập gì. |
| 2026-07-23 | **Mở việc thiết kế IAM thật — DỪNG ngay ở bước khảo sát, chờ phiên Opus (KHÔNG code, KHÔNG thiết kế chi tiết).** Sếp lệnh thiết kế module `iam` (users/roles/JWT) thay dev-header, cross-module ảnh hưởng toàn hệ thống. Hỏi sếp model cho việc này (đúng quy tắc dự án: thiết kế mới hoàn toàn → Opus + phiên hạn mức đầy, phiên hiện tại là Sonnet) — **sếp chọn dừng, mở phiên Opus mới**. Đã khảo sát hạ tầng sẵn có để phiên sau không dò lại: `core/security/{jwt,password,rbac}.py` (JwtService.issue/decode, hash_password/verify_password, require_permission — đều đã chạy được từ Sprint 2), `core/context.py` (`RequestContext` đã có `branch_id` tách biệt `tenant_id`), `core/db/base.py` (`TenantScopedMixin`), 26 permission string thật đang dùng trong `api/deps.py._DEV_PERMISSIONS` trải 6 module, khung endpoint `iam` đã phác ở `docs/11_API_DESIGN.md` §3. Ghi toàn bộ vào §7k kèm 5 câu hỏi thiết kế mở (refresh token, bootstrap admin đầu tiên, có giữ dev-header song song không, mô hình role 2 cấp chuỗi/nhà thuốc, role seed ban đầu) để Opus quyết định có cơ sở, không phải dò từ đầu. |
| 2026-07-23 | **Đọc + tóm tắt Luật Dược 105/2016/QH13 + Luật sửa đổi 44/2024/QH15 (đợt 2, KHÔNG code).** Sếp bổ sung 2 văn bản còn thiếu từ đợt 1: `Luật-105-2016-QH13.docx`, `Luật-44-2024-QH15.docx`. Đọc toàn văn, viết 2 file `docs/legal/*.SUMMARY.md` + cập nhật `docs/legal/README.md`. **4/4 văn bản pháp lý ban đầu sếp yêu cầu nay đã đủ.** Phát hiện quan trọng: (1) Luật Dược Điều 2.27-28 (định nghĩa thuốc kê đơn/không kê đơn) + Điều 6.5.h (cấm bán lẻ ETC không đơn) — **đây chính là nguồn Luật còn thiếu** mà `docs/13_COMPLIANCE_SPEC.md` dòng 14 đánh dấu "KHÔNG TÌM THẤY" cho rule "mọi thuốc ETC cần prescription_code"; Điều 75.2 (sửa bởi Luật 44/2024) cũng là nguồn Luật cấp cao nhất cho toàn bộ yêu cầu liên thông CSDL Dược (hiện docs/13 chỉ dẫn QĐ1867, chưa có gốc Luật) — **đã báo cáo sếp, chưa tự sửa spec đã khóa**. (2) Luật 44/2024 đưa vào khái niệm pháp lý mới **"chuỗi nhà thuốc"** (Điều 2.48, 17a, 47a): yêu cầu quản lý dữ liệu khách hàng thống nhất toàn chuỗi — **khớp sẵn** với kiến trúc `tenant_id`+`branch_id` đã có (`crm.Customer` scope theo tenant, không branch — đã validate đúng hướng, không cần sửa); nhưng cần role RBAC riêng "chuyên môn cấp chuỗi" vs "cấp nhà thuốc" khi thiết kế IAM. (3) Luật 44/2024 hợp pháp hóa thương mại điện tử dược (chỉ OTC được bán online) — ngoài ROADMAP hiện tại (POS offline-first), chỉ ghi nhận khung pháp lý. **Không code** — blocker RBAC/IAM (§7j mục 1) vẫn còn nguyên, 2 câu hỏi pháp lý mở (giấy phép DLCN, cập nhật docs/13) vẫn chờ sếp/luật sư. |
| 2026-07-23 | **Đọc + tóm tắt 5 văn bản pháp lý mới sếp bổ sung (KHÔNG code).** Sếp thả vào `docs/legal/`: Luật BVDLCN 91/2025/QH15, NĐ 356/2025/NĐ-CP, TT02/2018/TT-BYT (GPP), TT11/2025/TT-BYT (sửa GPP/GDP/GSP), TT29/2020/TT-BYT (sửa nhiều VB). Đọc toàn văn (convert docx→txt qua `soffice --headless`), viết 8 file `docs/legal/*.SUMMARY.md` (1 file/văn bản, kèm 3 file cũ 540/1867/TT20 trỏ về `docs/13_COMPLIANCE_SPEC.md` đã có sẵn) + `docs/legal/README.md` chỉ mục. Phát hiện đáng chú ý: (1) NĐ356 Điều 41.2 — miễn trừ DPIA cho hộ kinh doanh/DN siêu nhỏ **không áp dụng** khi xử lý dữ liệu nhạy cảm (dị ứng/bệnh nền là nhạy cảm theo Điều 4.1.d) → mọi tenant dù nhỏ vẫn phải DPIA cho tính năng hồ sơ KH; (2) câu hỏi pháp lý mở: BeraLLC có cần Giấy chứng nhận kinh doanh dịch vụ xử lý DLCN không (NĐ356 Điều 21-27) — cần tư vấn luật sư, không tự kết luận; (3) GPP (TT02/2018 II.4.d) là căn cứ cho retention tối thiểu 1 năm kể từ hết hạn dùng thuốc — dùng cho thiết kế retention policy hồ sơ KH sau này; (4) vẫn thiếu bản thân Luật Dược hiện hành (chỉ có văn bản hướng dẫn thi hành). **Không code** — đây là việc đọc/tóm tắt tài liệu, blocker RBAC/IAM (§7j mục 1) vẫn còn nguyên. |
| 2026-07-23 | **Resume sau crash phiên trước + In bill (S7) interface XONG.** Đầu phiên: `git log`+`git status`+`docker compose ps` theo đúng kỷ luật resume. Phát hiện cả `postgres`+`redis` cùng **Exited (255)** đột ngột lúc `02:38:53` — log không có dòng "received shutdown request" nào trước đó (khác hẳn các lần tắt êm khác trong log), không OOMKilled → kết luận **(b) lỗi hạ tầng do host/session crash**, không phải bug code. `docker compose up -d` lại — cả 2 container khỏe. Đối chiếu working tree: commit `4a5bc0b` (app — `ReceiptSummaryDTO`+`get_receipt`) đã có sẵn từ trước; phần **interface** (router `GET /sales/{id}/receipt?format=`, schemas `ReceiptResponse`/`ReceiptFormat`, renderer `receipt_rendering.py` K80+PDF A5/A4 qua reportlab, test e2e `test_sales_api_e2e.py` +4, dep `types-reportlab`) đã viết xong hoàn chỉnh từ phiên trước khi crash — không dở dang, không cần audit/thiết kế lại. Chạy đủ 4 cổng: ruff sạch · import-linter **12/0** · mypy strict **179 file** · pytest **380 passed** (0:01:26). Commit `53e31b3` **sales: interface — GET /sales/{id}/receipt (In bill S7)**. **In bill S7 giờ đủ 4 lớp domain→app→infra→interface, XONG.** |
| 2026-07-23 | **Rà soát toàn diện S1→S6 + chẩn đoán demo + neo `docs/14` (KHÔNG code).** (1) **Audit 7 bước tự kiểm chứng:** working tree sạch, mọi hash trích dẫn đúng, ruff sạch, mypy strict **178 file**, import-linter **12/0**, pytest **372 passed/0 skip**, 12 migration upgrade/downgrade + 2 round-trip sạch + `alembic check` no-drift (30 bảng), **chỉ 1 FK xuyên module** (`customer_allergies.ingredient_id`, `po_item_id` là nội-procurement), **0 import module→module**, LLM/gateway đều Mock, không secret trong git, 34 route smoke đúng. Phát hiện **4 lệch tài liệu↔thực tế**: demo_preview.py CRASH (dù docs ghi ✅), TODO:158 procurement `[ ]`, TODO:73 C.5 `[ ]`, cây rác `backend/backend/`. (2) **Chẩn đoán demo:** kết luận **(a) demo lỗi thời** — thiếu `ingredient_repo_factory` (CatalogService, `44f843c`) + `reconciliation_repo_factory` (InventoryService, `82b8fde`); service layer đúng, KHÔNG phải bug. (3) **Neo `docs/14_FEATURE_PROCESS.md`** (Compliance/Privacy by Design cho mọi tính năng mới) + memory `feature_process_gate`. Đọc 3 tính năng sắp tới (hồ sơ KH/tích điểm/in bill) qua checklist → **2 blocker nền**: RBAC/IAM vẫn dev-header (chặn hồ sơ KH+tích điểm); `docs/legal/` thiếu Luật BVDLCN 91/2025+Luật Dược+NĐ356/2025+GPP. In bill ít bị chặn hơn. **Chưa sửa 4 lệch, chưa code, chưa mở sprint** — chờ sếp quyết ưu tiên RBAC/IAM hay In bill (xem §7j). |
| 2026-07-22 | **🏁 Cross-module GRN→inventory — ĐÓNG Sprint 6 (Opus, thiết kế duyệt trước, 2 quyết định sếp chốt).** `wire_goods_receipt_stock_in` ở `api/v1/cross_module.py` subscribe `GoodsReceived` (khuôn `wire_sale_dispensing`); map `ReceivedItem`→`inventory.GoodsReceiptLine`→ use-case mới `InventoryService.receive_from_goods_receipt` (đối xứng `dispense_for_sale`, additive). Idempotent theo `grn_id` (`exists_for_ref("grn",grn_id)`, IN-movement `ref_type="grn"`). **QĐ1 (PA A):** va chạm `uq_batch_lot` → **pre-check `find_by_lot`** (port mới, tránh IntegrityError hỏng txn) → bỏ qua dòng + ghi `stock_reconciliation_needed`; gộp lô (PA B) hoãn cho cả 2 luồng. **QĐ2:** bảng bù nhẹ `stock_reconciliation_needed` (đặt ở `inventory`, `grn_id`/`po_item_id` UUID trần không FK → module-independence giữ 12/0) ghi MỌI ca GRN confirmed không tạo được lô — va chạm (dòng cụ thể) hoặc lỗi bất ngờ (best-effort txn riêng, `po_item_id=None`, không ném vì bus cô lập). Thêm `po_item_id` vào `ReceivedItem` để biết dòng va chạm. Entity `StockReconciliationNeeded`+port+ORM+repo đủ 4 lớp; `branch_id` lấy từ event (mang branch thật). Migration `0012_stock_reconciliation`: autogenerate→apply **live Postgres**→check sạch→downgrade→upgrade→check sạch. `InventoryService` +1 repo factory (cập nhật `register.py`+`conftest.py`). Test: `test_cross_module_goods_receipt.py` (+4) + `test_procurement_inventory_e2e.py` (+2 HTTP e2e); smoke live PG (tenant tạm, dọn sạch). Gate: ruff+format sạch, import-linter **12/0**, mypy **178 file**, pytest **372** (+6). **⇒ DoD "Nhập PO→GRN tạo lô" ĐẠT — Sprint 6 ĐÓNG.** Nợ sang S7: gộp lô, `MedicationHistoryEntry` từ event, dị ứng OTC, outbox bền, API resolve reconciliation. |
| 2026-07-22 | **`procurement` — interface HTTP XONG (DỪNG trước cross-module GRN→inventory, theo lệnh).** Gap phát hiện trước khi code: `create_goods_receipt` không kiểm tra `po_item_id` trước khi insert — FK thật tới `purchase_order_items.id` sẽ vỡ `IntegrityError`/500 thô, đúng dạng bug đã gặp ở `crm.add_allergy`; sửa gọn hơn vì cùng module (PO đã load sẵn): validate `po_item_id ∈ po.items[].id` tường minh, ném lại `UnknownPurchaseOrderItemError` có sẵn từ `apply_receipt` → 422, không cần bắt `IntegrityError`. Schemas: `CreateSupplierRequest`/`SupplierResponse`, `CreatePurchaseOrderRequest`(+items)/`PurchaseOrderResponse`, `CreateGoodsReceiptRequest`(+items)/`GoodsReceiptResponse`, validate ở boundary (`gt=0`/`ge=0`/không rỗng). Router: 3 sub-router gộp 1 `build_router()` (`/suppliers`, `/purchase-orders`, `/goods-receipts` — khác `clinical` 1 prefix vì docs/11 liệt kê 3 nhóm tài nguyên); mở rộng ngoài 3 route tối thiểu docs/11 nêu — thêm route hành động state-machine (`/place`/`/cancel`/`/close`/`/confirm`) theo tiền lệ `/prescriptions/{id}/validate`. Wiring: `register.py` (3 repo factory) + `api/v1/__init__.py` (`register_procurement`, đơn giản không cross-module) + `api/deps.py` thêm quyền dev `procurement.*`. Test: `test_procurement_api_e2e.py` (+14, HTTP thật qua `TestClient` — thay cho script Postgres thủ công dùng ở bước trước) + `test_procurement_flow.py` (+1: po_item_id lạ → 422 không 500). **KHÔNG cross-module** (GRN→inventory) — để dành, đây là hạng mục DoD gốc cuối cùng của Sprint 6. Gate: ruff+format sạch, import-linter **12/0** (không đổi), mypy strict **178 file**, pytest **366** (+15). **DỪNG theo lệnh — CHƯA sang cross-module, cần Opus + phiên riêng.** |
| 2026-07-22 | **`procurement` — app+infra+migration `0011` XONG (DỪNG trước interface HTTP, theo lệnh).** Thêm `update()` vào `GoodsReceiptRepository` (domain, cùng module — cần để persist `status` sau `confirm()`, không đổi 12 contract). Infra: `SqlAlchemySupplierRepository`/`SqlAlchemyPurchaseOrderRepository`/`SqlAlchemyGoodsReceiptRepository` (tenant-scoped) + ORM `SupplierORM`/`PurchaseOrderORM`+`PurchaseOrderItemORM`/`GoodsReceiptORM`+`GoodsReceiptItemORM`. `GoodsReceiptItemORM.po_item_id` có FK thật tới `purchase_order_items.id` — FK **cùng module** (khác FK xuyên module của `crm.CustomerAllergyORM` trước đây), an toàn tuyệt đối với `module-independence`, không cần lớp dịch lỗi. App: `ProcurementService` (3 repo factory, khuôn `ComplianceService`) — `create_supplier`/`get_supplier`/`list_suppliers`; `create_purchase_order`/`add_po_item`/`mark_ordered`(phát `PurchaseOrdered`)/`cancel_purchase_order`/`close_purchase_order`/`get_purchase_order`; `create_goods_receipt`/`confirm_goods_receipt`(gọi `grn.confirm()` rồi `po.apply_receipt()` cùng transaction, phát `GoodsReceived` sau commit)/`get_goods_receipt`. Quyền mới `procurement.supplier.{create,read}`/`procurement.po.{create,read,write}`/`procurement.grn.{create,read,confirm}` (`grn.confirm` tách riêng khỏi `grn.create`, khuôn `rx.approve`/`rx.create`). Migration `0011_procurement` (5 bảng): autogenerate→apply **live Postgres**→`alembic check` sạch→downgrade→upgrade lại→**check sạch lại**; xác nhận thêm thủ công qua script chạy trực tiếp trên Postgres sống (ngoài SQLite test-harness, vì chưa có router) — full flow supplier→PO→order→GRN→confirm→RECEIVED→CLOSED, `GoodsReceived` đúng 1 lần, dọn dữ liệu demo sau khi xác nhận. Test: `test_procurement_flow.py` (+19). **KHÔNG làm interface HTTP, KHÔNG cross-module** (GRN→inventory) — theo đúng yêu cầu. Gate: ruff+format sạch, import-linter **12/0** (không đổi), mypy strict **175 file**, pytest **351** (+19). **DỪNG theo lệnh — CHƯA sang interface HTTP.** |
| 2026-07-22 | **`procurement` — domain thuần XONG (DỪNG trước app+infra, theo lệnh).** `procurement/domain/`: `Supplier` (entity đơn giản, guard tên rỗng) + `PurchaseOrder`/`PurchaseOrderItem` (state machine docs/07 §6: DRAFT→ORDERED→(PARTIALLY_RECEIVED\|RECEIVED)→CLOSED, hoặc DRAFT→CANCELLED) + `GoodsReceiptNote`/`GoodsReceiptItem` (aggregate riêng, DRAFT→CONFIRMED, không un-confirm). `PurchaseOrder.apply_receipt(items)` nối 2 aggregate cùng module qua `po_item_id` (không phải cross-module — 2 aggregate cùng `procurement`), tự tính lại status, chặn `OverReceiptError`/`UnknownPurchaseOrderItemError`. Events `PurchaseOrdered`/`GoodsReceived` (mang `tuple[ReceivedItem,...]`, khuôn `SaleCompleted`+`SoldItem`) — `GoodsReceived` là điểm nối cho bước cross-module sau (inventory tạo `ProductBatch`+`StockMovement` IN, `grn_id` làm khoá idempotent). `goods_receipt_items` là mở rộng thiết kế hợp lý ngoài ERD gốc (chỉ liệt kê `goods_receipts`) — cần đủ `lot_no`/`expiry_date`/`unit_cost` theo đúng docs/06 §4. Contract mới `procurement-domain-innermost` + `procurement` vào `module-independence` (11→**12**, không đổi 11 cái cũ). Test: `test_procurement_domain.py` (+28). **KHÔNG đụng catalog/inventory** — cross-module (GRN→lô kho) để dành bước sau theo đúng yêu cầu. Gate: ruff+format sạch, import-linter **12/0**, mypy strict **170 file**, pytest **332** (+28). **DỪNG theo lệnh — CHƯA sang app+infra+migration.** |
| 2026-07-22 | **Sprint 6 Bước 2 — 5.5.4 auto-check tương tác + nối dị ứng KH, XONG HOÀN TOÀN (Opus, phiên riêng, từng bước duyệt).** Cross-module ở composition root `api/v1/cross_module.py`, **cảnh báo không chặn** — cả `SaleCompleted`+`PrescriptionDispensed` đều hậu-commit; chặn-vs-cảnh-báo là quyết định nghiệp vụ/pháp lý, **sếp chốt cảnh báo** (hỏi qua AskUserQuestion trước khi code). 3 quyết định pháp lý đều do sếp chốt, Claude không tự quyết: (1) cảnh báo; (2) dị ứng **chỉ luồng prescription**, bán lẻ OTC hoãn (cần `customer_id` trên `SalesOrder`+migration); (3) dị ứng **luôn chạy, không cổng AI, không persist**. **4 bước con, mỗi bước 4 cổng xanh + 1 commit:** **B1 `68a0d74`** `catalog.get_drug_ingredients(drug_id)->[(ingredient_id,name)]` (hạ tầng chung nội bộ catalog, trả cả UUID+tên vì tương tác khớp tên/dị ứng khớp id; +5 test). **B2 `aeea74d`** `wire_safety_checks` bắt 2 event → resolve hoạt chất qua catalog → `clinical.check_interactions`; audit `AiRecommendation`; tenant-gated (`TenantAiSettings` default OFF, `FeatureDisabledError` nuốt im lặng); bỏ qua giỏ <2 hoạt chất phân biệt; bus đã cô lập lỗi handler; `PrescriptionDispensed` không mang `branch_id`→dùng tenant làm branch (+6 test). **B3a `f0281f2`** `clinical.check_allergies` thuần (domain `AllergyAlert`+`find_allergy_alerts` khớp theo `ingredient_id`; nhận id tường minh nên clinical KHÔNG import crm/catalog; severity truyền dạng str để không kéo enum crm; +4 domain +3 app test). **B3b `2de9d2b`** nối dị ứng vào handler dispense: đọc `crm.get_customer(customer_id).allergies` (tái dùng read có sẵn); log `allergy_warning_raised`; đổi tên `wire_interaction_safety_check`→`wire_safety_checks` + thêm `crm.read`; đổi tên file test→`test_cross_module_safety_checks.py` +3 test dị ứng (`structlog.testing.capture_logs`). **`module-independence` GIỮ NGUYÊN 11/0** (api compose catalog+clinical+crm+prescription; các module không import nhau). Gate cuối: ruff+format sạch, import-linter **11/0**, mypy strict **161 file**, pytest **304** (+21). **Nợ còn treo:** ghi `MedicationHistoryEntry` từ event (chưa); dị ứng OTC (hoãn); UI cảnh báo + audit dị ứng riêng (chờ spec). **⇒ Sprint 6 chỉ còn `procurement`. DỪNG theo lệnh.** |
| 2026-07-22 | **Feature flag AI theo tenant (SaaS) — XONG hoàn toàn.** `clinical.TenantAiSettings` (entity mới, `tenant_id`+`enable_clinical_ai=False` mặc định) + port `TenantAiSettingsRepository` + ORM `TenantAiSettingsORM`/`SqlAlchemyTenantAiSettingsRepository`. **Tự quyết (báo lý do)** tạo bảng riêng trong `clinical` thay vì tái dùng `compliance.tenant_compliance_configs`: tái dùng sẽ là cross-module thật (vi phạm `module-independence` hoặc cần bước Opus-gated, trái với yêu cầu "không cross-module mới"), và 2 khái niệm không liên quan (mã pháp lý DAV vs cờ tính năng sản phẩm). `ClinicalService.check_interactions` gọi `_ensure_ai_enabled(ctx)` ngay sau `require_permission` — đọc tenant từ `RequestContext` sẵn có, chưa cấu hình → `FeatureDisabledError` (mới, 403). Chỉ `check_interactions` bị chặn, không chặn đọc/duyệt bản ghi AI cũ. Thêm `get_tenant_ai_settings`/`set_tenant_ai_settings` + `GET`/`PUT /clinical/settings`. Xoá `AISettings.enable_clinical_ai` (cờ chết, chưa từng được đọc) khỏi `core/config.py`; giữ `min_confidence` (tham số toàn triển khai, không phải cờ theo tenant). Cập nhật test cũ vỡ do đổi mặc định (autouse fixture bật AI trong `test_clinical_flow.py`; fixture `client_ai_off` mới trong e2e). Migration `0010_clinical_tenant_ai_settings`: autogenerate→apply **live Postgres**→`alembic check` sạch→downgrade→upgrade lại→**check sạch lại**; xác nhận thủ công qua ASGI app (403→200→tắt lại). Gate: ruff+format sạch, import-linter **11/0** (không đổi, không cross-module mới), mypy strict **161 file**, pytest **283** (+9). **DỪNG theo lệnh — CHƯA làm procurement.** |
| 2026-07-22 | **`crm.add_allergy` — gỡ gap 500→404 khi `ingredient_id` sai.** Sếp yêu cầu validate qua `ActiveIngredientRepository` giống `CatalogService.create_drug` — nhưng đó là cross-module thật (crm phụ thuộc catalog), đúng loại bước quy tắc của sếp bắt Opus+phiên riêng (S4.5/S5.4/C.5); đã hỏi trước (AskUserQuestion), sếp chọn phương án không cross-module: `CrmService.add_allergy` bắt `sqlalchemy.exc.IntegrityError` quanh `repo.update()`, dịch thành `NotFoundError` (404) — an toàn 100% vì `customer_id` đã xác nhận tồn tại trước đó nên FK `ingredient_id` là ràng buộc duy nhất còn có thể vỡ. FK Postgres giữ nguyên làm nguồn enforcement thật. **Sửa kèm bắt buộc:** `core/db/session.build_engine()` bật `PRAGMA foreign_keys=ON` cho SQLite (mặc định tắt) — nếu không test sẽ không bao giờ thấy được bug này (chỉ lộ trên Postgres sống); áp dụng cả app thật lẫn `conftest.py` fixture; chỉ ảnh hưởng dialect SQLite. Xác nhận thủ công qua ASGI app chạy trên Postgres sống: `ingredient_id` ngẫu nhiên → 404 problem+json đúng. Test mới (+2): `test_add_allergy_unknown_ingredient_404_not_500` (repo) + `test_unknown_ingredient_id_rejected_with_404_not_500` (e2e). `add_condition` không có gap tương tự (không có FK). Gate: ruff+format sạch, import-linter **11/0**, mypy strict **161 file**, pytest **274** (+2, chạy lại toàn bộ để xác nhận FK-enforcement mới không phá test nào khác — an toàn vì chưa có use-case xoá Drug/Customer nào). |
| 2026-07-22 | **Module `crm` — app+infra+migration `0009`+interface HTTP, XONG hoàn toàn.** `SqlAlchemyCustomerRepository` (tenant-scoped) + ORM `CustomerORM`/`CustomerAllergyORM`/`CustomerConditionORM`/`CustomerMedicationHistoryORM` + mapper (reconcile theo id-diff ở `update()` vì collection con chỉ insert-only). **Quyết định đáng chú ý:** `CustomerAllergyORM.ingredient_id` có FK thật tới `active_ingredients.id` — FK xuyên module đầu tiên trong codebase (khác hẳn `SaleLine.drug_id` không FK), nhưng an toàn với `module-independence` vì FK chỉ là string bảng trong DDL, không cần import ORM catalog; `active_ingredients` là bảng global nên không rủi ro xuyên tenant. Lưu ý: SQLite test harness không enforce FK (không bật `PRAGMA foreign_keys=ON`) nên chỉ Postgres sống mới thật sự chặn `ingredient_id` sai — đã tránh viết test dựa vào nhánh này. `CrmService` (create_customer/add_allergy/add_condition/get_customer/list_customers) theo khuôn `_get_or_404`+mutate-rồi-update() của `PrescriptionService`; quyền `crm.create`/`crm.read`/`crm.write`. Interface đủ: `router.py`/`schemas.py`/`register.py`, `/customers`+`/customers/{id}/allergies`+`/customers/{id}/conditions`, wire vào `api/v1/__init__.py` (đơn giản, không cross-module). Migration `0009_crm_customers`: autogenerate→apply **live Postgres**→`alembic check` sạch→downgrade→upgrade lại→**check sạch lại**. Test: `test_crm_repo.py` (+10) + `test_crm_api_e2e.py` (+4). **KHÔNG cross-module** — không nối dị ứng KH vào clinical (để dành Bước 2, cần Opus). Gate: ruff+format sạch, import-linter **11/0** (không đổi contract), mypy strict **161 file**, pytest **272** (+14). **DỪNG theo lệnh — CHƯA nối dị ứng KH vào clinical.** |
| 2026-07-22 | **Module `crm` — domain thuần.** Trước khi code: đối chiếu ROADMAP.md §Sprint 6 + docs/13 Phụ lục XXI, phát hiện `compliance.CustomerDetail` (VO bất biến, không id, gắn vào 1 dòng sổ kiểm soát) và `crm.Customer` dự kiến (master data có id) chỉ trùng 2 field tên/địa chỉ — hỏi sếp qua AskUserQuestion trước khi code, **chốt: tách biệt hoàn toàn, không liên kết** (xem §7e). `crm/domain/entities.py`: `Customer` (aggregate root, không tự mang `tenant_id`, giống `Drug`) + `Allergy` (**theo `ingredient_id`**, không phải tên thuốc tự do — khớp `catalog.ActiveIngredient` S6 Bước 1 + kiểu ingredient-based của `clinical.DrugInteraction`; `add_allergy()` chặn trùng hoạt chất) + `Condition` (mã ICD-10, chặn trùng mã) + `MedicationHistoryEntry` (tối giản: `drug_id`+`quantity>0`+`source`(SALE/PRESCRIPTION)+`ref_id`+`occurred_at`, theo khuôn `ref_type`/`ref_id` của `inventory.StockMovement` — chỉ là hình dạng, chưa nối event `SaleCompleted`/`PrescriptionDispensed`). Port `CustomerRepository` khai trong domain, chưa impl. Contract mới `crm-domain-innermost` + `crm` vào `module-independence` (10→**11**, không đổi 10 cái cũ). Test: `test_crm_domain.py` (+9). **KHÔNG cross-module** — không đụng clinical/sales/compliance. Gate: ruff+format sạch, import-linter **11/0**, mypy strict **150 file**, pytest **258** (+9). **DỪNG theo lệnh — CHƯA làm app+infra+migration crm.** |
| 2026-07-22 | **S6 Bước 1 tiếp · app+infra+migration `0008` hoạt chất — Bước 1 XONG hoàn toàn.** `SqlAlchemyActiveIngredientRepository` (global, session-only, giống khuôn `SqlAlchemyDrugInteractionRepository`) impl `add`/`get`/`find_by_name`/`list`. ORM `ActiveIngredientORM` (`active_ingredients`, **thêm `UniqueConstraint(name)`** — quyết định kỹ thuật để bảo vệ bất biến mà `find_by_name` giả định, không phải yêu cầu spec) + `DrugIngredientORM` (`drug_ingredients`, FK `drugs.id` CASCADE + FK `active_ingredients.id`) + quan hệ `DrugORM.ingredients`. Mapper `Drug` mở rộng roundtrip `ingredients`. `CatalogService` thêm tham số `ingredient_repo_factory`; `create_drug` validate `ingredients[].ingredient_id` tồn tại (else `NotFoundError`) trước khi `add_ingredient()` (bắt `DuplicateIngredientError`/`InvalidIngredientError` → `ValidationError`, giống khuôn `units`). **Interface (tuỳ chọn, đã làm):** `CreateDrugRequest`/`DrugResponse` mở rộng `ingredients` — **không** thêm endpoint CRUD `active_ingredients` riêng (ngoài phạm vi giao; hoạt chất phải có sẵn qua repo/seed trước, ghi TODO). Migration `0008_catalog_ingredients`: autogenerate→apply **live Postgres**→`alembic check` sạch→downgrade→upgrade lại→**check sạch lại**. Test: `test_catalog_repo.py` (+4: roundtrip tạo thuốc kèm hoạt chất thật, 404 khi `ingredient_id` lạ, 422 khi trùng hoạt chất cùng request, `find_by_name`/`list`). Trước khi code: `docker compose ps` phát hiện 2 container Exited dù PROJECT_STATE ghi "đang chạy" — đã `up -d` lại + sửa 4 chỗ trong tài liệu ghi rõ đây là ảnh chụp tại thời điểm, không phải trạng thái sống (xem đầu file). **KHÔNG động clinical/compliance/10 contract.** Gate: ruff+format sạch, import-linter **10/0**, mypy strict **145 file**, pytest **249** (+4). **⇒ Sprint 6 Bước 1 XONG hoàn toàn — điều kiện phụ thuộc Bước 2 (5.5.4) đã đủ. DỪNG — CHƯA sang Bước 2 (cần Opus + phiên riêng).** |
| 2026-07-22 | **S6 Bước 1 · Mô hình hoạt chất trong `catalog` — domain thuần.** Mở Sprint 6. `catalog/domain/entities.py`: `ActiveIngredient` (hoạt chất — reference toàn cục KHÔNG tenant-scope, `id`+`name`+`name_en?`, guard tên rỗng) + `DrugIngredient` (hàm lượng — `ingredient_id`+`amount: Decimal>0`+`unit`, docs/03 `drug_ingredients`). `Drug` aggregate thêm `ingredients: list[DrugIngredient]` (default `[]`, tương thích ngược, không đổi hành vi/infra hiện có) + `add_ingredient()` chặn trùng `ingredient_id` (1 thuốc nhiều hoạt chất — thuốc phối hợp, VD amoxicillin+acid clavulanic — là bình thường, không phải edge case). Exceptions `InvalidIngredientError`/`DuplicateIngredientError`. Port `ActiveIngredientRepository` khai trong domain (add/get/find_by_name/list), **chưa impl** (infra để bước sau). Đối chiếu docs/13_COMPLIANCE_SPEC.md mục B field 4 (`ten_hoat_chat`, "chỉ ghi khi ≤3 dược chất") xác nhận đúng thực tế đa hoạt chất; **KHÔNG động vào `compliance`/`clinical`** — `ten_hoat_chat` vẫn string tự do (là DTO xuất định dạng theo QĐ540, không phải chỗ cần model quan hệ). Test: `test_catalog_domain.py` (+8). Gate: ruff+format sạch, import-linter **10/0** (không đổi contract), mypy strict **145 file**, pytest **245** (+6). **DỪNG — CHƯA sang app+infra+migration, CHƯA sang Bước 2 (5.5.4).** |
| 2026-07-22 | **S5.5 (5.5.3) · Clinical interface HTTP — SPRINT 5 DONE ở mức MOCK.** Interface: `clinical/interface/schemas.py` (Pydantic `CheckInteractionsRequest` với `field_validator` strip + chặn hoạt chất rỗng; `InteractionCheckResponse` = `findings[]` [ingredient_a/b, severity, mechanism, management, **source**] + `recommendation` [model, **confidence**, requires_review, output, sources, accepted_by, created_at]), `router.py` (`POST /clinical/check-interactions`, `GET /clinical/recommendations/{id}`, `POST /clinical/recommendations/{id}/accept`), `register.py`. DI: `bootstrap` đăng ký `LLMProvider → MockLLMProvider` (`# BLOCKER: AI__API_KEY thật` — điểm swap `AnthropicProvider`); `api/v1/__init__.py` nối `register_clinical`. Test **e2e HTTP thật** `test_clinical_api_e2e.py` (6): kiểm response có **nguồn + confidence**, `model=mock-llm` (không API thật), xếp severity MAJOR→MODERATE, accept 200 rồi lại 409 (problem+json), schema 422. **DoD Sprint 5 đạt qua mock**; AI/RAG thật + auto-check cross-module (5.5.4) vẫn blocker → Sprint 6. Gate: ruff+format sạch, import-linter **10/0** (không đổi contract), mypy strict **145 file**, pytest **239** (+6). **DỪNG — không tự mở Sprint 6.** |
| 2026-07-22 | **S5.5 (5.5.2) · Clinical app+infra+migration `0007` (mock LLM).** App: `ClinicalService.check_interactions` (engine tất định trên bảng `drug_interactions` → LLM chỉ diễn giải → ghi 1 `AiRecommendation` bất biến với `requires_review` = guardrail dược sĩ), `get_recommendation`, `accept_recommendation` (human-in-the-loop; 404 lạ, 409 nếu đã duyệt) + DTO. Infra: ORM `DrugInteractionORM` (global, `uq` cặp canonical) + `AiRecommendationORM` (tenant-scoped, `output`/`sources` jsonb-variant PG/JSON SQLite, chỉ `accepted_by` mutate) + mapper + repo (interaction repo không tenant-scope). Kernel: `core/ai/MockLLMProvider` — KHÔNG gọi API, deterministic, sync `complete/stream/embed` (`# BLOCKER: AI__API_KEY thật`). Migration `0007_clinical` (2 bảng, index+unique): autogenerate→apply **live Postgres**→`alembic check` sạch→downgrade→upgrade→**check sạch lại**. Seed `seed_drug_interactions` (5 cặp **mẫu**, source `SAMPLE — không phải nguồn chính thức`, idempotent theo cặp — live PG 5→0). Quyền mới `clinical.check`/`clinical.accept` (dev context + system-permission test). **Quyết định (ghi TODO):** KHÔNG thêm mô hình hoạt chất vào catalog (chờ sếp: thêm ngay hay tách sprint); HOÃN bảng `drug_knowledge_chunks` (pgvector phá SQLite test-harness + là blocker RAG) sang khi làm RAG thật. Gate: ruff+format sạch, import-linter **10/0** (không đổi contract), mypy strict **141 file**, pytest **233** (+15). **DỪNG, CHƯA sang 5.5.3.** |
| 2026-07-21 | **Compliance · C.4 — NationalSyncLog + MockAdapter (DỪNG báo cáo, chờ duyệt C.5).** Domain: entity `NationalSyncLog` (state machine `PENDING`→`SENT`→`ACK`/`FAILED`, `FAILED` gửi lại được, `retry_count` đếm lỗi) + enum `SyncPayloadType`/`SyncStatus`; port thuần `NationalDrugDbGateway` + DTO `SyncRequest`/`SyncAck` (mục D). Application: `NationalSyncService.push_payload` (idempotent theo `client_uuid`; best-effort — gateway từ chối/ném lỗi ghi `FAILED` không ném ra ngoài) + `get_sync_log`; chỉ lưu `payload_hash` (sha256), KHÔNG lưu payload thô. Infra: ORM+mapper+repo tenant-scoped + migration `0006_national_sync_log`. **Composition root** `api/v1/national_sync.py`: `MockNationalDrugDbGateway` (log + ACK giả, `# BLOCKER: DAV API spec`, KHÔNG endpoint thật) + `wire_national_sync(container)` đăng ký service vào `build_api_router`. Migration autogenerate→apply **live Postgres**→`alembic check` sạch→downgrade/upgrade OK. Gate: ruff sạch, import-linter **9/0** (MockAdapter ở `api`, không phá module-independence), mypy strict 126 file, pytest **187** (+19). Chưa cross-module/event subscription (đó là C.5). **Dừng phiên theo lệnh, chờ duyệt C.5.** |
| 2026-07-21 | **Compliance · C.3 — Schemas + validators (DỪNG báo cáo tổng kết, chờ duyệt C.4/C.5).** `interface/schemas.py`: `RecordControlledEntryRequest` với `model_validator` cho rule C.3 (XUAT controlled cần khách hàng; GN/HT cần thêm `prescription_code`, TC thì không; NHAP/category NONE bỏ qua) — defense-in-depth song song domain rule; `SetTenantComplianceConfigRequest` enforce cỡ 12 (Bảng 1 mục 22/23). `interface/export.py`: `to_national_drug_record_export` map `NationalDrugRecord` → `NationalDrugRecordExport` (23 field) dùng đúng converter helpers, enforce cỡ tối đa Bảng 1 QĐ540. Chưa có router/endpoint HTTP. Gate: ruff sạch, import-linter **9/0**, mypy strict 124 file, pytest **168** (+13). **C.1–C.3 xong — dừng phiên theo lệnh, chờ duyệt C.4 (MockAdapter, Opus) / C.5 (cross-module, Opus, từng bước).** |
| 2026-07-21 | **Compliance · C.2 — Application + infrastructure + migration `0005_compliance`.** `ComplianceService`: `record_controlled_entry` (validate GN/HT cần `prescription_code`, TC thì không, chỉ áp dụng chiều XUAT) / `get_ledger_entry` / `set_tenant_config` (upsert) / `get_tenant_config`. ORM `controlled_ledger_entries` (hợp nhất cột Phụ lục VIII+XXI, `customer_name`/`customer_address` nullable cùng bảng) + `tenant_compliance_configs` (entity mới, tenant_id unique) + mapper + repo tenant-scoped. Cùng migration: bật `uq_drugs_tenant_registration_no` trên bảng `drugs` có sẵn (nợ kỹ thuật TODO.md). Autogenerate→apply **live trên Postgres**→`alembic check` không drift→downgrade→upgrade lại→sạch. Đăng ký `models_registry`. Gate: ruff sạch, import-linter **9/0**, mypy strict 121 file, pytest **155** (+11). Chưa wiring API. |
| 2026-07-21 | **Compliance · C.1 — Domain thuần (kéo sớm từ Sprint 7 theo yêu cầu pháp lý QĐ1867).** Module `compliance` lớp domain, bám sát [docs/13_COMPLIANCE_SPEC.md](docs/13_COMPLIANCE_SPEC.md) đã khóa spec (đối chiếu văn bản gốc + code thật): `ControlledSubstanceCategory` (7 giá trị, TT20/2017 Điều 3); `NationalDrugRecord` value object 23 trường Bảng 1 QĐ540 (mapping `so_lo`→`lot_no`, `don_vi_dong_goi_nn`→`Drug.base_unit` — đã sửa theo spec, không phải `batch_no`/`DrugUnit`); `ControlledLedgerEntry` + `CustomerDetail` (Phụ lục XXI — chỉ tên+địa chỉ, không CCCD); converter helpers `to_qld_date`/`to_qld_datetime`/`to_qld_code` (đã sửa: bỏ dấu tiếng Việt, khớp đúng ví dụ văn bản gốc `VN-12345-18-lọ 200 viên`→`VN1234518lo200vien`); rule `validate_controlled_sale` (GN/HT bắt buộc `prescription_code`, TC thì không) + `validate_etc_sale` dưới cờ `EtcPrescriptionPolicy` (mặc định **tắt** — nguồn C.3.1 chưa xác định, giữ TODO thay vì xóa); read-port `DrugMasterProvider`. Contract mới `compliance-domain-innermost`; `compliance` vào `module-independence`. Gate: ruff sạch, import-linter **9/0**, mypy strict 114 file, pytest **144** (+26). Chưa wiring, chưa infra — tiếp C.2 (migration `0005_compliance`). |
| 2026-07-21 | **Sprint 5 · S5.3 — Prescription interface + API (DỪNG báo cáo tổng kết).** Router/schemas Pydantic; `POST /api/v1/prescriptions` (201), `GET /api/v1/prescriptions/{id}`, `POST /api/v1/prescriptions/{id}/validate`, `POST /api/v1/prescriptions/{id}/reject`, `POST /api/v1/prescriptions/{id}/dispense`. `register()` wiring service + include vào `api/v1`; quyền `rx.create`/`rx.read`/`rx.approve`/`rx.dispense` (deps dev + ctx test). Chưa cross-module (chưa nối `prescription_ref` trên `SalesOrder`, chưa clinical). Gate: ruff sạch, import-linter **8/0**, mypy strict 107 file, pytest **118** (+6 e2e). **S5.1–S5.3 xong — dừng phiên theo lệnh, chờ duyệt S5.4/S5.5.** |
| 2026-07-21 | **Sprint 5 · S5.2 — Prescription application + infrastructure.** `PrescriptionService`: create/validate/reject/dispense/get, phát `PrescriptionValidated`/`PrescriptionRejected`/`PrescriptionDispensed` sau commit. ORM `prescriptions`/`prescription_items` + mapper + repo tenant-scoped (`update()` để ghi lại trạng thái sau fetch). Migration `0004_prescription` — autogenerate→apply **live trên Postgres**→`alembic check` không drift→downgrade/upgrade OK. Đăng ký `models_registry`. Gate: ruff sạch, import-linter **8/0**, mypy strict 103 file, pytest **112** (+6). Chưa wiring API. |
| 2026-07-21 | **Sprint 5 · S5.1 — Prescription domain thuần.** Module `prescription` lớp domain: `Prescription` aggregate (`DRAFT`→`VALIDATED`→`DISPENSED`, hoặc →`REJECTED` từ `DRAFT`/`VALIDATED`), `PrescriptionItem`, `PrescriptionSource`/`PrescriptionStatus`, events `PrescriptionValidated`/`PrescriptionRejected`/`PrescriptionDispensed`, exceptions, `PrescriptionRepository` port. Contract mới `prescription-domain-innermost`; `prescription` vào `module-independence`. Gate: ruff sạch, import-linter **8/0**, mypy strict 96 file, pytest **106** (+12). Chưa wiring, chưa infra. |
| 2026-07-21 | **Sprint 4 · S4.5 — Chặn ETC end-to-end (RỦI RO CAO, đạt).** Port `DrugInfoProvider` + DTO `DrugInfo` (sales.domain); adapter `CatalogDrugInfoProvider` (lớp `api`, đọc `CatalogService`); `SalesService` ghi đè `requires_prescription` theo catalog khi biết thuốc (thuốc lạ → fallback cờ client). Catalog thành nguồn thẩm quyền: client khai gian OTC↔ETC đều bị ghi đè. **sales vẫn không import catalog** (nối ở `api`). Gate: ruff sạch, import-linter **7/0**, mypy strict 90 file, pytest **94** (+6). **Backend Sprint 4 hoàn thành (S4.1–S4.5); FE S4.6 tách đợt sau.** |
| 2026-07-21 | **Sprint 4 · S4.4 — Cross-module: sale → inventory dispense (RỦI RO CAO, đạt).** Handler `api/v1/cross_module.py` subscribe `SaleCompleted` → `InventoryService.dispense_for_sale` (FEFO) dưới system-context. Idempotent cấp đơn qua `MovementRepository.exists_for_ref(ref_type="sale", ref_id=order_id)`. Thiếu tồn → xuất phần có sẵn (tồn không âm) + event `StockShortfallDetected`, không chặn bán (đơn đã COMPLETED). **`module-independence` KEPT** (nối ở lớp `api`, sales/inventory không import nhau). Gate: ruff sạch, import-linter **7/0**, mypy strict 90 file, pytest **88** (+7). Không migration mới. |
| 2026-07-21 | **Sprint 4 · S4.3 — Sales interface + API.** Router/schemas Pydantic; `POST /api/v1/sales` (201), `GET /api/v1/sales/{id}`, `POST /api/v1/sync/sales` (idempotent 200, upsert). `register()` wiring service + include vào `api/v1`; quyền `sales.read`/`sales.create` (deps dev + ctx test). Chưa cross-module (SaleCompleted chưa có subscriber → chưa trừ kho). Gate: ruff sạch, import-linter **7/0**, mypy strict 89 file, pytest **81** (+5 e2e). **DỪNG chờ duyệt S4.4.** |
| 2026-07-21 | **Sprint 4 · S4.2 — Sales application + infrastructure.** `SalesService.complete_sale` idempotent theo `client_uuid` (re-sync trả đơn cũ, **không** phát lại `SaleCompleted`) + `get_sale`. ORM `sales_orders`/`sale_lines`/`sale_payments` + mapper + repo tenant-scoped. Migration `0003_sales` (unique `tenant_id`+`client_uuid`) — autogenerate→apply→`alembic check` sạch→reversible (SQLite). Đăng ký models_registry. Gate: ruff sạch, import-linter **7/0**, mypy strict 85 file, pytest **76** (+7). Chưa wiring API/cross-module. |
| 2026-07-21 | **Sprint 4 · S4.1 — Sales domain thuần.** Module `sales` lớp domain: `SalesOrder` aggregate (DRAFT→COMPLETED→PARTIALLY_RETURNED/RETURNED), `SaleLine`/`Payment`/returns, `SaleStatus`/`PaymentMethod`, event `SaleCompleted`+`SoldItem`, exceptions, `SalesRepository` port, rule thuần `ensure_rx_for_etc`. Contract mới `sales-domain-innermost`; `sales` vào `module-independence`. Gate: ruff sạch, import-linter **7/0**, mypy strict 78 file, pytest **69** (+15). Chưa wiring, chưa infra. |
| 2026-07-21 | **Demo & Self-Refine.** Thêm `demo_preview.py` (xem trước sản phẩm, chạy end-to-end SQLite in-memory, trung thực về phạm vi — clinical đánh dấu CHƯA làm). Self-refine `modules/`: docstring use-case + `signed_quantity`; thêm `test_edge_cases.py` (8 test: qty=0, demand=0, lô rỗng, on_hand thuốc lạ, barcode trùng/khác tenant). Tạo `TODO.md`. Gate: 54 test, mypy strict 92 file, import-linter 6/0. |
| 2026-07-21 | **Sprint 3 HOÀN THÀNH.** Module `catalog` + `inventory` (Hexagonal, event-sourced, FEFO thuần). API v1 drugs/inventory. Migration `0002` (6 bảng) live + reversible, `alembic check` sạch. Seed ATC idempotent. Contract mới: domain-purity + module-independence. 46 test, domain coverage 97%, mypy strict 92 file, import-linter 6/0. |
| 2026-07-21 | **Quản trị pre-Sprint 3.** Chốt giấy phép **Apache-2.0** (thêm `LICENSE`, `NOTICE`, metadata pyproject). Commit git đầu tiên `c6fc698` (74 file, branch `main`); working tree sạch. |
| 2026-07-21 | **Sprint 2 HOÀN THÀNH.** Hiện thực kernel backend (config, DI, event bus, UoW, security, audit, AI port, plugin loader, errors, API v1 + health, Alembic `0001`). CI + docker-compose + Makefile. Gate xanh: pytest 21, mypy strict 35 file, ruff/format, import-linter 3/0; docker+migration chạy live. Cập nhật README/ROADMAP/PROJECT_STATE. |
| 2026-07-21 | Khởi tạo dự án. Hoàn thành Sprint 1: 15 tài liệu thiết kế. Chốt stack, kiến trúc, ERD, module, plugin, AI, config, API. README/ROADMAP/PROJECT_STATE hoàn chỉnh. |

---

## 9. Tuyên bố kết thúc Sprint 6 (backend)

> ✅ **Sprint 6 (Procurement & CRM, backend) đạt Definition of Done lõi.**
> **Nhập PO → GRN xác nhận → tạo lô inventory** (cross-module, idempotent theo `grn_id`; va chạm lô/lỗi ghi `stock_reconciliation_needed`) · **cờ AI cấu hình theo từng tenant** (`TenantAiSettings`) · nền hoạt chất `catalog` + auto-check tương tác/dị ứng KH (warn-only) · module `crm` đủ 4 lớp · module `procurement` đủ 4 lớp.
> Commit chính phiên procurement `55d2586`(domain)→`518dafe`(app/infra/migration `0011`)→`7a53457`(interface)→cross-module (commit tiếp) · **372 test xanh** · import-linter **12/0** (mọi cross-module nối ở composition root `api/v1/`, `module-independence` giữ nguyên) · mypy strict **178 file** · migration `0008`..`0012` live/reversible/no-drift.
> **Còn nợ (sang Sprint 7):** ghi `MedicationHistoryEntry` từ event bán/cấp phát (DoD có nhắc "lịch sử KH" — sếp đã hoãn), dị ứng OTC (cần `customer_id` trên `SalesOrder`), enhancement gộp lô (PA B), outbox/retry bền, API resolve `stock_reconciliation_needed` — xem §7i + [TODO.md](TODO.md).
> Bước kế tiếp: **Sprint 7 — Compliance & Analytics** (compliance C.1–C.5 đã kéo sớm & đóng; còn lại chủ yếu `analytics`). **Không tự động chuyển sprint** — chờ lệnh mở.

<details><summary>Lịch sử: Tuyên bố kết thúc Sprint 4 (backend)</summary>

> ✅ **Sprint 4 (backend) đạt Definition of Done.**
> Bán → tồn giảm đúng FEFO · re-sync cùng `client_uuid` **không nhân đôi** tồn/đơn · ETC thiếu đơn bị chặn (422, catalog là thẩm quyền) · bán quá tồn không làm tồn âm (`StockShortfallDetected`).
> 5 commit `d4e7029`→`85aa6d4` · **94 test xanh** · import-linter **7/0** (2 điểm cross-module nối ở composition root, `module-independence` giữ nguyên) · mypy strict 90 file · migration `0003` không drift/reversible.
> **Còn nợ:** S4.6 FE (tách đợt sau), persist trả hàng, 3 nợ cũ — xem [TODO.md](TODO.md).
> Bước kế tiếp: **Sprint 5 — Prescription & Clinical AI**. **Không tự động chuyển sprint** — chờ lệnh mở.

</details>

<details><summary>Lịch sử: Tuyên bố kết thúc Sprint 3</summary>

> ✅ **Sprint 3 đạt Definition of Done.** Nhập lô → tồn kho phản ánh · FEFO chọn đúng lô cận date · 46 test xanh · domain coverage 97% · import-linter 6/0 · mypy strict · migration `0002` live/reversible · seed ATC idempotent.

</details>
