# PROJECT_STATE — AI Pharmacy OS

> Nguồn sự thật về **trạng thái hiện tại** của dự án. Cập nhật mỗi khi có thay đổi quan trọng.
> Cập nhật cuối: **2026-07-21** · Sprint hiện tại: **Sprint 2 (HOÀN THÀNH)**

---

## 1. Trạng thái tổng quan

| Hạng mục | Trạng thái |
|----------|-----------|
| Giai đoạn | Giai đoạn 1 — Nền tảng |
| Sprint | Sprint 2 — Skeleton & Kernel |
| Tình trạng Sprint | ✅ **HOÀN THÀNH** |
| Kernel backend | ✅ Chạy được (health + OpenAPI); 21 test xanh |
| Module nghiệp vụ | ❌ Chưa (đúng chủ đích — bắt đầu Sprint 3) |
| Chất lượng | ✅ ruff · ✅ ruff format · ✅ import-linter (3/0) · ✅ mypy strict (35 file) · ✅ pytest (21) |
| Hạ tầng dev | ✅ docker compose (postgres pgvector + redis) healthy; ✅ alembic `0001` áp dụng live |
| Sprint kế tiếp | Sprint 3 — Catalog & Inventory (chưa khởi động) |

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

## 7. Việc cần làm ngay khi mở Sprint 3

1. `pip install -e ".[dev]"` trong `backend/` (hoặc `make install`).
2. Tạo module `catalog/` theo 4 lớp Hexagonal ([04](docs/04_FOLDER_STRUCTURE.md) §2.1).
3. ORM models kế thừa `Base` + mixins; migration mới cho bảng `drugs`, `drug_units`, `atc_codes`.
4. Module `inventory/`: `ProductBatch`, `StockMovement` (event-sourced), FEFO allocator.
5. Đăng ký router + event handler qua `register(container)`; thêm contract layer vào `.importlinter`.
6. Integration test với testcontainers (Postgres thật) — mục tiêu ≥ 80% domain.
7. (Quản trị) Chốt **giấy phép mã nguồn** + commit git đầu tiên nếu chủ dự án đồng ý.

> **Ranh giới:** kernel (Sprint 2) không chứa nghiệp vụ; nghiệp vụ bắt đầu ở Sprint 3.

---

## 8. Nhật ký thay đổi (Changelog)

| Ngày | Thay đổi |
|------|----------|
| 2026-07-21 | **Sprint 2 HOÀN THÀNH.** Hiện thực kernel backend (config, DI, event bus, UoW, security, audit, AI port, plugin loader, errors, API v1 + health, Alembic `0001`). CI + docker-compose + Makefile. Gate xanh: pytest 21, mypy strict 35 file, ruff/format, import-linter 3/0; docker+migration chạy live. Cập nhật README/ROADMAP/PROJECT_STATE. |
| 2026-07-21 | Khởi tạo dự án. Hoàn thành Sprint 1: 15 tài liệu thiết kế. Chốt stack, kiến trúc, ERD, module, plugin, AI, config, API. README/ROADMAP/PROJECT_STATE hoàn chỉnh. |

---

## 9. Tuyên bố kết thúc Sprint 2

> ✅ **Sprint 2 đạt Definition of Done.**
> `docker compose up` chạy · kernel test xanh (21) · contract phụ thuộc pass (3/0) · mypy strict sạch · migration live bật pgvector · **chưa có module nghiệp vụ** (đúng chủ đích).
> Chờ lệnh mở **Sprint 3 — Catalog & Inventory**.
> **Không tự động chuyển sang lập trình.** Chờ lệnh mở Sprint 2.
