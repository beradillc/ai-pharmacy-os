# LAN_DEV_REPORT — Kết quả triển khai chế độ LAN development

> 2026-07-29 · Linux Mint · GĐ tự triển khai dưới uỷ quyền cao nhất của Chain.
> Mọi con số dưới đây **đo bằng lệnh thật sau khi triển khai**, không phải kỳ vọng.

## 1. Kết quả một dòng

| Hạng mục | Giá trị |
|---|---|
| **LAN IP** | **192.168.1.10** (card `wlp1s0`, dải `192.168.1.0/24`) |
| **Frontend URL (điện thoại)** | **http://192.168.1.10:3000** |
| **Backend URL (điện thoại)** | **http://192.168.1.10:8000/api/v1** |
| Trên chính laptop | http://localhost:3000 |
| **Cổng đã dùng** | FE **3000** · API **8000** · PG **5432** *(loopback)* · Redis **6379** *(loopback)* |
| **Tường lửa** | UFW **BẬT** · 2 cổng dev **đã mở** cho `192.168.1.0/24` (29/07 08:03) |
| **CORS** | Danh sách đúng 2 nguồn, **không** wildcard |
| **CSDL có ra LAN không** | **KHÔNG** — `127.0.0.1:5432`, kiểm bằng kết nối TCP từ LAN IP: **đóng** |
| **Xác thực** | JWT thật; **dev-auth đã tắt** ở chế độ LAN |
| **Test/build** | backend `MAKE_CHECK_EXIT=0` · FE `lint/tsc/build` = 0 |

## 2. Đã làm gì

| # | Thay đổi | Tệp |
|---|---|---|
| 1 | Postgres + Redis bind **`127.0.0.1`** thay vì mọi giao diện | `docker-compose.yml` |
| 2 | Script một lệnh, tự phát hiện IP + tự kiểm 7 bước | `scripts/lan-dev.sh` (mới) |
| 3 | `make lan` | `Makefile` |
| 4 | Ba tài liệu | `docs/dev/` |

**Mã nghiệp vụ đổi: 0 dòng.** Chế độ LAN hoàn toàn nằm ở biến môi trường lúc
khởi chạy (`SECURITY__ALLOW_DEV_AUTH`, `APP__CORS_ORIGINS`,
`NEXT_PUBLIC_API_BASE_URL`) — không sửa `.env`, không sửa mã, không dựng hệ
thống song song với `make demo` đã có.

## 3. Bảy phép kiểm script tự chạy mỗi lần khởi động

```
▶ 1/7 · Địa chỉ LAN
   ✓ LAN IP: 192.168.1.10 (card wlp1s0, dải 192.168.1.0/24)
▶ 2/7 · Cổng
   ✓ cổng 8000 rảnh          ✓ cổng 3000 rảnh
▶ 3/7 · Postgres + Redis (chỉ loopback)
   ✓ Postgres sẵn sàng
   ✓ 5432 + 6379 chỉ nghe loopback — không thiết bị nào trong mạng vào được
▶ 4/7 · Tường lửa
   ! UFW đang BẬT, chính sách vào mặc định: DROP   → in ra 2 lệnh cần chạy
▶ 5/7 · Backend (0.0.0.0:8000)
   ✓ health: {"status":"ok","version":"0.2.0","service":"ai-pharmacy-os"}
   ✓ xác thực: dev-auth ĐÃ TẮT (bắt buộc đăng nhập thật)
   ✓ gọi API không token + tự khai X-Tenant-Id → 401 (đúng)
   ✓ CORS: cho http://192.168.1.10:3000, chặn nguồn lạ (không dùng `*`)
▶ 6/7 · Frontend (0.0.0.0:3000)
   ✓ next dev đang phục vụ /login
▶ 7/7 · Kiểm qua LAN IP — đúng đường điện thoại đi
   ✓ http://192.168.1.10:8000/api/v1/health → 200
   ✓ http://192.168.1.10:3000/login → 200
   ✓ URL API trình duyệt nhận: http://192.168.1.10:8000/api/v1
```

Script **dừng có báo lỗi** (không chạy tiếp nửa vời) nếu: không tìm được IP LAN ·
cổng bị chiếm · CSDL còn nghe `0.0.0.0` · dev-auth chưa đóng · CORS lọt nguồn lạ ·
URL API nhúng sai.

## 4. Kiểm bảo mật — chạy từ LAN IP, không phải loopback

| Phép thử | Kết quả | Nghĩa là |
|---|---|---|
| `GET /drugs` **không token** | **401** | Không có đường vào ẩn danh |
| `GET /drugs` **không token + tự khai `X-Tenant-Id`** | **401** | Cửa dev-auth đã đóng thật |
| `GET /drugs` token **hỏng** | **403** | Không có nhánh nào bỏ qua chữ ký |
| Token thật, **không** header giả | 4 thuốc | |
| Token thật **+ `X-Tenant-Id`/`X-Branch-Id` giả** | **4 thuốc — y hệt** | Header **không đè được** claim JWT ⇒ cô lập tenant còn nguyên |
| `Origin: http://evil.example` | **0 header CORS** | Không wildcard, nguồn lạ bị chặn |
| Mở TCP tới `192.168.1.10:5432` | **đóng** | CSDL không ra LAN |
| Đăng nhập thật qua LAN IP | **200 + JWT** | FE → BE → **CSDL** thông suốt |
| `GET /drugs` kèm token qua LAN IP | **200**, trả tên thuốc thật | Toàn chuỗi tới tận CSDL chạy được |

