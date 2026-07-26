# AUDIT PHIÊN A — Kiểm toán độc lập (2026-07-26)

> **Vai:** Kiểm toán viên độc lập. KHÔNG phải GĐ, KHÔNG phải Trợ lý Code.
> **Nguyên tắc:** mọi tuyên bố trong PROJECT_STATE/TODO/ROADMAP coi là **chưa được chứng minh**
> cho tới khi tự chạy lệnh xác minh. Mục tiêu là tìm chỗ SAI.
> **Phạm vi phiên này:** Giai đoạn 0 (bằng chứng nền) + Giai đoạn 1 (kiến trúc, ISO 25010).
> **Không sửa code, không cập nhật tài liệu nào khác.**

Commit tại thời điểm audit: `7bbc8d5` · branch `main` · working tree sạch.

---

## 0. TỔNG HỢP PHÁT HIỆN

| ID | Mức | Tiêu đề | Trạng thái |
|----|-----|---------|------------|
| A-01 | **High** | Toàn bộ 1001 test chạy trên SQLite; 2 primitive khoá của Postgres bị nuốt im lặng | Đã chứng minh |
| A-02 | **High · 🚫 RELEASE BLOCKER Sprint 9** | Prod khởi động được với khoá ký JWT dài **3 byte** — không có kiểm tra độ dài | Đã chứng minh |
| A-03 | **High · 🚫 RELEASE BLOCKER Sprint 9** | Prod khởi động được với `ENCRYPTION__ENABLED=false` — PII bệnh nhân nằm bản rõ, không có tín hiệu nào | Đã chứng minh |
| P0-03 | Medium | "pytest toàn repo 1001" **không** gồm 16 test của `payment_vnpay` | Đã chứng minh |
| P0-04 | Medium | Cổng `mypy` chỉ phủ `pharmacy_os`; `seeds/` (có script ghi đè dữ liệu) và `tests/` nằm ngoài | Đã chứng minh |
| A-04 | Medium | Repository của `iam` là bộ **duy nhất** không tenant-scope theo cấu trúc | Đã chứng minh |
| A-05 | Medium · ⏸️ **QUYẾT ĐỊNH KINH DOANH CHỜ CHAIN** | Một cặp credential VNPAY dùng chung cho mọi tenant + `get_across_tenants` | Đã chứng minh |
| A-06 | Medium | Docstring hứa timeout cho plugin — không có `wait_for` nào trong repo | Đã chứng minh |
| A-07 | Medium | Mock gateway CSDL Dược + Mock LLM được nạp cả khi `APP__ENV=prod`, không cảnh báo | Đã chứng minh |
| A-08 | Medium | `demo_preview.py` vẫn crash (từ 2026-07-23), không cổng nào phủ | Đã chứng minh |
| P0-01 | Low | `pytest -q` — đúng lệnh §7az quy định — **không in ra dòng "N passed"** | Đã chứng minh |
| P0-05 | Low | `make lint` chạy ruff từ `backend/`, sót 7 file (gồm `demo_preview.py` + package plugin) | Đã chứng minh |
| A-09 | Low | `_canonical_query`: docstring nói "mọi tham số `vnp_*`", code ký **mọi** khoá | Đã chứng minh |
| A-10 | Low | `vnp_IpAddr` cứng `127.0.0.1`; thiếu `vnp_ExpireDate` | Đã chứng minh |
| A-11 | Low | Kiểm tra port plugin bằng `isinstance` chỉ xét cấu trúc, không xét chữ ký hàm | Đã chứng minh |
| A-12 | Low | `main.py`/`models_registry.py`/`logging.py`/`workers/` nằm ngoài 4 tầng của contract `layers` | Đã chứng minh |

**Không tìm thấy** lỗ hổng Critical trong phạm vi đã soát. Cụ thể: không có rò dữ liệu chéo tenant
đang sống, không có secret thật trong lịch sử git, không có import chéo module, không có drift
migration. Chi tiết ở mục 3.

### Điều chỉnh của Chain sau khi đọc bản đầu (2026-07-26)

Hai điều chỉnh do Chain (CEO) ban hành sau khi đọc bản audit đầu tiên. Ghi tại đây để về sau truy
được ai đổi phân loại, từ lúc nào, vì lý do gì — bản thân báo cáo cũng chịu kỷ luật ghi ngày như
CLAUDE.md yêu cầu.

| # | Điều chỉnh | Lý do Chain nêu |
|---|---|---|
| 1 | **A-02 + A-03 nâng thành 🚫 RELEASE BLOCKER Sprint 9** (không còn chỉ là High) | (a) vi phạm trực tiếp ý đồ **"fail-fast prod"** đã tuyên bố từ Sprint 2 / `docs/10_CONFIG.md` — tức đây là lệch so với chuẩn **do chính dự án đặt ra**, không phải chuẩn ngoài áp vào; (b) liên quan dữ liệu cá nhân nhạy cảm theo **Luật BVDLCN 91/2025** |
| 2 | **A-05 đánh dấu thêm ⏸️ QUYẾT ĐỊNH KINH DOANH CHỜ CHAIN** | Không phải chỉ lỗi kỹ thuật. Phải nêu rõ 2 phương án kèm hệ quả pháp lý từng hướng để Chain quyết — xem bảng phương án trong mục A-05 |

**Giữ nguyên 0 Critical.** Chain xác nhận lập luận của kiểm toán viên: chưa có phơi nhiễm production
thật, nên A-02/A-03 là mìn cài chờ ngày deploy chứ không phải lỗ hổng đang chảy máu. "Release
blocker" và "Critical" là hai trục khác nhau và ở đây tách nhau đúng chỗ: **Critical** đo mức độ
đang bị khai thác; **release blocker** đo điều kiện được phép phát hành. A-02/A-03 mức 0 ở trục thứ
nhất và chặn cứng ở trục thứ hai.

**Hệ quả vận hành:** Sprint 9 **không được đóng** khi A-02 hoặc A-03 còn mở, bất kể các mục khác
xanh hết. Cụ thể phải có trong `_fail_fast_in_prod`: ngưỡng độ dài tối thiểu cho
`SECURITY__JWT_SECRET`, và chặn `env=prod` + `ENCRYPTION__ENABLED=false`.

---

## 1. GIAI ĐOẠN 0 — BẰNG CHỨNG NỀN

### 1.1 Cổng chất lượng — mã thoát thật, đo từng cổng riêng

| Cổng | Lệnh | Kết quả thật | PROJECT_STATE §7bd tuyên bố | Lệch? |
|------|------|--------------|------------------------------|-------|
| ruff check | `ruff check .` (cwd `backend/`) | `All checks passed!` · **EXIT=0** | "ruff+format sạch" | Không |
| ruff format | `ruff format --check .` | `383 files already formatted` · **EXIT=0** | — | Không |
| mypy | `mypy` | `Success: no issues found in 252 source files` · **EXIT=0** | "mypy --strict 252 file backend + 4 file `payment_vnpay`" | Không |
| import-linter | `lint-imports` | `Contracts: 18 kept, 0 broken.` · **EXIT=0** | "import-linter 18/0" | Không |
| pytest | `pytest` | `1001 passed, 46 warnings in 536.50s` · **EXIT=0** | "pytest 1001 EXIT=0" | Không |

Bằng chứng nguyên văn (rút gọn phần lặp):

```
$ ruff check . ; echo "RUFF_CHECK_EXIT=$?"
All checks passed!
RUFF_CHECK_EXIT=0

$ ruff format --check . ; echo "RUFF_FORMAT_EXIT=$?"
383 files already formatted
RUFF_FORMAT_EXIT=0

$ mypy ; echo "MYPY_EXIT=$?"
Success: no issues found in 252 source files
MYPY_EXIT=0

$ lint-imports ; echo "LINTIMPORTS_EXIT=$?"
Analyzed 292 files, 1419 dependencies.
...
Contracts: 18 kept, 0 broken.
LINTIMPORTS_EXIT=0

$ pytest > out.txt 2>&1 ; echo "EXIT=$?"
EXIT=0
$ grep -E "passed|failed" out.txt
1001 passed, 46 warnings in 536.50s (0:08:56)
```

**Con số tài liệu tuyên bố khớp 100% với con số thật.** Đây là điểm đáng ghi nhận: đã kiểm 5/5 cổng,
không cổng nào lệch.

---

### [P0-01] [Low] `pytest -q` — đúng lệnh §7az quy định — không in ra dòng "N passed"

**Bằng chứng:**

```
$ grep -E "passed|failed|error" pytest_out.txt | tail -5      # file sinh bởi: pytest -q > pytest_out.txt
(không có dòng nào)

$ tail -20 pytest_out.txt
........................................................................ [ 93%]
.................................................................  [100%]
=============================== warnings summary ===============================
...
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
```

Nguyên nhân: `backend/pyproject.toml` đã có `addopts = "-q"`. Thêm `-q` ở dòng lệnh thành `-qq`, mà
`-qq` **bỏ hẳn** dòng tổng kết. Bỏ `-q` đi thì có ngay:

```
$ pytest > pytest_plain.txt 2>&1 ; echo "EXIT=$?"
EXIT=0
$ grep -E "passed|failed" pytest_plain.txt
1001 passed, 46 warnings in 536.50s (0:08:56)
```

