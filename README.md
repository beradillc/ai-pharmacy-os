# BERAS

> **BERAS là sổ điện tử quản lý nhà thuốc chuẩn Cloud/SaaS thế hệ mới, tích hợp AI hỗ trợ chuyên
> sâu nghiệp vụ Dược và đảm bảo vận hành liên tục ngay cả khi mất kết nối Internet.**
> POS + Kho + Đơn thuốc + Dược sĩ AI, kiến trúc module hóa, tuân thủ quy định Bộ Y tế (DAV).

> Tên kỹ thuật của mã nguồn vẫn là `pharmacy_os` (package, thư mục, migration). Đổi tên kỹ thuật là
> việc riêng, không gộp vào lần đổi định vị thương hiệu này.

[![Sprint](https://img.shields.io/badge/Sprint%207-Compliance%20%26%20Analytics-brightgreen)]()
[![Stage](https://img.shields.io/badge/stage-foundation-blue)]()
[![Tests](https://img.shields.io/badge/tests-560%20passed-brightgreen)]()
[![Domain coverage](https://img.shields.io/badge/domain%20coverage-99%25-brightgreen)]()
[![Types](https://img.shields.io/badge/mypy-strict-brightgreen)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)]()

---

## 1. BERAS là gì?

Sổ điện tử quản lý nhà thuốc trên nền Cloud/SaaS: mọi nghiệp vụ hằng ngày (bán hàng, kê đơn, nhập kho, tư vấn) được ghi lại thành một sổ sách điện tử **chứng minh được tuân thủ khi thanh tra** — ai đã làm gì, lúc nào, trên căn cứ pháp lý nào. AI tham gia như lớp hỗ trợ **an toàn dược lý** và **tối ưu vận hành** trên nền sổ đó, luôn theo nguyên tắc **AI khuyến nghị, con người quyết định**.

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

✅ `catalog` · ✅ `inventory` · ✅ `sales` · ✅ `prescription` · ✅ `clinical` · ✅ `crm` · ✅ `procurement` · ✅ `compliance` · ✅ `iam` · ⏳ `analytics`

(✅ = đã hiện thực · ⏳ = đã thiết kế, theo lộ trình). Mỗi module theo Hexagonal (`domain → application → infrastructure → interface`), giao tiếp **chỉ qua domain events / ports** — được ép bằng `import-linter` (domain-purity + module-independence). Xem [docs/08_MODULES.md](docs/08_MODULES.md).

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
| 13 | [Compliance Spec](docs/13_COMPLIANCE_SPEC.md) | Spec pháp lý đã khóa (QĐ540/TT20/QĐ1867) |
| 14 | [Feature Process](docs/14_FEATURE_PROCESS.md) | Cổng bắt buộc cho tính năng mới (Compliance/Privacy by Design) |
| 15 | [IAM Design](docs/15_IAM_DESIGN.md) | Users/roles/JWT, vai trò 2 cấp chuỗi–nhà thuốc |
| 16 | [Brand & UI Guide](docs/16_BRAND_UI_GUIDE.md) | Nhận diện BERAS, tông màu, 3 trụ cột, nguyên tắc UI |

---

## 5. Trạng thái dự án

**Sprint 1–6 đã đóng · Sprint 7 (Compliance & Analytics) đang tiến hành.** Backend chạy end-to-end:
9 module nghiệp vụ + kernel, xác thực JWT thật, sổ thuốc kiểm soát đặc biệt, hồ sơ sức khỏe khách
hàng, và outbox giao dịch cho sự kiện miền.

| Sprint | Trạng thái | Nội dung chính |
|--------|-----------|----------------|
| 1 — Thiết kế | ✅ | 12 tài liệu + README/ROADMAP/PROJECT_STATE (nay đã lên 16, xem mục 4) |
| 2 — Kernel | ✅ | config, DI, event bus, UoW, security, audit, AI port, plugin loader, API v1 |
| 3 — Catalog & Inventory | ✅ | `catalog` (drug master, quy đổi đơn vị, Rx class) · `inventory` (lô/HSD, movement event-sourced, **FEFO**, cảnh báo cận date) |
| 4 — Sales / POS offline | ✅ *(backend)* | `sales`: đơn/thanh toán/trả hàng, idempotency `client_uuid`, `/sync/sales` offline-first. FE POS chưa thuộc phạm vi |
| 5 — Prescription & Clinical AI | ✅ *(mức MOCK)* | `prescription` + `clinical`: tra tương tác thuốc **tất định**, LLM chỉ diễn giải. `# BLOCKER: AI__API_KEY thật` — chưa gọi vendor thật |
| 6 — Procurement & CRM | ✅ | `procurement` (NCC/PO/GRN→lô) · `crm` (khách hàng, đồng ý, dị ứng) · cờ AI theo từng tenant |
| **7 — Compliance & Analytics** | 🔄 **đang làm** | xem hai mục dưới |

**Sprint 7 — đã xong:**

- ✅ `iam` — module IAM thật (users/roles/JWT 2 cấp chuỗi–nhà thuốc, thay dev-header) · [docs/15](docs/15_IAM_DESIGN.md)
- ✅ `audit_logs` persist (append-only) + `GET /audit-logs` mức tối thiểu
- ✅ Hồ sơ sức khỏe khách hàng (qua cổng [docs/14](docs/14_FEATURE_PROCESS.md) Bước 0–4) — tách 2 mức nhạy cảm, `crm.sensitive.read` riêng, 6 action audit, export/khử nhận dạng, endpoint metadata DPIA
- ✅ `compliance` — sổ thuốc kiểm soát đặc biệt (C.1–C.5) + router HTTP
- ✅ **Transactional outbox** — mọi `UnitOfWork` ghi `event_outbox` trong chính giao dịch nghiệp vụ; relay giao lại at-least-once; retention dọn dòng đã xong (xem §7 mục "Giao sự kiện miền" bên dưới)

**Sprint 7 — còn lại:**

- ⬜ Dashboard / audit query (nay mới có `GET /audit-logs` mức tối thiểu) + đưa retry liên thông DAV lên outbox thay cơ chế best-effort hiện tại
- ⬜ Module `analytics`: dashboard, dự báo nhu cầu, đề xuất nhập
- ⬜ Report xuất khẩu
- ⬜ *Nợ kỹ thuật đã ghi:* cảnh báo/khoá tồn-âm khi chạy outbox chế độ async — xem [TODO.md](TODO.md)

**Cổng chất lượng (2026-07-24):** `pytest` **665** · `mypy --strict` **222 file** · `import-linter`
**13 contract / 0 broken** · `ruff check` + `format --check` sạch · migration `0001`→`0019` live/reversible.

Xem chi tiết & lịch sử: [PROJECT_STATE.md](PROJECT_STATE.md) · lộ trình đầy đủ: [ROADMAP.md](ROADMAP.md).

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

# 3) Migration + seed + chạy API
alembic upgrade head                 # 0001 (extensions) → 0018 (index idempotent AI recommendation)
python -m seeds.run                  # seed mã ATC (idempotent)
uvicorn pharmacy_os.main:app --reload
# → /api/v1/health · /api/v1/docs · /api/v1/drugs · /api/v1/inventory/*
```

### ⚠️ Xác thực — đọc trước khi thắc mắc "sao API trả 401?"

Từ 2026-07-23 (module `iam`), **mọi endpoint nghiệp vụ đòi `Authorization: Bearer`**. Có 2 đường:

| | Dùng khi nào | Cách làm |
|---|---|---|
| **Dev nhanh** | Chạy demo/script cũ dùng header `X-Tenant-Id`/`X-Branch-Id` | Đặt `SECURITY__ALLOW_DEV_AUTH=true` trong `.env` (đã có sẵn trong `.env.example`). Khởi động sẽ log `dev_auth_enabled` để nhắc |
| **Đường thật** | Kiểm thử đúng như production | Tạo tài khoản rồi đăng nhập (bên dưới) |

```bash
# Tạo tenant + chi nhánh + 5 vai trò hệ thống + tài khoản admin đầu tiên
BOOTSTRAP_ADMIN_PASSWORD='MatKhauCuaBan2026' python -m seeds.bootstrap_tenant \
    --tenant-name "Nhà thuốc ABC" --branch-code HQ --branch-name "Chi nhánh chính" \
    --admin-email admin@abc.vn --admin-full-name "Nguyễn Văn A"

# Lấy token
curl -X POST localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
     -d '{"email":"admin@abc.vn","password":"MatKhauCuaBan2026"}'
```

`SECURITY__ALLOW_DEV_AUTH` **mặc định `false` trong code** (fail-closed): thiếu dòng đó trong `.env`
là mọi request không có token đều 401 — đúng chủ đích, không phải lỗi. `APP__ENV=prod` cộng với cờ
này bật thì ứng dụng **từ chối khởi động**.

`branch_id` nằm trong claim JWT đã ký; header `X-Branch-Id` **không** đè được trên request đã xác
thực. Đổi chi nhánh dùng `POST /api/v1/auth/switch-branch`. Chi tiết: [docs/15_IAM_DESIGN.md](docs/15_IAM_DESIGN.md).

### Giao sự kiện miền — transactional outbox (2026-07-24)

Mỗi `UnitOfWork` ghi sự kiện vào bảng `event_outbox` **ngay trong giao dịch nghiệp vụ**, nên không còn
cửa sổ "đã commit đơn hàng nhưng `SaleCompleted` bốc hơi vì tiến trình chết". Hai công tắc quyết định
sự kiện rời bảng đó bằng đường nào:

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `OUTBOX__SYNC_DRAIN` | `true` | Publish ngay sau commit, trong cùng request — giống hành vi cũ, chỉ khác là sự kiện đã nằm trên đĩa trước đó |
| `OUTBOX__RELAY_ENABLED` | `false` | Tiến trình nền quét `event_outbox`, giao lại những dòng còn `PENDING` do sự cố. **Đây mới là thứ làm outbox có giá trị** |
| `OUTBOX__RETENTION_ENABLED` | `false` | Tiến trình nền **dọn** dòng đã xong. Không có nó, bảng phình vô hạn (mỗi lần bán ≥3 dòng) |

**Prod đặt `OUTBOX__SYNC_DRAIN=false` + `OUTBOX__RELAY_ENABLED=true` + `OUTBOX__RETENTION_ENABLED=true`**
(bật cả sync lẫn relay cũng hợp lệ: inline cho độ trễ thấp, relay làm lưới an toàn). Cả hai công tắc giao
hàng cùng `false` khi `APP__ENV=prod` ⇒ app **từ chối khởi động**; thiếu retention thì log cảnh báo lúc khởi động.

**Retention xoá gì:** `PUBLISHED` quá 30 ngày (đổi bằng `OUTBOX__RETENTION_PUBLISHED_DAYS`) — dòng outbox là
hạ tầng giao hàng, không phải bằng chứng; bản ghi nghiệp vụ và `audit_logs` nằm ở bảng riêng. `FAILED`
**giữ vĩnh viễn** trừ khi đặt `OUTBOX__RETENTION_FAILED_DAYS` — đó là dấu vết duy nhất của sự kiện chưa
bao giờ giao được. `PENDING` **không bao giờ** bị xoá, ràng buộc bằng kiểu chứ không bằng lời dặn.

Giao hàng là **at-least-once**: một sự kiện có thể tới subscriber 2 lần, nên mọi subscriber đều có khoá
idempotent (`dispense_for_sale` theo `order_id`, GRN theo `grn_id`, medication-history theo
`(source, ref_id)`, interaction-check theo `(context_type, context_id)`). Thêm `DomainEvent` mới thì phải
khai vào `ALL_EVENTS` trong `api/v1/outbox_wiring.py` — quên sẽ bị `tests/unit/test_outbox_registry.py`
bắt ngay, không để lọt tới lúc chạy.

Hoặc dùng `make`: `make up` · `make install` · `make migrate` · `make seed` · `make serve` · `make check` (lint+contracts+types+test).

Cấu hình: [docs/10_CONFIG.md](docs/10_CONFIG.md).

---

## 8. Giấy phép & Miễn trừ

- **Giấy phép mã nguồn: [Apache License 2.0](LICENSE)** (kèm [NOTICE](NOTICE)). Cho phép dùng/sửa/phân phối kèm điều khoản bằng sáng chế; giữ ghi công.
- Nội dung lâm sàng do AI cung cấp mang tính **hỗ trợ**, phải được người có chứng chỉ hành nghề xem xét. Xem [docs/12_AI_INTEGRATION.md §9](docs/12_AI_INTEGRATION.md).
