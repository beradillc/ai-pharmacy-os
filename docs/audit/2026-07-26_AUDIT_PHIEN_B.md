# AUDIT PHIÊN B — Bảo mật · Toàn vẹn dữ liệu · Chất lượng test (2026-07-26)

> **Vai:** Kiểm toán viên độc lập. KHÔNG phải GĐ, KHÔNG phải Trợ lý Code.
> **Tiếp nối:** `docs/audit/2026-07-26_AUDIT_PHIEN_A.md` (đã đọc trước khi bắt đầu, gồm 2 điều
> chỉnh Chain ban hành: A-02/A-03 = 🚫 release blocker Sprint 9; A-05 = ⏸️ quyết định kinh doanh).
> **Phạm vi:** Giai đoạn 2 (OWASP ASVS L2), Giai đoạn 3 (toàn vẹn dữ liệu), Giai đoạn 4 (chất test).
> **Không sửa một dòng code nào. Không cập nhật PROJECT_STATE/TODO/ROADMAP.**

Commit tại thời điểm audit: `7bbc8d5` · `main` · working tree sạch (không đổi so với Phiên A).

**Môi trường thử:** database **mới** `audit_empty_a` trên Postgres dev (tách hoàn toàn khỏi
`pharmacy_os`), migration tới `head`, seed dữ liệu tham chiếu, **2 tenant thật** để thử cách ly:

| Tenant | tenant_id | branch_id | admin |
|---|---|---|---|
| A (tấn công) | `20223ca0-…6693` | `0e16bd28-…2d0b` | `admin@auditb.test` |
| V (nạn nhân) | `80e627d2-…2e32c3c` | `2f10498c-…e3b3` | `admin@victim.test` |

`uvicorn` thật cổng 8098, `SECURITY__ALLOW_DEV_AUTH=false` (đường xác thực thật, không dùng
header dev), `SECURITY__JWT_SECRET` riêng 36 byte. Mọi kết quả dưới đây là **HTTP thật trên
Postgres thật**, không phải TestClient/SQLite.

---

## 0. TỔNG HỢP PHÁT HIỆN PHIÊN B

| ID | Mức | Tiêu đề | Trạng thái |
|----|-----|---------|------------|
| B-01 | **High** | `StockBalanceRepository.adjust` mất cập nhật khi ghi đồng thời — sổ kho tự mâu thuẫn | Đã chứng minh trên Postgres |
| B-02 | **High** | Khoá chống lặp `exists_for_ref` thua race — **một sự kiện giao 2 lần ⇒ 2 dòng xuất kho cùng `ref_id`** | Đã chứng minh trên Postgres |
| B-03 | **High** | `APP__DEBUG=true` trong `.env.example` ⇒ SQL echo đổ **PII bệnh nhân ra log** (tên, SĐT, CCCD) | Đã chứng minh |
| B-04 | Medium | Bán vượt tồn khi đồng thời: **không** phát `StockShortfallDetected`, **không** dòng đối soát nào | Đã chứng minh |
| B-05 | Medium | Endpoint HTTP gỡ 2FA của người khác **không đòi step-up**, yếu hơn chính thứ nó bảo vệ | Đã chứng minh |
| B-06 | Medium | `national_id_hash` (CCCD): tên cột nói "hash" nhưng lưu **nguyên văn**, không mã hoá, không hash | Đã chứng minh |
| B-07 | Medium | Không có ràng buộc `branch_id ∈ tenant` ở tầng nào — DB không FK, request không kiểm lại | Đã chứng minh |
| B-08 | Medium | Kiểm quyền nằm ở tầng service, **không** ở route ⇒ 422 chạy trước 403, lộ schema cho người không quyền | Đã chứng minh |
| B-09 | Medium | **0 test đồng thời** trong toàn bộ 1001 test — chính là lỗ hổng để B-01/B-02/B-04 sống sót | Đã chứng minh |
| B-10 | Medium | Không có rate limit ở bất kỳ đâu; `/auth/login` và webhook VNPAY mở hoàn toàn | Đã chứng minh |
| B-11 | Low | Cơ chế cứu sự kiện của outbox **mặc định tắt**; validator prod cho phép đúng cấu hình vô hiệu hoá nó | Đã chứng minh |
| B-12 | Low | Không thể chạy test suite trên CSDL có sẵn dữ liệu — conftest ghim cứng SQLite | Đã chứng minh |
| B-13 | Low | Token không ràng buộc `sub` ↔ `tenant` ↔ `branch`; không có `jti`/`iss`/thu hồi trước hạn | Đã chứng minh |

**Vẫn 0 Critical.** Không tìm thấy đường nào để một người dùng đã xác thực bình thường vượt sang
tenant khác, và không tìm thấy endpoint HTTP nào thiếu kiểm quyền. Các phát hiện High của phiên này
là **toàn vẹn dữ liệu dưới tải đồng thời** và **rò PII qua log**, không phải leo thang đặc quyền.

---

## 1. GIAI ĐOẠN 2 — BẢO MẬT (OWASP ASVS L2)

### 2.1 Xác thực JWT — thử giả mạo thật

| # | Thử nghiệm | Kết quả | Đánh giá |
|---|---|---|---|
| 1 | Token `alg=none`, không chữ ký | `PermissionDeniedError` | **Chặn** ✅ |
| 2 | HS256 ký bằng secret sai | `PermissionDeniedError` | **Chặn** ✅ |
| 3 | Token hết hạn (`exp` quá khứ) | `PermissionDeniedError` | **Chặn** ✅ |
| 4 | Cấu hình `JWT_ALGORITHM=none` rồi nạp token không chữ ký | `PermissionDeniedError` | **Chặn** ✅ (PyJWT từ chối `none` trừ khi bật tường minh) |
| 5 | Refresh token có phải JWT không? | Không — chuỗi mờ 64 ký tự, tra theo `token_hash` | **Đúng thiết kế** ✅ |
| 6 | Refresh có xoay vòng không? | Có, `r1 != r2` | ✅ |
| 7 | Dùng lại refresh đã tiêu | `401` + *"Phiên đăng nhập đã bị thu hồi"* | **Phát hiện tái sử dụng** ✅ |
| 8 | Token mới `r2` sau khi `r1` bị tái sử dụng | `401` — **thu hồi cả chuỗi phiên** | **Đúng chuẩn ASVS 3.3** ✅ |

Bằng chứng (rút gọn):

```
$ python -c "... svc.decode(none_tok) ..."
header: {'alg': 'HS256', 'typ': 'JWT'}
ALG_NONE:     REJECTED -> Token không hợp lệ hoặc đã hết hạn
WRONG_SECRET: REJECTED -> Token không hợp lệ hoặc đã hết hạn
EXPIRED:      REJECTED -> Token không hợp lệ hoặc đã hết hạn
CONFIG alg=none: rejected -> PermissionDeniedError

  refresh token là JWT? -> False | dài 64
  refresh #1 -> 200
  token xoay vòng (r1 != r2)? -> True
  DÙNG LẠI r1 (đã tiêu) -> 401 {"detail":"Phiên đăng nhập đã bị thu hồi, vui lòng đăng nhập lại"}
  r2 sau khi r1 bị tái sử dụng -> 401
```

`core/security/jwt.py:52` ghim `algorithms=[self._algorithm]` (danh sách một phần tử lấy từ config),
đúng cách chống thay-đổi-thuật-toán. Phát hiện tái sử dụng refresh + thu hồi toàn bộ phiên
(`auth_service.py:277-294`) là mức làm tốt hơn nhiều dự án cùng quy mô.

**Nguồn secret:** biến môi trường `SECURITY__JWT_SECRET`, mặc định `__set_me__`, prod từ chối
placeholder. Khiếm khuyết độ dài đã ghi ở **A-02 (release blocker)** — không lặp lại ở đây.

---

### [B-13] [Low] Token không ràng buộc `sub` ↔ `tenant` ↔ `branch`; không có `jti`/thu hồi trước hạn

**Bằng chứng:** ký một token hợp lệ với `sub` = admin của tenant **A** nhưng `tenant`/`branch` của
tenant **V**, rồi gọi API:

```
  token sub=userA + tenant=V, /auth/me -> 200
  {"user_id":"d4790bad-…(user tenant A)","tenant_id":"80e627d2-…(tenant V)",
   "branch_id":"2f10498c-…(branch tenant V)","permissions":["iam.user.read"]}

  đọc user tenant V bằng token đó -> 200
  {"id":"20a5e1f2-…","tenant_id":"80e627d2-…","email":"admin@victim.test", …}
```