**Ảnh hưởng:** PROJECT_STATE §7az ghi quy trình sửa lỗi đo đạc là *"`pytest -q > file; echo EXIT=$?`
… đọc trực tiếp dòng cuối 'N passed'/'N failed' trong file output"* (PROJECT_STATE:3083). Quy trình
đó **không thực hiện được bằng chính lệnh nó quy định** — dòng đó không tồn tại. Người làm theo sẽ
hoặc chép lại con số từ phiên trước, hoặc quay về `--collect-only`. Exit code vẫn đúng nên không có
hậu quả trực tiếp, nhưng đây là một quy trình tự kiểm chứng đang hỏng lặng lẽ ở đúng chỗ nó vừa được
dựng lên để chống lại.

**Khuyến nghị:** đổi lệnh chuẩn trong §7az thành `pytest > file 2>&1; echo EXIT=$?` (bỏ `-q` thừa),
hoặc bỏ `addopts = "-q"` khỏi `pyproject.toml`.

---

### [P0-03] [Medium] "pytest toàn repo 1001" không phải toàn repo — sót 16 test của `payment_vnpay`

**Bằng chứng:**

```
$ cd backend && pytest --collect-only | tail -1
1001 tests collected in 1.19s

$ cd plugins/payment_vnpay && python -m pytest --collect-only -q | tail -1
16 tests collected in 0.07s
```

`backend/pyproject.toml`: `testpaths = ["tests"]` (rootdir = `backend/`) ⇒ `plugins/payment_vnpay/tests/`
nằm ngoài. `Makefile` target `test` là `cd backend && pytest` ⇒ **`make test` không bao giờ chạy test
của plugin.**

Đối chiếu tuyên bố (PROJECT_STATE:3449): *"28 test mới (16 package `payment_vnpay` + 12 integration
`sales` …). 4 cổng xanh, pytest toàn repo **1001 EXIT=0**"*. Trong repo chỉ có 3 file test nhắc tới
vnpay ở `backend/tests/` (`test_plugin_contracts.py`, `test_sales_vnpay_api_e2e.py` 3 test,
`test_sales_vnpay_flow.py` 12 test). 16 test kia nằm ở package plugin, **không** nằm trong 1001.

**Ảnh hưởng:** cụ thể — 16 test bao gồm `test_signature.py` (thuật toán HMAC ký giao dịch tiền) và
`test_plugin.py`. Đây là phần đụng tiền, và nó nằm ngoài cổng thường trực. Một thay đổi làm hỏng
`sign()`/`verify()` sẽ đi qua cả 4 cổng mà không ai biết, cho tới lúc chạy tay đúng thư mục plugin.
Câu "pytest toàn repo" trong nhật ký cũng làm phiên sau tin sai về độ phủ.

**Khuyến nghị:** thêm `plugins/payment_vnpay/tests` vào `testpaths` (hoặc thêm target `make test`
chạy cả hai rootdir), và sửa chữ "toàn repo" ở §7bd cho đúng phạm vi.

---

### [P0-04] [Medium] Cổng `mypy` chỉ phủ package `pharmacy_os` — `seeds/` và `tests/` nằm ngoài

**Bằng chứng:**

`backend/pyproject.toml`:
```toml
[tool.mypy]
strict = true
packages = ["pharmacy_os"]
```

⇒ `mypy` (lệnh của `make typecheck`) không nhìn `seeds/`, `tests/`, hay package plugin. Chạy tường minh:

```
$ mypy --strict seeds ; echo "SEEDS_EXIT=$?"
Success: no issues found in 7 source files
SEEDS_EXIT=0

$ mypy --strict ../plugins/payment_vnpay/src ; echo "PLUGIN_EXIT=$?"
Success: no issues found in 4 source files
PLUGIN_EXIT=0

$ mypy --strict seeds tests ../plugins/payment_vnpay/src
tests/integration/test_procurement_api_e2e.py:161: error: Value of type "object" is not indexable  [index]
tests/integration/test_iam_flow.py:58: error: Unused "type: ignore" comment  [unused-ignore]
tests/integration/test_analytics_e2e.py:149: error: Returning Any from function declared to return "str"  [no-any-return]
... (rút gọn)
Found 109 errors in 28 files (checked 102 source files)
MYPY_EXPLICIT_EXIT=1
```

**Ảnh hưởng:** `seeds/` và plugin hôm nay sạch — nhưng **do may, không do cổng**. Trong `seeds/` có
`encrypt_backfill.py`, script đọc-rồi-ghi-đè dữ liệu đã mã hoá; PROJECT_STATE §7bc tự mô tả nó là
*"sai là mất vĩnh viễn, còn nặng hơn seed/permission thường"*. Đúng file nguy hiểm nhất repo lại nằm
ngoài cổng type-check thường trực. `tests/` có 109 lỗi strict, trong đó nhóm `Value of type "object"
is not indexable` cho thấy assertion đang thao tác trên kiểu chưa xác định — test yếu kiểu thì bằng
chứng nó đưa ra cũng yếu theo.

**Khuyến nghị:** thêm `seeds` và package plugin vào `[tool.mypy] packages`/`files` ngay (chi phí ~0,
đang sạch). `tests/` để riêng: hoặc mở `[[tool.mypy.overrides]]` nới cho `tests.*` rồi siết dần, hoặc
ghi rõ là nợ có chủ đích thay vì im lặng.

---

### [P0-05] [Low] `make lint` sót 7 file

**Bằng chứng:**

```
$ cd backend && ruff format --check .
383 files already formatted

$ cd <repo root> && ruff format --check .
390 files already formatted
```

`Makefile`: `lint: cd backend && ruff check . && ruff format --check .`. 7 file chênh gồm
`demo_preview.py` và `plugins/payment_vnpay/**`. Chạy từ gốc repo hiện **vẫn EXIT=0** (`All checks
passed!`), nên đây là lỗ hổng độ phủ chứ chưa phải lỗi sống.

---

### 1.2 Chuỗi migration từ CSDL RỖNG

Thực hiện trên một database sạch (`audit_empty_a`) tạo mới trên chính Postgres dev — **không đụng
`pharmacy_os`**, không xoá gì.

| # | Bước | Kết quả |
|---|------|---------|
| 1 | `alembic upgrade head` (DB rỗng) | 32 migration `0001` → `0032` chạy hết · **EXIT=0** |
| 2 | `alembic check` | `No new upgrade operations detected.` · **EXIT=0** |
| 3 | `alembic downgrade base` | gỡ ngược hết về `0001` → rỗng · **EXIT=0** |
| 4 | `alembic upgrade head` (lần 2) | **EXIT=0** |
| 5 | `alembic check` (lần 2) | `No new upgrade operations detected.` · **EXIT=0** |

**Không phát hiện lệch.** Chuỗi migration đảo ngược được và không drift so với ORM metadata. Đây là
phần vững nhất trong toàn bộ những gì audit này soát.

---

### 1.3 Lịch sử git và hash tài liệu trích dẫn

| Chỉ số | Giá trị |
|--------|---------|
| `git log --oneline --all \| wc -l` | **208** |
| `git rev-list --count HEAD` | 208 (chỉ 1 branch `main`) |
| Tag | `checkpoint_20260723_0856`, `checkpoint_20260723_0900` |
| Hash dạng `` `xxxxxxx` `` trích trong PROJECT_STATE/TODO/ROADMAP/docs | 112 chuỗi ứng viên |
| Hash **không** tồn tại trong repo này | 3 (`5ae5c83`, `3eddb19`, `0b8c38e`) |

3 hash đó đều được tài liệu ghi kèm nhãn `(root)` (PROJECT_STATE:1361/1365/1369) — tức repo gốc vault,
không phải repo này. Kiểm chứng:

```
$ cd /home/gau/Vault && git cat-file -e 5ae5c83^{commit} && echo "5ae5c83 OK"
5ae5c83 OK
$ git cat-file -e 3eddb19^{commit} && echo "3eddb19 OK"
3eddb19 OK
$ git cat-file -e 0b8c38e^{commit} && echo "0b8c38e OK"
0b8c38e OK
```

**Kết luận: 112/112 hash trích dẫn đều đúng.** Không có hash bịa.

---

### 1.4 Secrets trong lịch sử git

| Kiểm tra | Kết quả |
|----------|---------|
| `backend/.env` hoặc `.env` từng vào git | **Chưa bao giờ** (`git log --all -- backend/.env .env` rỗng) |
| File `*.env` / `*.pem` / `*.key` / `*credential*` / `*secret*` từng được thêm | 0 (chỉ khớp nhầm `0029_encrypt_two_factor_secret.py`) |
| `BEGIN … PRIVATE KEY` trong toàn bộ diff | **0** |
| Regex khoá thật `sk-ant-…` / `AKIA…` / `ghp_…` / `xox[baprs]-…` | **0 kết quả** |
| `.env.example` | placeholder `__set_me__` (`AI__API_KEY`, `SECURITY__JWT_SECRET`), `ENCRYPTION__KEYS={}` |

Các dòng khớp `password=`/`secret=` còn lại đều là tên tham số hàm hoặc hằng test
(`ADMIN_PASSWORD`, `current_password="SaiRoi"`, `jwt_secret=SecretStr("real")` trong `test_config.py`).

**Không có secret thật trong lịch sử git. Không có phát hiện Critical ở mục này.**

---

## 2. GIAI ĐOẠN 1 — KIẾN TRÚC

