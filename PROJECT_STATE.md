# PROJECT_STATE — AI Pharmacy OS

> Nguồn sự thật về **trạng thái hiện tại** của dự án. Cập nhật mỗi khi có thay đổi quan trọng.
> Cập nhật cuối: **2026-07-21** · Sprint hiện tại: **Sprint 4 (ĐANG CHẠY — S4.2 xong)**

---

## 1. Trạng thái tổng quan

| Hạng mục | Trạng thái |
|----------|-----------|
| Giai đoạn | Giai đoạn 1 — Nền tảng |
| Sprint | Sprint 3 — Catalog & Inventory (+ Demo & Self-Refine) |
| Tình trạng Sprint | ✅ **HOÀN THÀNH** |
| Kernel backend | ✅ (Sprint 2) |
| Module nghiệp vụ | ✅ `catalog`, `inventory` (Hexagonal, event-sourced, FEFO) |
| Demo | ✅ `demo_preview.py` — chạy end-to-end, trung thực (clinical đánh dấu CHƯA làm) |
| Self-Refine | ✅ docstring use-case + 8 edge-case test; xem [TODO.md](TODO.md) |
| Chất lượng | ✅ ruff · ✅ format · ✅ import-linter (**6/0**) · ✅ mypy strict (**92 file**) · ✅ pytest (**54**) · domain coverage **97%** |
| Hạ tầng dev | ✅ docker compose healthy; ✅ alembic `0001`+`0002` áp dụng live; ✅ seed ATC idempotent |
| Sprint kế tiếp | Sprint 4 — Sales / POS offline (chưa khởi động) |

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
| S4.3 | Sales **interface + API** `/sales`, `/sync/sales` (dedup `client_uuid`), quyền `sales.*`. → DỪNG báo cáo. | ⏳ |
| S4.4 ⚠️ | Cross-module: `SaleCompleted` → inventory FEFO dispense (handler ở composition root `api`). | ⏳ chờ duyệt |
| S4.5 ⚠️ | Chặn ETC end-to-end: adapter `DrugInfoProvider` đọc catalog ở composition root. | ⏳ chờ duyệt |

**Ghi chú thiết kế:** rx_class **không** để sales import catalog — dùng cờ `requires_prescription` snapshot trên `SaleLine`;
S4.1–S4.3 nhận cờ từ request, **S4.5** thay bằng nguồn thẩm quyền (catalog qua port/adapter). `DrugInfoProvider` port
hoãn tới S4.5 (nơi thực sự tiêu thụ) để tránh abstraction treo. `DispenseInput.ref_type/ref_id` sẵn có để móc idempotent ở S4.4.

**Bằng chứng S4.1:** `ruff` sạch · `import-linter` **7/0** · `mypy` strict **78 file** · `pytest` **69 passed** (+15 test domain sales).
**Bằng chứng S4.2:** `ruff` sạch · `import-linter` **7/0** · `mypy` strict **85 file** · `pytest` **76 passed** (+7 integration sales) · migration `0003_sales` apply→`alembic check` **không drift**→downgrade/upgrade OK (SQLite; Postgres pending khi docker bật).

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

## 7. Việc cần làm ngay khi mở Sprint 4 (Sales / POS)

1. Module `sales/`: `SalesOrder` aggregate, items, payments, returns (Hexagonal).
2. Idempotency `client_uuid` + endpoint `/sync/sales` (offline-first).
3. Sự kiện `SaleCompleted` → handler ở `inventory` gọi FEFO dispense (nối 2 module qua event bus — lần đầu cross-module).
4. Rule chặn ETC thiếu đơn (`ensure_rx_for_etc`) — dùng `Drug.is_prescription_required()`.
5. FE POS tối thiểu + Dexie offline queue (khởi tạo `frontend/`, `pnpm`).
6. Thay context tạm ở `api/deps.py` bằng JWT thực khi IAM sẵn sàng (hoặc giữ tới Sprint 6).

> **Nợ kỹ thuật cần theo dõi:** `api/deps.py` dùng context dev-header tạm (không dùng ở prod); FK `drugs.atc_code`→`atc_codes` chưa bật (đang là string). Ghi tại đây để không quên.

