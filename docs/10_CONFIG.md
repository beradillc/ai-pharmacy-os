# 10 — CẤU HÌNH (Configuration)

> Cấu hình phân lớp, validate bằng Pydantic Settings. Không hard-code, không commit secret.

---

## 1. Thứ tự ưu tiên (Precedence)

Từ thấp → cao (cái sau ghi đè cái trước):

```text
1. Giá trị mặc định trong code (Settings defaults)
2. File cấu hình theo môi trường (config/{env}.toml)
3. Biến môi trường (.env / OS env)  ← 12-factor
4. Secret store (Vault/KMS) cho bí mật
5. Cấu hình động trong DB (bảng settings, theo tenant/branch)
```

- Cấu hình **hạ tầng** (DB URL, Redis, khóa API) → env/secret.
- Cấu hình **nghiệp vụ** (VAT mặc định, ngưỡng cận date, bật AI) → bảng `settings` theo scope.

---

## 2. Phân nhóm cấu hình

```python
# THIẾT KẾ — core/config.py (pseudo)
class AppSettings(BaseSettings):
    env: Literal["dev","staging","prod"] = "dev"
    debug: bool = False

class DatabaseSettings(BaseSettings):
    url: PostgresDsn
    pool_size: int = 10

class RedisSettings(BaseSettings):
    url: RedisDsn

class AISettings(BaseSettings):
    provider: str = "anthropic"
    model_reasoning: str = "claude-opus-4-8"
    model_fast: str = "claude-sonnet-5"
    api_key: SecretStr
    max_tokens: int = 2048
    enable_clinical_ai: bool = True
    min_confidence: float = 0.6

class SecuritySettings(BaseSettings):
    jwt_secret: SecretStr
    jwt_ttl_minutes: int = 60
    require_2fa_roles: list[str] = ["pharmacist","admin"]

class Settings(BaseSettings):
    app: AppSettings
    db: DatabaseSettings
    redis: RedisSettings
    ai: AISettings
    security: SecuritySettings
    model_config = SettingsConfigDict(env_nested_delimiter="__")
```

Biến môi trường dạng: `AI__API_KEY`, `DB__URL`, `SECURITY__JWT_SECRET`.

---

## 3. Cấu hình nghiệp vụ động (bảng `settings`)

| scope | key | ví dụ value | ghi chú |
|-------|-----|-------------|---------|
| SYSTEM | `currency` | `"VND"` | toàn hệ thống |
| TENANT | `vat_default` | `0.08` | theo pháp nhân |
| BRANCH | `near_expiry_days` | `90` | cảnh báo cận date |
| BRANCH | `reorder_lead_days` | `7` | dự báo nhập |
| TENANT | `ai.enable_clinical` | `true` | bật dược sĩ AI |
| TENANT | `plugins.payment.default` | `"vnpay"` | plugin thanh toán |

Đọc qua `ConfigService.get(scope, key)` với fallback SYSTEM → TENANT → BRANCH.

---

## 4. File môi trường mẫu (`.env.example`)

```dotenv
# --- App ---
APP__ENV=dev
APP__DEBUG=true

# --- Database ---
DB__URL=postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os
DB__POOL_SIZE=10

# --- Redis ---
REDIS__URL=redis://localhost:6379/0

# --- AI (Claude) ---
AI__PROVIDER=anthropic
AI__MODEL_REASONING=claude-opus-4-8
AI__MODEL_FAST=claude-sonnet-5
AI__API_KEY=__set_me__
AI__ENABLE_CLINICAL_AI=true
AI__MIN_CONFIDENCE=0.6

# --- Security ---
SECURITY__JWT_SECRET=__set_me__
SECURITY__JWT_TTL_MINUTES=60
SECURITY__REFRESH_TTL_DAYS=30
SECURITY__ALLOW_DEV_AUTH=true      # chỉ dev/test — xem cảnh báo bên dưới
```

> `.env` **không** được commit. Chỉ commit `.env.example`.

### `SECURITY__ALLOW_DEV_AUTH` (thêm 2026-07-23 cùng module `iam`)

| | |
|---|---|
| **Mặc định trong code** | `false` — fail-closed |
| **Tác dụng khi `true`** | Request không có `Authorization: Bearer` được chấp nhận, danh tính lấy từ header `X-Tenant-Id`/`X-Branch-Id`/`X-User-Id` với **toàn bộ 38 permission** |
| **Rào chắn** | `APP__ENV=prod` + cờ `true` ⇒ `Settings` ném lỗi, ứng dụng **không khởi động**. Khi bật, khởi động log `dev_auth_enabled` mức warning |
| **Vì sao mặc định tắt** | Trước `iam`, fallback tự bật ở mọi env khác `prod` — chỉ cần cấu hình sai biến `APP__ENV` trên staging là API mở toang. Xem `docs/15_IAM_DESIGN.md` §5 Q3 |

**Hệ quả cần biết:** thiếu dòng này trong `.env` thì mọi demo/script cũ gọi API bằng header sẽ nhận
**401**. Đó là chủ đích chứ không phải lỗi cấu hình.

> ⚠️ `AI__ENABLE_CLINICAL_AI` **đã bị bỏ** (bật/tắt AI lâm sàng nay là cờ theo tenant —
> `clinical.TenantAiSettings`, Sprint 6). Còn sót dòng đó trong `.env` thì `AISettings` báo
> `extra_forbidden` và ứng dụng **không khởi động được**.

---

## 5. Quản lý theo môi trường

| Môi trường | DB | AI | Debug | Ghi chú |
|-----------|----|----|-------|---------|
| dev | local Postgres | model fast | true | seed dữ liệu mẫu |
| staging | managed | model thật | false | dữ liệu ẩn danh |
| prod | HA + backup | model thật | false | secret qua Vault/KMS |

---

## 6. Nguyên tắc

1. **12-factor**: cấu hình qua env, không qua code.
2. **Validate sớm**: app fail-fast khi thiếu cấu hình bắt buộc lúc khởi động.
3. **Secret tách biệt**: `SecretStr`, không log ra.
4. **Có thể override theo tenant/branch** cho cấu hình nghiệp vụ.
5. **Phiên bản hóa schema config**: thay đổi cấu trúc → migration + tài liệu.
