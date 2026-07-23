# 15. Thiết kế module `iam` — Identity & Access (BẢN ĐỀ XUẤT, CHỜ DUYỆT)

> **Trạng thái:** THIẾT KẾ, chưa code, chưa commit. Lập trong phiên Opus 2026-07-23 theo
> `PROJECT_STATE.md` §7k. Mọi mục đánh dấu **[CHỜ SẾP]** cần sếp chốt trước khi viết dòng code đầu tiên.
> Nguồn khảo sát: đọc thật `core/security/*`, `core/context.py`, `core/db/base.py`, `core/bootstrap.py`,
> `api/deps.py`, `api/v1/__init__.py`, `.importlinter`, `docs/11` §3, `docs/08` §2.1, 10 file `docs/legal/*`.

---

## 0. Phát hiện trong lúc khảo sát (ảnh hưởng trực tiếp thiết kế)

| # | Phát hiện | Mức | Hệ quả cho thiết kế |
|---|-----------|-----|---------------------|
| F1 | `api/deps.py:70-73` — nhánh Bearer lấy `branch_id` **thẳng từ header `X-Branch-Id` không kiểm tra**; permission nằm sẵn trong token nên client đổi header là truy cập chi nhánh bất kỳ trong tenant | 🔴 **Lỗ hổng thật** | Đây là thứ IAM PHẢI đóng. Giải pháp: branch nằm **trong token đã ký** (§4), bỏ tin header |
| F2 | Cùng chỗ: không có `X-Branch-Id` thì `branch_id = payload.tenant_id` — gán nhầm ID tenant vào cột branch | 🟠 Sai ngữ nghĩa | Dữ liệu branch-scoped ghi sai khóa; token mới luôn mang branch cụ thể |
| F3 | Code đang gọi `require_permission` với **32 permission**, `_DEV_PERMISSIONS` chỉ có **26** — thiếu đúng 6 `compliance.*` (`config.read/write`, `ledger.read/write`, `sync.read/push`) | 🟡 Lệch | §7k ghi "26 permission" là thiếu. Seed role phải phủ **32** |
| F4 | Module `compliance` **chưa mount router** (`api/v1/__init__.py` không gọi `register_compliance`; `interface/` chỉ có `export.py`+`schemas.py`) — nên F3 chưa lộ ra | 🟡 Lệch tài liệu↔thực tế | Không sửa ở bước này; chỉ ghi nhận (báo cáo riêng) |
| F5 | `TenantScopedMixin` ép `branch_id NOT NULL` — **không dùng được** cho `users`/`roles`/`user_roles` (tenant-wide, branch nullable) | 🟠 Va chạm | IAM tự khai cột, **KHÔNG sửa mixin dùng chung** (8 module đang xài) |
| F6 | `TokenPayload` không có `branch_id`, không có `jti` | — | Mở rộng thêm `branch_id: UUID \| None` (nullable ⇒ token cũ vẫn decode được) |
| F7 | `crm.read` hiện gộp cả dữ liệu thường (tên/SĐT) lẫn **dữ liệu nhạy cảm** (dị ứng, bệnh nền) | 🟠 Rủi ro tuân thủ | NĐ356 Điều 4.2 + GPP TT02 I-1a.III.4.a đòi phân quyền riêng cho dữ liệu nhạy cảm → xem §5, Q5 |
| F8 | `AuditLogger` mới ghi ra structlog, **chưa có bảng `audit_logs`** (nợ Sprint 7) | 🟡 Nợ đã biết | IAM sẽ gọi audit đúng chỗ; việc persist vẫn là nợ cũ, không giải quyết ở bước này |

---

## 1. Phạm vi

**TRONG phạm vi:** `users`, `roles`, `role_permissions`, `user_roles` (2 cấp chuỗi/nhà thuốc),
`refresh_tokens`, `tenants`, `branches` (tối thiểu), `/auth/login` · `/auth/refresh` · `/auth/logout` ·
`/auth/switch-branch` · `/auth/me`, `/users`, `/roles`, CLI bootstrap tenant, viết lại `api/deps.py`.

