# 04 — CẤU TRÚC THƯ MỤC (Folder Structure)

> Monorepo. Backend (Python/FastAPI) + Frontend (Next.js) + hạ tầng.
> Mỗi business module là một package độc lập theo Hexagonal.

---

## 1. Cây thư mục gốc

```text
AI_Pharmacy_OS/
├── README.md
├── ROADMAP.md
├── PROJECT_STATE.md
├── docs/                      # Toàn bộ tài liệu thiết kế (Sprint 1)
│   ├── 01_ANALYSIS.md
│   ├── 02_ARCHITECTURE.md
│   ├── 03_DATABASE_ERD.md
│   ├── 04_FOLDER_STRUCTURE.md
│   ├── 05_DEPENDENCIES.md
│   ├── 06_WORKFLOWS.md
│   ├── 07_UML.md
│   ├── 08_MODULES.md
│   ├── 09_PLUGIN_SYSTEM.md
│   ├── 10_CONFIG.md
│   ├── 11_API_DESIGN.md
│   ├── 12_AI_INTEGRATION.md
│   └── adr/                   # Architecture Decision Records (Sprint 2+)
├── backend/
├── frontend/
├── plugins/
├── infra/
├── scripts/
└── docker-compose.yml
```

---

## 2. Backend (`backend/`)

```text
backend/
├── pyproject.toml             # deps + tool config (ruff, mypy, pytest)
├── alembic.ini
├── src/
│   └── pharmacy_os/
│       ├── main.py            # khởi tạo FastAPI app, mount routers, lifespan
│       ├── core/              # KERNEL — không chứa nghiệp vụ
│       │   ├── config.py      # Pydantic Settings, cấu hình phân lớp
│       │   ├── di.py          # DI container / providers
│       │   ├── events/        # EventBus, base DomainEvent, handlers registry
│       │   ├── db/            # engine, session, Base, UnitOfWork
│       │   ├── security/      # auth, RBAC, password, JWT
│       │   ├── context.py     # RequestContext (tenant_id, branch_id, user)
│       │   ├── audit/         # audit logger
│       │   ├── plugins/       # plugin loader, hook registry, interfaces
│       │   ├── ai/            # AI Gateway, LLMProvider port, guardrails, RAG
│       │   └── errors.py      # exception types + handlers
│       ├── modules/           # BUSINESS MODULES (mỗi cái Hexagonal)
│       │   ├── catalog/
│       │   ├── inventory/
│       │   ├── sales/
│       │   ├── prescription/
│       │   ├── clinical/      # tương tác, liều, gợi ý (dùng core/ai)
│       │   ├── crm/
│       │   ├── procurement/
│       │   ├── compliance/
│       │   ├── analytics/
│       │   └── iam/           # identity & access
│       ├── api/               # composition: gom routers, versioning /api/v1
│       │   └── v1/
│       ├── workers/           # Celery app, tasks (forecasting, sync, embeddings)
│       └── shared/            # kiểu dùng chung, value objects (Money, Quantity)
├── migrations/                # Alembic versions
│   ├── env.py
│   └── versions/
├── tests/
│   ├── unit/                  # domain thuần, không I/O
│   ├── integration/           # repo + DB thật (testcontainers)
│   └── e2e/                   # API end-to-end
└── seeds/                     # dữ liệu tham chiếu (ATC, units...)
```

### 2.1 Bên trong một module (ví dụ `modules/sales/`)

```text
modules/sales/
├── __init__.py                # register(): mount router, event handlers
├── domain/
│   ├── entities.py            # SalesOrder, SalesOrderItem (aggregate root)
│   ├── value_objects.py       # Money, Quantity
│   ├── events.py              # SaleCompleted, SaleReturned
│   ├── rules.py               # invariants: chặn ETC thiếu đơn
│   └── ports.py               # SalesRepository (interface), StockPort
├── application/
│   ├── use_cases/
│   │   ├── create_sale.py
│   │   ├── complete_sale.py
│   │   └── return_sale.py
│   ├── services.py
│   └── dto.py
├── infrastructure/
│   ├── models.py              # SQLAlchemy ORM models
│   ├── repositories.py        # cài đặt SalesRepository
│   └── mappers.py             # ORM <-> domain entity
└── interface/
    ├── router.py              # FastAPI APIRouter
    ├── schemas.py             # Pydantic request/response
    └── deps.py                # dependency wiring cho module
```

> **Quy tắc:** `domain/` không import `fastapi`, `sqlalchemy`. `interface/` và `infrastructure/` là nơi duy nhất chạm framework. Kiểm soát bằng import-linter (xem [05_DEPENDENCIES.md](05_DEPENDENCIES.md)).

---

## 3. Frontend (`frontend/`)

```text
frontend/
├── package.json
├── next.config.ts
├── src/
│   ├── app/                   # Next.js App Router
│   │   ├── (pos)/             # màn hình POS (offline-first)
│   │   ├── (inventory)/
│   │   ├── (rx)/
│   │   ├── (admin)/
│   │   └── layout.tsx
│   ├── features/              # feature-sliced: mỗi domain 1 slice
│   │   ├── sales/
│   │   ├── inventory/
│   │   ├── prescription/
│   │   └── ai-assistant/
│   ├── shared/                # ui kit, api client, hooks
│   ├── lib/                   # offline sync, IndexedDB, auth
│   └── styles/
└── tests/
```

---

## 4. Plugins (`plugins/`)

```text
plugins/
├── dav_connector/             # liên thông Dược Quốc gia
│   ├── pyproject.toml         # khai báo entry point: pharmacy_os.plugins
│   └── src/dav_connector/
├── payment_vnpay/
├── payment_momo/
└── hardware_escpos/           # in nhãn/hóa đơn ESC/POS
```

Mỗi plugin là **package Python riêng**, cài rời, đăng ký qua entry point (chi tiết [09_PLUGIN_SYSTEM.md](09_PLUGIN_SYSTEM.md)).

---

## 5. Hạ tầng & scripts

```text
infra/
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── worker.Dockerfile
├── compose/                   # override cho dev/staging/prod
├── k8s/                       # (giai đoạn sau) manifests/helm
└── observability/             # prometheus, grafana, otel config

scripts/
├── bootstrap.sh               # setup môi trường dev
├── seed.py                    # nạp dữ liệu mẫu
└── gen_erd.py                 # sinh ERD từ models (tương lai)
```

---

## 6. Bảng ánh xạ thư mục ↔ khái niệm

| Thư mục | Khái niệm kiến trúc | Tài liệu liên quan |
|---------|--------------------|-------------------|
| `core/` | Kernel, năng lực chung | [02_ARCHITECTURE.md](02_ARCHITECTURE.md) §5 |
| `modules/*/domain` | Domain layer (Hexagonal) | [07_UML.md](07_UML.md) |
| `modules/*/application` | Use-cases, ports | [08_MODULES.md](08_MODULES.md) |
| `core/ai`, `modules/clinical` | Tầng AI | [12_AI_INTEGRATION.md](12_AI_INTEGRATION.md) |
| `plugins/` | Plugin system | [09_PLUGIN_SYSTEM.md](09_PLUGIN_SYSTEM.md) |
| `migrations/` | Schema/ERD | [03_DATABASE_ERD.md](03_DATABASE_ERD.md) |
| `core/config.py` | Config phân lớp | [10_CONFIG.md](10_CONFIG.md) |
