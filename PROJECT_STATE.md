# PROJECT_STATE — AI Pharmacy OS

> Nguồn sự thật về **trạng thái hiện tại** của dự án. Cập nhật mỗi khi có thay đổi quan trọng.
> Cập nhật cuối: **2026-07-23** · Sprint hiện tại: **Sprint 6 (Procurement & CRM) — ✅ ĐÓNG (DoD lõi đạt): `procurement` đủ 4 lớp + cross-module GRN→inventory tạo lô (migration `0012`), `crm`, feature-flag AI theo tenant, hoạt chất — tất cả XONG** · Sprint 5 DONE mức MOCK ✅ song song **Compliance (kéo sớm từ Sprint 7): C.1–C.5 XONG ✅ — Sprint Compliance đóng**.
>
> **Kế tiếp (2026-07-23):** các tính năng thương mại **hồ sơ KH · tích điểm KH · in bill** (ngoài ROADMAP gốc) phải đi qua **[docs/14_FEATURE_PROCESS.md](docs/14_FEATURE_PROCESS.md)** (Compliance/Privacy by Design) trước khi code. Đã neo quy trình + phát hiện **2 blocker nền**: (1) RBAC/IAM vẫn dev-header, IAM chưa dựng → chặn hồ sơ KH + tích điểm; (2) `docs/legal/` thiếu Luật BVDLCN 91/2025, Luật Dược, NĐ 356/2025, GPP. **✅ In bill (S7) đã XONG đủ 4 lớp** (domain→app→infra→interface, commit `4a5bc0b`→`53e31b3`, 380 test xanh) — resume sau crash hạ tầng (§8, entry 2026-07-23 đầu). **Còn lại: hồ sơ KH + tích điểm KH vẫn chờ RBAC/IAM thật trước (xem §7j).** Sprint 7 (Analytics) vẫn chưa mở.

> ⚠️ **Lưu ý vận hành — trạng thái docker/hạ tầng trong tài liệu này là ảnh chụp tại thời điểm ghi, KHÔNG phải trạng thái sống.**
> Container có thể tự `Exited` giữa các phiên dù tài liệu ghi "đang chạy"/"healthy" (đã xảy ra 2026-07-22: postgres Exited 5h,
> redis Exited 18h dù §7b ghi "đang chạy healthy"). **Luôn chạy `docker compose ps` để xác nhận thực tế mỗi khi resume phiên —
> không tin nội dung mục "Hạ tầng dev"/"Hạ tầng còn mở" trong tài liệu.**

---

## 1. Trạng thái tổng quan

| Hạng mục          | Trạng thái                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| Giai đoạn         | Giai đoạn 2 — Bán hàng · (Compliance kéo sớm từ Giai đoạn 3)                                          |
| Sprint            | Sprint 6 — Procurement & CRM (backend) **✅ ĐÓNG** · Sprint 5 (Prescription & Clinical AI) DONE mức mock · **+ Compliance (docs/13, kéo sớm từ Sprint 7)** |
| Tình trạng Sprint | ✅ **Sprint 6 ĐÓNG (DoD lõi đạt).** Bước 1 (hoạt chất) + **`crm`** (migration `0009`) + **Bước 2** (5.5.4 auto-check + dị ứng KH) + **feature-flag AI theo tenant** (migration `0010`) + **`procurement` đủ 4 lớp** (migration `0011`) + **cross-module GRN xác nhận → inventory tạo lô** (migration `0012`, idempotent theo `grn_id`, va chạm lô/lỗi khác ghi `stock_reconciliation_needed`) — tất cả XONG. ✅ Sprint 5 DONE mức mock. ✅ Compliance: **C.1–C.5 XONG**, Sprint đóng. **Nợ mang sang Sprint 7:** ghi `MedicationHistoryEntry` từ event bán/cấp phát (DoD Sprint 6 nhắc, sếp đã hoãn); dị ứng OTC. |
| Kernel backend    | ✅ (Sprint 2)                                                                                          |
| Module nghiệp vụ  | ✅ `catalog` (Hexagonal 4 lớp + hoạt chất `ActiveIngredient`/`DrugIngredient` persist được, migration `0008`), `inventory`, `sales`, `prescription` (cross-module: sale→dispense, sale↔prescription-ref S5.4); ✅ `compliance` (C.1–C.5 đủ); ✅ `clinical` (S5.5 A1 đủ 4 lớp + auto-check tương tác/dị ứng cross-module + `TenantAiSettings` feature-flag theo tenant, router `/clinical/*` + `/clinical/settings`, mock LLM); ✅ `crm` (Hexagonal 4 lớp đủ: `Customer`/`Allergy`(theo hoạt chất, FK `active_ingredients`)/`Condition`/`MedicationHistoryEntry`, `CrmService`, router `/customers/*`, migration `0009`); ✅ `procurement` (Hexagonal 4 lớp đủ: `Supplier`/`PurchaseOrder`+`PurchaseOrderItem`/`GoodsReceiptNote`+`GoodsReceiptItem`, `ProcurementService`, router `/suppliers`+`/purchase-orders`+`/goods-receipts`, migration `0011`; **cross-module GRN confirmed → `inventory` tạo lô** ở composition root, migration `0012` bảng `stock_reconciliation_needed`) |
| Demo              | ✅ `demo_preview.py` — chạy end-to-end, trung thực (clinical đánh dấu CHƯA làm)                        |
| Self-Refine       | ✅ docstring use-case + edge-case test; xem [TODO.md](TODO.md)                                         |
| Chất lượng        | ✅ ruff · ✅ format · ✅ import-linter (**12/0**) · ✅ mypy strict (**178 file**) · ✅ pytest (**372**)    |
| Hạ tầng dev       | ✅ docker compose healthy (xác nhận `docker compose ps` 2026-07-22, up ~1h); ✅ alembic `0001`..`0012` (áp live Postgres, `0012` reversible/no-drift); ✅ seed ATC + tương tác mẫu idempotent |
| Sprint kế tiếp    | **Sprint 6 ĐÓNG** — kế tiếp **Sprint 7 (Compliance & Analytics)**: `compliance` C.1–C.5 đã kéo sớm & đóng (§7b), nên Sprint 7 còn lại chủ yếu **`analytics`** (dashboard, dự báo nhu cầu, đề xuất nhập → PO nháp) + report. **Chưa mở** — chờ lệnh. Nợ mang sang: `MedicationHistoryEntry` từ event, dị ứng OTC (§7g). |

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

