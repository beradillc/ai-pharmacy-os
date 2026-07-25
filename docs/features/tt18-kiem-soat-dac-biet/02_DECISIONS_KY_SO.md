# Ký sổ điện tử — hướng A (Bước 0-3 của `docs/14_FEATURE_PROCESS.md`)

> **Trạng thái: ĐANG LÀM (2026-07-25).** Bước 6/6 mạch TT18 — mục cuối cùng. Chain đã chọn "thiết kế
> trước, chưa code", sau đó **ủy quyền GĐ chọn và dùng Opus** để tự quyết phần còn lại (hướng A, ai
> ký, và thiết kế cross-module) — không chờ hỏi thêm. Nguồn: `01_THIET_KE_KY_DIEN_TU.md` (3 hướng,
> GĐ khuyến nghị A); `docs/13` mục C.5.

## Bước 0 — Đích (DoD ngược)

| Vai | Làm được |
|---|---|
| Dược sĩ phụ trách (chuỗi hoặc chi nhánh) | Sau khi kết xuất cuối ngày (bước 5), nhập lại mật khẩu để "ký xác nhận" đúng ngày đó cho 1 mẫu sổ (PL_VIII/PL_XVI) — hệ thống ghi ai ký, lúc nào, hash nội dung, móc xích vào ngày ký liền trước |

| Câu hỏi thanh tra | Hệ thống trả lời bằng |
|---|---|
| "Ai xác nhận sổ ngày X đúng, đủ?" | `ledger_book_signatures`: `signed_by_user_id`, `signed_at`, `content_sha256` |
| "Có ai sửa số liệu sau khi đã xác nhận không?" | `prev_hash` móc xích — sửa dữ liệu ngày đã ký làm hash ngày đó lệch khỏi bản đã ký, và chặn cứng không cho ghi thêm dòng vào ngày đã ký |
| "Đây là chữ ký số thật hay chỉ đăng nhập thường?" | Trả lời thật: đây là **"kỹ thuật xác nhận điện tử"** (vế thứ 2 của Điều 15.1.d, không phải chữ ký số USB/HSM) — re-auth bằng mật khẩu ngay trước hành vi ký, không chấp nhận phiên đang mở sẵn |

## Bước 1 — Checklist Compliance/Privacy by Design

| # | Mục | Trả lời |
|---|---|---|
| 1 | Căn cứ pháp lý | TT18 Điều 15.1.d ("... hoặc chữ ký số ..." — văn bản cho 2 lựa chọn, xem `01_THIET_KE_KY_DIEN_TU.md` mục 1). Điều kiện kèm theo bắt buộc: **vẫn phải in + ký tay mỗi ngày** cho tới khi có hướng dẫn thanh tra rõ hơn — bước này không thay thế nghĩa vụ giấy |
| 2 | Đồng ý (consent) | N/A — không phải dữ liệu khách hàng, là hành vi nghiệp vụ nội bộ của người dùng hệ thống |
| 3 | Phân loại dữ liệu | Không có PII khách hàng mới. Có 1 dữ liệu nhạy: **mật khẩu người ký** — chỉ dùng tức thời để re-auth (gọi `verify_password`), không lưu, không log |
| 4 | Audit log bất biến | `AuditAction.LEDGER_BOOK_SIGNED` mới — ghi `book_type`, `book_date`, `content_sha256` vào context; **không** ghi mật khẩu dưới bất kỳ hình thức nào |
| 5 | RBAC | Permission mới `compliance.ledger.sign`, **tách khỏi** `compliance.ledger.write`/`.read` — xem quyết định "ai ký" bên dưới |
| 6 | Backup/restore | Bảng mới `ledger_book_signatures` nằm trong backup Postgres hiện có (đã pg_dump trước migration theo kỷ luật full-auto điều 6) |
| 7 | AI qua port | N/A |
| 8 | Rà Luật Dược/BVDLCN/NĐ356/GPP | Luật Dược 44/2024 Điều 17a: "người chịu trách nhiệm chuyên môn về dược" là người ký chịu trách nhiệm pháp lý cho hồ sơ chuyên môn — dùng đúng khái niệm này để quyết định "ai ký" (xem dưới), không phải suy đoán |

