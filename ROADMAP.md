# ROADMAP — AI Pharmacy OS

> Lộ trình phát triển theo sprint. Cập nhật cuối: **2026-07-21**.
> Nguyên tắc: mỗi sprint có Definition of Done rõ ràng; không tràn phạm vi.

---

## Tổng quan giai đoạn

```mermaid
timeline
    title Lộ trình AI Pharmacy OS
    Giai đoạn 0 - Thiết kế : Sprint 1 (DONE) Kiến trúc & tài liệu
    Giai đoạn 1 - Nền tảng : Sprint 2 Skeleton & Kernel : Sprint 3 Catalog & Inventory
    Giai đoạn 2 - Bán hàng : Sprint 4 Sales POS offline : Sprint 5 Prescription & Clinical AI
    Giai đoạn 3 - Vận hành : Sprint 6 Procurement & CRM : Sprint 7 Compliance & Analytics
    Giai đoạn 4 - Mở rộng : Sprint 8 Plugin & Hardening : Sprint 9 Beta & Pilot
```

---

## ✅ Sprint 1 — Thiết kế kiến trúc *(HOÀN THÀNH)*

**Mục tiêu:** Thiết kế toàn bộ hệ thống, không viết code sản phẩm.

**Deliverables:**
- [x] Phân tích nghiệp vụ, actor, FR/NFR ([01](docs/01_ANALYSIS.md))
- [x] Kiến trúc C4 + Hexagonal + ADR ([02](docs/02_ARCHITECTURE.md))
- [x] ERD + schema DB ([03](docs/03_DATABASE_ERD.md))
- [x] Cấu trúc thư mục monorepo ([04](docs/04_FOLDER_STRUCTURE.md))
- [x] Phụ thuộc + quy tắc import ([05](docs/05_DEPENDENCIES.md))
- [x] Workflow nghiệp vụ ([06](docs/06_WORKFLOWS.md))
- [x] UML class/state/component ([07](docs/07_UML.md))
- [x] Đặc tả module ([08](docs/08_MODULES.md))
- [x] Plugin system ([09](docs/09_PLUGIN_SYSTEM.md))
- [x] Config ([10](docs/10_CONFIG.md))
- [x] API design ([11](docs/11_API_DESIGN.md))
- [x] AI integration ([12](docs/12_AI_INTEGRATION.md))
- [x] README, ROADMAP, PROJECT_STATE

**DoD:** ✅ README + ROADMAP + PROJECT_STATE hoàn chỉnh. **Không chuyển sang lập trình.**

---

## ✅ Sprint 2 — Skeleton & Kernel *(HOÀN THÀNH — 2026-07-21)*

**Mục tiêu:** Dựng bộ khung chạy được của kernel, chưa nghiệp vụ.

- [x] Khởi tạo monorepo backend, `pyproject.toml` (hatchling, PEP 621), git.
- [x] `core/`: config (Pydantic Settings, fail-fast prod), DI container, EventBus in-process (isolate handler), UnitOfWork (publish-after-commit), RequestContext.
- [x] `core/`: security (bcrypt password, JWT, RBAC), audit logger, AI `LLMProvider` port, plugin loader (entry points), errors (RFC 7807).
- [x] DB: async engine, `Base` + mixins, Alembic init, migration `0001` bật `vector` + `pgcrypto`.
- [x] `import-linter` (3 contract) + CI workflow (ruff, format, import-linter, mypy strict, pytest).
- [x] Health endpoint + OpenAPI (`/api/v1/health`, `/api/v1/docs`).
- [x] Docker compose (postgres pgvector + redis), Dockerfile, Makefile, bootstrap.sh.

**DoD:** ✅ Đạt. Bằng chứng đã chạy thật:
- `docker compose up` → postgres + redis **healthy**.
- `alembic upgrade head` áp dụng trên Postgres live; `vector` + `pgcrypto` đã bật.
- `pytest` **21 passed**; `mypy` strict **no issues (35 files)**; `ruff`/format sạch; `import-linter` **3 kept, 0 broken**.
- `modules/` rỗng đúng chủ đích — chưa nghiệp vụ.

