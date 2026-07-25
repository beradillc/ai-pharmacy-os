# 2FA cho vai trò nhạy cảm — quyết định thiết kế (Sprint 8, 2026-07-25)

> Trạng thái: **ĐÃ CHỐT** dưới ủy quyền toàn quyền GĐ (PROJECT_STATE §7ax). Opus full-auto.
> Phạm vi: **chỉ lát 2FA** của gạch đầu dòng `Bảo mật: 2FA vai trò nhạy cảm, rate limit, mã hóa
> at-rest` (ROADMAP Sprint 8). Rate limit + mã hóa at-rest là việc anh em **Sprint 8 #1b**, KHÔNG
> làm ở đây.

## Cổng docs/14 có phải chạy không?

**Không.** `docs/14_FEATURE_PROCESS.md` bắt buộc với "MỌI tính năng mới **ngoài ROADMAP gốc**".
2FA nằm đúng trong ROADMAP Sprint 8 từ đầu, nên không phải tính năng phát sinh. Tài liệu này vẫn
viết theo khuôn `docs/features/*/0X_DECISIONS.md` vì đó là chuẩn trình bày của dự án.

## Vì sao gấp — rủi ro thật, không giả định

`compliance.ledger.sign` (thêm **cùng ngày**, §7aw) cho `chain_pharmacist`/`branch_pharmacist`/
`system_admin` **ký xác nhận điện tử** sổ kiểm soát đặc biệt (TT 18/2026/TT-BYT Điều 15.1.d) — một
**hành vi pháp lý ràng buộc**: ký xong là chốt sổ, không ghi thêm, không ký lại.

Bảo vệ hiện có là re-auth **mật khẩu** (`AuthService.verify_own_password`). Nghĩa là:
**một mật khẩu lộ = đủ để giả mạo chữ ký pháp lý.** Không có yếu tố thứ hai nào. Đó chính xác là
khoảng hở 2FA phải đóng, và là cạnh sắc nhất trong toàn hệ thống — mọi hành vi khác đều sửa/hoàn
tác được, chữ ký sổ thì không.

---

## Q1 — Vai trò nào vào phạm vi?

**Chốt: không hardcode danh sách role — suy ra từ *quyền đang giữ*.**

`TWO_FACTOR_PERMISSIONS` (trong `iam/domain/two_factor.py`):

| Quyền | Vì sao vào danh sách |
|---|---|
| `compliance.ledger.sign` | Khoảng hở gấp: giả mạo chữ ký pháp lý TT18 Điều 15.1.d |
| `iam.role.assign` | Leo thang đặc quyền: ai tự gán role được thì tự cấp `.sign` cho mình được ⇒ bảo vệ mỗi `.sign` là **tường giấy** |
| `iam.role.write` | Sửa được tập quyền của role ⇒ nhét `.sign` vào role mình đang giữ. Cùng lập luận trên |

Ánh xạ ra role thực tế hôm nay: `.sign` → `chain_pharmacist`, `branch_pharmacist`, `system_admin`;
`iam.role.*` → `system_admin`. **Tổng đúng 3 role** — bằng đúng mức tối thiểu đề bài đặt ra, nhưng
đạt bằng một *quy tắc* thay vì một danh sách chép tay.

**Vì sao quy tắc hơn danh sách:** dự án đã có sẵn đường sinh role riêng của tenant
(`roles.tenant_id IS NOT NULL`, docs/15 §5 Q5 — schema có, v1 chưa mở). Ngày mở ra, một role tenant
được cấp `.sign` sẽ **tự động** vào phạm vi 2FA. Danh sách chép tay thì im lặng bỏ sót — đúng kiểu
lỗi §7l (permission mới không tới được deployment cũ).

**Cân nhắc rồi BỎ:** `crm.erase` (xóa dữ liệu cá nhân, không đảo ngược). Nguy hiểm thật, nhưng rủi
ro của nó là *phá hoại*, không phải *giả mạo danh tính* — và nó vốn đã chỉ nằm ở cấp chuỗi. Đưa vào
sẽ nới phạm vi ra ngoài khung rủi ro đang xử lý. **Ghi lại làm ứng viên đợt sau**, không tự thêm.