Máy chủ **không bao giờ kiểm lại** rằng `sub` thực sự thuộc `tenant`, hay `branch` thuộc `tenant`.
Mọi thứ trong token được tin tuyệt đối sau khi chữ ký hợp lệ.

**Ảnh hưởng — nói cho đúng mức:** thử nghiệm này cần **secret ký**, nên **không** phải lỗ hổng độc
lập. Đường phát token hợp pháp đã chặn đúng (xem 2.3 dưới: `/auth/switch-branch` trả **403**). Giá
trị của phát hiện là nó **định lượng bán kính của A-02**: khoá ký lộ không chỉ là "giả mạo đăng
nhập", mà là **toàn quyền trên mọi tenant ngay lập tức**, vì không còn lớp kiểm tra thứ hai nào ở
phía sau. Đồng thời, thiếu `jti` nghĩa là **không có cách thu hồi một access token cụ thể** trước
khi nó hết hạn (60 phút) — đã được ghi nhận là đánh đổi có chủ đích ở docs/15 D2, ghi lại ở đây cho
đủ bức tranh.

**Khuyến nghị:** khi vá A-02, cân nhắc thêm một kiểm tra rẻ tiền ở `get_context`: `sub` có thuộc
`tenant` không (một truy vấn đã có sẵn ở phần lớn request). Không thay được cho khoá mạnh, nhưng
biến "lộ khoá = mất tất cả" thành "lộ khoá = mất tất cả **và** để lại dấu vết bất thường".

---

### 2.2 Phân quyền theo từng endpoint

**Cách kiểm:** ký một token **hợp lệ nhưng rỗng quyền** (`permissions=frozenset()`) rồi gọi lần lượt
26 endpoint GET và 14 endpoint POST/PUT với thân request hợp lệ về hình dạng.

| Nhóm | Số endpoint thử | Kết quả |
|---|---|---|
| GET có quyền chặn đúng | 20 | **403** |
| GET dừng ở 422 trước khi tới lớp quyền | 3 | `on-hand`, `analytics/dashboard`, ledger book (thiếu tham số bắt buộc) |
| GET trả 2xx với token rỗng quyền | **3** | `/health` (công khai, đúng), `/auth/me`, `/auth/2fa` |
| POST/PUT chặn đúng | 8 | **403** |
| POST/PUT dừng ở 422 | 6 | thiếu trường bắt buộc |
| POST/PUT trả 2xx với token rỗng quyền | **0** | — |
| Không có token | 5/6 | **401**; `/health` 200 (đúng), `/sales/vnpay/callback` 200 + `RspCode 99` (đúng thiết kế webhook) |

**`/auth/me` và `/auth/2fa` trả 200 là ĐÚNG** — đều tự-phạm-vi (chỉ trả danh tính và trạng thái 2FA
của **chính** người gọi), không có tham số để trỏ sang người khác.

Kiểm chéo bằng phân tích tĩnh — mọi phương thức public của service **không** gọi `require_permission`:

| Phương thức | Có lộ ra HTTP không? | Đánh giá |
|---|---|---|
| `AuthService.login / refresh / logout / change_password / *_two_factor / verify_step_up` (11) | Có | **Đúng** — thao tác tự-phạm-vi, mật khẩu/token là yếu tố xác thực |
| `AuthService.reset_two_factor_for_user` | Qua `IamService` | `iam.user.write` kiểm ở lớp gọi ✅ (nhưng xem **B-05**) |
| `IamService.bootstrap_tenant`, `sync_system_roles` | **Không** — chỉ CLI | ✅ (đã đối chiếu 94 route: không có) |
| `SalesService.confirm_vnpay_callback` | Có (webhook) | **Đúng** — chữ ký HMAC là xác thực |
| `CrmService.record_medication_history` | Không | Phản ứng hệ thống, ghi rõ ở `cross_module.py` |
| `CrmService.allergy_severities_for_safety_check` | Không | Port đọc **dữ liệu dị ứng** cho cross-module — xem ghi chú B-08 |

**KẾT LUẬN 2.2: không tìm thấy endpoint HTTP nào thiếu kiểm quyền.** Đây là kết quả sạch.

---

### [B-08] [Medium] Kiểm quyền nằm ở tầng service, không ở route — 422 chạy trước 403

**Bằng chứng:**

```
   422  POST /drugs                 (422: dừng ở validate thân, chưa tới lớp quyền)
   422  POST /inventory/receive     (422: dừng ở validate thân, chưa tới lớp quyền)
   422  POST /prescriptions         (422: dừng ở validate thân, chưa tới lớp quyền)
   422  PUT  /compliance/tenant-config
   422  POST /compliance/sync-logs
   422  POST /clinical/check-interactions
   422  GET  /inventory/on-hand
```

Tất cả gọi bằng token **rỗng quyền**. Thân request:
`{"detail":[{"type":"missing","loc":["body","rx_class"],"msg":"Field required", …}]}`

Không route nào khai báo quyền của mình; `require_permission` sống trong service, chạy **sau** khi
Pydantic đã validate thân request.

**Ảnh hưởng — ba thứ, tách bạch:**
1. **Lộ schema (ASVS 4.1.5, mức nhẹ):** người không có quyền nào vẫn dò được trường bắt buộc, kiểu
   dữ liệu, giá trị enum của endpoint họ không được chạm. Không phải lỗ hổng nghiêm trọng vì
   `/api/v1/openapi.json` cũng công khai, nhưng vi phạm nguyên tắc "từ chối trước, xử lý sau".
2. **Không có lưới an toàn khai báo:** một route mới quên gọi service đã gác — hoặc gọi một phương
   thức không gác như `CrmService.allergy_severities_for_safety_check` (đọc **dữ liệu dị ứng**, hiện
   chỉ dùng nội bộ cross-module) — sẽ **không** bị công cụ nào bắt. Đây đúng hình dạng **A-04**
   (Phiên A) ở tầng khác: lớp phòng thủ tồn tại, nhưng ở một tầng mà người viết route mới không nhìn
   thấy.
3. **OpenAPI không ghi quyền:** client và người kiểm thử không biết endpoint đòi quyền gì nếu không
   đọc mã nguồn service.

**Khuyến nghị:** thêm một dependency khai báo ở route (`Depends(requires("catalog.create"))`) **song
song** với kiểm tra trong service — không thay thế nó. Lợi ích kép: 403 trả trước 422, và mỗi route
tự khai quyền của mình ngay chỗ dễ soát nhất khi review.

---

### 2.3 Cách ly chi nhánh (branch isolation)

| # | Thử nghiệm | Kết quả |
|---|---|---|
| 1 | `GET /auth/me` + header `X-Branch-Id` = branch tenant khác | **200, branch trong phản hồi KHÔNG đổi** — header bị bỏ qua ✅ |
| 2 | `GET /inventory/on-hand?drug_id=…` + `X-Branch-Id` lạ | **200, `on_hand: 10.000`** (đúng số của branch trong token) ✅ |
| 3 | Cùng lệnh + **cả 3** header dev `X-Tenant-Id`/`X-User-Id`/`X-Branch-Id` | **200, `on_hand: 10.000`** — không đổi gì ✅ |
| 4 | `POST /auth/switch-branch` sang branch của tenant khác | **403** *"Không có quyền làm việc tại chi nhánh này"* ✅ |
| 5 | Token **ký** với `branch` = branch tenant khác, `tenant` = A | 200, `on_hand: 0` — và **ghi kho thành công (201)** ⚠️ xem B-07 |

**Lỗ hổng `X-Branch-Id` mà PROJECT_STATE §7l tuyên bố đã vá — xác nhận ĐÃ VÁ THẬT.** Đường phát
token (`/auth/switch-branch`) cũng chặn đúng qua `_choose_branch` (`auth_service.py:650-656`), đối
chiếu với `branches.list_active(user.tenant_id)` — tenant-scoped.

---

### [B-07] [Medium] Không tầng nào ràng buộc `branch_id` phải thuộc `tenant_id`

**Bằng chứng:** với token ký `tenant=A` + `branch=` chi nhánh của tenant V:

```
  token KÝ branch=BV (branch tenant khác), tenant=A -> 200 {"on_hand":"0"}
  GHI kho vào branch lạ bằng token đó -> 201
  {"batch_id":"d40adb85-…","quantity_received":"5","on_hand":"5.000"}
```

