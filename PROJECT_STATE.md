# PROJECT_STATE — AI Pharmacy OS

> Nguồn sự thật về **trạng thái hiện tại** của dự án. Cập nhật mỗi khi có thay đổi quan trọng.
> Cập nhật cuối: **2026-07-21** · Sprint hiện tại: **Sprint 5 (S5.1–S5.4 xong; S5.5 đang làm — bước 5.5.1 domain xong)** song song **Compliance (kéo sớm từ Sprint 7): C.1–C.5 XONG ✅ — Sprint Compliance đóng**

---

## 1. Trạng thái tổng quan

| Hạng mục          | Trạng thái                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| Giai đoạn         | Giai đoạn 2 — Bán hàng · (Compliance kéo sớm từ Giai đoạn 3)                                          |
| Sprint            | Sprint 5 — Prescription & Clinical AI (backend) · **+ Compliance (docs/13, kéo sớm từ Sprint 7)**     |
| Tình trạng Sprint | 🔄 Sprint 5: **S5.1–S5.4 xong**; **S5.5 đang làm** (5.5.1 domain `clinical` xong, mock-only). ✅ Compliance: **C.1–C.5 XONG**, Sprint đóng |
| Kernel backend    | ✅ (Sprint 2)                                                                                          |
| Module nghiệp vụ  | ✅ `catalog`, `inventory`, `sales`, `prescription` (Hexagonal 4 lớp; cross-module: sale→dispense, sale↔prescription-ref S5.4); ✅ `compliance` (C.1–C.5 đủ); 🔄 `clinical` (S5.5 domain thuần xong: interaction engine + AiRecommendation, mock-only) |
| Demo              | ✅ `demo_preview.py` — chạy end-to-end, trung thực (clinical đánh dấu CHƯA làm)                        |
| Self-Refine       | ✅ docstring use-case + edge-case test; xem [TODO.md](TODO.md)                                         |
| Chất lượng        | ✅ ruff · ✅ format · ✅ import-linter (**10/0**) · ✅ mypy strict (**133 file**) · ✅ pytest (**218**)    |
| Hạ tầng dev       | ✅ docker compose healthy; ✅ alembic `0001`..`0006`; ✅ seed ATC idempotent                             |
| Sprint kế tiếp    | **S5.5 bước 5.5.2** (app+infra+migration `0007_clinical`, mock LLM, xem §7c) — chờ lệnh tiếp. Compliance C.1–C.5 đã đóng (§7b). |

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

**Hạ tầng còn mở từ phiên này:** docker compose (postgres+redis) đang chạy — kiểm tra `docker compose ps` khi mở phiên mới; `make down` nếu không cần nữa. Migration hiện tại: `0001`→`0006` (`0006_national_sync_log` đã apply live trên Postgres, `alembic check` sạch, downgrade/upgrade reversible).

> **Nợ kỹ thuật mang sang (chưa chặn S5.4):** `api/deps.py` dev-header context tạm (thay bằng JWT thật ở Sprint 6); FK `drugs.atc_code`→`atc_codes` chưa bật; **persist trả hàng** (`register_return`, Sprint 4) chưa có use-case + trả tồn. (Uniqueness `registration_no` đã enforce ở Compliance C.2, xem §7b.) Chi tiết ở [TODO.md](TODO.md).

---

## 7b. Compliance C.1–C.5 (ĐÃ ĐÓNG — lưu vết để phiên sau nối lại nếu mở tiếp)

> **Trạng thái:** Compliance **C.1→C.4 xong** + **C.5 (5a thiết kế · 5b implement · 5c e2e) XONG — SPRINT COMPLIANCE ĐÓNG.** ✅
> **HEAD `main` = C.5 5c** (e2e), working tree **sạch**. **192 test xanh, 9 contract kept/0 broken**,
> mypy strict 127 file, ruff sạch. Migration `0001`→`0006` (không thêm migration ở C.5 — không có bảng/field mới).
> Docker compose (postgres+redis) **đang chạy healthy** — chỉ `docker compose ps` để xác nhận.
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

## 7c. S5.5 Clinical AI (đang làm — mock LLM only, để phiên sau nối lại ngay)

> **Trạng thái:** **5.5.1 (domain thuần `clinical`) XONG.** Còn 5.5.2 (app+infra+migration) → 5.5.3 (interface) → 5.5.4 (cross-module,
> KHÔNG làm trong lõi). Working tree sạch sau commit 5.5.1. **218 test xanh, 10 contract kept/0 broken**, mypy 133 file, ruff sạch.

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

**3 điểm BLOCKER đã ghi trong code (chưa gỡ được ở S5.5):**
- `# BLOCKER: AI__API_KEY thật` — sẽ đặt `AnthropicProvider`; 5.5.2 chỉ wire `MockLLMProvider`.
- `# BLOCKER: nguồn tri thức dược thật + bản quyền` — RAG over `drug_knowledge_chunks`; bảng tạo nhưng để trống/stub.
- `# BLOCKER: catalog chưa có mô hình hoạt chất` (`active_ingredients`/`drug_ingredients` trong ERD chưa implement) — chặn
  drug→ingredient resolution ⇒ auto-check ở sale/prescription (5.5.4) chờ dependency này + duyệt riêng (chung mạch dị ứng KH Sprint 6).

**Bước kế 5.5.2 (app+infra+migration):** `ClinicalService.check_interactions`/`accept_recommendation`; ORM+mapper+repo cho
`drug_interactions`+`ai_recommendations` (+`drug_knowledge_chunks` stub); migration `0007_clinical`; `MockLLMProvider` ở `core/ai`;
seed vài cặp tương tác **mẫu** (ghi rõ không phải nguồn chính thức). Quyền mới: `clinical.check`/`clinical.accept` (thêm vào dev context).

---

## 8. Nhật ký thay đổi (Changelog)

| Ngày | Thay đổi |
|------|----------|
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

## 9. Tuyên bố kết thúc Sprint 4 (backend)

> ✅ **Sprint 4 (backend) đạt Definition of Done.**
> Bán → tồn giảm đúng FEFO · re-sync cùng `client_uuid` **không nhân đôi** tồn/đơn · ETC thiếu đơn bị chặn (422, catalog là thẩm quyền) · bán quá tồn không làm tồn âm (`StockShortfallDetected`).
> 5 commit `d4e7029`→`85aa6d4` · **94 test xanh** · import-linter **7/0** (2 điểm cross-module nối ở composition root, `module-independence` giữ nguyên) · mypy strict 90 file · migration `0003` không drift/reversible.
> **Còn nợ:** S4.6 FE (tách đợt sau), persist trả hàng, 3 nợ cũ — xem [TODO.md](TODO.md).
> Bước kế tiếp: **Sprint 5 — Prescription & Clinical AI**. **Không tự động chuyển sprint** — chờ lệnh mở.

<details><summary>Lịch sử: Tuyên bố kết thúc Sprint 3</summary>

> ✅ **Sprint 3 đạt Definition of Done.** Nhập lô → tồn kho phản ánh · FEFO chọn đúng lô cận date · 46 test xanh · domain coverage 97% · import-linter 6/0 · mypy strict · migration `0002` live/reversible · seed ATC idempotent.

</details>
