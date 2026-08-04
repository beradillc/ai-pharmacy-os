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

🔴 **`--set-path` CẮT phần tiền tố khớp trước khi chuyển tiếp** — đích (target URL) phải
tự lặp lại `/api/v1` (đúng như lệnh trên), không phải chỉ `http://127.0.0.1:8000`.
Thiếu cú pháp này thì mọi request `/api/v1/*` bị forward thành `/*` (không có tiền tố)
tới backend, và backend trả 404 vì route thật là `/api/v1/...`. Đã xác nhận bằng lệnh
thật 2026-08-04 (curl trực tiếp `127.0.0.1:8000/api/v1/health` = 200, `.../health`
không tiền tố = 404 — backend đúng, lỗi nằm ở cấu hình serve).

Nếu `tailscale serve` báo "Serve is not enabled on your tailnet" kèm link
`login.tailscale.com/f/serve?node=...` — thử chạy lại lệnh trước khi mở link, có thể
Serve (khác Funnel) không thật sự bị chặn bởi cờ đó; xác nhận bằng `tailscale serve
status` sau khi chạy.

### 6b. ⛔ Funnel — KHÔNG DÙNG ĐƯỢC Ở VIỆT NAM (giữ lại để không thử lại lần nữa)

🔴 **Đã mở thành công về mặt kỹ thuật, nhưng nhà mạng Việt Nam chặn tên miền `.ts.net`.**
Đo thật 2026-08-04, cùng một thời điểm:

| Đường | Từ ngoài VN (WebFetch) | Từ mạng Chain (5G + WiFi) |
|---|---|---|
| `https://bera-saas.tailfb7b8c.ts.net/` (443) | ✅ trang BERAS | ❌ `ERR_CONNECTION_CLOSED` |
| cùng URL, mở bằng Chrome thật (không qua Zalo) | ✅ | ❌ `ERR_CONNECTION_CLOSED` |
| `...:8443/` | ✅ | ❌ |

**Đổi cổng không cứu được ⇒ chặn theo tên miền/SNI, không phải theo cổng.**
`ERR_CONNECTION_CLOSED` (kết nối mở rồi bị đóng giữa chừng) là dấu hiệu đặc trưng của
DPI, khác hẳn `ERR_CONNECTION_TIMED_OUT` của lỗi định tuyến. Cùng lúc đó Cloudflare vào
được bình thường ⇒ không phải mạng Chain hỏng, mà đúng tên miền này bị chặn.

**Cách dùng hiện tại: Cloudflare Tunnel — xem mục 6c.** Phần dưới đây giữ nguyên làm tư
liệu (cú pháp Funnel đúng, bẫy DNS MagicDNS), phòng khi triển khai ở nơi không bị chặn.

<details>
<summary>Cú pháp Funnel (không dùng ở VN — bấm để xem)</summary>

#### Mở CÔNG KHAI ra internet bằng Funnel (2026-08-04)

Mục tiêu: người xem **mở link là vào**, không cài Tailscale, không cần tài khoản Tailscale.

🔴 **Cú pháp `tailscale funnel <target>` ở mục 6 KHÔNG dùng được nữa.** Bản trên máy này
(Tailscale hiện hành) trả `Error: the CLI for serve and funnel has changed.` với dạng
`tailscale funnel --bg 443 on`. Cú pháp đúng — và giữ nguyên bẫy `--set-path` ở mục 6:

```bash
tailscale funnel --bg --set-path /       http://127.0.0.1:3000
tailscale funnel --bg --set-path /api/v1 http://127.0.0.1:8000/api/v1
tailscale funnel status        # phải thấy "(Funnel on)", không phải "(tailnet only)"
```

**Không cần `sudo`** sau khi đã chạy **một lần**: `sudo tailscale set --operator=$USER`
(Chain chạy 2026-08-04). Trước đó mọi lệnh `serve`/`funnel` trả `Access denied: serve
config denied`.

