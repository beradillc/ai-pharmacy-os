# PROJECT_STATE — AI Pharmacy OS

> Nguồn sự thật về **trạng thái hiện tại** của dự án. Cập nhật mỗi khi có thay đổi quan trọng.
> Cập nhật cuối: **2026-07-21** · Sprint hiện tại: **Sprint 5 (ĐANG CHẠY — S5.1 xong)**

---

## 1. Trạng thái tổng quan

| Hạng mục          | Trạng thái                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| Giai đoạn         | Giai đoạn 2 — Bán hàng                                                                                |
| Sprint            | Sprint 5 — Prescription & Clinical AI (backend)                                                       |
| Tình trạng Sprint | 🔄 **ĐANG CHẠY — S5.1 xong** (domain `prescription`); S5.2/S5.3 tiếp theo, S5.4/S5.5 chưa đụng          |
| Kernel backend    | ✅ (Sprint 2)                                                                                          |
| Module nghiệp vụ  | ✅ `catalog`, `inventory`, `sales` · 🔄 `prescription` (domain+app+infra xong, interface/API chưa)    |
| Demo              | ✅ `demo_preview.py` — chạy end-to-end, trung thực (clinical đánh dấu CHƯA làm)                        |
| Self-Refine       | ✅ docstring use-case + edge-case test; xem [TODO.md](TODO.md)                                         |
| Chất lượng        | ✅ ruff · ✅ format · ✅ import-linter (**8/0**) · ✅ mypy strict (**103 file**) · ✅ pytest (**112**)     |
| Hạ tầng dev       | ✅ docker compose healthy; ✅ alembic `0001`+`0002`+`0003`; ✅ seed ATC idempotent                       |
| Sprint kế tiếp    | Sprint 5 tiếp: S5.2 (app+infra+migration `0004`), S5.3 (interface+API) — cùng phiên; S5.4/S5.5 sau     |

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
| S5.3 | Prescription **interface + API**: `POST /prescriptions` (201), `GET /prescriptions/{id}`, `POST /prescriptions/{id}/validate`, `POST /prescriptions/{id}/reject`, `POST /prescriptions/{id}/dispense`; quyền `rx.create`/`rx.read`/`rx.approve`/`rx.dispense`. → **DỪNG báo cáo tổng kết**. | ⏳ |

**Ghi chú thiết kế:** module thuần, không phụ thuộc catalog/sales/clinical — `drug_id` trên `PrescriptionItem` chỉ là UUID tham chiếu
(không FK, giống `SaleLine.drug_id`). `/prescriptions/{id}/reject` là điểm khác nhỏ so với phác thảo ban đầu ở
[docs/11_API_DESIGN.md](docs/11_API_DESIGN.md) (chỉ liệt kê create/extract/validate/dispense) — thêm endpoint riêng cho `reject`
vì đây là 1 trong 3 hành động độc lập của dược sĩ trên state machine (docs/07 §4), tách khỏi `validate` cho rõ ràng REST + dễ test,
thay vì gộp chung bằng 1 flag `approved` trong `/validate`. Endpoint `/prescriptions/extract` (OCR/vision) **không làm** trong phiên
này — thuộc S5.5 Clinical AI.

**Bằng chứng S5.1:** `ruff` sạch · `import-linter` **8/0** · `mypy` strict **96 file** · `pytest` **106 passed** (+12 test domain prescription).
**Bằng chứng S5.2:** `ruff` sạch · `import-linter` **8/0** · `mypy` strict **103 file** · `pytest` **112 passed** (+6 integration: create→validate→dispense, reject từ DRAFT, chặn dispense chưa validate, chặn validate đơn rỗng). Migration `0004_prescription` (bảng `prescriptions`, `prescription_items`) autogenerate→apply **live trên Postgres** (docker compose)→`alembic check` không drift→downgrade/upgrade OK. Đăng ký `models_registry`.

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