## Q2 — Cưỡng chế ở đâu: login, step-up, hay cả hai?

**Chốt: CẢ HAI.** Không phải cho chắc ăn — hai chỗ đóng hai đường tấn công **khác nhau**:

| Đường tấn công | Login-2FA đóng? | Step-up đóng? |
|---|---|---|
| Mật khẩu bị lộ (phishing, dùng lại mật khẩu, rò CSDL nơi khác) → đăng nhập từ xa | ✅ | ✅ |
| **Phiên đang mở trên máy quầy không có người trông** → vào ký | ❌ (đã đăng nhập rồi) | ✅ |
| Nhìn trộm mật khẩu qua vai rồi ký từ chính phiên đang mở | ❌ | ✅ |

Chỉ làm login-2FA thì máy quầy bỏ trống vẫn ký được — mà **chính vì lo điều đó** bước 6 mới bắt
nhập lại mật khẩu khi ký (§7aw: "không chấp nhận phiên đang mở sẵn"). Bỏ step-up là tự tay hạ
chuẩn vừa đặt ra hôm qua.

Chỉ làm step-up thì mật khẩu lộ vẫn cho attacker toàn quyền mọi thứ *khác* của dược sĩ phụ trách
(sửa cấu hình, đọc hồ sơ sức khỏe KH, thu hồi role...).

Chi phí ma sát: ký sổ là **1 lần/ngày/sổ**. Nhập thêm 6 chữ số cho một hành vi pháp lý ràng buộc
là cái giá không đáng bàn.

## Q3 — Luồng đăng ký (enrollment)

TOTP RFC 6238, 3 nhịp — **bí mật chưa xác nhận thì chưa có hiệu lực**:

1. `POST /auth/2fa/enroll` → sinh secret, lưu trạng thái `PENDING`, trả `secret` + `otpauth://` URI
   (client tự vẽ QR — server **không** sinh ảnh QR, tránh kéo thêm thư viện ảnh vào backend).
2. `POST /auth/2fa/activate {code}` → nhập đúng 1 mã → `ACTIVE`, **trả 10 mã dự phòng đúng 1 lần**.
3. Gọi lại `enroll` khi đang `PENDING` → cấp secret mới (làm lại từ đầu, người dùng bấm nhầm/mất
   QR giữa chừng). Gọi khi đã `ACTIVE` → 409, phải `disable` hoặc nhờ admin reset trước.

Vì sao bắt xác nhận 1 mã trước khi `ACTIVE`: nếu bật ngay lúc phát secret, người quét QR hỏng sẽ
**tự khóa mình ra ngoài** ngay lần đăng nhập kế tiếp.

## Q4 — Mất thiết bị: mã dự phòng **và** admin reset

Hai đường, có chủ đích:

- **10 mã dự phòng** (`XXXX-XXXX-XXXX-XXXX`, 64-bit), hiện đúng 1 lần lúc activate, lưu **hash
  SHA-256**, dùng 1 lần rồi đánh dấu `used_at` (không xóa — còn dấu vết đã tiêu thụ mã nào, lúc nào).
  - *SHA-256 chứ không bcrypt*: đúng lập luận `hash_refresh_token` đã ghi sẵn trong
    `auth_service.py` — bí mật 64-bit ngẫu nhiên không có gì để "làm chậm người đoán", KDF chỉ là
    chi phí mỗi request đổi lấy con số không.
- **Admin reset**: `POST /users/{id}/2fa/reset`, chặn bằng `iam.user.write`. Xóa sạch cấu hình 2FA
  của người đó → họ đăng ký lại từ đầu. Dành cho ca mất cả điện thoại lẫn tờ mã dự phòng.
  - Ghi audit `TWO_FACTOR_RESET` — đây là hành vi **hạ mức bảo vệ của người khác**, phải truy được.

## Q5 — Bí mật TOTP lưu ở đâu, có mã hóa at-rest không?