**Tắt lại khi demo xong:**
```bash
tailscale funnel reset         # gỡ công khai, quay về tailnet-only
```

🔴 **`curl` từ máy trong tailnet KHÔNG chứng minh được Funnel hoạt động** — máy đó vào
được kể cả khi Funnel tắt. Phải đo từ **ngoài** tailnet. Cách đã dùng 2026-08-04: gọi
`https://bera-saas.tailfb7b8c.ts.net/` bằng một dịch vụ chạy ngoài mạng (WebFetch của
Claude, hạ tầng Anthropic) — trả về đúng trang `BERAS — Sổ Quản Lý Nhà Thuốc`, và
`/api/v1/health` trả `{"status":"ok","version":"0.2.0",...}`. Đúng tinh thần kỷ luật #15.

🔴 **Bẫy DNS khi thử trên máy TỪNG cài Tailscale.** Cùng một tên miền phân giải ra hai
địa chỉ khác nhau tuỳ nguồn DNS:

| Nguồn DNS | Trả về | Route được ngoài tailnet? |
|---|---|---|
| Công cộng (`8.8.8.8`, `1.1.1.1`) | `103.84.155.153/.217` (IP Funnel) | ✅ |
| MagicDNS (trong tailnet) | `100.76.165.120` (IP tailnet) | ❌ |

Tắt app Tailscale **không** xoá cấu hình DNS mà VPN profile đã cài, cũng không xoá cache
DNS ⇒ máy vẫn trỏ về IP tailnet, và triệu chứng là **timeout**. Phải gỡ hẳn VPN profile
(hoặc bật/tắt chế độ máy bay) mới thành phép thử sạch. **Phép thử đúng nhất vẫn là một
máy CHƯA TỪNG cài Tailscale** — máy đã cài mang sẵn một điều kiện mà không người xem nào có.

</details>

### 6c. ✅ Mở công khai bằng **Cloudflare Tunnel** — cách đang dùng (2026-08-04)

Ba mảnh phải có đủ, thiếu một là không chạy:

**① Gộp frontend + API vào MỘT cổng.** Một đường hầm Cloudflare chỉ trỏ tới **một** cổng,
trong khi `tailscale serve` trước đây phục vụ hai tuyến. Service `edge` (Caddy) trong
`docker-compose.prod.yml` làm việc này ở cổng `8080` — xem `infra/caddy/Caddyfile`.
Khối `/api/v1*` phải đứng **trước** khối bắt-tất-cả, nếu không request API rơi vào
frontend và trả trang 404 của Next thay vì JSON.

**② `NEXT_PUBLIC_API_BASE_URL` phải là đường dẫn TƯƠNG ĐỐI `/api/v1`.** Mặc định trong
compose nay đã là vậy. Trước 04/08 nó là URL tuyệt đối bắt buộc khai ⇒ tên miền bị nướng
vào ảnh Docker lúc build ⇒ **mỗi lần đổi đường ra internet phải build lại frontend**.
Kiểm nhanh ảnh có sạch không:
```bash
podman exec pharmacy-os-prod_frontend_1 grep -rl 'tailfb7b8c' /app/.next   # phải RỖNG
```

**③ Đường hầm chạy bền bằng systemd user unit** `~/.config/systemd/user/cloudflared-demo.service`
(`enabled`, `Restart=always`, log ghi ra `~/cloudflared-demo.log`). Binary ở
`~/.local/bin/cloudflared`.
⚠️ `nohup cloudflared … &` **không sống sót** khi phiên SSH đóng — đã vấp 04/08, tiến
trình chết im lặng trong khi log cũ vẫn còn nên tưởng đang chạy. Phải là systemd unit.

**Lấy link demo hiện tại:**
```bash
link-demo          # ~/.local/bin/link-demo — in URL + trạng thái unit + mã HTTP
```