**NGOÀI phạm vi (ghi nhận, không code):** quản lý chuỗi nhà thuốc theo Luật 44/2024 (kho chuỗi,
luân chuyển thuốc Điều 47a) · 2FA (`settings.security.require_2fa_roles` đã có field nhưng chưa dùng) ·
SSO/OAuth · bảng `audit_logs` persist (nợ Sprint 7) · tách `crm.read` (đề xuất riêng, xem Q5) ·
mount router `compliance` (F4).

---

## 2. Kiến trúc — 4 lớp, đúng khuôn mẫu module hiện có

```
modules/iam/
  domain/        entities.py (User, Role, RoleAssignment, RefreshSession, Tenant, Branch)
                 ports.py    (UserRepository, RoleRepository, RoleAssignmentRepository,
                              RefreshTokenRepository, TenantRepository, BranchRepository)
                 exceptions.py (InvalidCredentials, UserLocked, UserInactive,
                                BranchNotAccessible, RefreshTokenReused, ...)
  application/   auth_service.py (login/refresh/logout/switch_branch/resolve_permissions)
                 iam_service.py  (create_user/deactivate/assign_role/revoke_role/list_roles)
                 dto.py
  infrastructure/ models.py · mappers.py · repository.py
  interface/     router.py (auth_router + users_router + roles_router) · schemas.py · register.py
```

**Không vi phạm module-independence:** không module nghiệp vụ nào import `iam`. `get_context` sống ở
tầng `api` (composition root) — tầng `api` được phép import `modules` theo contract `layers` hiện có.
⇒ **Đây KHÔNG phải cross-module theo nghĩa 2 module nghiệp vụ nối nhau.**