### 2.1 Domain purity — kiểm thủ công, không tin import-linter

Quét **toàn bộ 10 module** (không chỉ 3 như yêu cầu tối thiểu):

```
$ grep -rn "^\s*\(from\|import\)\s" modules/*/domain/ \
    | grep -E "sqlalchemy|fastapi|pydantic|redis|httpx|starlette|asyncpg|alembic"
(không có kết quả)

$ grep -rn "from \.\." modules/*/domain/
(không có kết quả)
```

Tham chiếu duy nhất từ `domain/` ra ngoài là 4 file import `pharmacy_os.core.events.DomainEvent` và
`pharmacy_os.core.context.RequestContext` (`iam`, `prescription`, `inventory`, `procurement`, `sales`,
`compliance`) — đều là kiểu thuần của kernel, đúng thiết kế hexagonal, được contract cho phép. Các
kết quả khác chỉ là tên lớp trong docstring.

**Không phát hiện. Domain purity là thật, không phải chỉ do contract xanh.**

---

### 2.2 Module independence — kể cả 3 dạng import-linter KHÔNG bắt được

| Dạng | Cách kiểm | Kết quả |
|------|-----------|---------|
| Import tĩnh chéo module | quét từng module tìm `pharmacy_os.modules.<khác>` | **0** |
| Import động (`importlib`) | `grep -rn "importlib\|__import__\|import_module"` | Chỉ `core/plugins/loader.py` dùng `importlib.metadata.entry_points` — nạp **plugin**, không nạp module nghiệp vụ |
| `TYPE_CHECKING` | `grep -rn "TYPE_CHECKING"` | Đúng **1** chỗ: `modules/iam/domain/policy.py` — nội bộ module, phá vòng lặp giữa `policy` và `entities` |
| Tên module dạng chuỗi trong config | `grep` chuỗi `"pharmacy_os.modules.*"` trong `core/`, `api/`, `main.py`, `models_registry.py` | **0** (2 kết quả đều nằm trong docstring) |

**Không phát hiện.** Module independence đứng vững cả ở 3 dạng mà import-linter mù.

---

### 2.3 FK xuyên module trong DDL

Liệt kê toàn bộ `ForeignKey(...)` trong `modules/*/infrastructure/models.py` rồi đối chiếu bảng đích
với module sở hữu bảng đó:

| Module nguồn | Cột | Bảng đích | Module sở hữu đích | Xuyên module? |
|---|---|---|---|---|
| crm | `customer_allergies.ingredient_id` | `active_ingredients` | **catalog** | **CÓ — duy nhất** |
| catalog | `drug_ingredients.ingredient_id` | `active_ingredients` | catalog | Không |
| catalog | `drug_units.drug_id`, `drug_ingredients.drug_id` | `drugs` | catalog | Không |
| crm | 4 FK `→ customers.id` | `customers` | crm | Không |
| iam | 12 FK (`tenants`/`users`/`roles`/`branches`/`user_two_factor`) | — | iam | Không |
| prescription | `prescription_items.prescription_id` | `prescriptions` | prescription | Không |
| sales | `sale_lines.order_id`, `sale_payments.order_id` | `sales_orders` | sales | Không |
| procurement | `purchase_order_items`, `goods_receipt_items`, `po_item_id` | nội bộ procurement | procurement | Không |
| compliance | `drug_return_items.record_id` | `drug_return_records` | compliance | Không |

**Đúng 1 FK xuyên module** — khớp con số tài liệu ghi (PROJECT_STATE:3489).

**Lớp dịch lỗi:** có, đúng chỗ. `modules/crm/application/service.py:103-119`:

```python
# ... this insert can only come from the ``ingredient_id`` FK.
except IntegrityError as exc:
    raise NotFoundError(f"Không tìm thấy hoạt chất {data.ingredient_id}") from exc
```

⇒ `IntegrityError` thô của Postgres được dịch thành `NotFoundError` (404), không lọt 500. **Không
phát hiện.**

Mọi liên kết chéo module còn lại (`sales_orders.customer_id`, `sales_orders.sold_by_user_id`,
`sale_lines.drug_id`, `prescription_ref`) là **UUID mềm không FK**, có comment giải thích tại
`modules/sales/infrastructure/models.py:23`. Nhất quán.

---

### 2.4 Composition root

`api/v1/cross_module.py` + 5 file wiring anh em (`analytics_wiring`, `compliance_cross`,
`national_sync`, `outbox_wiring`, `audit_dashboard`). Mọi adapter/handler nối 2 module đều nằm ở đây:

| Handler / Adapter | Nối | Vị trí |
|---|---|---|
| `wire_sale_dispensing` | sales → inventory | `api/v1/cross_module.py` |
| `wire_goods_receipt_stock_in` | procurement → inventory | `api/v1/cross_module.py` |
| `wire_safety_checks` | sales/rx/crm/catalog → clinical | `api/v1/cross_module.py` |
| `wire_medication_history` | sales/rx → crm | `api/v1/cross_module.py` |
| `CatalogDrugInfoProvider` | catalog → sales (port) | `api/v1/cross_module.py` |
| `CatalogDrugMasterProvider` | catalog → compliance (port) | `api/v1/cross_module.py` |
| `PrescriptionInfoAdapter` | prescription → sales (port) | `api/v1/cross_module.py` |
| `IamAuthReauthProvider` | iam → compliance (port) | `api/v1/cross_module.py` |
| `wire_compliance_sync` | compliance ↔ sync | `api/v1/compliance_cross.py` |

**Không tìm thấy handler nào lẽ ra phải ở composition root mà đang nằm trong module.** Các module chỉ
chạm `core.config`/`core.http` ở tầng `interface/` (7 chỗ, đã kiểm từng chỗ) — chấp nhận được, không
rò xuống application/domain.

---

### [A-01] [High] Toàn bộ 1001 test chạy trên SQLite; 2 primitive khoá của Postgres bị nuốt im lặng

**Bằng chứng:**

```
$ grep -rn "sqlite\|postgres" tests/conftest.py tests/integration/conftest.py
tests/conftest.py:21:        db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
tests/integration/conftest.py:78:        "sqlite+aiosqlite://",
tests/integration/conftest.py:86:    def _set_sqlite_pragma(dbapi_connection: object, ...)
```

Không có conftest nào trỏ Postgres ⇒ **1001/1001 test chạy trên SQLite in-memory.**

Trong khi đó code production dùng 2 primitive chỉ Postgres mới có:

```
src/pharmacy_os/core/outbox/repository.py:75:            .with_for_update(skip_locked=True)
src/pharmacy_os/modules/compliance/infrastructure/repository.py:291:            .with_for_update(skip_locked=True)
```

Biên dịch cùng một câu lệnh trên 2 dialect:

```
$ python -c "... stmt = select(OutboxEventORM).limit(1).with_for_update(skip_locked=True) ..."
POSTGRES: ... FROM event_outbox   LIMIT %(param_1)s FOR UPDATE SKIP LOCKED
SQLITE  : ... FROM event_outbox  LIMIT ? OFFSET ?
```

SQLAlchemy **bỏ hẳn** mệnh đề `FOR UPDATE SKIP LOCKED` khi dialect là SQLite — không cảnh báo, không
lỗi.

**Ảnh hưởng — cụ thể, không chung chung:** `OutboxRepository.claim_pending` và
`NationalSyncRetryClaimer.claim_due` là hai chỗ *duy nhất* trong hệ thống dựa vào khoá hàng để hai
tiến trình không cùng nhặt một bản ghi. Trong test, cơ chế đó **chưa từng được thực thi một lần nào**
— test luôn chỉ có một relay, và ngay cả khi có hai thì SQL sinh ra cũng không có khoá.

Prod thì ngược lại: `main._lifespan` tạo `outbox-relay` task cho **mỗi tiến trình**, nên `uvicorn
--workers N` hay N pod = N relay tranh nhau cùng bảng `event_outbox`. Chuỗi hỏng cụ thể: hai relay
cùng `claim_pending` một dòng `SaleCompleted` → cùng phát sự kiện → `wire_sale_dispensing` gọi
`inventory.dispense_for_sale` **hai lần cho một đơn hàng** → tồn kho bị trừ đôi. Đây đúng loại lỗi
"505 test đều xanh mà tính năng hỏng trên máy thật" đã sinh ra kỷ luật #7 — lần này nằm ở tầng CSDL
thay vì tầng seed.

Cùng nguyên nhân, một họ rủi ro thứ hai: SQLite **bỏ qua độ dài `VARCHAR(n)`**. Một giá trị dài hơn
cột sẽ pass toàn bộ test rồi vỡ ở Postgres bằng `value too long`. Dự án đã tự dựng
`tests/unit/test_request_schema_lengths.py` để chặn ở tầng schema — đúng hướng, nhưng nó chặn ở
Pydantic, không chặn ở đường ghi nội bộ (seed, backfill, handler cross-module).

**Khuyến nghị:**
1. Thêm một lớp test integration chạy trên Postgres thật (docker compose đã sẵn) cho **ít nhất** 2
   repository dùng `skip_locked` — kịch bản 2 claimer song song, khẳng định không nhặt trùng.
   Đánh dấu `@pytest.mark.postgres`, chạy trong `make check`.
2. Ghi rõ vào PROJECT_STATE: con số "N passed" là bằng chứng trên SQLite, **không** là bằng chứng
   trên Postgres. Hiện tài liệu không phân biệt hai thứ này ở bất kỳ chỗ nào.