🔴 **URL ĐỔI mỗi lần cloudflared khởi động lại** (`trycloudflare.com` cấp ngẫu nhiên).
`Restart=always` nghĩa là mạng chập một nhịp cũng đổi; reboot cũng đổi. **Đây là lý do
cấu hình hiện tại CHƯA thoả mục tiêu "bật máy lên là vào được ngay"** — vào được, nhưng
bằng một địa chỉ khác, phải chạy `link-demo` để lấy.
**Cách gỡ vĩnh viễn:** một tên miền riêng trỏ nameserver về Cloudflare ⇒ "named tunnel"
⇒ địa chỉ cố định, không đổi. Chain xác nhận 2026-08-04 **chưa có tên miền**.

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

- **Tự khởi động khi máy reboot** — ✅ ĐÃ LÀM (2026-08-04): `systemd --user` unit
  `~/.config/systemd/user/pharmacy-os.service` (`EnvironmentFile=~/.config/pharmacy-os.env`,
  chứa `PROD_DB_PASSWORD`/`NEXT_PUBLIC_API_BASE_URL`/`PHARMACY_ALLOW_MOCKS_IN_PROD`) +
  `loginctl enable-linger chain` (chạy được cả khi chưa ai đăng nhập). Kiểm bằng
  `systemctl --user status pharmacy-os.service`.
- **Backup tự động** — ✅ ĐÃ LÀM (2026-08-04): cron dùng thẳng
  `scripts/backup_verify.sh` (mỗi giờ, có tự khôi phục kiểm chứng) +
  `scripts/backup_deadman.sh` (lệch 15 phút, báo khi backup ngừng chạy) +
  `scripts/backup_secrets.sh` (mới, sao lưu `.env.prod` — khoá mã hoá — TÁCH RIÊNG thư
  mục khỏi bản dump CSDL, đúng quy tắc B.2 `docs/18`). Cần `podman-docker` (gói
  tương thích `docker` CLI) để 2 script gốc chạy nguyên vẹn, không sửa code — đã cài.
  `crontab -l` xem lịch; log ở `~/pharmacy_backups.log` / `~/pharmacy_deadman.log` /
  `~/pharmacy_secrets_backup.log`.
- **Xem log:** `podman-compose -f docker-compose.prod.yml logs -f backend`
- **Cập nhật code:** `git pull && podman-compose -f docker-compose.prod.yml build &&
  podman-compose -f docker-compose.prod.yml up -d && podman-compose -f
  docker-compose.prod.yml exec backend alembic upgrade head`

### 🔌 BẬT MÁY LÊN LÀ VÀO ĐƯỢC NGAY — không thao tác gì (rà 2026-08-04)

Bốn mắt xích phải cùng đúng thì mở link là chạy. Đã rà từng cái bằng lệnh thật:

| # | Mắt xích | Lệnh kiểm | Trạng thái 2026-08-04 |
|---|---|---|---|
| 1 | `tailscaled` tự chạy khi boot | `systemctl is-enabled tailscaled` | ✅ `enabled` + `active` |
| 2 | **`Linger`** — cho `systemd --user` chạy khi **chưa ai đăng nhập** | `loginctl show-user chain \| grep Linger` | ✅ `Linger=yes` |
| 3 | Unit app tự dựng 4 container | `systemctl --user is-enabled pharmacy-os.service` | ✅ `enabled` + `active` |
| 4 | ~~Funnel còn bật~~ → **`cloudflared` tự chạy** | `systemctl --user is-enabled cloudflared-demo.service` | ✅ `enabled` + `active` |
| 5 | Caddy gộp 2 tuyến | `curl -s -o /dev/null -w '%{http_code}' localhost:8080/api/v1/health` | ✅ `200` |