Dữ liệu thật để lại trong CSDL:

```sql
SELECT tenant_id, branch_id, drug_id, quantity FROM stock_balances;
              tenant_id               |              branch_id               | quantity
--------------------------------------+--------------------------------------+----------
 20223ca0-…(tenant A)                 | 2f10498c-…(branch của tenant V)      |    5.000   <-- lai tenant
 20223ca0-…(tenant A)                 | 0e16bd28-…(branch của tenant A)      |    8.000
```

Ba tầng đều không chặn:
- **DB:** module `inventory` có **0 ForeignKey** (đã xác nhận ở Phiên A mục 2.3) ⇒ không ràng buộc
  `branch_id` tồn tại, càng không ràng buộc nó thuộc tenant nào.
- **Repository:** lọc `tenant_id` **và** `branch_id`, nhưng coi cả hai là dữ liệu đầu vào tin cậy.
- **Request:** `get_context` không kiểm lại quan hệ branch↔tenant sau khi giải mã token.

**Ảnh hưởng:** như B-13, **cần secret ký** nên không độc lập khai thác được. Điều đáng ghi là hậu
quả **không đảo ngược bằng git revert**: nó tạo ra hàng dữ liệu lai tenant nằm im trong CSDL, không
báo cáo nào hiển thị (mọi báo cáo lọc theo branch của người xem), và không có kiểm tra toàn vẹn nào
phát hiện ra. Cùng nhóm với A-02 về nguyên nhân, nhưng khác về cách dọn dẹp — nên xử cùng lúc.

**Khuyến nghị:** thêm ràng buộc ở tầng rẻ nhất trước — FK `product_batches.branch_id → branches.id`
và `stock_*.branch_id → branches.id`. Việc `inventory` không có FK nào là lựa chọn module-independence
hợp lý cho `drug_id`, nhưng `branch_id` trỏ tới bảng của `iam` **đã** là quan hệ xuyên module giống
hệt `customer_allergies.ingredient_id` mà dự án chấp nhận (Phiên A mục 2.3) — nhất quán thì nên có.

---

### 2.4 Cách ly tenant — 5 repository + thử xuyên tenant thật

**Thử trên HTTP thật, token tenant A hợp lệ đầy đủ quyền, nhắm tài nguyên tenant V:**

| # | Thao tác | Kết quả |
|---|---|---|
| 1 | `GET /users/{user tenant V}` | **404** ✅ |
| 2 | `GET /users/{user V}/roles` | **404** ✅ |
| 3 | `PUT /users/{user V}/active` (vô hiệu hoá) | **404** ✅ |
| 4 | `POST /users/{user V}/reset-password` | **404** ✅ |
| 5 | `POST /users/{user V}/2fa/reset` | **404** ✅ |

**404 chứ không phải 403** là lựa chọn đúng: 403 sẽ xác nhận tài nguyên tồn tại (dò tenant).

**5 repository kiểm chi tiết mọi truy vấn (kể cả `get_by_id`):**

| Repository | Nhận `ctx`? | Mọi truy vấn lọc `tenant_id`? | Ghi chú |
|---|---|---|---|
| `catalog.SqlAlchemyDrugRepository` | Có | **Có** (3/3: `get`, `by_barcode`, `list`) | ✅ |
| `sales.SqlAlchemySalesRepository` | Có | **Có, trừ `get_across_tenants`** | Ngoại lệ duy nhất, chỉ webhook VNPAY dùng, có docstring |
| `crm.SqlAlchemyCustomerRepository` | Có | **Có** (4/4) | ✅ |
| `inventory.*` (3 repo) | Có | **Có** — lọc cả `tenant_id` lẫn `branch_id` | ✅ |
| `iam.*` (7 repo) | **Không** | **Không** — truy theo khoá chính | Xem **A-04** (Phiên A): gác ở tầng service, đã kiểm đủ 5/5 đường vào ở trên |
| `catalog.SqlAlchemyActiveIngredientRepository` | Không | Không | **Đúng** — dữ liệu tham chiếu toàn cục có chủ đích |

**KẾT LUẬN 2.4: không tìm thấy rò dữ liệu chéo tenant.** Kết quả này giữ nguyên nhận định Phiên A.

---

### [B-03] [High] `.env.example` bật `APP__DEBUG=true` ⇒ PII bệnh nhân đổ ra log

**Bằng chứng.** Tạo một khách hàng qua API thật, rồi soi log máy chủ:

```
$ grep -icE "0912345678|CCCD-001|Nguyen Van Benh" uvicorn.log
2

$ grep -inE "0912345678|CCCD-001" uvicorn.log
2324:2026-07-26 17:03:34,759 INFO sqlalchemy.engine.Engine [generated in 0.00010s]
  (UUID('20223ca0-…'), 'Nguyen Van Benh', '0912345678', None,
   datetime.date(1980, 1, 1), 'MALE', None, 'CCCD-001-BI-MAT', None, UUID('f0ad17b1-…'))
```

Họ tên, số điện thoại, ngày sinh, giới tính và **số CCCD** nằm nguyên văn trong log ứng dụng.

Chuỗi nguyên nhân:

```
backend/.env.example:3   APP__DEBUG=true
core/bootstrap.py:79     engine = build_engine(..., echo=settings.app.debug)
                         ⇒ echo=True ⇒ SQLAlchemy ghi TOÀN BỘ tham số mỗi câu lệnh
core/config.py:264       _fail_fast_in_prod KHÔNG kiểm app.debug
```

`.env.example` chính là file `CLAUDE.md` hướng dẫn sao chép để tạo `.env`
(*"tạo lại bằng `cp backend/.env.example backend/.env`"*). Một deployment làm đúng hướng dẫn sẽ bật
SQL echo.

**Ảnh hưởng:** hai lớp, tách bạch.
- **Kỹ thuật:** mọi tham số INSERT/UPDATE — gồm dữ liệu sức khoẻ (`customer_conditions.condition_code`,
  `customer_allergies.note`), PII bệnh nhân trong `compliance`, và **cả bí mật TOTP** khi ghi
  `user_two_factor` — chảy vào stdout. Log thường được gom, chuyển đi và giữ lâu, dưới cơ chế kiểm
  soát **yếu hơn** CSDL. Mã hoá at-rest (mục 3/4 Sprint 8) **không** che được đường này: cipher nằm
  ở tầng kiểu SQLAlchemy, còn echo ghi tham số **trước** khi mã hoá.
- **Nguyên tắc:** dự án đã tự phát biểu chính xác rủi ro này ở §7l khi thiết kế `audit_logs` —
  *"chép dữ liệu bị truy cập vào audit là tự tạo kho DLCN thứ hai ít được canh hơn kho nó bảo vệ"*.
  Đây là **đúng sai lầm đó qua một kênh khác**, và kênh này bật mặc định trong file mẫu.

Về mức độ pháp lý (Luật BVDLCN 91/2025, dữ liệu sức khoẻ = dữ liệu cá nhân nhạy cảm): kiểm toán
viên chỉ xác minh được trạng thái kỹ thuật; mức độ nghĩa vụ cần người có chuyên môn pháp lý xác nhận
— cùng lập luận đã nêu cho A-03.

**Khuyến nghị:** (1) `.env.example` đổi thành `APP__DEBUG=false` kèm một dòng cảnh báo rằng bật lên
sẽ ghi PII ra log; (2) tách `DB__ECHO` thành cờ riêng thay vì bám theo `app.debug` — người ta bật
debug để xem traceback, không phải để xem tham số SQL; (3) thêm `app.debug` vào `_fail_fast_in_prod`
cùng đợt vá A-02/A-03, vì cả ba cùng một họ.

---

### [B-06] [Medium] `national_id_hash` — tên cột nói "hash", thực tế lưu nguyên văn

**Bằng chứng.** Gửi chuỗi tuỳ ý vào trường đó qua API, rồi đọc thẳng CSDL:

```
POST /customers {"full_name":"Nguyen Van Benh","phone":"0912345678",
                 "national_id_hash":"CCCD-001-BI-MAT", …}  -> 201

$ psql -c "SELECT full_name, phone, national_id_hash, dob FROM customers;"
    full_name    |   phone    | national_id_hash |    dob
-----------------+------------+------------------+------------
 Nguyen Van Benh | 0912345678 | CCCD-001-BI-MAT  | 1980-01-01
```

API cũng **trả lại nguyên văn** trong `POST /customers` và trong danh sách `GET /customers?phone=…`.