---

### [A-02] [High · 🚫 RELEASE BLOCKER Sprint 9] Prod khởi động được với khoá ký JWT dài 3 byte

> **Chain nâng phân loại 2026-07-26:** release blocker cho Sprint 9. Lý do: vi phạm trực tiếp ý đồ
> "fail-fast prod" dự án đã tự tuyên bố từ Sprint 2 / `docs/10_CONFIG.md`. Vẫn không phải Critical
> vì chưa có deployment production nào. Sprint 9 không được đóng khi mục này còn mở.

**Bằng chứng:**

```
$ env -i PATH=$PATH HOME=$HOME APP__ENV=prod SECURITY__JWT_SECRET=abc \
      SECURITY__ALLOW_DEV_AUTH=false AI__API_KEY=x OUTBOX__SYNC_DRAIN=true \
      python -c "from pharmacy_os.core.config import Settings; s=Settings(); ..."
env         = prod
jwt_secret  = 'abc' len = 3
encryption.enabled = False
BOOTED OK IN PROD -> no minimum-length check, no encryption requirement
```

`core/config.py:264-286` — `_fail_fast_in_prod` chỉ so sánh **bằng đúng chuỗi placeholder**:

```python
missing = [
    name
    for name, secret in (
        ("SECURITY__JWT_SECRET", self.security.jwt_secret),
        ("AI__API_KEY", self.ai.api_key),
    )
    if secret.get_secret_value() == _PLACEHOLDER
]
```

Không có kiểm tra độ dài, không có kiểm tra entropy. `SecuritySettings.jwt_secret` (`core/config.py:203`)
cũng không có `min_length`.

Chính test suite đã in cảnh báo này 44 lần mỗi lần chạy, và nó đang bị bỏ qua:

```
tests/integration/test_iam_flow.py: 29 warnings
  .../jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 11 bytes long,
  which is below the minimum recommended length of 32 bytes for SHA256.
```

**Ảnh hưởng:** thuật toán là `HS256` (`core/config.py:209`) — khoá đối xứng. Khoá ngắn/ít entropy bị
dò offline từ **một** access token bất kỳ (token nào cũng được, kể cả token hợp lệ của chính kẻ tấn
công sau khi đăng ký dùng thử). Có khoá thì ký được token tuỳ ý — `tenant_id` bất kỳ, `permissions`
bất kỳ, `branch_id` bất kỳ. Đây là đường **duy nhất** phá được toàn bộ cách ly tenant mà audit này
tìm thấy, và nó vòng qua sạch mọi guard `_user_or_404`/`tenant_id == ctx.tenant_id` ở tầng service,
vì `get_context` tin token đã giải mã được. Nó cũng vòng qua 2FA: token đã ký thì không cần đăng nhập.

Đáng nói hơn: dự án **đã** thiết lập đúng kỷ luật "cấu hình nguy hiểm phải chặn ở lúc deploy, thật
to" cho `ALLOW_DEV_AUTH` và cho `ENCRYPTION__*` (validator ngay bên dưới, `config.py:288-303`, kiểm
cả `keys` rỗng lẫn `current_version` không khớp). Khoá ký JWT — thứ đứng trước tất cả — lại không có
kiểm tra tương đương. Đây là chỗ trống trong một hàng rào vốn đã được xây tốt, không phải là hàng rào
chưa xây.

**Khuyến nghị:** trong `_fail_fast_in_prod`, thêm ngưỡng độ dài tối thiểu 32 byte cho
`SECURITY__JWT_SECRET` (khớp khuyến nghị RFC 7518 §3.2 mà PyJWT đang cảnh báo). Cân nhắc `min_length`
trên `SecuritySettings` để áp cả ở dev, và nâng `InsecureKeyLengthWarning` thành error trong
`pytest` (`filterwarnings`) để nó không im lặng 44 lần nữa.

---

### [A-03] [High · 🚫 RELEASE BLOCKER Sprint 9] Prod khởi động được với `ENCRYPTION__ENABLED=false` — PII bệnh nhân nằm bản rõ, không có tín hiệu nào

> **Chain nâng phân loại 2026-07-26:** release blocker cho Sprint 9. Hai lý do: (a) vi phạm ý đồ
> "fail-fast prod" của Sprint 2 / `docs/10_CONFIG.md`; (b) đối tượng là dữ liệu cá nhân **nhạy cảm**
> theo Luật BVDLCN 91/2025, không phải dữ liệu thường. Vẫn không phải Critical vì chưa có deployment
> production nào — chưa có dữ liệu bệnh nhân thật nào đang nằm bản rõ. Sprint 9 không được đóng khi
> mục này còn mở.

**Bằng chứng:** cùng lệnh A-02 ở trên, dòng `encryption.enabled = False` với `APP__ENV=prod` và
EXIT=0. `core/config.py:183`:

```python
enabled: bool = False
"""Encrypt on write. Off by default so an upgrade never starts writing ciphertext
a deployment has no key for; reads handle both shapes regardless, which is what
lets a backfill run while the application is live."""
```

Validator `_fail_fast_in_prod` kiểm `encryption.keys`/`current_version`/`blind_index_key` **chỉ khi**
`enabled=true`. Không có nhánh nào yêu cầu `enabled=true` khi `env=prod`.

**Ảnh hưởng:** PROJECT_STATE §7bc ghi mục 3/4 "mã hoá at-rest" đã làm xong 5/N bước, phủ: bí mật TOTP
(`user_two_factor.secret`), PII bệnh nhân + người trả thuốc trong `compliance`, số điện thoại + dữ
liệu sức khoẻ khách hàng trong `crm`. Toàn bộ phần đó **mặc định tắt**, và cơ chế "reads handle both
shapes" — đúng lựa chọn kỹ thuật để backfill chạy khi app đang sống — cũng đồng thời làm biến mất mọi
tín hiệu cho biết nó đang tắt: không lỗi, không cảnh báo khởi động, đọc/ghi vẫn bình thường, test vẫn
xanh. Cách duy nhất phát hiện là mở CSDL ra nhìn.

Hai hệ quả tách bạch, nên tách bạch khi xử lý:
- **Kỹ thuật:** một deployment đi vào production với `.env` sao chép từ `.env.example` sẽ lưu bản rõ
  toàn bộ dữ liệu sức khoẻ, mà nhật ký dự án lại ghi mục này "đã có".
- **Pháp lý (nêu để Chain và người có thẩm quyền quyết, không phải kết luận pháp lý):** dữ liệu sức
  khoẻ là dữ liệu cá nhân nhạy cảm theo Luật BVDLCN 91/2025; khoảng cách giữa "đã cài đặt cơ chế" và
  "cơ chế đang bật" là khoảng cách mà một đợt thanh tra sẽ hỏi tới. Việc này cần người có chuyên môn
  pháp lý xác nhận mức độ, không phải kiểm toán viên kỹ thuật.

Ghi nhận công bằng: PROJECT_STATE §7bc **có** ghi nợ *"runbook bật trên deployment thật"* và
`.env.example` có quy trình 6 bước. Vấn đề không phải là giấu, mà là chỗ duy nhất chặn được sai sót
lúc deploy thì đang để trống, trong khi hai cấu hình nguy hiểm khác cùng file đã được chặn.

**Khuyến nghị:** thêm vào `_fail_fast_in_prod`: `env == "prod"` và `encryption.enabled is False` ⇒
raise, kèm hướng dẫn tắt có chủ đích bằng một biến riêng (ví dụ
`ENCRYPTION__ACKNOWLEDGE_PLAINTEXT_IN_PROD=true`) để việc chạy bản rõ trên prod phải là một quyết
định được ký, không phải một giá trị mặc định.

---

### [A-04] [Medium] Repository của `iam` là bộ duy nhất không tenant-scope theo cấu trúc

**Bằng chứng:** 9/10 module nhận `RequestContext` vào constructor repository và lọc `tenant_id` ngay
trong câu SQL. Ví dụ `modules/catalog/infrastructure/repository.py:21`:

```python
class SqlAlchemyDrugRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
    ...
    async def get(self, drug_id: UUID) -> Drug | None:
        stmt = select(DrugORM).where(
            DrugORM.id == drug_id, DrugORM.tenant_id == self._ctx.tenant_id
        )
```

`iam` thì không — không repository nào nhận `ctx`, và truy vấn theo khoá chính:

```python
# modules/iam/infrastructure/repository.py
class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:      # <- không có ctx
    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserORM, user_id)      # <- không lọc tenant

class SqlAlchemyRoleRepository:
    async def get(self, role_id: UUID) -> Role | None:
        row = await self._session.get(RoleORM, role_id)

class SqlAlchemyBranchRepository:
    async def get(self, branch_id: UUID) -> Branch | None:
        row = await self._session.get(BranchORM, branch_id)

class SqlAlchemyRoleAssignmentRepository:
    async def delete(self, assignment_id: UUID) -> None:
        await self._session.execute(delete(UserRoleORM).where(UserRoleORM.id == assignment_id))
```

Quét AST toàn bộ `src/` tìm truy vấn trên model có cột `tenant_id` mà câu lệnh không nhắc `tenant_id`
— sau khi loại các trường hợp xuyên-tenant có chủ đích (outbox relay, national-sync retry claimer):
17 kết quả, **16 nằm trong `modules/iam/`**, 1 là `find_by_email` (email có `unique=True` toàn cục,
`models.py:71`, nên không nhập nhằng).