⚠️ **Mắt xích 4 lên được nhưng ĐỊA CHỈ ĐỔI** — xem cảnh báo cuối mục 6c. "Vào được ngay"
đúng theo nghĩa dịch vụ sống, **không** đúng theo nghĩa link cũ còn dùng được. Sau mỗi
lần bật máy phải chạy `link-demo` lấy địa chỉ mới, cho tới khi có tên miền riêng.

🔴 **Mắt xích số 2 là chỗ dễ hỏng nhất và im lặng nhất.** Không có `Linger=yes` thì
`systemd --user` chỉ sống trong lúc có phiên đăng nhập ⇒ máy boot xong, **không ai SSH
vào thì app không bao giờ khởi động** — mà `systemctl --user is-enabled` vẫn báo
`enabled`, nên nhìn cấu hình sẽ tưởng đúng. Bật bằng `loginctl enable-linger chain`.

⚠️ **Chưa kiểm chứng bằng reboot thật SAU khi bật Funnel.** §7ea (2026-08-04) đã reboot
thật và xác nhận **4 container tự lên** — nhưng lúc đó Funnel **chưa tồn tại**. Việc
"cấu hình Funnel bền qua reboot" hiện mới ở mức **suy luận từ cờ `--bg`** (ghi vào state
của `tailscaled`, mà `tailscaled` thì `enabled`), **chưa phải bằng chứng**. Muốn có bằng
chứng thì chạy:

```bash
sudo reboot                    # cần mật khẩu — Claude không chạy được, phải là người
# sau khi máy dậy, kiểm TỪ NGOÀI tailnet (điện thoại tắt WiFi, dùng 4G):
#   https://bera-saas.tailfb7b8c.ts.net/     → phải ra màn đăng nhập BERAS
```

### 🔄 Đồng bộ mã nguồn máy dev ↔ `bera-saas` (rà 2026-08-04)

Repo trên server **không có `git remote`** (deploy key nằm ở máy Mint, không ở server).
Ngày 04/08 phát hiện server tụt **6 commit** sau máy dev, nghĩa là bản mã đang phục vụ
thật đã trôi khỏi repo chính — sửa gì trực tiếp trên server sẽ mất ở lần deploy sau.

Cách đồng bộ **không cần GitHub, không đưa gì ra internet** — dùng `git bundle` qua
Tailscale (đã dùng thật 04/08, fast-forward sạch):

```bash
# trên máy dev
git bundle create /tmp/sync.bundle <commit-server-đang-đứng>..main
git bundle verify /tmp/sync.bundle
scp /tmp/sync.bundle chain@bera-saas:/tmp/sync.bundle

# trên server
cd ~/ai-pharmacy-os
git checkout -- .                                   # bỏ thay đổi cục bộ (xem cảnh báo dưới)
git fetch /tmp/sync.bundle main:refs/remotes/mint/main
git merge --ff-only refs/remotes/mint/main
```

🔴 **Merge sẽ bị chặn bởi file `untracked` trùng tên với file trong commit mới**
(`error: untracked working tree files would be overwritten`). Ngày 04/08 thủ phạm là
`scripts/backup_secrets.sh` — được tạo tay trên server và **đang chạy trong cron**.
**Đối chiếu nội dung trước khi gỡ** (`diff` với bản trong commit), đừng `rm` mù: nếu bản
trên server mới hơn thì gỡ đi là mất một thứ đang chạy production.

Trước khi `git checkout -- .`, chép riêng những file đang phục vụ thật
(`docker-compose.prod.yml`, `.env.prod`) ra `/tmp` để đối chiếu sau merge — `.env.prod`
nằm trong `.gitignore` nên không bị đụng, nhưng compose thì có.

## 🚧 Nợ — chưa làm

- **fail2ban cho chính ứng dụng** (khác fail2ban cấp hệ điều hành đã bật sẵn) — rate
  limit đăng nhập đã có ở tầng app (`SECURITY__RATE_LIMIT_*`), chưa có gì ở tầng
  mạng cho riêng cổng ứng dụng.