> Ghi chú: dùng `pip`/`venv` (không có `uv`); FE `pnpm` workspace hoãn sang khi bắt đầu code FE (Sprint 4).

---

## ✅ Sprint 3 — Catalog & Inventory *(HOÀN THÀNH — 2026-07-21)*

- [x] Module `catalog`: `Drug`, đơn vị quy đổi (`DrugUnit`, hệ số về base unit), ATC, phân loại Rx (OTC/ETC/CONTROLLED). Hexagonal 4 lớp.
- [x] Module `inventory`: `ProductBatch`, `StockMovement` (event-sourced), `allocate_fefo` (domain thuần), projection `stock_balances`.
- [x] Cảnh báo cận date (`/inventory/alerts/near-expiry`) + sự kiện `LowStockDetected` khi hết định mức.
- [x] Seed dữ liệu tham chiếu (10 mã ATC) — idempotent, chạy `make seed`.
- [x] API v1 (`/drugs`, `/inventory/receive|dispense|on-hand|alerts`) + test integration (service + HTTP e2e).
- [x] Migration `0002_catalog_inventory` (6 bảng) — autogenerate, áp dụng live, reversible, `alembic check` không drift.
- [x] Contract kiến trúc mới: domain purity (không import framework) + module independence (catalog ⟂ inventory).

**DoD:** ✅ Đạt. Bằng chứng đã chạy thật:
- Nhập lô → `on_hand` phản ánh (test + HTTP e2e trên Postgres/SQLite).
- FEFO chọn đúng lô cận date nhất, chặn xuất quá tồn (rollback), loại lô hết hạn.
- Test **46 passed**; **domain coverage 97%** (≥ 80%); `mypy` strict; `import-linter` **6/0**; `ruff`/format sạch.
- Sự kiện `StockMovedIn/Out` publish sau commit (test kiểm chứng thứ tự).

---

## Sprint 4 — Sales / POS offline *(BACKEND HOÀN THÀNH — 2026-07-21)*

- [x] Module `sales`: SalesOrder, items, payments, returns (Hexagonal 4 lớp).
- [x] Idempotency (`client_uuid`), endpoint `/sync/sales` (upsert 200).
- [x] Sự kiện `SaleCompleted` → inventory trừ tồn FEFO (nối ở composition root; idempotent cấp đơn; thiếu tồn → `StockShortfallDetected`, không chặn bán).
- [x] Chặn ETC thiếu đơn — catalog là nguồn thẩm quyền qua port `DrugInfoProvider` + adapter.
- [x] FE POS tối thiểu (S4.6, hồi sinh 2026-07-23) — đăng nhập JWT thật, tra thuốc, giỏ hàng,
      thanh toán `POST /sales`. `frontend/` mới, không sửa module backend nào ngoài CORS
      (`main.py`, xin phép riêng). Xem `frontend/README.md` mục "Phạm vi hiện tại".
- [x] Dexie offline queue (S4.6 Bước 5, 2026-07-23) — mất mạng lúc thanh toán thì lưu vào
      IndexedDB (`frontend/src/shared/offline/`), tự đồng bộ qua `POST /sync/sales` khi có mạng
      lại. Xem `frontend/README.md` mục "Hàng đợi offline".

**DoD backend:** ✅ Đạt. Bán → tồn giảm đúng FEFO; re-sync cùng `client_uuid` **không nhân đôi** tồn/đơn; ETC thiếu đơn bị chặn (422); bán quá tồn không làm tồn âm.