**Import-linter — [CHỜ SẾP] vì đụng contract cũ (kỷ luật #4):**
| Thay đổi | Loại |
|----------|------|
| Thêm contract `iam-domain-innermost` (giống 8 contract domain hiện có) | Thêm mới → OK theo kỷ luật #4 |
| Thêm `pharmacy_os.modules.iam` vào danh sách contract `module-independence` | **Sửa contract cũ → cần sếp gật** |

---

## 3. Lược đồ CSDL (migration `0013_iam`)

> Quy ước giữ nguyên toàn dự án: **không FK từ bảng nghiệp vụ sang bảng iam** (giống `grn_id` UUID trần
> ở `stock_reconciliation_needed`) — giữ module-independence ở cả tầng schema. FK chỉ tồn tại **nội bộ iam**.

| Bảng | Cột chính | Ghi chú |
|------|-----------|---------|
| `tenants` | `id` PK, `name`, `status`, timestamps | Không dùng `TenantScopedMixin` (F5) |
| `branches` | `id` PK, `tenant_id`→`tenants.id`, `code`, `name`, `status`, timestamps | `UNIQUE(tenant_id, code)` |
| `users` | `id` PK, `tenant_id`→`tenants.id`, `email`, `password_hash`, `full_name`, `status`, `must_change_password`, `last_login_at`, `failed_login_count`, `locked_until`, timestamps | `UNIQUE(email)` toàn hệ thống — xem Q2-phụ |
| `roles` | `id` PK, `tenant_id` **NULLABLE**→`tenants.id`, `code`, `name`, `description`, `is_system` | `NULL` = role hệ thống dùng chung mọi tenant; non-NULL = role riêng tenant (v1 chưa mở API tạo) |
| `role_permissions` | PK(`role_id`, `permission`) | `permission` là chuỗi thô, khớp `require_permission` |
| `user_roles` | `id` PK, `user_id`, `tenant_id`, `branch_id` **NULLABLE**→`branches.id`, `role_id`, `granted_by`, `granted_at` | `branch_id IS NULL` = áp dụng toàn chuỗi |
| `refresh_tokens` | `id` PK, `user_id`, `tenant_id`, `branch_id`, `token_hash` UNIQUE, `issued_at`, `expires_at`, `revoked_at?`, `replaced_by?` | Lưu **hash** (sha256), không lưu token thô |

**Ràng buộc duy nhất trên `user_roles`** — Postgres coi mỗi `NULL` là khác nhau nên
`UNIQUE(user_id, role_id, branch_id)` **KHÔNG chặn được trùng dòng chuỗi-wide**. Dùng 2 partial index:
```sql
CREATE UNIQUE INDEX uq_user_role_chain  ON user_roles (user_id, role_id) WHERE branch_id IS NULL;
CREATE UNIQUE INDEX uq_user_role_branch ON user_roles (user_id, role_id, branch_id) WHERE branch_id IS NOT NULL;
```
(pg16 đang chạy nên `UNIQUE NULLS NOT DISTINCT` cũng dùng được — chọn partial index vì rõ ràng hơn và
alembic autogenerate xử lý ổn định hơn.)

**Migration an toàn:** chỉ **thêm bảng mới**, không đụng bảng nghiệp vụ hiện có ⇒ revert được bằng
`downgrade`. Vẫn `pg_dump` trước khi chạy theo kỷ luật full-auto #6.

---

## 4. Luồng xác thực

```
POST /auth/login {email, password, branch_id?}
  ├─ tra user theo email → kiểm status/locked_until → verify_password (bcrypt, đã có)
  ├─ sai → failed_login_count++ ; đủ ngưỡng → locked_until = now + N phút ; audit login_failed
  ├─ đúng → tính danh sách branch truy cập được:
  │     role branch_id IS NULL  → mọi branch active của tenant
  │     role branch_id = X      → chỉ branch X
  ├─ branch_id không truyền & chỉ 1 branch → tự chọn
  │  branch_id không truyền & nhiều branch → 400 BRANCH_REQUIRED + kèm danh sách để client chọn
  │  branch_id truyền nhưng không thuộc danh sách → 403 (đóng F1)
  ├─ permissions = UNION role_permissions của mọi role có (branch_id IS NULL OR branch_id = chọn)
  └─ trả access_token (JWT, mang tenant+branch+perms) + refresh_token (thô, chỉ trả 1 lần)

POST /auth/refresh {refresh_token}
  ├─ hash → tra bảng ; hết hạn/không thấy → 401
  ├─ đã revoked → PHÁT HIỆN TÁI SỬ DỤNG: thu hồi TOÀN BỘ session của user + audit + 401
  └─ hợp lệ → xoay vòng (revoke dòng cũ, set replaced_by) + **tính lại permissions từ DB**
             ⇒ refresh chính là điểm chốt thu hồi quyền

POST /auth/switch-branch {branch_id}   → kiểm quyền trên branch mới → access token mới
POST /auth/logout                      → revoke refresh token hiện tại
GET  /auth/me                          → user + branch hiện tại + danh sách branch + permissions
```

`get_context` mới: **chỉ đọc `Authorization: Bearer`**, `branch_id` lấy từ claim `branch` đã ký —
`X-Branch-Id` bị **bỏ qua hoàn toàn** ở nhánh thật (đóng F1/F2).

---

## 5. Trả lời 5 câu hỏi mở của §7k

### Q1 — Refresh token: stateless hay revocable?

| Tiêu chí | Stateless (JWT thứ 2) | **Revocable (bảng DB) — ĐỀ XUẤT** |
|----------|----------------------|-----------------------------------|
| Thu hồi khi nghỉ việc / lộ token | ❌ Không, phải chờ hết TTL (7-30 ngày) | ✅ Ngay lập tức |
| Đổi mật khẩu → tống xuất phiên cũ | ❌ Không | ✅ Có |
| Sửa role → hiệu lực | Chờ TTL access token | Lần refresh kế tiếp (tính lại từ DB) |
| Phát hiện trộm token (reuse detection) | ❌ Không thể | ✅ Có (xoay vòng + cờ replaced_by) |
| Chi phí | 0 | 1 bảng, 1 index, 3 truy vấn, 1 job dọn |
| Rủi ro thêm | 0 | Thêm 1 điểm hỏng (DB) — nhưng DB đã là bắt buộc cho mọi request rồi |

**Đề xuất: REVOCABLE + xoay vòng (rotation) + phát hiện tái sử dụng.** Lý do quyết định: bối cảnh nhà
thuốc có **luân chuyển nhân sự thật** (Luật 44/2024 Điều 47a.1.đ còn nói thẳng chuyện luân chuyển dược
sĩ giữa các nhà thuốc trong chuỗi); một dược sĩ nghỉ việc mà token còn sống 30 ngày, thu hồi không được,
là rủi ro không chấp nhận được đối với hệ thống chạm dữ liệu sức khỏe. Độ phức tạp tăng thêm rất nhỏ và
nằm gọn trong 1 module.

Dọn rác: xóa dòng `expires_at < now()` mỗi lần refresh thành công (rẻ, không cần cron riêng).

**TTL — [CHỜ SẾP]:** giữ nguyên `jwt_ttl_minutes = 60` hay hạ xuống 15?
- Giữ **60** (đề xuất): không đụng gì đang chạy; **hệ quả phải chấp nhận: thu hồi quyền trễ tối đa 60 phút**.
- Hạ **15**: trễ tối đa 15 phút, nhưng POS **offline-first** — máy mất mạng quá 15 phút là thu ngân bị
  đá ra giữa ca. Auth cho POS offline dài hạn là bài toán riêng **chưa được giải ở bước này**, nên hạ TTL
  bây giờ là đổi một rủi ro lấy một rủi ro. Đề xuất giữ 60, ghi nợ rõ.

### Q2 — Bootstrap admin đầu tiên

| Phương án | Đánh giá |
|-----------|----------|
| Seed cứng trong migration | ❌ **Bác bỏ.** Mật khẩu nằm trong git, giống hệt nhau ở mọi bản triển khai, downgrade/rerun rối |
| Endpoint "chạy lần đầu" | ❌ **Bác bỏ cho prod.** Mở một cửa công khai tự phong admin; nếu điều kiện "lần đầu" tính sai (DB rỗng do sự cố) là mất trắng hệ thống |
| **CLI `python -m seeds.bootstrap_tenant`** | ✅ **ĐỀ XUẤT** |

CLI vì: người chạy được CLI là người **đã có credential DB** — không mở thêm bề mặt tấn công nào cả. Khớp
đúng khuôn mẫu `seeds/run.py` đã có. Trong SaaS, tạo tenant vốn là thao tác của nhà vận hành.

```
python -m seeds.bootstrap_tenant \
    --tenant-name "Nhà thuốc ABC" --branch-code HQ --branch-name "Chi nhánh chính" \
    --admin-email admin@abc.vn --admin-full-name "Nguyễn Văn A"
# mật khẩu: nhập qua stdin (ẩn) hoặc biến môi trường BOOTSTRAP_ADMIN_PASSWORD — KHÔNG có mặc định
```
- Idempotent: tenant đã có user → từ chối, trừ khi `--force`.
- User tạo ra mang `must_change_password = True`.
- **Logic đặt ở application layer** (`IamService.bootstrap_tenant`), CLI chỉ là adapter mỏng ⇒ sau này
  API cấp phát tenant tự động gọi lại đúng use-case, không viết lại.

**[CHỜ SẾP] — câu hỏi phụ nảy sinh:** email **unique toàn hệ thống** hay unique theo tenant?
Đề xuất **unique toàn hệ thống** cho v1 (nhân viên nhà thuốc thuộc đúng 1 doanh nghiệp; login chỉ cần
email + mật khẩu, không phải nhập thêm mã tenant). Đánh đổi: một người không thể làm ở 2 tenant khác
nhau bằng cùng email. Đổi sang unique-theo-tenant sau này được, nhưng phải thêm bước chọn tenant khi
đăng nhập (đổi cả UX).

### Q3 — Giữ dev-header song song?

**Đề xuất: GIỮ, nhưng siết lại thành fail-closed** (bỏ hẳn ngay sẽ phải viết lại phần lớn trong ~380 test
hiện có — churn lớn không cần thiết ở bước nền móng).

| Hiện tại | Sau khi siết |
|----------|--------------|
| Bật mặc định ở mọi env ≠ prod | Chỉ bật khi **cả hai**: `env != "prod"` **VÀ** cờ mới `security.allow_dev_auth = True` (**mặc định `False`**) |
| Không cảnh báo | Log `warning` to lúc khởi động khi đang bật |
| Cấu hình sai staging = mở toang | Validator ở `Settings`: `env == "prod"` + `allow_dev_auth` → **từ chối boot** (đúng khuôn mẫu `_fail_fast_in_prod` đã có) |
| 26 permission | Đủ **32** (vá F3) |

Test cũ: bật cờ trong fixture, giữ nguyên. Test IAM mới: đi qua **login thật**. Việc gỡ hẳn dev-header
ghi thành nợ riêng, làm sau khi mọi e2e đã chuyển sang login thật.

### Q4 — Mô hình role 2 cấp chuỗi/nhà thuốc

**Đánh giá đề xuất sơ bộ trong §7k: ĐÚNG HƯỚNG, giữ nguyên hình dạng (`branch_id` NULLABLE = toàn
chuỗi, permission = hợp của các role khớp). Cần 4 điều chỉnh:**

| # | Điều chỉnh | Vì sao |
|---|-----------|--------|
| 1 | **Branch phải được xác thực, không tin `X-Branch-Id`** — branch nằm trong claim JWT đã ký, chọn lúc login/switch-branch | Nếu vẫn tin header thì mô hình 2 cấp chỉ để trang trí: ai cũng đổi header sang branch khác được (F1). **Đây là điểm quan trọng nhất của cả Q4** |
| 2 | Permission **tính 1 lần lúc login/refresh** theo branch đã chọn rồi nhét vào token — không tra DB mỗi request | Giữ đúng kiến trúc hiện tại (permission nằm trong token), không thêm 1 round-trip DB cho mọi request POS |
| 3 | Dùng **2 partial unique index** thay vì 1 UNIQUE 3 cột | `NULL` trong UNIQUE của Postgres không chống trùng (§3) |
| 4 | `users`/`roles`/`user_roles` **không dùng `TenantScopedMixin`**, tự khai cột | Mixin ép `branch_id NOT NULL`, ngược yêu cầu (F5). Không sửa mixin — 8 module đang dùng |

Khớp pháp lý: Luật 44/2024 Điều 17a phân biệt người chịu trách nhiệm chuyên môn **cấp chuỗi** và **cấp
từng nhà thuốc** → đúng hai giá trị `branch_id NULL` / `branch_id = X`. Điều 47a.1.đ (luân chuyển dược sĩ
giữa các nhà thuốc) → thu hồi/gán lại 1 dòng `user_roles`, có `granted_by`/`granted_at` + audit.
**Chưa làm** hiệu lực theo thời gian (`valid_from/valid_to`) — chưa có nhu cầu thật, ghi nợ.

### Q5 — Role seed sẵn

**Đề xuất: 5 role hệ thống, đặt tên theo chức danh nghiệp vụ thật** (không đặt theo nhóm permission kỹ
thuật) — vì chủ nhà thuốc là người gán role, họ nghĩ theo "dược sĩ / thu ngân / thủ kho", và vì Luật
44/2024 Điều 17a đã đặt tên sẵn 2 vai trò chuyên môn, bám theo luật thì audit về sau dễ giải trình.

| Role | `code` | Cấp | Căn cứ |
|------|--------|-----|--------|
| Quản trị hệ thống | `system_admin` | Chuỗi | Kỹ thuật — chủ sở hữu tenant |
| Người chịu TN chuyên môn cấp chuỗi | `chain_pharmacist` | Chuỗi | Luật 44/2024 Điều 17a |
| Dược sĩ phụ trách nhà thuốc | `branch_pharmacist` | Chi nhánh | Luật 44/2024 Điều 17a · GPP TT02/2018 |
| Nhân viên bán thuốc / thu ngân | `cashier` | Chi nhánh | GPP TT02/2018 I-1a.III.4.a |
| Thủ kho / nhập hàng | `warehouse` | Chi nhánh | — |

Ánh xạ 32 permission (✅ có · — không):

| Permission | admin | chain_ph | branch_ph | cashier | warehouse |
|------------|:-----:|:--------:|:---------:|:-------:|:---------:|
| `catalog.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `catalog.create` | ✅ | ✅ | — | — | — |
| `inventory.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `inventory.receive` | ✅ | ✅ | ✅ | — | ✅ |
| `inventory.dispense` | ✅ | ✅ | ✅ | ✅ | — |
| `sales.read` | ✅ | ✅ | ✅ | ✅ | — |
| `sales.create` | ✅ | ✅ | ✅ | ✅ | — |
| `rx.read` | ✅ | ✅ | ✅ | ✅ | — |
| `rx.create` | ✅ | ✅ | ✅ | — | — |
| `rx.approve` | ✅ | ✅ | ✅ | — | — |
| `rx.dispense` | ✅ | ✅ | ✅ | — | — |
| `clinical.check` | ✅ | ✅ | ✅ | — | — |
| `clinical.accept` | ✅ | ✅ | ✅ | — | — |
| `clinical.settings.read` | ✅ | ✅ | ✅ | — | — |
| `clinical.settings.write` | ✅ | ✅ | — | — | — |
| `crm.create` | ✅ | ✅ | ✅ | — | — |
| `crm.read` | ✅ | ✅ | ✅ | — | — |
| `crm.write` | ✅ | ✅ | ✅ | — | — |
| `compliance.config.read` | ✅ | ✅ | ✅ | — | — |
| `compliance.config.write` | ✅ | ✅ | — | — | — |
| `compliance.ledger.read` | ✅ | ✅ | ✅ | — | — |
| `compliance.ledger.write` | ✅ | ✅ | ✅ | — | — |
| `compliance.sync.read` | ✅ | ✅ | ✅ | — | — |
| `compliance.sync.push` | ✅ | ✅ | ✅ | — | — |
| `procurement.supplier.read` | ✅ | ✅ | ✅ | — | ✅ |
| `procurement.supplier.create` | ✅ | ✅ | — | — | ✅ |
| `procurement.po.read` | ✅ | ✅ | ✅ | — | ✅ |
| `procurement.po.create` | ✅ | ✅ | ✅ | — | ✅ |
| `procurement.po.write` | ✅ | ✅ | ✅ | — | ✅ |
| `procurement.grn.read` | ✅ | ✅ | ✅ | — | ✅ |
| `procurement.grn.create` | ✅ | ✅ | ✅ | — | ✅ |
| `procurement.grn.confirm` | ✅ | ✅ | ✅ | — | ✅ |
| `iam.user.read` | ✅ | ✅ | — | — | — |
| `iam.user.create` / `.write` | ✅ | — | — | — | — |
| `iam.role.read` | ✅ | ✅ | — | — | — |
| `iam.role.write` / `.assign` | ✅ | — | — | — | — |

Ghi chú lựa chọn:
- `catalog.create` chỉ ở cấp chuỗi — giữ danh mục thuốc nhất quán toàn chuỗi, chi nhánh không tự đẻ mã thuốc.
- `clinical.settings.write` (bật/tắt AI) và `compliance.config.write` chỉ ở cấp chuỗi — quyết định cấp doanh nghiệp.
- `rx.approve` + `rx.dispense` **không cấp cho thu ngân** — duyệt/cấp phát thuốc kê đơn là hành vi chuyên
  môn của dược sĩ (Luật Dược Điều 6.5.h). Đây là ràng buộc pháp lý, không phải sở thích cấu hình.
- 6 permission `iam.*` là **mới**, `require_permission` chưa gọi ở đâu (module chưa tồn tại) — sẽ dùng ngay trong router `iam`.

**⚠️ [CHỜ SẾP] — vấn đề `crm.read` (F7):** thu ngân **KHÔNG được cấp quyền crm nào** ở bảng trên. Lý do:
`crm.read` hôm nay mở luôn dị ứng/bệnh nền — NĐ356 Điều 4.2 đòi *phân quyền giới hạn truy cập riêng* cho
dữ liệu nhạy cảm, GPP TT02 I-1a.III.4.a đòi người bán lẻ giữ bí mật thông tin người bệnh. Hiện chưa mất
gì: `SalesOrder` **chưa có `customer_id`** (nợ đã ghi ở §7i) nên thu ngân không cần crm để bán hàng.
Hai đường đi:
- **(a) ĐỀ XUẤT** — giữ như bảng (thu ngân không có crm). Không cần đụng module `crm` ở bước này.
- **(b)** Tách `crm.read` → `crm.read` (tên/SĐT) + `crm.sensitive.read` (dị ứng/bệnh nền), rồi cấp
  `crm.read`+`crm.create` cho thu ngân. Đúng tinh thần NĐ356 hơn, **nhưng phải sửa module `crm`** ⇒ nên
  là bước riêng sau IAM, không nhét vào bước nền móng.

---

## 6. Chính sách bảo mật kèm theo — [CHỜ SẾP] chốt tham số

| Mục | Đề xuất | Ghi chú |
|-----|---------|---------|
| Độ dài mật khẩu tối thiểu | 10 ký tự, **không** ép chữ hoa/ký tự đặc biệt | Theo hướng NIST hiện hành; luật VN không quy định cụ thể |
| Khóa sau đăng nhập sai | 5 lần → khóa 15 phút (`failed_login_count` + `locked_until`) | Lưu ở DB (sống sót qua restart), không cần Redis |
| TTL access token | 60 phút (giữ nguyên) | Xem đánh đổi ở Q1 |
| TTL refresh token | 30 ngày | Xoay vòng mỗi lần refresh |
| Đổi mật khẩu | Thu hồi toàn bộ refresh token của user | |
| Audit | login thành công/thất bại, tạo/khóa user, gán/thu hồi role, đổi mật khẩu | Qua `AuditLogger` sẵn có — **vẫn chỉ ra structlog** (nợ F8) |

---

## 7. Kế hoạch stepped-commit (4 bước, 4 cổng xanh mỗi bước)

| Bước | Nội dung | Cổng |
|------|----------|------|
| 1 | `iam/domain` thuần: entities + ports + exceptions + logic tính permission theo branch. Unit test không chạm DB. Thêm contract `iam-domain-innermost` | ruff · mypy · import-linter · pytest |
| 2 | `application` (AuthService, IamService) + `infrastructure` (models/mappers/repos) + migration `0013_iam` (**pg_dump trước**) + đăng ký `models_registry.py`. Test service-level trên Postgres thật | 4 cổng + `alembic check` + downgrade/upgrade lại |
| 3 | `interface` (router auth/users/roles) + `register.py` + **viết lại `api/deps.py`** + cờ `allow_dev_auth` + vá `_DEV_PERMISSIONS` 26→32 + mở rộng `TokenPayload.branch_id`. Test e2e qua login thật | 4 cổng |
| 4 | CLI `seeds/bootstrap_tenant.py` + seed 5 role hệ thống + 32 dòng `role_permissions` | 4 cổng + chạy thử CLI trên DB thật |

Rủi ro không đảo ngược bằng `git revert`: **không có** — chỉ thêm bảng mới, không sửa/xóa dữ liệu nghiệp
vụ hiện có. Vẫn `pg_dump` trước bước 2 theo kỷ luật full-auto #6.

---

## 8. Danh mục cần sếp gật (gom lại)

| # | Điểm | Đề xuất của Trợ lý Code |
|---|------|-------------------------|
| D1 | Refresh token | Revocable + rotation + reuse detection |
| D2 | TTL access token | Giữ 60 phút, chấp nhận trễ thu hồi ≤60 phút (thay vì hạ 15 làm hỏng POS offline) |
| D3 | Bootstrap | CLI `bootstrap_tenant`, logic ở application layer |
| D4 | Email unique | Toàn hệ thống (v1) |
| D5 | Dev-header | Giữ nhưng fail-closed (cờ `allow_dev_auth` mặc định False + validator chặn prod) |
| D6 | Mô hình role 2 cấp | Giữ hình dạng §7k + 4 điều chỉnh (quan trọng nhất: branch trong token, bỏ tin `X-Branch-Id`) |
| D7 | Role seed | 5 role theo chức danh nghiệp vụ, ánh xạ 32 permission như bảng Q5 |
| D8 | `crm.read` cho thu ngân | Phương án (a): thu ngân không có quyền crm ở v1; tách `crm.sensitive.read` để bước sau |
| D9 | **Mở rộng phạm vi**: IAM sở hữu luôn bảng `tenants` + `branches` tối thiểu | Cần, vì `user_roles.branch_id` không có nghĩa nếu không có bảng `branches`, và bootstrap phải tạo tenant+branch đầu tiên |
| D10 | **Sửa contract cũ**: thêm `iam` vào `module-independence` | Cần gật theo kỷ luật #4 |
| D11 | Chính sách mật khẩu/khóa tài khoản | 10 ký tự · 5 lần sai → khóa 15 phút |