- ~~**Mở công khai ra internet** — cố ý CHƯA làm~~ → **ĐÃ MỞ 2026-08-04** bằng
  **Tailscale Funnel** (mục 6b), Chain duyệt để demo rộng rãi. Không cần domain riêng,
  không cần certbot, không mở cổng nào trên firewalld/router — Funnel đi qua hạ tầng
  Tailscale và tự cấp TLS. 🔴 **Hệ quả:** dòng "fail2ban cho chính ứng dụng" ngay trên
  đây từ nay **không còn là nợ hoãn được** — app đã nằm trên internet công khai, bot quét
  sẽ tìm ra. Chưa chặn pilot, nhưng phải xử trước khi có nhà thuốc thật chạy trên máy này.
- 🔴 **`SECURITY__RATE_LIMIT_LOGIN_ATTEMPTS` đang ở `300`, KHÔNG phải `10`** — nới tạm
  2026-08-04 cho demo công khai, **phải trả về `10` cùng lúc với `tailscale funnel reset`**.
  *Vì sao phải nới:* backend đọc IP client bằng `request.client.host`
  (`core/http.py:client_ip_of`, cố ý không đọc `X-Forwarded-For` để sổ audit không giả mạo
  được). Sau reverse-proxy, **mọi người dùng đều mang cùng một IP** — đo thật: `10.89.0.4`
  (gateway mạng container). Hạn mức 10 lượt/phút vì thế là 10 lượt cho **toàn hệ thống**,
  không phải mỗi người: **một người gõ sai mật khẩu 10 lần là khoá đường đăng nhập của
  tất cả những người còn lại**. Lớp khoá tài khoản sau 5 lần sai **vẫn nguyên**, nên
  chống dò mật khẩu vào một tài khoản không bị yếu đi.
  **Cách sửa đúng (chưa làm):** cho `client_ip_of` tin `X-Forwarded-For` khi socket peer
  nằm trong danh sách proxy tin cậy — đọc từ **phải sang trái**, lấy IP đầu tiên không
  thuộc danh sách (đi từ trái sẽ tin phần client tự gửi). Đã đo xác nhận `tailscale serve`
  **có** gửi `X-Forwarded-For` với IP thật, nên bản vá sẽ chạy. Chính docstring của hàm đó
  đã ghi sẵn đây là *"the follow-up"*.
- **`AI__API_KEY` thật** — chưa cấp, tầng AI (ROADMAP V4) vẫn dùng `MockLLMProvider`
  (đang chạy dưới cờ diễn tập vận hành `PHARMACY_ALLOW_MOCKS_IN_PROD=true` — Chain chốt
  2026-08-04, xem PROJECT_STATE §7dy). **Tắt cờ này ngay khi có khoá thật.**
- **Backup chưa có bản sao NGOÀI máy `bera-saas`** — 3 script trên chỉ bảo vệ khỏi lỗi
  dữ liệu/thao tác sai, KHÔNG bảo vệ khỏi máy/ổ cứng hỏng vật lý (laptop, không phải
  server rack có RAID). Cải thiện thêm: đồng bộ định kỳ `~/pharmacy_backups` +
  `~/pharmacy_secrets_backup` sang máy khác hoặc lưu trữ đám mây.
- **Dead-man's switch chỉ chạy trên chính máy `bera-saas`** — nếu cron chết hẳn (không
  chỉ script backup chết) thì cả 2 lớp cùng im lặng. Đóng hẳn lỗ hổng cần dịch vụ NGOÀI
  máy chủ (`PING_URL` trỏ healthchecks.io/Uptime Kuma — xem chú thích trong
  `scripts/backup_deadman.sh`), chưa cấu hình.
- **Bug logging structlog mất traceback** (`pharmacy_os/logging.py` thiếu
  `format_exc_info`) — không liên quan triển khai nhưng làm log khó gỡ lỗi thật.
