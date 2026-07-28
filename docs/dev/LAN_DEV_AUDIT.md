# LAN_DEV_AUDIT — Rà soát trước khi mở BERAS ra mạng nội bộ

> 2026-07-29. Mọi dòng dưới đây đo bằng lệnh thật trên máy Linux Mint của Chain,
> **trước** khi sửa bất cứ thứ gì. Không suy luận từ mã nguồn.

## 1. Hệ thống tự phát hiện được

| Hạng mục | Giá trị | Đo bằng |
|---|---|---|
| Backend | FastAPI + uvicorn, venv `backend/.venv` | `pyproject.toml`, `main.py` |
| Frontend | Next.js **16.2.11**, npm, Turbopack | `frontend/package.json` |
| CSDL | PostgreSQL 16 (pgvector) trong Docker Compose | `docker-compose.yml` |
| Cache | Redis 7 | nt |
| Cổng | API **8000** · FE **3000** · PG **5432** · Redis **6379** | `ss -tlnp` |
| Biến URL API của FE | `NEXT_PUBLIC_API_BASE_URL`, mặc định `http://localhost:8000/api/v1` | `shared/api/client.ts` |
| CORS | `APP__CORS_ORIGINS`, mặc định `["http://localhost:3000"]` | `core/config.py:30` |
| Xác thực | JWT Bearer + **fallback header dev** | `api/deps.py` |
| Health check | `GET /api/v1/health` — **đã có sẵn** | `api/v1/health.py` |
| LAN IPv4 | **192.168.1.10** (card `wlp1s0`, dải `192.168.1.0/24`) | `ip route get 1.1.1.1` |
| Tường lửa | **UFW BẬT**, `DEFAULT_INPUT_POLICY=DROP` | `/etc/ufw/ufw.conf`, `/etc/default/ufw` |

## 2. 🔴 Ba rủi ro bảo mật — cả ba đều là "vô hại trên loopback, nguy hiểm trên LAN"

### R-1 · Fallback xác thực bằng header cấp TOÀN QUYỀN cho mọi thiết bị

`backend/.env` trên máy dev đặt `SECURITY__ALLOW_DEV_AUTH=true`. Khi đó
`api/deps.py` xử lý request **không có bearer token** như sau:

```python
if not settings.security.allow_dev_auth:
    raise UnauthenticatedError("Yêu cầu xác thực")
return RequestContext(
    tenant_id=UUID(request.headers.get("X-Tenant-Id", str(_DEV_TENANT))),
    branch_id=UUID(request.headers.get("X-Branch-Id", str(_DEV_BRANCH))),
    user_id=UUID(request.headers.get("X-User-Id", str(_DEV_USER))),
    permissions=_DEV_PERMISSIONS,   # = ALL_PERMISSIONS
)
```

Nghĩa là: **caller tự khai mình là tenant nào, chi nhánh nào, người nào — và nhận
đủ MỌI quyền hệ thống định nghĩa.** Trên `127.0.0.1` chỉ người ngồi trước máy làm
được. Bind `0.0.0.0` thì **mọi điện thoại trong nhà, kể cả máy của khách, đọc ghi
được mọi tenant mà không cần mật khẩu**.

Đây là rủi ro lớn nhất của cả việc mở LAN, và nó **không phải lỗi của mã** — cờ
này được thiết kế fail-closed, mặc định `False`, và app **từ chối khởi động** nếu
`APP__ENV=prod` mà cờ bật. Chỉ là nó không lường trước chuyện dev bind ra LAN.

**Xử lý:** `scripts/lan-dev.sh` export `SECURITY__ALLOW_DEV_AUTH=false` trước khi
chạy uvicorn (biến môi trường thắng `.env` trong pydantic-settings). Không sửa
mã, không sửa `.env`.

### R-2 · Postgres và Redis nghe trên mọi giao diện mạng

```
$ ss -tln | grep -E ':(5432|6379)'
LISTEN 0 4096 0.0.0.0:5432 0.0.0.0:*
LISTEN 0 4096 0.0.0.0:6379 0.0.0.0:*
```

`docker-compose.yml` khai `"5432:5432"` — Docker hiểu là bind mọi giao diện.
Postgres dùng cặp `pharma/pharma` ghi thẳng trong tệp; Redis **không có mật khẩu**.
Chưa ai vào được chỉ vì UFW đang chặn — tức là an toàn hiện tại đang dựa vào **một
lớp ngoài dự án**.

**Xử lý:** đổi thành `"127.0.0.1:5432:5432"` / `"127.0.0.1:6379:6379"`.
⚠️ Container đang chạy **giữ nguyên binding cũ** cho tới khi `docker compose down`
rồi `up` lại — script kiểm bằng `ss` và dừng nếu còn thấy `0.0.0.0`.

### R-3 · Điện thoại không phân giải được `localhost` của laptop

`shared/api/client.ts` mặc định `http://localhost:8000/api/v1`. Trên điện thoại,
`localhost` là **chính điện thoại** ⇒ mọi lời gọi API hỏng, và hỏng theo kiểu khó
đoán (không phải lỗi mạng rõ ràng).

**Xử lý:** `NEXT_PUBLIC_API_BASE_URL=http://192.168.1.10:8000/api/v1` khi chạy
`next dev`.

🔴 **Cạm bẫy đã gặp:** `frontend/.env.local` (không vào git) đang chứa
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`. Theo tài liệu Next thì
biến môi trường của tiến trình thắng `.env.local` — và đo ra đúng là vậy:

```
const BASE_URL = ("TURBOPACK compile-time value", "http://192.168.1.10:8000/api/v1")
                 ?? "http://localhost:8000/api/v1";
```

Nhưng "theo tài liệu" là một giả định. Script vì vậy **đọc thẳng mã JS đang phục
vụ** và dừng nếu giá trị nhúng không phải LAN IP.

## 3. Cái KHÔNG cần đụng

| | Vì sao |
|---|---|
| CORS | `APP__CORS_ORIGINS` đã là biến cấu hình — chỉ cần liệt kê thêm nguồn LAN, **không** dùng `*` |
| Health check | `GET /api/v1/health` có sẵn từ Sprint 2 |
| `docker-compose.yml` phần dịch vụ | Chỉ đổi **binding cổng**, không đổi image/volume/healthcheck |
| Mã nghiệp vụ | **0 dòng.** Toàn bộ chế độ LAN nằm ở biến môi trường lúc khởi chạy |
| `scripts/demo.sh`, `make demo` | Tái dùng nguyên, không dựng hệ thống song song |

## 4. ⚠️ NEEDS REVIEW — việc cần sudo, script KHÔNG tự làm

UFW đang bật với chính sách vào `DROP`. Điện thoại **sẽ không vào được** cho tới
khi mở hai cổng. Script **in ra lệnh và dừng ở đó** — sửa tường lửa là quyết định
của người, và nó cần quyền root mà công cụ tự động không có (và không nên có).

```bash
sudo ufw allow from 192.168.1.0/24 to any port 3000 proto tcp comment 'BERAS dev FE'
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp comment 'BERAS dev API'
```

Giới hạn theo **dải mạng nhà**, không mở cho mọi nguồn. Lệnh gỡ khi dùng xong nằm
trong đầu ra của script.