**DoD FE (S4.6, 5/5 bước):** ✅ Đăng nhập thật + chọn chi nhánh · tra thuốc (lọc client, `GET /drugs`
không có tham số tìm kiếm — lệch docs/11) · giỏ hàng · `POST /sales` thành công · hàng đợi offline
Dexie khi mất mạng, tự đồng bộ khi có mạng lại. Đã kiểm chứng bằng curl mô phỏng đúng request FE
gửi trên backend live + `next dev` thật (không chỉ `next build`).
**Chưa test bằng trình duyệt thật** (môi trường không có browser tool) — chỉ xác nhận hợp đồng API
khớp 100% qua curl và server không lỗi runtime; luồng offline (ngắt mạng, gõ đơn, bật mạng lại) mới
xác nhận đúng bằng code review + phân biệt lỗi `ApiError` vs lỗi mạng, **chưa tự tay diễn tập trên
trình duyệt thật**. Sếp cần tự mở trình duyệt kiểm tra trước khi coi Sprint 4 là "offline-first"
thật sự.
- Migration `0003_sales` (unique `tenant_id`+`client_uuid`) apply→`alembic check` không drift→reversible.
- `import-linter` **7/0** (thêm `sales-domain-innermost`; 2 điểm cross-module nối ở lớp `api`, `module-independence` giữ nguyên); `mypy` strict 90 file; `pytest` **94 passed** (+40 so với 54).

---

## Sprint 5 — Prescription & Clinical AI *(DONE ở mức MOCK — 2026-07-22)*

- [x] Module `prescription`: state machine, xác thực, cấp phát *(S5.1–S5.4)*.
- [x] `core/ai`: `LLMProvider` port + guardrail human-in-the-loop. **Impl = `MockLLMProvider`** (KHÔNG gọi API).
      🔒 **BLOCKER:** `AnthropicProvider` thật chờ `AI__API_KEY` + SDK.
- [x] Module `clinical` (A1): rule engine tương tác chéo (bảng `drug_interactions`, tất định) + LLM **diễn giải** (mock);
      full 4 lớp Hexagonal + endpoint `POST /clinical/check-interactions` (+ get/accept recommendation).
- [x] Ghi `ai_recommendations`, human-in-the-loop (dược sĩ `accept`, guardrail `requires_review`).
- [ ] 🔒 **BLOCKER — RAG:** pgvector `drug_knowledge_chunks` chưa tạo (cột `vector(1536)` phá test-harness SQLite + nguồn tri thức
      dược thật/bản quyền chưa có). Tạo bảng+index+migration riêng khi làm RAG thật. **Quyết định đã chốt:** hoãn, không stub rỗng.
- [ ] 🔒 **BLOCKER — hoạt chất:** `catalog` chưa có `active_ingredients`/`drug_ingredients` ⇒ chưa map `drug_id→hoạt chất` ⇒
      auto-check tương tác ở sale/prescription (5.5.4) hoãn. **Quyết định đã chốt:** KHÔNG thêm vào catalog vội — gộp cùng mạch
      dị ứng KH ở **Sprint 6** (xem dưới). Nay `/clinical/check-interactions` nhận danh sách hoạt chất tường minh.
- [ ] Dose-check / substitute / trích xuất đơn từ ảnh (vision) — hoãn (A2–A6, ngoài phạm vi lõi A1).

**DoD:** ✅ Kiểm tra tương tác trả kết quả **có nguồn + confidence**; log `ai_recommendations` đầy đủ; dược sĩ duyệt được.
**Đạt qua MOCK** (`MockLLMProvider`, e2e HTTP thật). Phần AI/RAG **thật** vẫn blocker (chờ API key + nguồn tri thức dược).

---

## ✅ Sprint 6 — Procurement & CRM *(HOÀN THÀNH — 2026-07-22, DoD lõi)*

- [x] **Mô hình hoạt chất trong `catalog`** (`active_ingredients`/`drug_ingredients`) — gỡ blocker S5.5, map `drug_id→hoạt chất`. *(2026-07-22)*
- [x] **Auto-check tương tác (clinical 5.5.4)** *(2026-07-22)* — nối `clinical.check_interactions` vào sale/prescription ở composition
      root (`wire_safety_checks`), **cảnh báo không chặn**, tenant-gated. Module-independence giữ nguyên (11 kept/0).
- [x] Module `crm`: Customer, dị ứng, bệnh nền, lịch sử — nối **dị ứng KH** vào kiểm tra clinical *(2026-07-22)* — `check_allergies`
      thuần + đọc crm ở dispense (chỉ luồng prescription; OTC hoãn). Lịch sử KH từ event bán/cấp phát: **chưa** (còn treo).