**Chốt: lưu base32 dạng rõ trong `user_two_factor.secret`, CÓ TODO bàn giao — và đây là lý do
thật, không phải né việc.**

- Dự án **chưa có bất kỳ hạ tầng quản lý khóa nào** (không KMS, không khóa phong bì, không vòng
  xoay khóa). Tự chế mã hóa bằng khóa lấy từ `SECURITY__JWT_SECRET` sẽ tạo **cảm giác an toàn giả**:
  khóa đó nằm cùng file `.env`, cùng máy, cùng quyền đọc với CSDL. Kẻ đọc được CSDL gần như chắc
  chắn đọc được luôn `.env` ⇒ mã hóa bằng khóa cạnh bên = không mã hóa, chỉ tốn thêm chế độ hỏng.
- "Mã hóa at-rest" là **đúng phạm vi việc anh em Sprint 8 #1b**. Giải pháp chung ở đó (khóa riêng,
  vòng xoay khóa, kiểu cột tái dùng được) sẽ phủ cột này — làm bản vá riêng ở đây rồi vứt đi là
  lãng phí và để lại 2 cơ chế.
- **Mức thiệt hại thật nếu CSDL lộ mà secret để rõ:** 2FA tụt về 1FA — attacker sinh được mã TOTP,
  **nhưng vẫn phải có mật khẩu** (login-2FA đòi cả hai; step-up ký sổ đòi cả hai). Rò CSDL đơn
  thuần **không** thành chiếm tài khoản. Đó là suy giảm chấp nhận được trong một sprint, không phải
  thủng.
- Đánh dấu tại chỗ: `# TODO(sprint8-1b): mã hóa at-rest cột secret` ngay trên cột, cùng khuôn
  `# BLOCKER: DAV API spec` — người làm #1b grep là thấy.

## Q6 — Câu chuyện triển khai: KHÔNG được khóa ai ra ngoài

Cờ `SECURITY__TWO_FACTOR_ENFORCED`, **mặc định `false`** — đúng tinh thần
`OUTBOX__RELAY_ENABLED`/`NATIONAL_SYNC__RETRY_ENABLED`.

**Ma trận đăng nhập** (áp dụng cho *mọi* người dùng, không phân biệt role):

| 2FA của user | Đăng nhập |
|---|---|
| chưa đăng ký | **y hệt hôm nay** — trả token luôn |
| `PENDING` | **y hệt hôm nay** — bí mật chưa xác nhận thì chưa có hiệu lực |
| `ACTIVE` | 2 nhịp: `/auth/login` trả *challenge*, `/auth/login/2fa` đổi mã lấy token |

Người dùng tự bật được 2FA **bất kể cờ** — bật lên là hệ thống tôn trọng ngay. Cờ chỉ quyết định
việc *ép* nhóm nhạy cảm.

**Ma trận ký sổ** (`sign_daily_closure`):

| `TWO_FACTOR_ENFORCED` | 2FA của user | Ký cần gì |
|---|---|---|
| `false` | chưa đăng ký | mật khẩu (**không đổi so với §7aw**) |
| `false` | `ACTIVE` | mật khẩu + mã TOTP |
| `true` | chưa đăng ký | **CHẶN** — bắt đăng ký 2FA trước (403) |
| `true` | `ACTIVE` | mật khẩu + mã TOTP |

Khi bật cờ, người thuộc nhóm nhạy cảm **chưa đăng ký vẫn đăng nhập và làm việc bình thường**, chỉ
nhận cờ `must_enroll_two_factor=true` trong `SessionOutput` để client nhắc — **đúng khuôn
`must_change_password` đã có sẵn**. Chỉ **hành vi pháp lý ràng buộc** (ký sổ) mới bị chặn cứng.

Vì sao không chặn thẳng ở login khi bật cờ: chủ nhà thuốc bật cờ lúc 8h sáng sẽ **làm cả ca trực
không đăng nhập được**, trong khi rủi ro thật chỉ nằm ở hành vi ký. Nhắc rộng, chặn hẹp.