## 7. Điểm bắt đầu Sprint 5 — Prescription & Clinical AI (để phiên sau nối lại ngay)

> **Trạng thái vào Sprint 5:** backend Sprint 4 DONE, HEAD `main` = commit doc Sprint-4-DONE, working tree sạch, 94 test xanh, 7 contract. Chưa khởi động Sprint 5.

**⚠️ Phải CHỐT trước khi code (blocker):**
- **Nguồn tri thức dược cụ thể cho RAG + bản quyền** (PROJECT_STATE §5 đã hẹn "trước Sprint 5"). Chưa có nguồn hợp pháp thì **không** seed `drug_knowledge_chunks` / không demo RAG.
- **`AI__API_KEY` thực** để chạy thử LLM (hiện test dùng `"test-key"`; config sẵn ở `AISettings`: `AI__MODEL_REASONING=claude-opus-4-8`, `AI__MODEL_FAST=claude-sonnet-5`).

**Hành động đầu tiên (2 phút để vào việc):** mở `backend/src/pharmacy_os/core/ai/provider.py` (port `LLMProvider` — đang chỉ có interface, chưa impl) và `docs/12_AI_INTEGRATION.md`; quyết impl adapter Anthropic trước hay module `prescription` (thuần domain, không cần AI) trước. **Khuyến nghị: làm `prescription` domain trước** (không phụ thuộc blocker AI/RAG), để có tiến độ ngay.

**Hạng mục Sprint 5** (từ [ROADMAP](ROADMAP.md)):
1. Module `prescription/`: state machine (nháp→xác thực→cấp phát), Hexagonal 4 lớp.
2. `core/ai`: impl `LLMProvider` (Anthropic), AI Gateway + guardrails.
3. RAG: pgvector (**đã bật từ migration `0001`**), chunk/embed `drug_knowledge_chunks`.
4. Module `clinical/`: rule engine tương tác thuốc + LLM diễn giải; kiểm liều / thay thế.
5. Trích xuất đơn từ ảnh (vision). Ghi `ai_recommendations` + human-in-the-loop.

**Hook code đã sẵn (không phải làm lại):**
- `core.ai.LLMProvider` port — `backend/src/pharmacy_os/core/ai/provider.py`.
- `Drug.is_prescription_required()` + `RxClass` (catalog) — phân loại ETC/CONTROLLED.
- **`SalesOrder.prescription_ref`** (mới ở Sprint 4) — chỗ để nối đơn thuốc ↔ đơn bán.
- ERD `drug_interactions`, `drug_knowledge_chunks`, `ai_recommendations` — [docs/03](docs/03_DATABASE_ERD.md).
- pgvector + pgcrypto đã bật live (migration `0001`).

**Khuôn mẫu bắt buộc giữ (theo Sprint 3–4):**
- Mỗi module mới (`prescription`, `clinical`) = Hexagonal 4 lớp; thêm contract `<mod>-domain-innermost` + đưa vào `module-independence` (7 → 9 contract).
- Cross-module (vd `PrescriptionDispensed` → sales/inventory, hay clinical đọc catalog/crm) **nối ở composition root** `api/v1/cross_module.py` — không để module import module (đã có tiền lệ Sprint 4).
- Mỗi bước = 1 commit chạy được, 3 cổng xanh (pytest + mypy strict + import-linter), cập nhật PROJECT_STATE sau commit.

> **Nợ kỹ thuật mang sang (chưa chặn Sprint 5):** `api/deps.py` dev-header context tạm (thay bằng JWT thật ở Sprint 6); FK `drugs.atc_code`→`atc_codes` chưa bật; uniqueness `registration_no` chưa enforce; **persist trả hàng** (`register_return`) chưa có use-case + trả tồn. Chi tiết ở [TODO.md](TODO.md).

---

## 8. Nhật ký thay đổi (Changelog)

| Ngày | Thay đổi |
|------|----------|
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