Đối chiếu thiết kế mã hoá (`crm/infrastructure/models.py`):

| Trường | Mã hoá? | Có ghi lý do khi không mã hoá? |
|---|---|---|
| `phone` | **Có** (`EncryptedText` + `phone_fingerprint` blind index) | — |
| `gender` | **Có** | — |
| `full_name` | Không | **Có** — docstring 6 dòng: sắp xếp theo tên sẽ hỏng, ghi là nợ mở |
| `dob` | Không | **Có** — docstring 3 dòng: đổi `date` sang text mất kiểu |
| `weight_kg` | Không | Không (ít nhạy cảm, chấp nhận được) |
| **`national_id_hash`** | **Không** | **KHÔNG có docstring, không có lý do nào** |

**Ảnh hưởng:** đây không phải "quên mã hoá một trường". Trong module này mọi trường bị hoãn đều có
lý do ghi tại chỗ — trừ đúng trường số định danh cá nhân. Và tên `..._hash` **tạo bảo đảm sai**: bất
kỳ ai đọc lược đồ, đọc DPIA, hay trả lời câu hỏi thanh tra "CCCD lưu thế nào" sẽ trả lời "đã băm",
trong khi không có chỗ nào trong code thực hiện băm — client gửi gì lưu nấy. So sánh nội bộ càng rõ:
module `compliance` **đã** mã hoá `returner_id_number` (số giấy tờ người trả thuốc). Cùng loại dữ
liệu, hai module đối xử khác nhau.

**Khuyến nghị:** quyết một trong hai và ghi lý do như các trường khác — (a) đổi thành
`EncryptedText` + blind index như `phone` nếu cần tra cứu; hoặc (b) thực sự băm ở tầng service và
**từ chối** giá trị không đúng định dạng hash. Trong cả hai trường hợp, cân nhắc loại trường này
khỏi phản hồi danh sách (`GET /customers`) — không màn hình nào cần CCCD khi liệt kê khách.

---

### 2.6 Mã hoá at-rest — đã áp dụng thật cho trường nào

| Module | Bảng | Trường mã hoá (`EncryptedText`/`EncryptedString`) |
|---|---|---|
| `iam` | `user_two_factor` | `secret` (bí mật TOTP) |
| `crm` | `customers` | `phone`, `gender` |
| `crm` | `customer_allergies` | `note` |
| `crm` | `customer_conditions` | `condition_code`, `note` |
| `compliance` | `controlled_ledger_entries` | `customer_name`, `customer_address` |
| `compliance` | `drug_return_records` | `returner_name`, `returner_address`, `returner_id_number`, `returner_id_issuer`, `receiving_pharmacist_name` |

**Quản lý khoá:**

| Câu hỏi | Trả lời |
|---|---|
| Khoá nằm đâu? | Biến môi trường `ENCRYPTION__KEYS` (base64, có phiên bản) + `ENCRYPTION__BLIND_INDEX_KEY` riêng |
| Có commit vào git không? | **KHÔNG.** `.gitignore` bỏ `.env`/`.env.*` (giữ `.env.example`); toàn lịch sử git chỉ có `ENCRYPTION__KEYS={}` và `__set_me__` |
| Có KMS/HSM không? | **Không** — khoá sống trong `.env` trên cùng máy chạy app |
| Xoay khoá được không? | Có — nhiều phiên bản song song, ciphertext mang thẻ `v1:`/`v2:`, có `seeds/encrypt_backfill.py` |
| Có chặn cấu hình sai không? | **Có, tốt** — bật mà thiếu khoá / `current_version` không khớp / thiếu blind index ⇒ **từ chối khởi động ở MỌI môi trường** |

**Trạng thái thật khi chạy mặc định:** dữ liệu ở bảng trên nằm **bản rõ** — đã chụp bằng chứng ở
B-06. Đây là hệ quả trực tiếp của **A-03 (release blocker)**, không tính thành phát hiện mới.

Một ghi nhận công bằng: thiết kế xoay khoá (nhiều phiên bản, thẻ phiên bản trên từng ciphertext,
lệnh backfill chạy được khi hệ thống đang sống, cờ `--verify` bắt buộc trước khi xoá backup) là phần
được nghĩ kỹ nhất mà audit này gặp. Khiếm khuyết duy nhất là nó **mặc định tắt** và không có cổng
chặn ở prod.

---

### [B-05] [Medium] Gỡ 2FA của người khác qua HTTP không đòi step-up — yếu hơn chính thứ nó bảo vệ

**Bằng chứng.** `POST /api/v1/users/{user_id}/2fa/reset` (`iam/interface/router.py:204`):

```python
require_permission(ctx, "iam.user.write")     # iam_service.py:171
```

Đối chiếu phạm vi 2FA (`iam/domain/two_factor.py:26`):

```python
TWO_FACTOR_PERMISSIONS = frozenset({
    "compliance.ledger.sign",
    "iam.role.assign",
    "iam.role.write",
})
```

`iam.user.write` **không** nằm trong tập đó, và endpoint này **không** gọi `verify_step_up` — trong
khi hành vi mà 2FA bảo vệ (ký sổ kiểm soát đặc biệt) **có** đòi step-up.

Chuỗi tấn công cụ thể: kẻ chiếm được **một phiên đang mở** của tài khoản có `iam.user.write` (máy
quầy bỏ trống — chính mối đe doạ mà §7bb viện dẫn để xây step-up) → `POST /users/{dược-sĩ}/2fa/reset`
(204, không hỏi gì thêm) → `POST /users/{dược-sĩ}/reset-password` (cũng chỉ `iam.user.write`) →
đăng nhập bằng danh tính dược sĩ, **không còn 2FA** → ký sổ kiểm soát đặc biệt.

**Ảnh hưởng:** §7bb biện minh cho lệnh break-glass ở máy chủ bằng lập luận *"không mở bề mặt tấn
công vì ai chạy được đã có credential CSDL"*. Lập luận đó **đúng cho CLI và không áp dụng cho endpoint
HTTP này**, vốn chỉ cần một access token. Kết quả: bảo đảm "chữ ký sổ kiểm soát đặc biệt luôn có yếu
tố thứ hai" (TT18 Điều 15.1.d) rút xuống thành "tin phiên đăng nhập của quản trị viên". Ghi nhận
giảm nhẹ: `system_admin` **có** `iam.role.assign` nên bản thân họ thuộc diện 2FA khi **đăng nhập** —
nhưng step-up tồn tại chính vì login-2FA không chặn được phiên đã mở.

**Khuyến nghị:** bắt `reset_two_factor` đi qua đúng `verify_step_up` mà việc ký đang dùng. Nguyên
tắc chung đáng ghi vào docs/15: **thao tác hạ một lớp phòng thủ phải được bảo vệ ít nhất bằng chính
lớp đó.**

---

### [B-10] [Medium] Không có rate limit ở bất kỳ đâu

**Bằng chứng:**

```
$ grep -rniE "rate.?limit|slowapi|limiter|throttl" src/ .env.example
(chỉ khớp nhầm 2 dòng "env_nested_delimiter" trong config.py)

$ grep -rn "add_middleware" src/pharmacy_os/main.py
103:    app.add_middleware(          # <- CORSMiddleware, và chỉ có nó
```

Bề mặt bị ảnh hưởng, xếp theo mức phơi nhiễm:

| Endpoint | Xác thực | Bảo vệ hiện có | Còn thiếu |
|---|---|---|---|
| `POST /auth/login` | công khai | khoá tài khoản (`failed_login_count`/`locked_until`) | **Không giới hạn theo IP** ⇒ dò mật khẩu rộng khắp nhiều tài khoản; và khoá tài khoản tự nó thành công cụ **DoS**: kẻ tấn công khoá được cả ca trực bằng cách nhập sai có chủ đích |
| `POST /auth/2fa/login` | công khai | 5 lần đoán / challenge | Không giới hạn số **challenge** mở được |
| `GET /sales/vnpay/callback` | chữ ký HMAC | — | Hoàn toàn mở; mỗi request tốn một lần HMAC-SHA512 |
| 92 endpoint còn lại | Bearer | — | Không có |

§7bb **đã ghi nhận** đây là nợ (*"Chưa có rate limit theo IP/endpoint"*). Phiên này xác nhận nợ đó
vẫn nguyên và bổ sung một hệ quả chưa được ghi: **khoá tài khoản không kèm giới hạn IP là một vector
DoS**, không chỉ là thiếu một lớp phòng thủ.