---

## 8. Nhật ký thay đổi (Changelog)

| Ngày | Thay đổi |
|------|----------|
| 2026-07-21 | **Sprint 4 · S4.2 — Sales application + infrastructure.** `SalesService.complete_sale` idempotent theo `client_uuid` (re-sync trả đơn cũ, **không** phát lại `SaleCompleted`) + `get_sale`. ORM `sales_orders`/`sale_lines`/`sale_payments` + mapper + repo tenant-scoped. Migration `0003_sales` (unique `tenant_id`+`client_uuid`) — autogenerate→apply→`alembic check` sạch→reversible (SQLite). Đăng ký models_registry. Gate: ruff sạch, import-linter **7/0**, mypy strict 85 file, pytest **76** (+7). Chưa wiring API/cross-module. |
| 2026-07-21 | **Sprint 4 · S4.1 — Sales domain thuần.** Module `sales` lớp domain: `SalesOrder` aggregate (DRAFT→COMPLETED→PARTIALLY_RETURNED/RETURNED), `SaleLine`/`Payment`/returns, `SaleStatus`/`PaymentMethod`, event `SaleCompleted`+`SoldItem`, exceptions, `SalesRepository` port, rule thuần `ensure_rx_for_etc`. Contract mới `sales-domain-innermost`; `sales` vào `module-independence`. Gate: ruff sạch, import-linter **7/0**, mypy strict 78 file, pytest **69** (+15). Chưa wiring, chưa infra. |
| 2026-07-21 | **Demo & Self-Refine.** Thêm `demo_preview.py` (xem trước sản phẩm, chạy end-to-end SQLite in-memory, trung thực về phạm vi — clinical đánh dấu CHƯA làm). Self-refine `modules/`: docstring use-case + `signed_quantity`; thêm `test_edge_cases.py` (8 test: qty=0, demand=0, lô rỗng, on_hand thuốc lạ, barcode trùng/khác tenant). Tạo `TODO.md`. Gate: 54 test, mypy strict 92 file, import-linter 6/0. |
| 2026-07-21 | **Sprint 3 HOÀN THÀNH.** Module `catalog` + `inventory` (Hexagonal, event-sourced, FEFO thuần). API v1 drugs/inventory. Migration `0002` (6 bảng) live + reversible, `alembic check` sạch. Seed ATC idempotent. Contract mới: domain-purity + module-independence. 46 test, domain coverage 97%, mypy strict 92 file, import-linter 6/0. |
| 2026-07-21 | **Quản trị pre-Sprint 3.** Chốt giấy phép **Apache-2.0** (thêm `LICENSE`, `NOTICE`, metadata pyproject). Commit git đầu tiên `c6fc698` (74 file, branch `main`); working tree sạch. |
| 2026-07-21 | **Sprint 2 HOÀN THÀNH.** Hiện thực kernel backend (config, DI, event bus, UoW, security, audit, AI port, plugin loader, errors, API v1 + health, Alembic `0001`). CI + docker-compose + Makefile. Gate xanh: pytest 21, mypy strict 35 file, ruff/format, import-linter 3/0; docker+migration chạy live. Cập nhật README/ROADMAP/PROJECT_STATE. |
| 2026-07-21 | Khởi tạo dự án. Hoàn thành Sprint 1: 15 tài liệu thiết kế. Chốt stack, kiến trúc, ERD, module, plugin, AI, config, API. README/ROADMAP/PROJECT_STATE hoàn chỉnh. |

---

## 9. Tuyên bố kết thúc Sprint 3

> ✅ **Sprint 3 đạt Definition of Done.**
> Nhập lô → tồn kho phản ánh · FEFO chọn đúng lô cận date · 46 test xanh · domain coverage 97% · import-linter 6/0 (domain-purity + module-independence) · mypy strict · migration `0002` live/reversible · seed ATC idempotent.
> Chờ lệnh mở **Sprint 4 — Sales / POS offline**.
> **Không tự động chuyển sang sprint tiếp theo.** Giữ ranh giới sprint.