### Quyết định "ai ký" (câu hỏi #2 còn treo trong `01_THIET_KE_KY_DIEN_TU.md` mục 5) — GĐ quyết dưới ủy quyền

**Chỉ vai trò đã có `compliance.ledger.write`** (tức `chain_pharmacist` + `branch_pharmacist` +
`system_admin` qua `ALL_PERMISSIONS`) **được cấp thêm `compliance.ledger.sign`** — KHÔNG mở cho
`cashier`/`warehouse` dù có "trưởng ca" là vai không chính thức trong hệ thống (không có role
riêng cho "trưởng ca" trong 5 role hiện tại — `docs/15` §5). Lý do: Luật 44/2024 Điều 17a chỉ trao
trách nhiệm chuyên môn dược cho "người chịu trách nhiệm chuyên môn về dược" cấp chuỗi/cấp nhà thuốc,
đúng 2 role `chain_pharmacist`/`branch_pharmacist` đã seed sẵn — ký xác nhận sổ kiểm soát đặc biệt
là hành vi thuộc thẩm quyền đó, không giao được cho thu ngân/thủ kho dù họ có thể là người trực ca.
Nhất quán với việc 2 role này đã là 2 role duy nhất giữ `compliance.ledger.write` — ai ghi được sổ
thì thuộc nhóm được ký, không mở rộng thêm giao cho ai khác.

## Bước 2 — Rà chồng lấn

- Không trùng `export_daily_closure` (bước 5) — kết xuất là xem/tính hash, **không** phải hành vi
  xác nhận; ký là bước riêng, sau khi đã xem kết xuất. Chữ ký **tính lại hash từ đúng nội dung** mà
  `export_daily_closure` trả (cùng hàm `render_ledger_book_csv_text`), không tin hash client gửi lên
  — tránh ký sai nội dung do client tự tính/giả mạo hash.
- Sửa 1 điểm trong bảng thiết kế gốc (`01_THIET_KE_KY_DIEN_TU.md` mục 4): bảng liệt kê cột `drug_id`
  cho `ledger_book_signatures` — **sai**, vì `export_daily_closure` (đã code ở bước 5) kết xuất
  **cả sổ** (mọi thuốc) của 1 `book_type` trong 1 ngày, không lọc theo `drug_id`. Chữ ký phải khớp
  đúng phạm vi đã kết xuất/ký thật ⇒ khóa là `(tenant_id, book_type, book_date)`, không có `drug_id`.
  Cũng không thêm `branch_id`: `ControlledLedgerEntry`/sổ là hồ sơ theo **cơ sở** (tenant), không
  theo quầy — đã ghi rõ ở `SqlAlchemyControlledLedgerRepository.list_for_book` (bước 3).
- Tái dùng đúng pattern re-auth đã có ở `iam.AuthService.change_password` (xác minh mật khẩu hiện tại
  bằng `verify_password` trước khi cho hành động nhạy) — không phát minh cơ chế mới.

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module (CROSS-MODULE THẬT — lý do bắt buộc Opus)

| Module bị đụng | Thay đổi | Cross-module? |
|---|---|---|
| `compliance` | Entity `LedgerBookSignature`, port + repo + migration, `ComplianceService.sign_daily_closure()`, endpoint, permission mới | — |
| `iam` | Thêm 1 method **đọc-only** `AuthService.verify_own_password(ctx, plain_password) -> bool` — tái dùng logic đã có ở `change_password`, không sửa hành vi cũ, không thêm mutation | **CÓ** |
| `core/audit` | Thêm `AuditAction.LEDGER_BOOK_SIGNED` | Không |
| `iam.system_roles` | `compliance.ledger.sign` thêm vào `COMPLIANCE_PERMISSIONS`, seed sẵn cho `chain_pharmacist`/`branch_pharmacist`/`system_admin` (qua `ALL_PERMISSIONS`) | Không (đổi seed data, không đổi cấu trúc role) |