---

## 2. GIAI ĐOẠN 3 — TOÀN VẸN DỮ LIỆU

### 3.1 Idempotency — chạy 2 lần cùng payload trên CSDL thật

**Danh mục đầy đủ mọi điểm nhận sự kiện/callback từ ngoài:**

| # | Điểm vào | Khoá chống lặp | Có ràng buộc CSDL đỡ không? | Thử 2 lần tuần tự | Thử 2 lần **đồng thời** |
|---|---|---|---|---|---|
| 1 | `POST /sync/sales` | `client_uuid` | **Có** — `uq_sale_client_uuid UNIQUE(tenant_id, client_uuid)` | ✅ cùng `id`, tồn 10→8 | ✅ không nhân đôi đơn |
| 2 | `POST /sales` | `client_uuid` | **Có** — cùng ràng buộc | ✅ 1 đơn duy nhất trong CSDL | ✅ |
| 3 | `GET /sales/vnpay/callback` | trạng thái đơn + `gateway_ref` | **Có** — `sale_payments.gateway_ref UNIQUE` | (không có sandbox — xem 4.4) | — |
| 4 | Handler `SaleCompleted` → xuất kho | `exists_for_ref("sale", order_id)` | **KHÔNG** | ✅ | ❌ **B-02** |
| 5 | Handler `GoodsReceived` → nhập kho | `exists_for_ref("grn", grn_id)` | **KHÔNG** | ✅ | ❌ cùng lỗi B-02 |
| 6 | `OutboxRelay` giao sự kiện | at-least-once, dựa vào #4/#5 | — | ✅ | ❌ thừa hưởng B-02 |
| 7 | `NationalSyncRetryRelay` | `client_uuid` trong `national_sync_logs` | — | ✅ | chưa thử |

Bằng chứng cho #1 và #2:

```
  POST /sync/sales lần 1 -> 200 id=0bf9243b-5bdc-4883-8d5d-a2c95a9ad35b
  POST /sync/sales lần 2 -> 200 id=0bf9243b-5bdc-4883-8d5d-a2c95a9ad35b
  CÙNG id? -> True
  tồn (10 - 2 = 8 nếu không nhân đôi) -> {"on_hand":"8.000"}

$ psql -c "SELECT count(*), client_uuid FROM sales_orders GROUP BY client_uuid ORDER BY 1 DESC LIMIT 5;"
 so_don |             client_uuid
--------+--------------------------------------
      1 | efd49897-…      (mọi client_uuid đều đúng 1 đơn)
      1 | 10d5c696-…
```

**Idempotency ở tầng đơn hàng là thật và được CSDL bảo đảm.** Vấn đề nằm ở #4/#5 — mục kế tiếp.

---

### [B-02] [High] Khoá chống lặp `exists_for_ref` thua race — một sự kiện giao 2 lần tạo 2 dòng xuất kho cùng `ref_id`

**Bằng chứng — gọi thẳng service, hai lần **cùng một `order_id`**, chạy song song trên Postgres:**

```python
await asyncio.gather(
    inv.dispense_for_sale(items, order, ctx),   # items = 10 viên
    inv.dispense_for_sale(items, order, ctx),   # CÙNG order_id
)
```

```
tồn sau nhập 100 : 100.000
[info] stock_moved_out  quantity=10
[info] stock_moved_out  quantity=10        <-- CẢ HAI đều đi qua khoá chống lặp
tồn sau 2 lần giao CÙNG order_id (kỳ vọng 90): 90.000
```

Trạng thái CSDL sau đó:

```sql
SELECT type, ref_type, ref_id, quantity FROM stock_movements WHERE drug_id='db9d4406-…';
 type | ref_type |                ref_id                | quantity
------+----------+--------------------------------------+----------
 IN   | GRN      |                                      |  100.000
 OUT  | sale     | ff8f49ba-bb1b-4fcd-a179-370ec2ec2fcb |   10.000
 OUT  | sale     | ff8f49ba-bb1b-4fcd-a179-370ec2ec2fcb |   10.000   <-- TRÙNG ref_id

  nhap   |  xuat            so_du
---------+--------          --------
 100.000 |  20.000           90.000     <-- sổ nói xuất 20, số dư nói xuất 10
```

Nguyên nhân, `inventory/application/service.py:256`:

```python
if await movements.exists_for_ref("sale", order_id):
    return  # this sale was already dispensed
```

Đọc-rồi-ghi, không khoá hàng, và **không có unique index đỡ phía sau**:

```sql
SELECT indexname FROM pg_indexes WHERE tablename='stock_movements';
 ix_stock_movements_tenant_id / drug_id / branch_id / batch_id / stock_movements_pkey
 -- KHÔNG có unique trên (ref_type, ref_id)
```

**Ảnh hưởng:** docstring của outbox (`core/outbox/sink.py:17`) đặt toàn bộ bảo đảm lên câu *"delivery
is at-least-once … which is why every subscriber carries an idempotency key"*. Khoá đó **có tồn tại**
nhưng **không nguyên tử** — nó chỉ đúng khi không có hai lần giao chồng nhau, tức đúng trong trường
hợp duy nhất mà nó không cần thiết. Ở prod, at-least-once + nhiều relay (`uvicorn --workers N`, nhiều
pod) là điều kiện thường trực, không phải ngoại lệ.

Với nhà thuốc: `stock_movements` là **sổ xuất nhập tồn**. Sổ tự mâu thuẫn với số dư nghĩa là không
đối chiếu được với kiểm kê thực tế, và với thuốc kiểm soát đặc biệt thì đó là vấn đề hồ sơ pháp lý,
không chỉ là sai số kho.

**Khuyến nghị:** ràng buộc thật ở CSDL — `UNIQUE (tenant_id, ref_type, ref_id, batch_id)` trên
`stock_movements` — rồi bắt `IntegrityError` và coi như replay. Đây là cùng khuôn mà `sales_orders`
đang dùng đúng (`uq_sale_client_uuid`), chỉ là chưa áp cho `stock_movements`.

---

### [B-01] [High] `StockBalanceRepository.adjust` mất cập nhật khi ghi đồng thời

**Bằng chứng — hai lệnh bán song song, mỗi lệnh bán đúng bằng toàn bộ tồn (6), qua HTTP thật:**

```
  tồn trước: 6.000
  request 1 -> 200
  request 2 -> 200
  tồn sau 2 lệnh bán, mỗi lệnh 6.0 -> {"on_hand":"0.000"}
```

Sổ kho của chính loại thuốc đó:

```sql
 type | ref_type |                ref_id                | quantity
------+----------+--------------------------------------+----------
 IN   | GRN      |                                      |   10.000
 OUT  | sale     | 0bf9243b-…                           |    2.000
 OUT  | sale     | 5e8ecaca-…                           |    2.000
 OUT  | sale     | 8afd908a-…                           |    6.000
 OUT  | sale     | bd989ef7-…                           |    6.000

  nhap  |  xuat
--------+--------
 10.000 | 16.000        <-- xuất nhiều hơn nhập 6 đơn vị; số dư vẫn hiển thị 0
```

Nguyên nhân, `inventory/infrastructure/repository.py:197-219`:

```python
row = (await self._session.execute(stmt)).scalar_one_or_none()
...
row.quantity = row.quantity + delta      # đọc trong Python, cộng trong Python, ghi lại
await self._session.flush()
```

Không `SELECT … FOR UPDATE`, không `UPDATE … SET quantity = quantity - :d` nguyên tử, không cột
version lạc quan, và không `CHECK (quantity >= 0)` trong lược đồ. Toàn module `inventory`:

```
$ grep -rn "with_for_update\|version_id_col\|CheckConstraint" src/pharmacy_os/modules/inventory/
(không có kết quả)
```

Hai phiên cùng đọc `6`, cùng ghi `6 + (-6) = 0`. Đây là **lost update** kinh điển, không phải "kẹp
về 0" — số dư 0 chỉ là trùng hợp của phép cộng.

**Ảnh hưởng:** B-01 và B-02 **che lấp lẫn nhau**, và đó là điều tệ nhất. Ở thử nghiệm B-02, lost
update biến hai lần xuất 10 thành số dư 90 — **đúng con số mong đợi**, trong khi sổ có 2 dòng trùng.
Một người vận hành nhìn số dư sẽ thấy mọi thứ bình thường; sai lệch chỉ lộ ra khi ai đó cộng lại
`stock_movements`, tức là khi kiểm kê — thường là hàng tháng, và lúc đó không còn truy được nguyên
nhân.