- [x] **Feature flag AI theo tenant (SaaS)** *(2026-07-22)* — `clinical.TenantAiSettings`, mỗi nhà thuốc bật/tắt AI độc lập.
- [x] Module `procurement`: Supplier, PO, GRN → inventory IN *(2026-07-22)* — đủ 4 lớp Hexagonal (migration `0011`) + cross-module
      `GoodsReceived` → `InventoryService` tạo lô ở composition root (`wire_goods_receipt_stock_in`), idempotent theo `grn_id`; va
      chạm lô/lỗi ghi `stock_reconciliation_needed` (migration `0012`). Module-independence giữ nguyên (12 kept/0).

**DoD:** ✅ Nhập PO→GRN tạo lô (đạt) · ✅ cờ AI cấu hình theo từng tenant (đạt). ⚠️ *lịch sử KH cập nhật từ sự kiện bán/cấp phát*
**hoãn sang Sprint 7** (sếp chốt hoãn — cross-module riêng, không chặn đóng Sprint 6).

> **Đóng Sprint 6:** 372 test xanh · import-linter 12/0 · mypy strict 178 file · migration `0008`..`0012` live/reversible. Nợ mang
> sang Sprint 7: ~~`MedicationHistoryEntry` từ event~~ (XONG 2026-07-24, §7ad), ~~dị ứng OTC~~ (XONG 2026-07-24, §7ad),
> ~~gộp lô (PA B)~~ (XONG 2026-07-23, §7ac), ~~API resolve reconciliation~~ (XONG 2026-07-23, §7ab). **Còn: outbox bền.**

---

## Sprint 7 — Compliance & Analytics

- [x] **`iam` — module IAM thật** (users/roles/JWT 2 cấp chuỗi-nhà thuốc, thay dev-header).
      *Kéo lên trước vì là điều kiện tiên quyết của mọi tính năng chạm dữ liệu nhạy cảm
      (`docs/14` Bước 1.5). Xong 2026-07-23 — `docs/15_IAM_DESIGN.md`, PROJECT_STATE §7k.*
- [x] **`audit_logs` persist** (append-only + `GET /audit-logs` mức tối thiểu).
      *Gỡ nợ F8. Xong 2026-07-23 — PROJECT_STATE §7l. Dashboard/analytics audit vẫn thuộc sprint này.*
- [x] **Hồ sơ sức khỏe khách hàng** — ngoài ROADMAP gốc, đã qua cổng `docs/14` Bước 0-4 và được
      duyệt 2026-07-23: `docs/features/ho-so-suc-khoe-khach-hang/01_DECISIONS.md`.
      Đồng ý tách 2 mức · tách `crm.sensitive.read` · 6 action audit · export/khử nhận dạng ·
      endpoint metadata DPIA. ~~**Ngoài phạm vi:** `SalesOrder.customer_id`, ghi
      `MedicationHistoryEntry` tự động (2 cross-module, tách bước riêng).~~ **2 việc "tách bước riêng"
      này nay XONG 2026-07-24** (phiên Opus full-auto, PROJECT_STATE §7ad): `SalesOrder.customer_id`
      (mig `0016`) + ghi `MedicationHistoryEntry` tự động từ `SaleCompleted`/`PrescriptionDispensed`
      (consent-gated) + dị ứng OTC.
      *4/4 bước xong 2026-07-23 — PROJECT_STATE §7m/§7t mục A1. (Checkbox cập nhật 2026-07-23, đã
      xong từ trước — tài liệu lệch với thực tế, phát hiện khi rà soát việc tiếp theo.)*
- [x] `compliance`: sổ thuốc kiểm soát (C.1–C.5, PROJECT_STATE §7b) + router HTTP (§7q) — **XONG**.
- [x] **Outbox/retry bền** (`event_outbox`, migration `0017`+`0018`) — **XONG 2026-07-24**,
      PROJECT_STATE §7ag/§7ai. Mọi `UnitOfWork` ghi sự kiện trong chính giao dịch nghiệp vụ; relay
      giao lại at-least-once. Thay hoàn toàn cơ chế **phát sự kiện** best-effort cũ (publish sau
      commit — chết giữa chừng là mất hẳn sự kiện).
      *Phạm vi chưa bao gồm:* vòng retry đẩy DAV của `NationalSyncService` vẫn best-effort riêng —
      dòng `NationalSyncLog` `FAILED` nằm im tới khi có người gọi push lại, chưa có gì tự re-drive.
