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
```

> `.env` **không** được commit. Chỉ commit `.env.example`.

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