> **Trạng thái tại đây:** Sprint 6 ĐÓNG (HEAD `82b8fde`, working tree code sạch). Đã **rà soát toàn diện S1→S6** (khớp, 4 lệch nhỏ chưa sửa — xem changelog 2026-07-23) và **neo quy trình thêm tính năng mới** `docs/14_FEATURE_PROCESS.md` + memory `feature_process_gate`. Các tính năng thương mại tiếp theo (**hồ sơ KH · tích điểm KH · in bill**) nằm NGOÀI ROADMAP gốc → **bắt buộc đi qua Bước 0-4 của docs/14 trước khi code.**

**Ưu tiên điểm bắt đầu — CHỜ SẾP QUYẾT giữa 2 hướng:**
- **Hướng 1 — RBAC/IAM thật trước:** dựng module IAM (users/roles/cấp JWT) thay dev-header. Là **điều kiện tiên quyết (Bước 1.5)** mở khóa **hồ sơ KH + tích điểm** (đều chạm PII nhạy cảm). Bản thân IAM cũng chạy qua docs/14.
- **Hướng 2 — In bill trước:** ít bị chặn hơn (chủ yếu dữ liệu giao dịch, ít PII nhạy cảm) → có thể tiến hành phiên tới. Vẫn cần xác nhận văn bản hóa đơn áp dụng (Bước 1.1) trước khi code.

**2 blocker nền (đã kiểm chứng 2026-07-23, chặn phần lớn công việc thực thi):**
1. **RBAC/IAM (Bước 1.5) CHƯA THỎA** — `api/deps.py` vẫn dev-header cho non-prod, IAM chưa dựng → không xây tính năng PII nhạy cảm trên nền này.
2. **Văn bản pháp lý thiếu (Bước 1.1/1.8)** — `docs/legal/` mới có QĐ540/QĐ1867/TT20; **cần sếp thả thêm** Luật BVDLCN 91/2025, Luật Dược hiện hành, NĐ 356/2025, GPP — không tự suy diễn.

**4 lệch đã báo cáo (sếp chốt sửa SAU khi xong 3 tính năng):** demo_preview.py lỗi thời (2 constructor thiếu tham số); TODO:158 procurement chưa tick; TODO:73 C.5 chưa tick; cây rỗng untracked `backend/backend/`.

> **Chưa code, chưa mở sprint** — chờ lệnh sếp. Đầu phiên sau: `docker compose ps` xác nhận hạ tầng thật (đừng tin mục "Hạ tầng dev").

---

## 8. Nhật ký thay đổi (Changelog)

| Ngày | Thay đổi |
|------|----------|
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