- [x] Audit query dashboard — **XONG 2026-07-24 (§7al).** Dựng như **kernel-infra** (`core/audit` +
      endpoint `api/v1/audit-dashboard`), KHÔNG trong `compliance` như phác thảo cũ. Quyền RIÊNG
      `audit.dashboard.read` (admin+chain+branch, không cashier/warehouse) tách khỏi `audit.read`; lọc
      actor+time+`target_type`+action; export CSV. `/audit-logs` mức tối thiểu (§7l) vẫn giữ nguyên.
- [ ] Module `analytics` — **yêu cầu chốt 2026-07-24 (GĐ, xem PROJECT_STATE §7am)**: dự báo v1 =
      trung bình trượt 90 ngày + mốc tái đặt hàng, cấp **thuốc × chi nhánh**; đề xuất nhập sinh
      **PO nháp** trong `procurement` (không tự gửi NCC); dashboard đầu = doanh thu/top thuốc/cảnh
      báo cận date+tồn thấp/số PO nháp chờ duyệt. Hoãn v2: phát hiện bất thường + mùa vụ/dịch bệnh.
      Giao Opus (thiết kế mới + cross-module `sales`/`inventory`→`procurement`).
- [ ] Report xuất khẩu — **yêu cầu chốt 2026-07-24 (GĐ, xem PROJECT_STATE §7am)**: KHÔNG phải biểu
      mẫu pháp lý (đính chính docs/13 #21 — Phụ lục X/XI không áp dụng bán lẻ). Nội dung: doanh thu
      (ngày/tuần/tháng, theo chi nhánh/nhân viên) + tồn kho theo lô/HSD → sau đó top thuốc bán chạy
      + xuất `ControlledLedgerEntry`. Định dạng CSV (tái dùng `csv_export.py` từ audit dashboard).
      Quyền: tái dùng `sales.read`/`inventory.read` hiện có, không tạo quyền mới. Giao Sonnet (tái
      dùng khuôn CSV vừa dựng, không phải thiết kế mới).

**DoD:** Sổ kiểm soát khớp movements; dashboard hiển thị số liệu thật; đề xuất nhập sinh PO nháp;
**hồ sơ sức khỏe KH trả lời được 6 câu hỏi thanh tra bằng dữ liệu trong hệ thống** (xem Bước 0 của
tài liệu tính năng), thu ngân không xem được dị ứng/bệnh nền.

---

## Sprint 8 — Plugin & Hardening

- [ ] Plugin loader hoàn chỉnh (entry points, hooks, vòng đời).
- [ ] `dav_connector` (liên thông), `payment_vnpay`.
- [ ] Bảo mật: 2FA vai trò nhạy cảm, rate limit, mã hóa at-rest.
- [ ] Observability đầy đủ (tracing, metrics, alert).
- [ ] Load test POS (p95 < 300ms).

**DoD:** Bật/tắt plugin không sửa lõi; liên thông gửi thử thành công; chỉ tiêu NFR đạt.

---

## Sprint 9 — Beta & Pilot

- [ ] Triển khai staging → pilot 1 nhà thuốc thật.
- [ ] Đào tạo, phản hồi, sửa lỗi.
- [ ] Tài liệu vận hành & backup/restore.

**DoD:** Pilot chạy 2 tuần ổn định; checklist go-live đạt.

---

## Backlog (sau v1)

- Ứng dụng bệnh nhân, sàn B2C.
- Claim BHYT tự động.
- Schema-per-tenant cho khách hàng lớn.
- Tách microservice cho module tải cao (thay EventBus bằng broker).
- Đa ngôn ngữ giao diện.

---

## Nguyên tắc quản trị lộ trình

- Mỗi sprint **không** bắt đầu code khi thiết kế liên quan chưa chốt.
- Thay đổi phạm vi → cập nhật ROADMAP + PROJECT_STATE cùng lúc.
- ADR mới → lưu `docs/adr/`.