**Đã kiểm từng đường vào — hiện tại KHÔNG rò.** Tầng service chặn đủ:

| Đường vào | Guard | Vị trí |
|---|---|---|
| `get_user`, `set_user_active`, `reset_password` | `_user_or_404` → `user.tenant_id != ctx.tenant_id` | `iam_service.py:376-381` |
| `assign_role` | `_user_or_404` + `_role_or_404` + `_branch_or_404` | `iam_service.py:207-211` |
| `revoke_role` | `assignment.tenant_id != ctx.tenant_id` (kiểm trước `delete`) | `iam_service.py:249-256` |
| `list_assignments` | `_user_or_404` trước khi `list_for_user` | `iam_service.py:191` |
| `list_users` | truyền thẳng `ctx.tenant_id` xuống repo | `iam_service.py:103` |
| đổi mật khẩu / switch-branch / 2FA | `user.tenant_id != ctx.tenant_id` (4 chỗ) | `auth_service.py:343,370,523,581` |

**Ảnh hưởng:** đây là phát hiện về **thiết kế phòng thủ**, không phải lỗ hổng đang sống. Ở 9 module
kia, quên một guard ở tầng service vẫn còn lưới đỡ ở tầng repository. Ở `iam` không có lưới đó — một
endpoint mới quên gọi `_user_or_404` sẽ đọc/sửa được dữ liệu tenant khác ngay, và **không cổng nào
bắt được**: import-linter không biết gì về tenant, mypy không biết gì về tenant, và pytest dựng DB
rỗng một tenant nên test cross-tenant phải được viết tay mới có. Module không có lưới lại đúng là
module giữ tài khoản, vai trò và phiên đăng nhập — nơi một lần quên là leo thang đặc quyền chứ không
phải rò một bản ghi.

**Khuyến nghị:** không cần sửa gấp (đang đúng). Nhưng nên (a) thêm test hồi quy cross-tenant cho từng
endpoint `iam` — dựng 2 tenant, gọi bằng token tenant A lên `user_id` của tenant B, khẳng định 404;
(b) ghi rõ vào `docs/15_IAM_DESIGN.md` rằng `iam` cố ý lệch khuôn tenant-scope của các module khác và
vì sao (tra `find_by_email` lúc login chưa có tenant), để phiên sau không tưởng đó là sơ suất rồi
"sửa" nhầm hướng.

---

### [A-05] [Medium · ⏸️ QUYẾT ĐỊNH KINH DOANH CHỜ CHAIN] Một cặp credential VNPAY dùng chung cho mọi tenant

> **Chain đánh dấu lại 2026-07-26:** đây **không phải chỉ lỗi kỹ thuật**. Hình dạng tài khoản
> merchant quyết định dòng tiền, nghĩa vụ thuế và tư cách pháp lý của BeraLLC trong mỗi giao dịch —
> là quyết định của CEO, không phải của tầng kỹ thuật. Hai phương án + hệ quả pháp lý ở cuối mục này.
> **Phải chốt TRƯỚC khi mở bước sandbox VNPAY thật**, vì bước đó đăng ký `tmn_code` và chốt luôn
> hướng đi.

**Bằng chứng:** `plugins/payment_vnpay/src/payment_vnpay/config.py` — `tmn_code` và `hash_secret` là
trường phẳng của `VnpayConfig`, nạp một lần từ `PLUGINS__CONFIG` lúc khởi động
(`main._lifespan` → `loader.load_enabled(...)`), giữ trong `VNPayPlugin._config` suốt vòng đời tiến
trình. Không có tham số tenant ở bất kỳ đâu trong package.

Ghép với `modules/sales/application/service.py:303`:

```python
lookup_repo = self._repo_factory(uow, _LOOKUP_ONLY_CTX)
order = await lookup_repo.get_across_tenants(order_id)
```

⇒ một callback ký hợp lệ bằng cặp khoá dùng chung sẽ xác nhận thanh toán cho đơn hàng của **bất kỳ**
tenant nào.

PROJECT_STATE:3023-3025 có ghi quyết định *"cờ toàn cục … không per-tenant — … per-tenant để dành
quyết định sau nếu thực tế cần"*, đóng khung nó như một lựa chọn kỹ thuật về phạm vi cờ bật/tắt.

**Ảnh hưởng — hai thứ tài liệu chưa ghi:**
1. **Tiền chảy về đâu.** `tmn_code` là mã merchant, gắn với **một** tài khoản nhận tiền. Một cặp
   `tmn_code`/`hash_secret` cho cả hệ thống nghĩa là tiền khách trả ở **mọi nhà thuốc** đổ về **một**
   tài khoản merchant — của bên vận hành SaaS, không phải của từng nhà thuốc. Với sản phẩm bán cho
   nhà thuốc lẻ (phân khúc C1 đã chốt), đây không phải chi tiết kỹ thuật hoãn được: nó quyết định
   dòng tiền, nghĩa vụ thuế và hợp đồng với VNPAY. Cần Chain và người có chuyên môn pháp lý/kế toán
   xác nhận, không phải quyết định của tầng kỹ thuật.