Đối chiếu nợ đã ghi: TODO.md:77 ghi *"`inventory` — cảnh báo/khoá tồn-âm khi eventual-consistency ở
prod"*. Phát hiện này **khác** nợ đó ở hai điểm quan trọng: (1) nó xảy ra với `OUTBOX__SYNC_DRAIN=true`,
tức **đồng bộ, một tiến trình** — không cần eventual consistency; (2) triệu chứng không phải tồn âm
(tồn không bao giờ âm) mà là **sổ và số dư lệch nhau trong im lặng**. Nợ đã ghi không phủ trường hợp
này.

**Khuyến nghị:** đổi `adjust` sang `UPDATE stock_balances SET quantity = quantity + :delta WHERE …`
(nguyên tử ở CSDL, không đọc trước), và thêm `CHECK (quantity >= 0)` để lỗi lộ ra ngay ở dòng gây ra
thay vì tháng sau. Cả hai đều rẻ và không đổi kiến trúc.

---

### [B-04] [Medium] Bán vượt tồn khi đồng thời: không phát cảnh báo, không dòng đối soát nào

**Bằng chứng:** sau khi bán 12 đơn vị từ tồn 6 (thử nghiệm B-01):

```sql
SELECT count(*) FROM stock_reconciliation_needed;
 count
-------
     0
```

Thiết kế **có** cơ chế và **có** test cho nó (`inventory/application/service.py:296`):

```python
if item.quantity > total:
    uow.collect(StockShortfallDetected(...))
```

`tests/integration/test_cross_module_dispense.py:57 test_oversell_dispenses_available_and_flags_shortfall`
khẳng định đúng hành vi này — nhập 5, bán 10, tồn về 0, **1** sự kiện shortfall, `requested=10`,
`available=5`. Test đó **đúng và có giá trị**.

Nhưng điều kiện `item.quantity > total` được tính từ `total` **đọc trước đó**. Khi hai request đồng
thời cùng đọc `total = 6` và mỗi bên xin 6, **không bên nào** thấy `6 > 6`. Cả hai đi tiếp lặng lẽ.

**Ảnh hưởng:** cơ chế cảnh báo bán vượt tồn — thứ duy nhất biến "bán thuốc không có trong kho" từ lỗi
âm thầm thành việc có người xử lý — **tắt đúng lúc cần nhất**: khi hai quầy cùng bán viên cuối cùng.
Đó là kịch bản thực tế nhất của một nhà thuốc đông khách, không phải trường hợp biên.

**Khuyến nghị:** đi kèm B-01 — khi `adjust` là `UPDATE … quantity = quantity + :delta` nguyên tử,
lấy số dư **trả về sau khi cập nhật** làm căn cứ phát `StockShortfallDetected`, thay vì số đọc trước.

---

### 3.2 Outbox — sự kiện có mất khi relay chết không?

**Thử thật, ba bước, trên Postgres:**

**Bước 1 — mô phỏng relay chết** (`OUTBOX__SYNC_DRAIN=false`, `OUTBOX__RELAY_ENABLED=false`):

```
tồn trước khi bán: {"on_hand":"20.000"}
bán 7 -> 201
tồn SAU khi bán 7 (relay tắt, sync_drain tắt): {"on_hand":"20.000"}
```

Đơn hàng **COMPLETED** nhưng kho **không hề đổi** — sự kiện nằm lại trong bảng:

```sql
  status   | count
-----------+-------
 PENDING   |     2
 PUBLISHED |    13
```

**Bước 2 — bật relay lên, khởi động lại tiến trình:**

```sql
  status   | count            drug_id           | quantity
-----------+-------          ---------------------+----------
 PUBLISHED |    16            fb4b9b95-…          |   13.000
```

**Kết luận: sự kiện KHÔNG mất. Relay nhặt đúng 2 dòng PENDING và áp dụng đủ (20 → 13).**
Cơ chế phục hồi là thật và chạy đúng.

**Xác nhận thêm về ranh giới giao dịch (3.3):** `core/db/uow.py:100-107` ghi outbox **bên trong**
giao dịch nghiệp vụ:

```python
staged = await self._outbox.stage(self.session, events)   # cùng session, cùng transaction
await self.session.commit()
await self._outbox.after_commit(staged)
```

⇒ **không có dual-write.** Dữ liệu và thông báo cùng bền vững hoặc cùng không. `UnitOfWorkFactory`
luôn truyền sink nên không module nào lỡ dựng UoW thiếu outbox. Nhánh `if self._outbox is None`
(publish sau commit, có dual-write) chỉ dùng trong test. **Không phát hiện ở 3.3.**

---

### [B-11] [Low] Cơ chế cứu sự kiện mặc định tắt, và validator prod cho phép đúng cấu hình vô hiệu hoá nó

**Bằng chứng:**

| Cờ | Mặc định |
|---|---|
| `OUTBOX__SYNC_DRAIN` | **`True`** |
| `OUTBOX__RELAY_ENABLED` | **`False`** |
| `OUTBOX__RETENTION_ENABLED` | **`False`** |

`core/config.py:272` chỉ chặn **một** tổ hợp:

```python
if not self.outbox.sync_drain and not self.outbox.relay_enabled:
    raise ValueError("... events would be written to event_outbox and never delivered")
```

Tổ hợp **mặc định** (`sync_drain=True`, `relay_enabled=False`) đi qua validator. Trong tổ hợp đó,
sự kiện được phát ngay trong request — nhưng nếu tiến trình chết **giữa commit và publish**, dòng
`PENDING` để lại **không còn ai giao**. Đúng câu mà docstring `sink.py:11` hứa —
*"a crash between the commit and the publish now leaves a PENDING row for the relay instead of losing
the event"* — với điều kiện **relay đang chạy**, mà mặc định thì không.

Ghi nhận giảm nhẹ: `outbox_wiring.py:105,113` **có** phát cảnh báo prod cho cả `relay_enabled` lẫn
`retention_enabled` khi tắt. Nên đây là cảnh báo-chứ-không-chặn, không phải im lặng hoàn toàn.

**Khuyến nghị:** mở rộng validator: `env=prod` ⇒ đòi `relay_enabled=True` bất kể `sync_drain`, vì
relay là **cơ chế phục hồi**, không phải chế độ giao hàng thay thế. Cùng nhóm việc với A-02/A-03/B-03.

---

## 3. GIAI ĐOẠN 4 — CHẤT LƯỢNG TEST

### 4.1 Test khẳng định sai hành vi mong muốn

**Rà toàn bộ 1001 test. Không tìm thấy test nào khẳng định một hành vi đã lỗi thời** — không có
trường hợp lặp lại tiền lệ "test cashier 403". Cụ thể đã soi kỹ:

| Nhóm nghi ngờ | Kiểm | Kết luận |
|---|---|---|
| Test dùng mock rồi khẳng định kết quả của mock | `test_cross_module_compliance_sync.py` dùng `MockNationalDrugDbGateway` (luôn `ok=True`) | **Không phải chứng minh vòng tròn** — test khẳng định *sự kiện đã tạo đúng 1 dòng log và không nhân đôi khi replay*, tức khẳng định **hành vi của mình**, không phải của mock |
| Test tồn âm | `test_oversell_dispenses_available_and_flags_shortfall` | **Đúng và có giá trị** — chỉ không phủ nhánh đồng thời (xem B-04) |
| Test 403 phân quyền | `test_iam_api_e2e.py:218,237,243`, `test_two_factor_api_e2e.py:401` | Khớp hành vi thật đã kiểm chứng qua HTTP ở mục 2.2 |

**Một điểm đáng nêu, chưa tới mức "sai" nhưng tên hứa hơn nội dung:**
`test_an_admin_can_reset_another_users_two_factor` (`test_two_factor_api_e2e.py:372`) tạo một user
**chưa từng đăng ký 2FA** rồi khẳng định endpoint trả `204`. Nó chứng minh endpoint tồn tại và trả
đúng mã, **không** chứng minh nó gỡ được một yếu tố thứ hai **đang hoạt động** của một dược sĩ có
`compliance.ledger.sign` — đúng trường hợp nguy hiểm ở **B-05**, và cũng là trường hợp duy nhất
khiến endpoint này đáng tồn tại.

---

### [B-09] [Medium] 0 test đồng thời trong toàn bộ 1001 test