## 5. ✅ Tường lửa — ĐÃ MỞ (29/07 08:03, Chain uỷ quyền kèm mật khẩu sudo)

```
$ sudo ufw status numbered
[ 1] 3000/tcp   ALLOW IN   192.168.1.0/24   # BERAS dev FE
[ 2] 8000/tcp   ALLOW IN   192.168.1.0/24   # BERAS dev API
```

🔴 **Điều này CHƯA chứng minh điện thoại vào được.** Máy không tự kiểm được tường
lửa của chính nó: lưu lượng từ laptop gọi tới `192.168.1.10` đi qua loopback và
UFW không lọc — nên kết quả `200` ở mục 3 phía trên **không phải** bằng chứng.
Phép thử thật duy nhất là **cầm điện thoại lên mở**.

Lệnh đã chạy (giữ lại để dựng lại khi đổi máy/đổi dải mạng):

```bash
sudo ufw allow from 192.168.1.0/24 to any port 3000 proto tcp comment 'BERAS dev FE'
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp comment 'BERAS dev API'
```

**Vì sao script không tự chạy:** cần `sudo`. Lần này Chain **uỷ quyền riêng kèm
mật khẩu** nên GĐ chạy hộ; script thì vẫn giữ nguyên nguyên tắc chỉ *in ra lệnh*,
vì mật khẩu là thứ được cấp cho một lần cụ thể, không phải một quyền thường trực.
Không tắt firewall dòng nào — chỉ **thêm** đúng 2 luật, giới hạn theo dải mạng nhà.

Lệnh trên giới hạn theo **dải mạng nhà**, không mở cho mọi nguồn. Gỡ khi xong:

```bash
sudo ufw delete allow from 192.168.1.0/24 to any port 3000 proto tcp
sudo ufw delete allow from 192.168.1.0/24 to any port 8000 proto tcp
```

## 6. 🔴 Rủi ro đã phát hiện và cách xử lý

| # | Rủi ro | Nếu bỏ qua | Đã xử lý |
|---|---|---|---|
| R-1 | `ALLOW_DEV_AUTH=true` + bind `0.0.0.0` | **Mọi điện thoại trong nhà có TOÀN QUYỀN trên MỌI tenant, không cần mật khẩu** | Script tắt cờ; tự kiểm bằng một lời gọi không token phải nhận 401 |
| R-2 | PG/Redis nghe `0.0.0.0`, mật khẩu `pharma/pharma`, Redis không mật khẩu | Bất kỳ ai trong mạng đọc/ghi/xoá được CSDL | Bind `127.0.0.1`; script dừng nếu `ss` còn thấy `0.0.0.0` |
| R-3 | FE mặc định gọi `localhost` | Điện thoại gọi về **chính nó** ⇒ mọi lời gọi hỏng khó đoán | Truyền LAN IP; script **đọc mã JS đang phục vụ** để xác nhận, không tin thứ tự ưu tiên biến môi trường |

Chi tiết bằng chứng: `LAN_DEV_AUDIT.md`.

## 7. Giới hạn — nói trước để không ai hiểu nhầm

1. **Đây là chế độ DEVELOPMENT.** HTTP thuần, không TLS; `next dev` không phải bản
   build sản phẩm. Chỉ dùng trong mạng nhà, **không** phơi ra Internet, **không**
   port-forward trên router.
2. **IP LAN đổi khi router cấp lại.** Luôn lấy theo dòng script in, đừng nhớ thuộc.
3. **CSDL mặc định là `pharmacy_os` (dev)**, không phải dữ liệu demo đẹp. Muốn
   demo thì `DB__URL='…pharmacy_os_demo' make lan`.
4. **Chưa ai mở BERAS trên điện thoại thật ở phiên này** — script chứng minh
   *đường mạng* thông (health 200, login 200, JWT thật, dữ liệu CSDL trả về), nhưng
   *giao diện trông ra sao trên màn 390px* thì chỉ mắt người trả lời được. Bảng
   kiểm: `LAN_MOBILE_TEST.md`.
5. **Múi giờ**: xem `PROJECT_STATE` §7bw B-bis — cửa sổ "hôm nay" tính theo giờ
   máy chủ. Điện thoại ở múi giờ khác sẽ thấy lệch ngày.

## 8. Định nghĩa hoàn thành — đối chiếu

| DoD | Trạng thái |
|---|---|
| Laptop chạy BERAS | ✅ `make lan`, 7/7 phép kiểm xanh |
| Điện thoại vào `http://LAN_IP:3000` | ⚠️ Cổng đã mở; **chưa ai cầm điện thoại thử** — máy không tự kiểm được tường lửa của chính nó |
| Frontend gọi được backend | ✅ URL nhúng = LAN IP, đã đọc từ JS phục vụ thật |
| Backend gọi được database | ✅ login 200 + `/drugs` trả tên thuốc thật |
| Authentication hoạt động | ✅ 401 không token · 403 token hỏng · 200 token thật |
| Không expose database | ✅ TCP tới `192.168.1.10:5432` **đóng** |
| Test/build pass | ✅ backend `MAKE_CHECK_EXIT=0` (1135+16 passed) · FE lint/tsc/build = 0 |
