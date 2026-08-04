# Triển khai lên AlmaLinux — máy `bera-saas` (chuẩn bị 2026-08-04)

> Production, **dữ liệu THẬT ngay từ đầu** (Chain chốt 2026-08-04) — không phải staging.
> Truy cập **chỉ qua Tailscale**, chưa mở công khai ra internet (Chain chốt cùng ngày).
> Đây là lần triển khai ĐẦU TIÊN lên máy này — không có gì để "cập nhật", toàn bộ các
> bước dưới đây chạy một lần.

## Kiến trúc

```
Trình duyệt (thiết bị trong Tailscale)
        │  HTTPS (chứng chỉ Tailscale tự cấp)
        ▼
  tailscale serve  ── chạy NGOÀI container, ngay trên máy host ──
        │
        ├── /            → 127.0.0.1:3000  (frontend, Next.js standalone)
        └── /api/v1       → 127.0.0.1:8000  (backend, FastAPI/uvicorn)
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
              postgres (nội bộ)            redis (nội bộ)
        không publish port ra host, chỉ mạng compose nội bộ
```

Không nginx, không certbot, không domain công khai — `tailscale serve` làm hết việc
reverse-proxy + TLS. Không cổng nào của Postgres/Redis lộ ra ngoài container.

## 0. Máy chủ đã sẵn sàng (đã làm 2026-08-04, không lặp lại)

- Gập nắp KHÔNG làm máy ngủ (`/etc/systemd/logind.conf.d/99-server-no-sleep.conf`).
- zram bật (2G, zstd) — `/etc/systemd/zram-generator.conf`.
- Tuned profile `throughput-performance`, BBR bật, swappiness=20
  (`/etc/sysctl.d/99-server.conf`, có từ trước).
- `tailscale0` trong zone `trusted` của firewalld — SSH/Tailscale không lộ ra WiFi
  công cộng (zone `public` chỉ có `dhcpv6-client`).
- SELinux **Enforcing** — giữ nguyên, không tắt.

## 1. Cài Podman

AlmaLinux 10 chưa có kho Docker CE chính thức (quá mới) — dùng Podman, có sẵn trong
kho AppStream, hợp SELinux hơn.

```bash
sudo dnf install -y podman podman-compose
podman --version
```

## 2. Lấy mã nguồn lên máy

```bash
cd ~
git clone <URL_REPO> ai-pharmacy-os   # hoặc rsync/scp nếu repo chưa có remote công khai
cd ai-pharmacy-os
```

> 🔴 Nếu repo chưa có remote (nhiều khả năng — `AI_Pharmacy_OS/CLAUDE.md` kỷ luật #10
> ghi rõ "repo không remote" tính tới 2026-08-04): dùng `rsync -av --exclude=.venv
> --exclude=node_modules --exclude=.next <máy dev>:AI_Pharmacy_OS/ ~/ai-pharmacy-os/`
> từ máy đang giữ repo, hoặc tạo remote (GitHub riêng tư) rồi push trước.

## 3. Sinh bí mật — làm NGAY TRÊN MÁY SERVER, không qua chat/email

```bash
cd ~/ai-pharmacy-os
cp .env.prod.example .env.prod

# JWT secret
python3 -c "import secrets;print(secrets.token_urlsafe(48))"

# Mật khẩu Postgres (dùng cho cả PROD_DB_PASSWORD lẫn DB__URL trong .env.prod —
# hai chỗ, không tự đồng bộ, phải gõ tay khớp nhau)
python3 -c "import secrets;print(secrets.token_urlsafe(32))"
```

Hai khoá mã hoá at-rest cần chạy bằng đúng Python của backend (có `pharmacy_os.core
.security.crypto`) — build image backend trước rồi chạy tạm một container để sinh khoá:

```bash
podman build -f infra/docker/backend.Dockerfile -t pharmacy-os-backend:tmp .
podman run --rm pharmacy-os-backend:tmp python3 -c \
  "from pharmacy_os.core.security.crypto import generate_key, encode_key; print(encode_key(generate_key()))"
# chạy lệnh trên HAI LẦN — một cho ENCRYPTION__KEYS, một khác cho ENCRYPTION__BLIND_INDEX_KEY
```

Mở `.env.prod` (`nano`/`vim`), điền mọi chỗ `__set_me__` bằng các giá trị vừa sinh.
`AI__API_KEY` để nguyên `__set_me__` cũng chạy được (`MockLLMProvider`, tầng AI chưa
mở theo ROADMAP V4).

## 4. Build và chạy

```bash
export PROD_DB_PASSWORD='<đúng mật khẩu đã điền trong DB__URL của .env.prod>'
export NEXT_PUBLIC_API_BASE_URL='https://bera-saas.tailfb7b8c.ts.net/api/v1'

podman-compose -f docker-compose.prod.yml build
podman-compose -f docker-compose.prod.yml up -d
podman-compose -f docker-compose.prod.yml ps   # cả 4 service phải "Up"/"healthy"
```