**Bằng chứng:**

```
$ grep -rln "asyncio.gather\|ThreadPool\|concurrent" tests/
(không có kết quả)
```

**Ảnh hưởng:** đây là **nguyên nhân gốc chung** của B-01, B-02 và B-04. Cả ba nằm ở đường code **đã
được phủ** — độ phủ dòng của `inventory/application/service.py` là **93%**, của
`inventory/infrastructure/repository.py` cũng nằm trong tổng thể **96%** toàn repo. Không phải "chưa
viết test cho hàm đó"; test có, chạy, xanh, phủ dòng. Chỉ là **mỗi test gọi hàm đúng một lần**.

Ghép với **A-01** (Phiên A: toàn bộ test chạy SQLite, `FOR UPDATE SKIP LOCKED` bị nuốt): dự án hiện
**không có cách nào** phát hiện một lỗi tương tranh — không engine phù hợp, và không kịch bản song
song. Ba lỗi tôi tìm được trong một buổi chiều đều thuộc lớp đó, và không lỗi nào cần công cụ đặc
biệt: chỉ cần `asyncio.gather` với hai lời gọi.

**Khuyến nghị:** một file `tests/integration/test_concurrency_postgres.py`, đánh dấu
`@pytest.mark.postgres`, phủ tối thiểu 3 kịch bản: (1) hai lần giao cùng `order_id`; (2) hai lệnh bán
cùng lô cuối; (3) hai claimer outbox tranh cùng hàng đợi. Kịch bản (1) và (2) tôi đã dựng sẵn trong
phiên này, chi phí chuyển thành test là nhỏ.

---

### [B-12] [Low] Không thể chạy test suite trên CSDL đã có dữ liệu

**Yêu cầu 4.2 là "chạy toàn bộ suite trên DB ĐÃ CÓ DỮ LIỆU, so kết quả". Không thực hiện được** —
và chính điều đó là phát hiện.

```python
# tests/conftest.py:21
db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),

# tests/integration/conftest.py:78
engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool, ...)
```

Cả hai ghim cứng, không có biến môi trường để trỏ sang Postgres. Mỗi test dựng lược đồ mới bằng
`Base.metadata.create_all` trên CSDL rỗng.

**Đây đúng là điều kiện cấu trúc đã sinh ra kỷ luật #7** (§7l: role hệ thống chỉ seed một lần, 505
test xanh trong khi admin bị 403 trên máy thật). Kỷ luật #7 giải quyết bằng **quy trình** — bắt buộc
chạy tay `python -m seeds.run` trên CSDL có dữ liệu. Nhưng bộ test tự nó vẫn **không thể** chạy ở
chế độ đó, nên bảo đảm phụ thuộc hoàn toàn vào việc người thực hiện nhớ làm.

**Việc thay thế đã làm được, và kết quả tốt:** chạy `python -m seeds.run` **hai lần** — lần đầu trên
CSDL rỗng, lần sau trên chính CSDL đó sau khi đã có 2 tenant + dữ liệu nghiệp vụ:

```
lần 1 (rỗng):  atc_codes_inserted=10  controlled_substances_created=122
               drug_interactions_inserted=5   system_roles_created=5   system_roles_updated=0
lần 2 (có dữ liệu): atc_codes_inserted=0  controlled_substances_created=0
               controlled_substances_updated=0  drug_interactions_inserted=0
               system_roles_created=0  system_roles_updated=0
```

**Nhánh "cập nhật cái đã tồn tại" chạy đúng, không nhân bản, không lỗi.** Lỗ hổng §7l đã được vá
thật, xác nhận trên CSDL có dữ liệu sẵn.

---

### 4.3 Đường code quan trọng không có test

| Đường quan trọng | Số file test | Đánh giá |
|---|---|---|
| Ký sổ kiểm soát đặc biệt (`compliance.ledger.sign`) | 4 | Phủ tốt |
| Thuốc kiểm soát đặc biệt (TT18) | 7 | Phủ tốt |
| Mã hoá / `FieldCipher` / `BlindIndex` | 2 | Có (`test_crypto.py`) |
| Step-up khi ký | 1 | Có |
| `confirm_vnpay_callback` | 1 (+16 test package **ngoài cổng**, xem P0-03 Phiên A) | Có, nhưng chưa chạy thật (4.4) |
| **Tương tranh (bất kỳ đường nào)** | **0** | **B-09** |
| **Rate limit / chống dò mật khẩu** | **0** | Không có gì để test — B-10 |
| **Gỡ 2FA của dược sĩ ĐANG bật 2FA** | **0** | B-05 |
| **Truy cập chéo tenant (2 tenant trong một test)** | **0** | Hành vi hiện **đúng** (kiểm bằng tay ở 2.4), nhưng không test nào khoá lại — xem A-04 |

**Độ phủ dòng tổng: 96%** (`coverage`, 10.313 câu lệnh, 306 miss, 984 nhánh, 95 nhánh phủ một phần,
EXIT=0). Thấp nhất: `workers/celery_app.py` 0% (stub), `sales/interface/router.py` 79%,
`iam/application/auth_service.py` 80%.

Nhận định quan trọng: **96% độ phủ dòng, 0% độ phủ tương tranh.** Con số 96% là thật và đáng ghi
nhận — nhưng nó đo thứ khác với thứ đang hỏng.

---

### 4.4 Tỷ lệ mock/thật — tính năng nào chưa từng chạy thật

| Tính năng | Trạng thái | Chứng minh bằng | Chặn bởi |
|---|---|---|---|
| **LLM lâm sàng** | `MockLLMProvider` là implement **duy nhất** | test trên mock | `# BLOCKER: AI__API_KEY thật` |
| **Liên thông CSDL Dược (DAV)** | `MockNationalDrugDbGateway` là implement **duy nhất**, luôn `ok=True` | test trên mock | `# BLOCKER: DAV API spec` (dự kiến ~6/2026, QĐ1867) |
| **VNPAY** | Plugin thật, thuật toán ký thật | 16 test package (**ngoài cổng thường trực**) + 12 test integration dùng gateway giả qua `HookRegistry` | **Chưa có sandbox thật** — cần `tmn_code`/`hash_secret` |
| **Blockchain** | **Không tồn tại, không được tuyên bố ở đâu** | — | — (xem Phiên A mục 2.5) |
| Mã hoá at-rest | Primitive thật, chạy thật | `test_crypto.py` + backfill đã chạy trên Postgres (§7bc) | **Mặc định tắt** — A-03 |
| 2FA | Thật, đã kiểm chứng HTTP thật (§7bb 17 mục) | test + kiểm tay | — |

**Ba tính năng mà nhật ký dự án ghi là "xong" nhưng chưa từng chạm hệ thống thật:** LLM, DAV, VNPAY.
Cả ba **đều được ghi nhận trung thực** trong PROJECT_STATE bằng `# BLOCKER` tại chỗ — đây là điểm dự
án làm đúng, và tôi không xếp nó thành phát hiện. Rủi ro còn lại đã nêu riêng ở **A-07** (mock chạy
cả ở prod mà không cảnh báo) và **A-09/A-10** (chi tiết giao thức VNPAY chỉ lộ khi gặp cổng thật).

---

## 4. Ý KIẾN KIỂM TOÁN VIÊN

**[Kiểm toán viên độc lập]:** Phiên A kết luận rằng chỗ yếu của dự án này là "hàng rào xây đúng, bỏ
trống một ô". Phiên B tìm thấy một dạng khác, và tôi nghĩ nó quan trọng hơn: **cơ chế đúng, nhưng
không nguyên tử.**

Cả ba phát hiện High về dữ liệu đều cùng hình dạng đó. Khoá chống lặp `exists_for_ref` có tồn tại —
nhưng là `if` trong Python thay vì ràng buộc trong CSDL. Cảnh báo bán vượt tồn có tồn tại, có test
tốt — nhưng so sánh với một con số đọc từ trước. `adjust` cộng trừ đúng — trong bộ nhớ Python. Không
chỗ nào là cẩu thả; mỗi chỗ đều là một lập trình viên đã **nghĩ tới** vấn đề và cài một lời giải
đúng cho luồng tuần tự. Điều thiếu là bước cuối: đẩy bảo đảm xuống nơi duy nhất giữ được nó khi có
hai người cùng bấm nút. Và dự án **biết** cách làm điều đó — `sales_orders` có `uq_sale_client_uuid`
và nhờ nó mà idempotency đơn hàng đứng vững trước đúng phép thử đã đánh gục kho. Cùng một repo, cùng
một tuần, hai chuẩn khác nhau.