**Tương thích ngược: tuyệt đối.** Cờ mặc định tắt + chưa ai đăng ký ⇒ **không một luồng nào đổi
hành vi** khi deploy. Phiên đang mở không bị thu hồi, migration chỉ thêm bảng mới.

---

## Chống dò mã — thuộc lát này, không phải lát rate-limit

Mã TOTP chỉ 6 chữ số (10⁶). Không giới hạn số lần thử thì 2FA **gần như vô nghĩa**. Nên:

- **Challenge đăng nhập**: bản ghi CSDL, mờ (opaque), lưu hash SHA-256, **dùng 1 lần**, sống 5
  phút, **tối đa 5 lần đoán** rồi hủy → phải nhập lại mật khẩu.
- **Step-up khi ký**: sai mã ⇒ 401 và ghi audit; không có phiên nào để tiêu thụ.

Đây là **giới hạn theo challenge**, gắn liền vào máy trạng thái 2FA — khác hẳn *rate limit theo IP/
endpoint* dùng Redis mà việc #1b sẽ dựng. Không chồng lấn.

## Vì sao challenge là bản ghi CSDL, không phải JWT ngắn hạn

Đã cân nhắc JWT ngắn hạn (không cần bảng mới). **Bỏ, vì một lỗ hổng cụ thể:** `api/deps.py`
`get_context` nhận *mọi* token giải mã được. Một "JWT challenge" sẽ **lọt qua như access token**
(perms rỗng) — và `POST /auth/change-password` **không đòi permission nào**, chỉ đòi mật khẩu hiện
tại, thứ attacker vừa nhập xong ở nhịp 1. Kết quả: kẻ có mật khẩu **đổi được mật khẩu mà không cần
qua 2FA**. Đúng thứ 2FA sinh ra để chặn.

Bảng riêng, token mờ, không giải mã được bởi `JwtService` ⇒ không tồn tại đường lọt đó. Kèm theo
được luôn *dùng-1-lần* và *đếm số lần đoán* mà JWT stateless không làm được.

## Sửa nợ phát hiện dọc đường

`core/config.py` có sẵn `SecuritySettings.require_2fa_roles = ["pharmacist", "admin"]` — **code
chết**: không nơi nào đọc, và 2 mã role đó **không tồn tại** trong hệ thống (thật là
`chain_pharmacist`/`branch_pharmacist`/`system_admin`/`cashier`/`warehouse`). Di tích từ thời
skeleton trước khi có `iam`. Thay bằng `two_factor_enforced` — giữ lại chỉ nuôi hiểu nhầm rằng đã
có gì đó đang chạy.

## Kế hoạch commit (4 bước, 4 cổng xanh mỗi bước)

| # | Nội dung | Vì sao tách vậy |
|---|---|---|
| 1 | `iam/domain` thuần (entity/port/exception 2FA) + `core/security/totp.py` + dep `pyotp` + unit test | Domain thuần, không CSDL |
| 2 | app + infra + **migration `0028`** (3 bảng) + `AuthService`/`IamService` + config + audit action | Đúng nhịp 2 của kỷ luật #1 |
| 3 | interface `iam` (5 endpoint) + schema | Đúng nhịp 3 |
| 4 | **Seam cross-module**: port `SigningReauthProvider` + adapter + `sign_daily_closure` step-up + schema/router `compliance` | Xem ghi chú dưới |

**Lệch có chủ đích so với "domain → app → interface" ở bước 4:** đổi `SigningReauthProvider` là
sửa *domain của `compliance`*, nhưng người hiện thực nó (`IamAuthReauthProvider` trong `api/`) và
người dùng nó (`ComplianceService`) phải đổi **cùng lúc** — Protocol thêm method mà adapter chưa
có thì mypy đỏ ngay. Tách ra sẽ tạo commit đỏ, phá đúng cổng mà kỷ luật #1 muốn bảo vệ. Nên gom
nguyên seam cross-module thành **một bước tự chứa**, vẫn 4 cổng xanh.