2. **Bán kính vụ nổ khi lộ khoá.** Docstring của `hash_secret` đã cảnh báo đúng mức độ (*"A leaked
   hash secret lets anyone forge a 'payment succeeded' callback for any amount"*) nhưng nói ở phạm vi
   một merchant. Thực tế phạm vi là **toàn bộ tenant trên hệ thống**, vì `get_across_tenants` không
   giới hạn gì.

**Khuyến nghị:** ghi mục này vào phần rủi ro của thiết kế `payment_vnpay` trước khi mở khoá bước
sandbox thật (bước đang chặn), vì bước đó sẽ chốt luôn hình dạng tài khoản merchant. Nếu giữ hướng
per-tenant, `PLUGINS__CONFIG` phẳng hiện tại không đủ và phải quyết trước khi có dữ liệu thật.

#### ⏸️ HAI PHƯƠNG ÁN CHỜ CHAIN QUYẾT

Trình bày để Chain chọn. Kiểm toán viên **không** khuyến nghị hướng nào — đây là quyết định về mô
hình kinh doanh, không phải về kiến trúc. Phần dưới là mô tả hệ quả, không phải tư vấn pháp lý ràng
buộc; cả hai hướng đều cần luật sư/kế toán thật xác nhận trước khi ký hợp đồng với VNPAY.

| Trục | **PA1 — Mỗi nhà thuốc một merchant account** | **PA2 — Gom về BeraLLC, đối soát nội bộ** |
|---|---|---|
| Tiền khách trả đi đâu | Thẳng vào tài khoản của chính nhà thuốc đó | Vào tài khoản BeraLLC, sau đó BeraLLC chi trả lại từng nhà thuốc |
| Ai ký hợp đồng với VNPAY | Từng nhà thuốc tự ký, tự cung cấp giấy phép kinh doanh | BeraLLC ký một hợp đồng |
| Tư cách của BeraLLC trong giao dịch | **Nhà cung cấp phần mềm.** Không chạm tiền khách | **Trung gian giữ hộ tiền của người khác** |
| Nghĩa vụ thuế / hoá đơn | Doanh thu bán thuốc là của nhà thuốc, BeraLLC chỉ xuất hoá đơn phí phần mềm | Tiền vào tài khoản BeraLLC nhưng **không phải doanh thu BeraLLC** — phải tách bạch được trên sổ, nếu không rủi ro bị coi là doanh thu và bị truy thu |
| Rủi ro pháp lý đặc thù | Thấp. BeraLLC không giữ tiền của ai | **Cao và cần kiểm tra riêng:** giữ hộ + chi trả lại cho bên thứ ba có thể chạm định nghĩa **trung gian thanh toán** — hoạt động có điều kiện, cần giấy phép NHNN. Đây là điểm phải hỏi luật sư trước tiên, không phải chi tiết kỹ thuật |
| Khi nhà thuốc rời hệ thống | Không vướng — tài khoản là của họ | Phải đối soát và tất toán công nợ trước khi cắt |
| Bán kính khi lộ `hash_secret` | Một nhà thuốc | **Toàn bộ tenant** — kẻ có khoá giả được callback "đã thanh toán" cho đơn của bất kỳ nhà thuốc nào |
| Việc phải làm ở code | `PLUGINS__CONFIG` phẳng hiện tại **không đủ** — cần config theo tenant, đổi cách `SalesService` phân giải gateway, và xem lại `get_across_tenants` | **Chạy được ngay với code hiện tại.** Đây là hướng code đang mặc nhiên đi theo mà chưa ai chọn |
| Vận hành hàng ngày | Mỗi nhà thuốc tự xem tiền về; BeraLLC không phải đối soát | BeraLLC phải chạy đối soát + chi trả định kỳ — công việc thật, cần người và quy trình |

**Điểm quan trọng nhất:** code hôm nay **đã là PA2** — không do ai chọn PA2, mà do quyết định
"cờ toàn cục, per-tenant để sau" (PROJECT_STATE:3023-3025) được ghi như một lựa chọn kỹ thuật, trong
khi hệ quả của nó là một mô hình kinh doanh. Nếu Chain muốn PA1, càng chốt sớm càng rẻ: `tmn_code`
đăng ký sandbox theo hướng nào thì hướng đó khó đổi về sau, và giá phải trả tăng vọt một khi có tiền
thật đã chảy qua.

**Câu hỏi tối thiểu nên hỏi luật sư nếu nghiêng PA2:** việc BeraLLC nhận tiền khách hàng của nhà
thuốc rồi chi trả lại có bị coi là **hoạt động trung gian thanh toán cần giấy phép** không? Trả lời
"có" thì PA2 bị loại luôn, không cần bàn tiếp phần kỹ thuật.

---

### [A-06] [Medium] Docstring hứa timeout cho plugin — không có `wait_for` nào trong repo

**Bằng chứng:** `core/plugins/interfaces.py:72-80`:

```
Both methods are ``async`` on purpose, and this is the load-bearing decision of
the whole plugin surface. ... Being ``async`` also
makes them the only shape ``asyncio.wait_for`` can actually time out, which is
what turns docs/09 mục 6 ("timeout") from an aspiration into something
enforceable.
```

```
$ grep -rn "wait_for\|asyncio" modules/sales/application/service.py core/plugins/*.py api/v1/*.py
core/plugins/interfaces.py:78:    makes them the only shape ``asyncio.wait_for`` can actually time out, which is
```

Kết quả duy nhất là chính câu docstring đó. Điểm gọi thật (`service.py`, `gateway.create_charge(...)`
và `gateway.verify_callback(...)`) không bọc timeout nào.

**Ảnh hưởng:** `async` **cho phép** đặt timeout, nó không **là** timeout. Hôm nay VNPAY
`create_charge` không gọi mạng (chỉ dựng URL đã ký) nên chưa treo được — nhưng contract
`PaymentGateway` được viết cho mọi gateway tương lai, và docstring nói với người viết plugin sau rằng
yêu cầu timeout của docs/09 mục 6 đã "enforceable". Nó chưa. Cổng thanh toán chậm sẽ giữ request của
POS đến khi client tự bỏ, đúng kịch bản mà chính đoạn docstring viện dẫn để biện minh cho `async`
("every other counter in the pharmacy freezes").

**Khuyến nghị:** hoặc bọc `asyncio.wait_for` ở điểm gọi trong `SalesService` với ngưỡng cấu hình
được, hoặc sửa docstring cho đúng hiện trạng ("`async` mở đường cho timeout; chưa cưỡng chế —
xem nợ …"). Không nên để nguyên: đây là dạng câu mà phiên sau đọc và tin là đã xong.

---

### [A-07] [Medium] Mock gateway CSDL Dược + Mock LLM nạp cả khi `APP__ENV=prod`, không một dòng cảnh báo

**Bằng chứng:** `api/v1/national_sync.py:78-80` — không nhánh nào theo `env`:

```python
service = NationalSyncService(
    uow_factory, repo_factory, MockNationalDrugDbGateway(), retry_queue
)
```

`core/bootstrap.py:110` — tương tự:

```python
container.register_singleton(LLMProvider, lambda _c: MockLLMProvider())
```

`MockNationalDrugDbGateway.push` trả `SyncAck(ok=True, response_code="200", ...)` — luôn thành công.

Đối chiếu: cùng file `national_sync.py:95` **có** cảnh báo `env == "prod"` cho một thứ nhẹ hơn nhiều
(`retry_enabled` tắt). Toàn repo có 3 chỗ cảnh báo prod (`outbox_wiring.py:105,113`,
`national_sync.py:95`) và 1 chỗ chặn cứng (`config.py:266`). Việc cổng liên thông là **mock** không
nằm trong số đó.

**Ảnh hưởng:** một deployment prod sẽ ghi `national_sync_logs` trạng thái ACK 200, hàng đợi retry
trống, dashboard sạch — trong khi **không byte nào tới cơ quan quản lý**. Đây là loại sai lệch tệ hơn
lỗi: hệ thống báo cáo thành công cho một nghĩa vụ chưa được thực hiện. Việc chưa có adapter thật là
hoàn toàn hợp lý và đã ghi rõ (`# BLOCKER: DAV API spec`, spec dự kiến ~6/2026 theo QĐ1867) — vấn đề
là mock im lặng thay vì ồn ào.

**Khuyến nghị:** ở `wire_national_sync`, nếu `settings.app.env == "prod"` thì **từ chối khởi động**
(khớp khuôn `ALLOW_DEV_AUTH`) hoặc tối thiểu `_log.warning` mỗi lần push kèm cờ xác nhận có chủ đích.
Áp cùng cách cho `MockLLMProvider`.

---

### [A-08] [Medium] `demo_preview.py` vẫn crash, không cổng nào phủ

**Bằng chứng:**

```
$ python demo_preview.py ; echo "DEMO_EXIT=$?"
  File ".../demo_preview.py", line 133, in _build_services
    catalog = CatalogService(uow, lambda u, c: SqlAlchemyDrugRepository(u.session, c))
TypeError: CatalogService.__init__() missing 2 required positional arguments:
           'ingredient_repo_factory' and 'audit'
DEMO_EXIT=1
```

Đã được ghi nhận từ **2026-07-23** (PROJECT_STATE:3489, chẩn đoán đúng nguyên nhân: demo lỗi thời,
không phải bug service layer). Sau 3 ngày và ~20 commit, file vẫn ở gốc repo và vẫn hỏng.

**Ảnh hưởng:** không cổng nào chạm tới nó — `mypy` không thấy (ngoài `packages=["pharmacy_os"]`),
`pytest` không import, `ruff` từ `backend/` cũng không thấy (P0-05). Một file 13KB ở gốc repo mang
tên "preview" là thứ người mới (hoặc chính Chain khi muốn xem nhanh) sẽ chạy đầu tiên, và ấn tượng
đầu tiên là traceback. Chẩn đoán đã có sẵn từ lâu, chi phí sửa là thêm 2 tham số.

**Khuyến nghị:** sửa (rẻ), hoặc xoá, hoặc chuyển vào `scripts/` kèm ghi chú lỗi thời. Để nguyên là
lựa chọn tệ nhất trong ba.

---

### [A-09] [Low] `_canonical_query` — docstring nói "mọi tham số `vnp_*`", code ký mọi khoá

**Bằng chứng:** `plugins/payment_vnpay/src/payment_vnpay/signature.py`:

Docstring (dòng 11-13): *"take every ``vnp_*`` parameter except ``vnp_SecureHash``/
``vnp_SecureHashType``, sort by key, …"*

Code:
```python
_EXCLUDED = {"vnp_SecureHash", "vnp_SecureHashType"}

def _canonical_query(params: dict[str, str]) -> str:
    signable = {k: v for k, v in params.items() if k not in _EXCLUDED and v is not None}
    return "&".join(f"{k}={quote_plus(str(signable[k]))}" for k in sorted(signable))
```

Không có bộ lọc `startswith("vnp_")`.

**Ảnh hưởng:** không khai thác được (thêm tham số vào callback chỉ làm chữ ký lệch → bị từ chối, đúng
hướng fail-closed). Nhưng ở chiều liên thông thật: nếu IPN của VNPAY, hoặc một reverse proxy/CDN
đứng trước endpoint, đính thêm bất kỳ query param nào không thuộc `vnp_*`, `verify()` sẽ trả `False`
và mọi callback bị từ chối với `RspCode 97`. Triệu chứng sẽ là "sandbox không xác nhận được thanh
toán" — đúng bước đang bị chặn, và là dạng lỗi mất nhiều giờ để lần ra vì mã trông đúng và test nội
bộ (tự sinh params rồi tự ký) không thể bắt được: cả hai chiều đều dùng chung `_canonical_query`.

**Khuyến nghị:** trước khi chạy sandbox thật, quyết dứt điểm một trong hai: lọc `vnp_` theo đúng
docstring, hoặc sửa docstring và ghi rõ endpoint phải nhận query "sạch". Thêm một test với tham số
lạ trong payload để khoá hành vi đã chọn.

---

### [A-10] [Low] `vnp_IpAddr` cứng `127.0.0.1`; thiếu `vnp_ExpireDate`

**Bằng chứng:** `plugins/payment_vnpay/src/payment_vnpay/plugin.py`, `create_charge`:

```python
params = {
    "vnp_Version": "2.1.0",
    ...
    "vnp_IpAddr": "127.0.0.1",
    "vnp_CreateDate": now.strftime("%Y%m%d%H%M%S"),
}
```

Không có `vnp_ExpireDate`. `create_charge(order_id, amount, method)` — chữ ký của port
(`core/plugins/interfaces.py:96`) không có chỗ truyền IP khách, nên đây không sửa được trong riêng
package plugin.

**Ảnh hưởng:** `vnp_IpAddr` theo đặc tả VNPAY là IP của khách hàng, dùng cho đối soát và chấm điểm
gian lận. Gửi cố định `127.0.0.1` cho mọi giao dịch: hợp lệ về cú pháp, nên **test nội bộ không bắt
được**, nhưng sẽ hiện ra ở khâu đối soát/kiểm tra tích hợp của VNPAY. Thiếu `vnp_ExpireDate` thì đơn
không có hạn ở phía cổng. Cả hai là loại chỉ lộ ở đúng bước sandbox thật đang bị chặn — nên đáng biết
**trước** khi bước đó mở, không phải trong lúc debug nó.

**Khuyến nghị:** khi mở lại mục 4/4, xử luôn: thêm tham số IP khách vào port `PaymentGateway`
(đổi contract ⇒ bump `CORE_PLUGIN_API_VERSION` theo đúng quy tắc đã ghi ở `interfaces.py:14-22`),
và bổ sung `vnp_ExpireDate`.

---

### [A-11] [Low] Kiểm tra port plugin bằng `isinstance` chỉ xét cấu trúc, không xét chữ ký hàm

**Bằng chứng:** `core/plugins/loader.py:105`:

```python
ports = [port for port in KNOWN_PORTS if isinstance(plugin, port)]
```

`PaymentGateway` và `RegulatoryConnector` là `@runtime_checkable` Protocol
(`core/plugins/interfaces.py:70,102`). `isinstance` với `runtime_checkable` **chỉ kiểm tra thuộc
tính/phương thức có tồn tại**, không kiểm tra số tham số, kiểu, hay `async`.

**Ảnh hưởng:** một plugin định nghĩa `create_charge(self, order_id)` (thiếu 2 tham số) hoặc định
nghĩa nó là hàm đồng bộ vẫn qua được kiểm tra ở dòng 105, được đăng ký vào `HookRegistry`, và chỉ vỡ
bằng `TypeError` ở lần đầu thu ngân bấm "thanh toán". Đây đúng kịch bản mà toàn bộ triết lý fail-fast
của loader được viết ra để chặn (docstring dòng 17-21: *"Skipping silently moves the failure to a
cashier pressing 'pay'"*) — kiểm tra hiện tại chặn được plugin *thiếu* phương thức nhưng không chặn
được plugin có phương thức *sai*. Rủi ro thực tế thấp trong khi mọi plugin đều tự viết; tăng dần nếu
sau này có plugin bên thứ ba, đúng viễn cảnh docs/09 mô tả.

**Khuyến nghị:** khi nạp, đối chiếu thêm `inspect.signature` và `inspect.iscoroutinefunction` với
port; hoặc ghi rõ giới hạn này vào docs/09 mục 6 để không ai tin `isinstance` là kiểm tra contract
đầy đủ.

---

### [A-12] [Low] `main.py` / `models_registry.py` / `logging.py` / `workers/` nằm ngoài contract `layers`

**Bằng chứng:** `backend/.importlinter`:

```ini
[importlinter:contract:layers]
layers =
    pharmacy_os.api
    pharmacy_os.modules
    pharmacy_os.core
    pharmacy_os.shared
```

Top-level thực tế trong `src/pharmacy_os/`:

```
$ ls src/pharmacy_os/ | grep -v "^api$\|^modules$\|^core$\|^shared$\|__pycache__"
__init__.py
logging.py
main.py
models_registry.py
py.typed
workers
```

4 mục không thuộc tầng nào ⇒ contract `layers` không ràng buộc chúng theo cả hai chiều.

**Ảnh hưởng — hạn chế, cần nói cho đúng:** các contract `forbidden` (`kernel-knows-no-business`,
`shared-is-leaf`) có bắt **chuỗi gián tiếp**, nên đường vòng kiểu `core → models_registry → modules`
vẫn bị chặn. Cái không được bảo vệ là quan hệ thứ tự giữa 4 mục này với nhau và với các tầng: ví dụ
`workers/` (hiện là stub, chỉ import `core.config`) sau này lớn lên thành nơi chạy job nền có thể
import thẳng `modules` **và** `api` mà không contract nào phàn nàn. Đó là chỗ dễ mọc ra một
composition root thứ hai, song song với `api/v1/cross_module.py`, mà không ai nhận ra.

**Khuyến nghị:** thêm `pharmacy_os.workers` vào danh sách `layers` (đặt ngang `pharmacy_os.api`)
trước khi nó có code thật. Đây là *thêm* contract nên không vướng kỷ luật #4.

---

### 2.5 Khả năng mở rộng (portability / modularity)

| Hạng mục | Kiểm bằng | Kết quả |
|---|---|---|
| Gỡ 1 plugin, hệ thống còn chạy? | `PluginLoader().load_enabled({})` | **Có** — chạy bình thường, log `plugins_available_but_disabled plugins=['vnpay']`. Mặc định `PLUGINS__ENABLED=[]` nên trạng thái "không plugin" là đường đi chính, không phải đường lạ |
| Bật plugin chưa cài | `load_enabled({"payment_momo": {}})` | **Chặn đúng** — `PluginLoadError: Plugin 'payment_momo' được bật … nhưng không tìm thấy` |
| Gọi VNPAY khi chưa bật plugin | đọc `SalesService.initiate_vnpay_payment` | Trả `ValidationError("Cổng thanh toán chưa được bật")`, không 500. Callback trả `RspCode 99` |
| `LLMProvider` thay adapter được? | truy vết import | **Được** — 1 điểm đăng ký duy nhất (`core/bootstrap.py:110`); `clinical` chỉ phụ thuộc Protocol. Hiện chỉ có `MockLLMProvider` (xem A-07) |
| `NationalDrugDbGateway` thay adapter được? | truy vết import | **Được** — port khai trong `compliance/domain/ports.py:255`, adapter lắp ở `api/v1/national_sync.py`; domain/application không biết implement nào (xem A-07) |
| `BlockchainProvider` | `grep -rn -i "blockchain"` toàn repo + docs | **Không tồn tại và không được tuyên bố ở đâu.** Kết quả duy nhất nằm trong bản tóm tắt NĐ356/2025 (`docs/legal/`), là trích văn bản luật, không phải cam kết kiến trúc. Không có gì để audit |
| Rò dữ liệu chéo tenant | quét AST toàn `src/` + đọc từng đường vào `iam` | **Không tìm thấy chỗ nào đang rò.** Xem A-04 (thiết kế phòng thủ) và A-02 (đường vòng qua khoá JWT yếu) |

---

### 2.6 Chỉ số coupling

**Không có vòng phụ thuộc.** Dựng đồ thị import toàn `pharmacy_os` bằng AST, gom về mức package
(3 đoạn), DFS tìm chu trình:

```
No package-level import cycles found (depth=3)
```

**Module nghiệp vụ phụ thuộc nhiều nhất** (đếm số submodule của `core` mà mỗi module chạm):

| Module | Số core submodule | Danh sách |
|---|---|---|
| **sales** | **9** | audit, config, context, db, di, errors, events, **plugins**, security |
| **iam** | **9** | audit, config, context, db, di, errors, events, **http**, security |
| **compliance** | **8** | audit, context, db, di, errors, **http**, **outbox**, security |
| clinical | 8 | **ai**, audit, config, context, db, di, errors, security |
| inventory / prescription / procurement | 7 | audit, context, db, di, errors, events, security |
| analytics / catalog / crm | 6 | audit, context, db, di, errors, security |

**Module bị phụ thuộc nhiều nhất** (số file trong `api/` + `core/` chạm tới):

| Module | Số file api/core tham chiếu |
|---|---|
| **sales** | **7** |
| **compliance** | **7** |
| inventory | 6 |
| iam | 5 |
| procurement | 5 |
| prescription | 4 |
| analytics / catalog / clinical / crm | 3 |

**Submodule kernel bị phụ thuộc nhiều nhất:**

| core submodule | Số module tham chiếu |
|---|---|
| `core.context` | 52 |
| `core.audit` | 51 |
| `core.db` | 49 |
| `core.security` | 24 |
| `core.outbox` / `core.errors` / `core.events` | 20 |
| `core.di` | 18 |
| `core.plugins` / `core.config` | 10 |
| `core.ai` | 6 |
| `core.http` | 5 |

**Nhận định:** hình dạng coupling đúng như một hexagonal modular monolith nên có — 0 cạnh
module↔module, mọi phụ thuộc đi qua kernel hoặc composition root. `sales` là điểm nóng ở **cả hai
chiều** (phụ thuộc nhiều nhất *và* bị phụ thuộc nhiều nhất, đồng thời là module duy nhất chạm
`core.plugins`), nên nó là chỗ mọi thay đổi tốn nhiều nhất và cũng là chỗ đáng đầu tư test hồi quy
nhất. `core.context`/`core.audit`/`core.db` với fan-in ~50 là ba API kernel đã hoá xi măng: đổi chữ
ký của chúng là chạm gần như toàn bộ repo. Không có gì bất thường, chỉ nên biết trước khi ai đó đề
xuất refactor `RequestContext`.

---

## 3. NHỮNG GÌ ĐÃ KIỂM VÀ KHÔNG TÌM RA LỖI

Ghi lại để lần audit sau không phải làm lại, và để cân bằng — danh sách phát hiện ở trên không phải
bức tranh đầy đủ.

| Hạng mục | Cách kiểm | Kết quả |
|---|---|---|
| 5 cổng chất lượng | chạy từng cổng, đọc mã thoát thật, không qua pipe | 5/5 EXIT=0, con số khớp tài liệu 100% |
| Migration từ DB rỗng | upgrade → check → downgrade base → upgrade → check trên Postgres sạch | 5/5 bước EXIT=0, không drift |
| Hash commit tài liệu trích | 112 hash, `git cat-file -e` từng cái (2 repo) | 112/112 tồn tại |
| Secret trong lịch sử git | 5 hướng quét (file, private key, regex nhà cung cấp, `.env`, placeholder) | 0 |
| Domain purity | grep thủ công 10/10 module, cả import tương đối | 0 vi phạm |
| Module independence | tĩnh + `importlib` + `TYPE_CHECKING` + chuỗi trong config | 0 vi phạm |
| FK xuyên module | liệt kê toàn bộ `ForeignKey`, map bảng→module | Đúng 1, có lớp dịch lỗi |
| Composition root | liệt kê 9 handler/adapter cross-module | Tất cả ở đúng chỗ |
| Vòng phụ thuộc ẩn | DFS trên đồ thị import AST | 0 |
| Cách ly tenant ở 9 module ngoài `iam` | quét AST + đọc repository | Lọc `tenant_id` ở tầng repository, nhất quán |
| Truy vấn xuyên tenant có chủ đích | outbox relay, national-sync claimer, `get_across_tenants` | 3 chỗ, đều có docstring giải thích, đều đúng ngữ cảnh |
| Test bị skip/xfail | grep `pytest.mark.skip`/`xfail` | **0** — 1001 passed là 1001 chạy thật |
| CORS | `allow_credentials=True` + `allow_origins` | Mặc định `["http://localhost:3000"]`, không `["*"]` — đúng |
| `.env.example` | đọc toàn bộ | Placeholder `__set_me__`, không secret thật |
| Bề mặt API | `app.openapi()` | 86 path / 94 operation, mount đủ |
| Chống replay 2FA, khoá tài khoản | đọc model + service | `last_used_timestep`, `failed_login_count`, `locked_until` đều có |
| Chữ ký VNPAY so sánh hằng thời gian | đọc `verify()` | Dùng `hmac.compare_digest` — đúng |
| Callback VNPAY: xác thực trước, đọc dữ liệu sau | đọc `confirm_vnpay_callback` | Đúng thứ tự; đối chiếu `vnp_Amount` với `subtotal` đã lưu; idempotent theo `gateway_ref` (`unique=True`, `models.py:66`) |

---

## 4. Ý KIẾN KIỂM TOÁN VIÊN

**[Kiểm toán viên độc lập]:** Mặt bằng chung của repo này cao hơn hẳn mức tôi gặp ở một dự án chưa ra
production. Năm cổng đều xanh **và** con số khớp tài liệu đến từng đơn vị — hiếm; chuỗi 32 migration
đảo ngược sạch trên DB rỗng — hiếm hơn; 112/112 hash trích dẫn tồn tại thật; không một secret nào
trong lịch sử git; 0 import chéo module qua cả 3 dạng mà công cụ không bắt được. Kỷ luật ghi chép
tốt tới mức phần lớn công sức audit này là *xác minh* chứ không phải *phát hiện*, và đó là lời khen
về quy trình chứ không phải về may mắn.

Điều đó làm ba phát hiện High trở nên đáng nói hơn, vì cả ba đều cùng một hình dạng: **hàng rào đã
được xây đúng chỗ, nhưng bỏ trống đúng một ô.** `_fail_fast_in_prod` chặn `ALLOW_DEV_AUTH`, chặn
outbox chết, chặn khoá mã hoá sai — nhưng không chặn khoá ký JWT 3 byte (A-02) và không chặn mã hoá
tắt trên prod (A-03). `national_sync.py` cảnh báo prod cho `retry_enabled` tắt — nhưng im lặng khi
chính gateway là mock (A-07). Bộ test 1001 case rất kỹ — nhưng chạy trên engine không có
`FOR UPDATE SKIP LOCKED`, đúng hai chỗ duy nhất cần nó (A-01). Không phát hiện nào là do ẩu; tất cả
là do phạm vi của một cơ chế đúng bị dừng sớm hơn nửa bước.

Về mức độ: tôi **không** xếp cái nào là Critical, và muốn nói rõ vì sao để khỏi bị hiểu là nương tay.
A-02 có hậu quả cỡ Critical (giả mạo token là phá sạch cách ly tenant, vòng qua cả 2FA) nhưng nó cần
một điều kiện chưa xảy ra — chưa có deployment prod nào. Nó là **quả mìn đã cài chờ ngày deploy**,
không phải lỗ hổng đang chảy máu. Cùng lập luận cho A-03. Xử cả hai trước lần deploy đầu tiên thì
chúng biến mất hoàn toàn; deploy trước rồi sửa sau thì chúng biến thành sự cố có dữ liệu thật bên
trong. Đây là thứ tự đáng giữ.

Ba việc tôi cho là đáng làm sớm, xếp theo tỉ lệ rủi ro trên công sức: (1) A-02 — thêm ngưỡng 32 byte
cho khoá JWT, sửa vài dòng trong một validator đã tồn tại, gần như không có rủi ro hồi quy;
(2) P0-03/P0-04 — kéo `plugins/payment_vnpay/tests` và `seeds/` vào cổng thường trực, cả hai **đang
sạch** nên chi phí bằng không hôm nay và tăng dần mỗi ngày trì hoãn, trong khi `seeds/encrypt_backfill.py`
là file mà chính nhật ký dự án mô tả "sai là mất vĩnh viễn"; (3) A-01 — một lớp test Postgres cho hai
chỗ `skip_locked`, tốn công hơn nhưng là chỗ duy nhất trong audit này mà "test xanh" đang **thực sự
không chứng minh** điều người đọc tưởng nó chứng minh.

Hai việc còn lại tôi không đề xuất, tôi báo để người có thẩm quyền quyết, vì chúng vượt phạm vi kỹ
thuật: **A-05** (một tài khoản merchant VNPAY cho mọi nhà thuốc — tiền của tất cả tenant đổ về một
chỗ) là câu hỏi về dòng tiền, thuế và hợp đồng, cần Chain cùng người có chuyên môn kế toán/pháp lý
trả lời **trước** khi bước sandbox thật mở khoá, vì bước đó sẽ chốt luôn hình dạng tài khoản. Và
**A-03** ở khía cạnh Luật BVDLCN 91/2025 cần người có chuyên môn pháp lý xác nhận mức độ — tôi chỉ
xác minh được trạng thái kỹ thuật (mặc định tắt, không tín hiệu), không kết luận được nghĩa vụ tuân
thủ.

**Bổ sung sau điều chỉnh của Chain (2026-07-26):** Chain nâng A-02/A-03 thành release blocker Sprint
9 và giữ nguyên 0 Critical. Tôi đồng tình, và lý do Chain nêu mạnh hơn lý do ban đầu của tôi: tôi
xếp hai mục này theo mức thiệt hại nếu bị khai thác, Chain xếp theo **khoảng cách so với chuẩn dự án
đã tự đặt ra**. Trục thứ hai đúng hơn cho một quyết định phát hành — "fail-fast prod" là cam kết
Sprint 2 ghi trong `docs/10_CONFIG.md`, nên A-02/A-03 không phải phát hiện của người ngoài áp chuẩn
lạ vào, mà là hai chỗ dự án chưa làm đúng điều chính nó đã hứa. Với A-05, việc Chain kéo nó ra khỏi
cột kỹ thuật là xử lý đúng: tôi có thể chứng minh code đang làm gì, nhưng câu hỏi thật ở đây —
BeraLLC có được phép giữ hộ rồi chi trả lại tiền của nhà thuốc không — là câu hỏi cần giấy phép trả
lời, không phải cần thêm test.

Một ghi chú về phương pháp, ngoài phạm vi tính điểm nhưng đáng đọc: P0-01 cho thấy quy trình tự kiểm
chứng dựng ở §7az — dựng ra chính vì một lỗi đo đạc — hiện không đọc được con số nó cần đọc. Cơ chế
tự kiểm chứng cũng cần được kiểm chứng. Đó là lý do tồn tại của một phiên như phiên này, và là lý do
nên có phiên tiếp theo cho Giai đoạn 2 trở đi.

---

## 5. CHƯA LÀM TRONG PHIÊN NÀY

Phiên A chỉ phủ Giai đoạn 0 và 1. **Chưa** đụng tới:

- Đúng đắn nghiệp vụ (FEFO, máy trạng thái đơn thuốc, sổ kiểm soát đặc biệt, tính tiền/trả hàng)
- Đối chiếu `docs/13_COMPLIANCE_SPEC.md` với code (QĐ540 / TT20 / QĐ1867 / TT18)
- Chất lượng test theo chiều sâu (độ phủ nhánh, test có ý nghĩa hay chỉ chạm dòng, mutation)
- Bảo mật ngoài mục đã nêu: rate limit (đã ghi nợ ở §7bb), CSRF, kích thước payload, chuỗi ủy quyền
  đầy đủ trên toàn bộ 94 endpoint
- Hiệu năng, chỉ số N+1 query, chiến lược index
- Frontend (`frontend/`)
- `docs/14_FEATURE_PROCESS.md`: rà xem mọi tính năng đã build có hồ sơ Bước 0-4 tương ứng không —
  nhận xét sơ bộ: `docs/features/` có 6 thư mục, không có thư mục nào cho `payment_vnpay` hay
  "mã hoá at-rest"; **chưa xác minh** hai mục đó có nằm trong ROADMAP gốc (được miễn cổng) hay không.
  Để lại cho phiên sau, không kết luận ở đây.

**Không sửa bất kỳ dòng code nào. Không cập nhật PROJECT_STATE/TODO/ROADMAP.** Database thử nghiệm
`audit_empty_a` được tạo mới, tách biệt hoàn toàn với `pharmacy_os`; không lệnh nào chạm dữ liệu dev.

---

*Kết thúc Phiên A.*