Điều làm tôi chú ý nhất không phải từng lỗi, mà việc **B-01 và B-02 che nhau**. Ở phép thử hai lần
giao trùng, sổ ghi 2 dòng xuất 10 trong khi số dư chỉ giảm 10 — số dư **đúng bằng con số mong đợi**.
Nếu tôi chỉ nhìn `on_hand` như một người vận hành, tôi đã kết luận idempotency hoạt động tốt. Hai
lỗi độc lập triệt tiêu triệu chứng của nhau và để lại một hệ thống trông khoẻ mạnh. Đó là lý do tôi
xếp cả hai là High dù chưa có deployment thật: chúng không tự bộc lộ, và khoảng cách giữa lúc phát
sinh và lúc bị phát hiện là một kỳ kiểm kê.

Về B-09 — không một test tương tranh nào trong 1001 test — tôi muốn nói rõ để tránh bị đọc thành lời
chê chung chung. Độ phủ dòng 96% là con số cao thật, và các đường tôi phá đều **đã được phủ**: mỗi
hàm có test, mỗi test xanh, mỗi nhánh được chạm. Vấn đề là mọi test gọi hàm đúng một lần. Ghép với
A-01 (toàn bộ suite chạy SQLite, nơi `FOR UPDATE SKIP LOCKED` biến mất không dấu vết), dự án hiện
không có **phương tiện** phát hiện lớp lỗi này — thiếu cả engine lẫn kịch bản. Ba lỗi tôi tìm được
không cần công cụ gì đặc biệt: một `asyncio.gather` với hai lời gọi. Chi phí để bộ test nhìn thấy
chúng là nhỏ; chi phí để không nhìn thấy chúng là một sổ kho không đối chiếu được.

Phần bảo mật thì ngược lại, và đây là tin tốt cần nói rõ ràng như tin xấu. Tôi đã thử giả mạo token
bốn kiểu, dò 40 endpoint bằng token rỗng quyền, và tấn công chéo tenant năm đường bằng quyền admin
đầy đủ. **Không đường nào thủng.** Phát hiện tái sử dụng refresh token thu hồi cả chuỗi phiên — đúng
chuẩn ASVS 3.3, nhiều hệ thống lớn hơn không có. Lỗ hổng `X-Branch-Id` mà §7l tuyên bố đã vá thì
đúng là đã vá thật, kiểm bằng HTTP thật chứ không đọc code. Cách ly tenant trả 404 chứ không 403,
tức người viết đã nghĩ tới cả việc rò *sự tồn tại* của tài nguyên. Cổng đồng ý xử lý dữ liệu sức
khoẻ chặn đúng khi chưa có consent. Những thứ này không phải may.

Hai phát hiện tôi đặc biệt muốn Chain đọc kỹ, vì cả hai đều là **dự án tự đặt chuẩn rồi để hở đúng
chỗ mình vừa nói**. B-05: endpoint gỡ 2FA của người khác không đòi step-up, trong khi hành vi mà 2FA
đó bảo vệ thì có đòi — lời biện minh trong §7bb ("ai chạy được đã có credential CSDL") đúng cho lệnh
CLI và không áp dụng cho một endpoint HTTP chỉ cần access token. B-03: `.env.example` — file mà
CLAUDE.md bảo sao chép ra để tạo `.env` — bật `APP__DEBUG=true`, và qua `echo=settings.app.debug`
điều đó đổ tên, số điện thoại, ngày sinh và số CCCD của bệnh nhân vào log ứng dụng. Mã hoá at-rest
không cứu được đường này vì echo ghi tham số trước khi cipher chạy. Chính dự án đã phát biểu rủi ro
này chuẩn xác ở §7l khi thiết kế `audit_logs` — "tự tạo kho DLCN thứ hai ít được canh hơn kho nó bảo
vệ" — rồi mắc đúng nó qua một kênh khác.

Thứ tự tôi đề nghị, theo tỉ lệ rủi ro trên công sức: (1) **B-03** — sửa một dòng trong `.env.example`,
tách `DB__ECHO` khỏi `app.debug`, gộp vào cùng đợt vá A-02/A-03 vì cả ba là một họ "cấu hình mặc
định không an toàn cho prod"; (2) **B-02** — thêm `UNIQUE (tenant_id, ref_type, ref_id, batch_id)`
trên `stock_movements`, đúng khuôn `uq_sale_client_uuid` đã dùng đúng ở chỗ khác, một migration; (3)
**B-01 + B-04** cùng lúc — `adjust` thành `UPDATE … quantity = quantity + :delta` nguyên tử, lấy số
dư trả về làm căn cứ phát cảnh báo, thêm `CHECK (quantity >= 0)`; (4) **B-09** — ba kịch bản tương
tranh, tôi đã dựng sẵn hai trong phiên này.

Còn lại là những thứ tôi không đề xuất mà báo để người có thẩm quyền quyết. **B-06**: trường
`national_id_hash` lưu CCCD nguyên văn dưới một cái tên nói rằng nó đã được băm. Tôi xếp Medium theo
tiêu chí kỹ thuật, nhưng lưu ý rằng đây là trường duy nhất trong module `crm` **không có** lý do ghi
tại chỗ — mọi trường hoãn mã hoá khác đều có docstring giải thích — nên nhiều khả năng là bỏ sót chứ
không phải quyết định. Trả lời một câu hỏi thanh tra "CCCD lưu thế nào" dựa trên tên cột sẽ ra câu
trả lời sai. Và như A-03, mức độ nghĩa vụ theo Luật BVDLCN 91/2025 cần luật sư xác nhận, không phải
kiểm toán viên kỹ thuật.

Cuối cùng, một nhận xét về chính bộ tài liệu. Trong cả hai phiên, mọi lần tôi tìm thấy thứ gì, việc
đầu tiên tôi làm là tra xem PROJECT_STATE đã ghi chưa — và **phần lớn là đã ghi**: rate limit
(§7bb), mock DAV (`# BLOCKER` tại chỗ), tồn âm (TODO:77), `full_name`/`dob` chưa mã hoá (docstring
tại chỗ). Điều đó tiết kiệm cho tôi rất nhiều thời gian và nó là dấu hiệu của một dự án trung thực
với chính nó. Hai chỗ tài liệu **không** phủ đúng, và đó là hai chỗ đáng chú ý nhất: TODO:77 mô tả
vấn đề tồn kho là "eventual-consistency ở prod" trong khi tôi tái hiện được nó ở chế độ **đồng bộ,
một tiến trình** (B-01); và §7bb mô tả bề mặt tấn công của break-glass là CLI trong khi có một
endpoint HTTP làm việc tương đương yếu hơn (B-05). Cả hai đều là nợ **đã được nhìn thấy nhưng đóng
khung hẹp hơn thực tế** — dạng sai lệch khó tự phát hiện nhất, vì nó trông giống như đã xử lý.

---

## 5. CHƯA LÀM TRONG PHIÊN NÀY

- Đúng đắn nghiệp vụ chuyên môn: FEFO chọn lô có đúng quy tắc dược không, máy trạng thái đơn thuốc,
  công thức tính tiền/trả hàng, các mẫu biểu TT18/QĐ540
- Đối chiếu từng điều khoản `docs/13_COMPLIANCE_SPEC.md` với code
- `docs/14_FEATURE_PROCESS.md`: rà hồ sơ Bước 0-4 cho từng tính năng đã build (nêu sơ bộ cuối Phiên A,
  **vẫn chưa xác minh**)
- Hiệu năng, N+1 query, chiến lược index dưới tải
- Frontend (`frontend/`)
- Tương tranh ở các module ngoài `inventory` (`compliance` ledger, `procurement` GRN, `crm`) —
  cùng khuôn đọc-rồi-ghi, **chưa kiểm**, nên coi B-01/B-02 là mẫu chứ không phải danh sách đầy đủ
- Kịch bản khôi phục thảm hoạ: mất khoá mã hoá, khôi phục từ `pg_dump`

**Không sửa bất kỳ dòng code nào. Không cập nhật PROJECT_STATE/TODO/ROADMAP.** Toàn bộ thử nghiệm
chạy trên database `audit_empty_a` tách riêng; `pharmacy_os` (CSDL dev thật) **không bị chạm** ở bất
kỳ bước nào.

*Kết thúc Phiên B.*