## 5. Migration

```bash
podman-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 6. Đăng ký `tailscale serve`

```bash
sudo tailscale serve --bg --https=443 --set-path=/api/v1 http://127.0.0.1:8000/api/v1
sudo tailscale serve --bg --https=443 / http://127.0.0.1:3000
tailscale serve status
```

Nếu `tailscale serve` báo lỗi "path already served" khi chạy lệnh thứ hai, dùng
`tailscale serve --https=443 --yes` hoặc xem `tailscale serve --help` cho cú pháp
bản Tailscale hiện có (cú pháp `serve` từng đổi giữa các bản) — dán lỗi vào đây nếu
gặp, đừng tự đoán cờ.

## 7. Kiểm thử TRƯỚC khi có dữ liệu thật — bắt buộc, không bỏ qua

Đúng kỷ luật #15 (`AI_Pharmacy_OS/CLAUDE.md`): "không cổng nào chạy JS trong trình
duyệt thật" từng làm app trắng tinh trên điện thoại dù mọi lớp tự động đều xanh.
Trước khi bootstrap tenant thật:

1. Từ một thiết bị **trong Tailscale** (điện thoại/laptop khác), mở
   `https://bera-saas.tailfb7b8c.ts.net` — phải thấy màn đăng nhập, không phải
   trắng/lỗi chứng chỉ.
2. `curl -s https://bera-saas.tailfb7b8c.ts.net/api/v1/health` (hoặc endpoint health
   thật của backend) từ một máy khác trong Tailscale — phải trả 200.
3. Xem log cả 4 service: `podman-compose -f docker-compose.prod.yml logs --tail=50`
   — không có traceback/lỗi khởi động.

Không bước nào ở trên xanh thì **chưa bootstrap tenant thật** — quay lại sửa trước.

## 8. Bootstrap tenant thật đầu tiên

```bash
podman-compose -f docker-compose.prod.yml exec backend \
  env BOOTSTRAP_ADMIN_PASSWORD='<mật khẩu admin thật>' \
  python3 -m seeds.bootstrap_tenant \
    --tenant-name "<tên nhà thuốc thật>" \
    --branch-code HQ \
    --branch-name "<tên chi nhánh>" \
    --admin-email "<email admin thật>" \
    --admin-full-name "<tên đầy đủ admin>"
```

Đăng nhập thử ngay bằng tài khoản vừa tạo trên trình duyệt thật (bước 7 lặp lại) —
đây mới là lúc dữ liệu thật bắt đầu vào hệ thống.

## 9. Vận hành hằng ngày

- **Tự khởi động khi máy reboot:** `podman-compose` không tự chạy lại sau khi máy khởi
  động lại trừ khi có systemd unit — **CHƯA LÀM**, xem mục Nợ bên dưới.
- **Backup:** `docs/18_RUNBOOK_BACKUP_RESTORE.md` đã có runbook — chưa áp dụng cho
  máy này, xem mục Nợ.
- **Xem log:** `podman-compose -f docker-compose.prod.yml logs -f backend`
- **Cập nhật code:** `git pull && podman-compose -f docker-compose.prod.yml build &&
  podman-compose -f docker-compose.prod.yml up -d && podman-compose -f
  docker-compose.prod.yml exec backend alembic upgrade head`

## 🚧 Nợ — chưa làm trong lần chuẩn bị này

- **systemd unit / `podman-compose` tự khởi động lại sau khi máy reboot** — hiện tại
  nếu máy khởi động lại (mất điện, cập nhật kernel), app **không tự lên**. Cần
  `podman generate systemd` cho từng container hoặc một unit gọi
  `podman-compose up -d` lúc boot.
- **Backup tự động** (`docs/18_RUNBOOK_BACKUP_RESTORE.md`) — runbook có sẵn nhưng
  chưa nối vào cron/systemd timer trên máy này.
- **fail2ban cho chính ứng dụng** (khác fail2ban cấp hệ điều hành đã bật sẵn) — rate
  limit đăng nhập đã có ở tầng app (`SECURITY__RATE_LIMIT_*`), chưa có gì ở tầng
  mạng cho riêng cổng ứng dụng.
- **Mở công khai ra internet** — cố ý CHƯA làm (Chain chốt 2026-08-04). Khi nào cần,
  phải quay lại: domain thật, TLS Let's Encrypt/certbot, mở cổng 80/443 qua
  firewalld zone `public`, và rà lại toàn bộ rate-limit/fail2ban trước khi mở.
- **`AI__API_KEY` thật** — chưa cấp, tầng AI (ROADMAP V4) vẫn dùng `MockLLMProvider`.