**Thiết kế cross-module (điểm mới, chưa có khuôn mẫu — đây là lý do việc này thuộc diện Opus):**

`compliance` cần xác minh mật khẩu của người dùng đang đăng nhập — nhưng `compliance` không sở hữu
`User`/`password_hash` (thuộc `iam`). Áp đúng pattern composition-root read-port đã dùng cho
`DrugMasterProvider`/`CatalogDrugMasterProvider` (bước báo cáo định kỳ, 2026-07-25):

1. **Port mới trong `compliance/domain/ports.py`**: `SigningReauthProvider` — 1 method
   `async def verify(self, ctx: RequestContext, plain_password: str) -> bool`. `compliance` không
   import `iam`.
2. **`iam.AuthService.verify_own_password`** (method mới, đọc-only): lấy `ctx.user_id`, so mật khẩu
   bằng `verify_password` — giống hệt bước xác minh đầu tiên của `change_password`, nhưng KHÔNG đổi
   mật khẩu, KHÔNG revoke session, KHÔNG audit riêng (việc ký đã tự audit
   `LEDGER_BOOK_SIGNED`/thất bại thì service ném lỗi 401, không cần audit kép).
3. **Adapter tại composition root** (`api/v1/cross_module.py`): `IamAuthReauthProvider`, bọc
   `AuthService`, implement `SigningReauthProvider` — cùng vị trí và hình dạng với
   `CatalogDrugMasterProvider`. Wiring tại `api/v1/__init__.py`: `container.resolve(AuthService)`
   (đã đăng ký instance sẵn ở `iam/interface/register.py`).
4. `ComplianceService` nhận `reauth: SigningReauthProvider | None = None` (optional, cùng convention
   `drug_master`) — nếu `None` thì `sign_daily_closure` từ chối luôn (lỗi cấu hình, không phải lỗi
   người dùng, cùng cách `_drug_return_repo` đang làm).

**Rủi ro đã cân nhắc:**
- *Rủi ro*: thêm method vào `AuthService` có thể bị hiểu nhầm là "iam biết về compliance". **Không
  đúng** — `AuthService.verify_own_password` không import gì từ `compliance`, không biết nó được
  gọi để làm gì; hướng phụ thuộc vẫn đúng chiều (compliance → cross_module adapter → iam), giống hệt
  `CatalogDrugMasterProvider` không làm `catalog` phụ thuộc `compliance`.
- *Rủi ro*: nếu sau này thêm hành vi nhạy cảm khác cần re-auth (VD xóa dữ liệu), port này tái dùng
  được ngay — không cần thiết kế lại.

## Chặn nghiệp vụ (business rule, GĐ quyết dưới ủy quyền — không hỏi lại)

- Không cho ký lại một ngày đã ký (cùng `tenant_id` + `book_type` + `book_date`) — trả lỗi 409
  (`ConflictError`), không phải ghi đè.
- Không cho `record_controlled_entry` ghi dòng mới vào 1 ngày (`transaction_at` date) đã có chữ ký
  cho `book_type` tương ứng của thuốc đó — chặn ở tầng service trước khi insert, trả `ConflictError`.
  Đây là hệ quả trực tiếp của "ký xong là chốt sổ ngày đó", không phải quy tắc phát sinh thêm.
- `prev_hash`: lấy chữ ký gần nhất theo ngày trước đó (cùng tenant + book_type) đã tồn tại — không
  bắt buộc liên tục từng ngày lịch (nhà thuốc có thể không phát sinh giao dịch/không ký một số ngày),
  chỉ móc theo **chữ ký trước đó gần nhất theo thời gian**, không phải "ngày hôm qua theo lịch".
