# AI Pharmacy OS

> **Hệ điều hành nghiệp vụ AI-native cho nhà thuốc / chuỗi nhà thuốc tại Việt Nam.**
> POS + Kho + Đơn thuốc + Dược sĩ AI, kiến trúc module hóa, tuân thủ quy định Bộ Y tế (DAV).

[![Sprint](https://img.shields.io/badge/Sprint%202-Kernel%20Complete-brightgreen)]()
[![Stage](https://img.shields.io/badge/stage-foundation-blue)]()
[![Tests](https://img.shields.io/badge/tests-21%20passed-brightgreen)]()
[![Types](https://img.shields.io/badge/mypy-strict-brightgreen)]()

---

## 1. AI Pharmacy OS là gì?

Một nền tảng quản lý nhà thuốc lấy AI làm lõi, biến mỗi nghiệp vụ (bán hàng, kê đơn, nhập kho, tư vấn) thành luồng có AI hỗ trợ ra quyết định **an toàn dược lý** và **tối ưu vận hành** — trong khi vẫn giữ nguyên tắc **AI khuyến nghị, con người quyết định**.

### Năng lực cốt lõi
- 🧾 **POS offline-first** — bán hàng nhanh, hoạt động cả khi mất mạng, đồng bộ idempotent.
- 📦 **Kho theo lô/hạn dùng (FEFO)** — event-sourced, cảnh báo cận date & dưới định mức.
- 💊 **Quản lý đơn thuốc (Rx)** — tiếp nhận, trích xuất từ ảnh bằng AI, xác thực, cấp phát.
- 🤖 **Dược sĩ AI** — kiểm tra tương tác/dị ứng/liều, gợi ý thay thế, hội thoại RAG có trích nguồn.
- 👥 **CRM bệnh nhân** — hồ sơ dị ứng, bệnh nền, lịch sử dùng thuốc.
- 🛒 **Mua hàng & dự báo** — PO, nhập kho, đề xuất nhập theo dự báo nhu cầu.
- 🛡️ **Tuân thủ** — sổ thuốc kiểm soát (TT 20/2017), audit bất biến, liên thông Dược Quốc gia.
- 🏢 **Đa chi nhánh** — multi-tenant, RBAC theo vai trò & chi nhánh.

---

## 2. Kiến trúc tóm tắt

**Modular Monolith** (Hexagonal per module) + **event-driven** nội bộ + **plugin** cho phần biến động (pháp lý, thanh toán, phần cứng) + **AI Gateway** đứng sau port `LLMProvider`.

```text
Client (Next.js, POS offline)  →  FastAPI (Kernel + Modules + AI Gateway)
                                        │
        ┌───────────────┬───────────────┼───────────────┐
   PostgreSQL+pgvector  Redis/Celery   Claude API      Plugins (DAV, Payment, HW)
```

| Lớp | Công nghệ |
|-----|-----------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic |
| Dữ liệu | PostgreSQL 16 + pgvector · Redis |
| Async | Celery (forecasting, embeddings, sync, liên thông) |
| AI | Anthropic Claude (`claude-opus-4-8` suy luận / `claude-sonnet-5` nhanh) |
| Frontend | Next.js · TypeScript · TanStack Query · Dexie (offline) |
| Hạ tầng | Docker · OpenTelemetry · Prometheus/Grafana |

Chi tiết: [docs/02_ARCHITECTURE.md](docs/02_ARCHITECTURE.md).

---

## 3. Module nghiệp vụ

`iam` · `catalog` · `inventory` · `procurement` · `sales` · `prescription` · `clinical` · `crm` · `compliance` · `analytics`

Mỗi module theo Hexagonal (`domain → application → infrastructure → interface`), giao tiếp **chỉ qua domain events / ports**. Xem [docs/08_MODULES.md](docs/08_MODULES.md).

---

## 4. Bản đồ tài liệu (Documentation Map)

| # | Tài liệu | Nội dung |
|---|----------|----------|
| 01 | [Phân tích](docs/01_ANALYSIS.md) | Vision, actor, FR/NFR, rủi ro, scope |
| 02 | [Kiến trúc](docs/02_ARCHITECTURE.md) | C4, Hexagonal, kernel, event-driven, ADR |
| 03 | [Database & ERD](docs/03_DATABASE_ERD.md) | ERD, bảng theo context, index, event-sourcing |
| 04 | [Cấu trúc thư mục](docs/04_FOLDER_STRUCTURE.md) | Monorepo, layout module, plugin, infra |
| 05 | [Phụ thuộc & Package](docs/05_DEPENDENCIES.md) | Thư viện + quy tắc phụ thuộc (import-linter) |
| 06 | [Workflow](docs/06_WORKFLOWS.md) | Sequence/flow các nghiệp vụ chính |
| 07 | [UML](docs/07_UML.md) | Class, state machine, component diagrams |
| 08 | [Module](docs/08_MODULES.md) | Đặc tả từng bounded context |
| 09 | [Plugin System](docs/09_PLUGIN_SYSTEM.md) | Cơ chế mở rộng, contract, vòng đời |
| 10 | [Config](docs/10_CONFIG.md) | Cấu hình phân lớp, env, settings động |
| 11 | [API Design](docs/11_API_DESIGN.md) | REST v1, endpoint map, idempotency, AI streaming |
| 12 | [AI Integration](docs/12_AI_INTEGRATION.md) | AI Gateway, RAG, guardrails, an toàn |

---

## 5. Trạng thái dự án

**Sprint 2 — Skeleton & Kernel: HOÀN THÀNH.** Kernel backend chạy được; chưa có module nghiệp vụ (đúng chủ đích).

- ✅ Sprint 1 — Thiết kế: 12 tài liệu + README/ROADMAP/PROJECT_STATE
- ✅ Sprint 2 — Kernel: config, DI, event bus, UoW, security, audit, AI port, plugin loader, API v1 + health, Alembic `0001` (pgvector)
- ✅ Gate xanh: `pytest` 21 · `mypy` strict (35 file) · `ruff`/format · `import-linter` 3/0 · `docker compose` + migration chạy live
- ⏭️ Sprint 3 — Catalog & Inventory (xem [ROADMAP.md](ROADMAP.md))

Xem chi tiết & lịch sử: [PROJECT_STATE.md](PROJECT_STATE.md).

---

## 6. Nguyên tắc thiết kế (Design Tenets)

1. **AI khuyến nghị, con người quyết định** — không tự động cấp phát thuốc.
2. **Tuân thủ là hạ tầng**, không phải tính năng thêm.
3. **Offline-first** cho POS.
4. **Biến động khu trú vào plugin**, lõi ổn định.
5. **Domain thuần**, không dính framework — kiểm thử được, thay adapter dễ.
6. **Có thể kiểm toán từ đầu** — RBAC + audit log bất biến.

---

## 7. Bắt đầu (Quickstart — kernel đã chạy được)

```bash
# 1) Hạ tầng: Postgres (pgvector) + Redis
docker compose up -d

# 2) Backend: venv + cài deps
python3 -m venv .venv && source .venv/bin/activate
cd backend && pip install -e ".[dev]"
cp .env.example .env                 # điền AI__API_KEY, SECURITY__JWT_SECRET...

# 3) Migration + chạy API
alembic upgrade head                 # bật vector + pgcrypto
uvicorn pharmacy_os.main:app --reload
# → http://localhost:8000/api/v1/health · /api/v1/docs
```

Hoặc dùng `make`: `make up` · `make install` · `make migrate` · `make serve` · `make check` (lint+contracts+types+test).

Cấu hình: [docs/10_CONFIG.md](docs/10_CONFIG.md).

---

## 8. Giấy phép & Miễn trừ

- **Giấy phép mã nguồn: [Apache License 2.0](LICENSE)** (kèm [NOTICE](NOTICE)). Cho phép dùng/sửa/phân phối kèm điều khoản bằng sáng chế; giữ ghi công.
- Nội dung lâm sàng do AI cung cấp mang tính **hỗ trợ**, phải được người có chứng chỉ hành nghề xem xét. Xem [docs/12_AI_INTEGRATION.md §9](docs/12_AI_INTEGRATION.md).
