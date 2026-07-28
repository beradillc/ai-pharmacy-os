# 18 — RUNBOOK: SAO LƯU · KHÔI PHỤC · BẬT MÃ HOÁ · XOAY KHOÁ

> **F-16** (diễn tập khôi phục) và **F-8** (runbook mã hoá) — hai mục chặn Sprint 9.
>
> Mọi con số trong tài liệu này **đo thật ngày 2026-07-28**, không phải ước lượng.
> Chỗ nào chưa chạy thật thì ghi rõ là **chưa chạy**.

---

## PHẦN A — SAO LƯU & KHÔI PHỤC (F-16)

### A.1 Vì sao mục này chặn pilot

Dự án đã có `pg_dump` chạy trước **mỗi** migration (full-auto điều 6, từ 2026-07-23).
Kiểm toán 2026-07-26 chỉ ra chỗ hở: **chưa từng restore lần nào**. Một bản backup chưa
khôi phục thử là một **giả định**, không phải một đường lùi. Pilot không có đường lùi đã
chứng minh thì không phải pilot.

### A.2 ✅ Diễn tập đã chạy — 2026-07-28

**Đây là phần quan trọng nhất của tài liệu này: nó không mô tả một quy trình, nó ghi lại
một lần đã chạy.**

| Bước | Lệnh thật | Kết quả đo được |
|---|---|---|
| 1. Dựng dữ liệu | 50 lô + 50 dòng xuất/nhập + 50 dòng số dư, cạnh dữ liệu sẵn có (1 tenant · 1 user · 5 role · 16 dòng audit) | CSDL **12 MB** |
| 2. Sao lưu | `docker exec … pg_dump -U pharma pharmacy_os > f16_drill_*.sql` | `PGDUMP_EXIT=0` · **<1 giây** · file **152 KB** |
| 3. Chụp "sự thật" bản gốc | 9 chỉ số: đếm 7 bảng + tổng tồn kho + revision alembic | `1\|1\|5\|50\|50\|50\|16\|5000.000\|0033_movement_ref_batch_uq` |
| 4. Tạo đích rỗng | `CREATE DATABASE pharmacy_os_restore_drill` | `EXIT=0` |
| 5. **Khôi phục** | `psql -d pharmacy_os_restore_drill -v ON_ERROR_STOP=1 < dump` | `RESTORE_EXIT=0` · **2 giây** · **0 lỗi/0 fatal** trong log |
| 6. Đối chiếu dữ liệu | so 9 chỉ số trên | **KHỚP TUYỆT ĐỐI** (`diff` rỗng) |
| 7. Đối chiếu **lược đồ** | index + ràng buộc | `uq_movement_ref_batch` **có** · 6 index trên `stock_movements` · **27 khoá ngoại** |
| 8. **Ứng dụng đọc được** | mở `build_engine`/`build_sessionmaker` **thật** trỏ vào bản khôi phục, đọc qua ORM | tenant `'Nhà thuốc FE Demo'` · user `'fe-demo@beral.vn'` · hash bcrypt 60 ký tự prefix `$2b$` · 50 lô · tồn **5000.000** ⇒ `APP_READ_OK` |

**Bước 8 là bước phân biệt thật/giả.** `psql` đọc được chỉ chứng minh **byte còn nguyên**.
Ứng dụng đọc được mới chứng minh **lược đồ, kiểu dữ liệu và các cột mã hoá vẫn khớp với
mã đang chạy** — tức là khôi phục xong thì **bán hàng lại được**, không phải chỉ "có file".

### A.3 Quy trình khôi phục — dùng khi có sự cố thật

> Gắn với `docs/17_INCIDENT_RESPONSE.md` bước 10: **R3 quyết định restore**, **R4 duyệt**
> nếu là P1. Không ai tự restore một mình trên dữ liệu thật.

```bash
# 0. DỪNG ứng dụng trước. Restore trong lúc app đang ghi = hai nguồn ghi vào một chỗ.
docker compose stop app      # hoặc dừng systemd unit tương ứng

# 1. Sao lưu CHÍNH CÁI ĐANG HỎNG trước khi đụng vào nó.
#    Kể cả khi nó hỏng — nó vẫn là bằng chứng duy nhất về chuyện đã xảy ra.
docker exec -e PGPASSWORD=$PGPASS <container> pg_dump -U pharma pharmacy_os \
  > ~/truoc_khi_khoi_phuc_$(date +%Y%m%d_%H%M%S).sql

# 2. Khôi phục vào CSDL MỚI, không đè lên cái đang có.
docker exec -e PGPASSWORD=$PGPASS <container> psql -U pharma -d postgres \
  -c 'CREATE DATABASE pharmacy_os_restored'
docker exec -i -e PGPASSWORD=$PGPASS <container> \
  psql -U pharma -d pharmacy_os_restored -v ON_ERROR_STOP=1 < <ban_backup>.sql

# 3. Đối chiếu TRƯỚC khi chuyển sang dùng (xem A.2 bước 6-8).
# 4. Chỉ khi cả 3 phép đối chiếu đạt: trỏ DB__URL sang CSDL mới, khởi động lại app.
```

**`-v ON_ERROR_STOP=1` là bắt buộc.** Thiếu nó, `psql` chạy tiếp qua lỗi và trả mã thoát
**0** — bạn sẽ có một bản khôi phục thiếu dữ liệu kèm một dấu hiệu "thành công".

**Khôi phục vào CSDL mới, không đè.** Đè lên là bỏ mất khả năng so sánh khi phát hiện bản
backup cũng có vấn đề, và biến một sự cố khôi phục được thành một sự cố mất dữ liệu.

### A.4 🔒 D-OPS-01 — quyết định Chain KHOÁ 2026-07-28

```
DECISION: RPO ≤ 1 giờ cho pilot
STATUS:   LOCKED
```

**Quyết định kinh doanh, chép nguyên văn:** *"Pilot chấp nhận mất tối đa khoảng 1 giờ
dữ liệu trong kịch bản thảm họa."*

| Điều kiện Chain đặt | Thực hiện ở đâu |
|---|---|
| Backup tự động **mỗi 1 giờ** | `scripts/backup_verify.sh` + cron `0 * * * *` |
| Giữ `pg_dump` trước mỗi migration làm **điểm backup bổ sung** | Full-auto điều 6, không đổi |
| Retention **30 ngày** | `RETENTION_DAYS=30`; xoá bản cũ **sau** khi bản mới đã kiểm chứng đạt |
| **Phát hiện + cảnh báo** khi backup hỏng | `trap ... ERR` → `ALERT_CMD`; mọi nhánh hỏng thoát khác 0 |
| **Không coi backup là DONE chỉ vì file dump được tạo** | Bước 3 của script: **khôi phục thật** vào CSDL tạm rồi đối chiếu |
| Phải có **restore verification** | Đối chiếu số bảng · số index · revision alembic; lệch ⇒ báo động, thoát 1 |

**RPO thấp hơn 1 giờ là quyết định MỚI**, không phải chỉnh tham số: nó có thể đòi chuyển
sang WAL/PITR hoặc kiến trúc backup khác. Không tự hạ xuống.

#### `scripts/backup_verify.sh` — đã chạy thử cả hai nhánh (2026-07-28)

| Nhánh | Lệnh | Kết quả |
|---|---|---|
| **Thành công** | `BACKUP_DIR=… ./scripts/backup_verify.sh` | `EXIT=0` · dump 116 KB · gốc `49\|164\|0033…` = khôi phục `49\|164\|0033…` ⇒ **kiểm chứng ĐẠT** · dọn theo retention |
| **Hỏng** | `PG_DB=khong_ton_tai_dau …` | `EXIT=1` · **ALERT bắn**: *"BACKUP THẤT BẠI … tại dòng 59"* · CSDL tạm **đã dọn** (0 dòng còn lại) |

Nhánh hỏng được kiểm **có chủ đích**: một script backup chỉ báo khi thành công là một
script không ai biết nó đã chết từ bao giờ.

### A.5 Nợ của phần A — ghi rõ

| Nợ | Vì sao chưa làm |
|---|---|
| ✅ **Dead-man's switch** | **ĐÃ CÓ (2026-07-28)** — `scripts/backup_deadman.sh`, chạy lệch 15 phút (`15 * * * *`) so với backup. Script **riêng** chứ không thêm vào `backup_verify.sh`: thứ giám sát nằm bên trong thứ nó giám sát thì im lặng cùng lúc với nó. Chỉ nhìn dấu vết trên đĩa, kiểm 3 điều theo thứ tự nghiêm trọng — chưa có bản nào · bản mới nhất quá cũ (>90 phút = RPO 1 giờ + dung sai) · bản mới nhất rỗng bất thường. **Đã kiểm chứng 5/5 ca theo kỷ luật #14** (4 ca hỏng đỏ đúng chỗ, 1 ca hợp lệ xanh) — và chính lần kiểm đó **bắt được một bug thật**: `local msg="…$msg"` tự tham chiếu dưới `set -u` làm cảnh báo mất sạch nội dung trong khi mã thoát vẫn đúng bằng 1. ⚠️ Giới hạn khai rõ: chạy bằng cron thì **chính nó cũng im lặng được** — đặt `PING_URL` trỏ vào dịch vụ ngoài (healthchecks.io/Uptime Kuma) mới đóng hẳn lỗ hổng |
| Diễn tập ở quy mô thật (CSDL **GB**, không phải 12 MB) | Chưa có deployment thật. **2 giây không suy ra được** thời gian khôi phục ở quy mô pilot sau vài tháng |
| Chưa diễn tập với **CSDL đã bật mã hoá** | Xem phần B — bật mã hoá xong **phải diễn tập lại**, vì backup **không kèm khoá** là vô dụng |

---

## PHẦN B — BẬT MÃ HOÁ AT-REST LẦN ĐẦU (F-8)

### B.1 Vì sao mục này thành bắt buộc

F-2 (2026-07-27) làm prod **từ chối khởi động** khi `ENCRYPTION__ENABLED=false`. Nên bật
mã hoá không còn là lựa chọn của deployment — nó là điều kiện để ứng dụng chạy được ở prod.

### B.2 🔴 Đọc trước khi làm bất cứ bước nào

**Mất khoá = mất dữ liệu vĩnh viễn.** Không có `git revert` nào cứu được: cột đã mã hoá
trở thành không đọc lại được, mãi mãi.

Ba quy tắc, không có ngoại lệ:

1. **Sao lưu khoá TÁCH RIÊNG khỏi bản dump CSDL.** Để chung một chỗ thì mất một lần là
   mất cả hai, và lúc đó bản backup chỉ còn là một file rác có kích thước.
2. **Diễn tập khôi phục THÀNH CÔNG trước khi bật** ở bất kỳ nơi nào có dữ liệu thật
   (phần A). Sau khi bật, một bản backup **không kèm khoá** là vô dụng.
3. **Không commit, không đặt cạnh file backup, không ghi vào log.**

### B.3 Trình tự bật trên deployment ĐÃ CÓ DỮ LIỆU

```bash
# 1. Sao lưu, cất RIÊNG. Đây là điểm quay lui duy nhất.
pg_dump … > ~/truoc_khi_bat_mahoa_$(date +%Y%m%d).sql

# 2. Sinh khoá (KHÔNG chạy trên máy chung, không dán vào chat)
python -c "from pharmacy_os.core.security.crypto import generate_key, encode_key; print(encode_key(generate_key()))"
#    Sinh HAI khoá: một cho ENCRYPTION__KEYS, một RIÊNG cho ENCRYPTION__BLIND_INDEX_KEY.
#    Một khoá một mục đích — yếu ở chỗ này không được kéo theo chỗ kia.

# 3. Nới cột (KHÔNG đụng dữ liệu)
alembic upgrade head

# 4. Đặt khoá + bật, khởi động lại
#    ENCRYPTION__KEYS={"1": "<base64>"}
#    ENCRYPTION__CURRENT_VERSION=1
#    ENCRYPTION__BLIND_INDEX_KEY=<base64 khác>
#    ENCRYPTION__ENABLED=true

# 5. Đếm trước khi ghi
python -m seeds.encrypt_backfill --dry-run

# 6. Mã hoá dữ liệu cũ (chạy được khi ứng dụng đang sống)
python -m seeds.encrypt_backfill

# 7. BẮT BUỘC trước khi xoá backup
python -m seeds.encrypt_backfill --verify

# 8. Diễn tập khôi phục LẠI (phần A) trên bản backup mới, có khoá.
#    Bước này không được bỏ: từ giờ backup và khoá là MỘT cặp, và cặp đó chưa ai thử.
```

**Vì sao đọc vẫn chạy được suốt quá trình:** tầng đọc xử lý **cả hai dạng** (đã mã hoá và
chưa), nên backfill chạy được khi ứng dụng đang phục vụ. Đó là chủ đích, không phải may mắn.

### B.4 Xoay khoá — quyết định thao tác

**Nguyên tắc:** xoay = **thêm** phiên bản mới rồi trỏ `CURRENT_VERSION` sang nó. **Không**
mã hoá lại toàn bộ, **không** xoá khoá cũ.

```
ENCRYPTION__KEYS={"1": "<khoá cũ>", "2": "<khoá mới>"}
ENCRYPTION__CURRENT_VERSION=2
```

Ghi mới dùng v2; dòng cũ mang thẻ `v1:` vẫn đọc được bằng khoá v1.

```
DECISION: Chu kỳ xoay khoá tiêu chuẩn 90 ngày
STATUS:   LOCKED (Chain, 2026-07-28)
```

**Chain ghi rõ: đây KHÔNG phải nghĩa vụ pháp lý** — là quyết định bảo mật/rủi ro/vận hành.
Đừng trích nó như một yêu cầu luật định ở bất kỳ đâu.

| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Bao lâu xoay một lần? | 🔒 **90 ngày** | Chain khoá 2026-07-28 |
| Khoá cũ và mới chồng lấn bao lâu? | 🔒 **tối đa 7 ngày** | Để token/session **đang hợp lệ** không bị cắt giữa chừng. Kiến trúc đã đỡ được: nhiều phiên bản khoá sống song song, mỗi ciphertext mang thẻ `v1:`/`v2:` |
| Xoay có cần vết kiểm toán không? | 🔒 **CÓ, bắt buộc** | Xoay khoá là thao tác chạm toàn bộ dữ liệu nhạy cảm; không có vết thì không ai trả lời được *"khoá này đổi lúc nào, ai đổi"* |
| Có được hard-code khoá vào mã nguồn/repo? | 🔒 **TUYỆT ĐỐI KHÔNG** | |
| Có xoá khoá cũ không? | **KHÔNG**, chừng nào còn dòng mang thẻ phiên bản đó | Xoá là làm mất khả năng đọc chính dữ liệu của mình. `encrypt_backfill` báo rõ *"thiếu khoá v mấy"* |
| Có mã hoá lại dòng cũ sang khoá mới không? | **Không bắt buộc** | Chỉ cần khi nghi khoá cũ đã lộ — lúc đó là **sự cố bảo mật**, chạy theo `docs/17`, không phải thao tác định kỳ |
| Khi nào bắt buộc xoay ngay? | **Nghi khoá lộ** — người có quyền truy cập rời tổ chức, khoá từng nằm ở nơi không đảm bảo | Đây là ca duy nhất phải mã hoá lại toàn bộ |

### B.5 ✅ Trình tự B.3 ĐÃ CHẠY HẾT trên staging — 2026-07-28

Chạy trên `docker-compose.staging.yml`, CSDL `pharmacy_os_staging` **có dữ liệu**, đúng
kịch bản *"bật mã hoá trên deployment đã có dữ liệu"* (khởi động với `ENCRYPTION__ENABLED=false`,
dựng tenant + 25 dòng PII nguyên văn, rồi mới bật).

| Bước | Kết quả đo |
|---|---|
| 1. `pg_dump` trước khi bật | `EXIT=0` · 88 KB |
| 3. `alembic upgrade head` | `EXIT=0` · chạy tới `0033_movement_ref_batch_uq` |
| 4. Đặt khoá + `ENCRYPTION__ENABLED=true` + khởi động lại | app trả `HEALTH=200` |
| 5. `--dry-run` | `EXIT=0` · **quét 25, sẽ ghi lại 25** |
| 6. `encrypt_backfill` | `EXIT=0` · **quét 25, đã ghi lại 25** |
| 7. `--verify` | `EXIT=0` · **25 dòng, 0 lỗi giải mã** ⇒ *"Mọi dòng đọc được bằng khoá hiện có"* |
| 8. Diễn tập khôi phục **lại** (bắt buộc sau khi bật) | `scripts/backup_verify.sh` `EXIT=0` · kiểm chứng ĐẠT · **25/25 dòng vẫn mang thẻ `v1:`** |

**Bằng chứng mã hoá thật sự xảy ra**, đọc thẳng từ CSDL sau backfill:

```
trước:  Nguyen Van PII 8 | 0900000001
sau:    Nguyen Van PII 8 | v1:gvbR1XOuHxOmMySgy…
```

🔴 **Quan sát cần Chain/kiến trúc xác nhận, KHÔNG tự kết luận:** `phone` đã thành
ciphertext mang thẻ `v1:`, nhưng **`full_name` vẫn nguyên văn**. Có thể là chủ đích (tên
cần cho hiển thị/tra cứu) — nhưng tên người **là dữ liệu cá nhân** theo Luật BVDLCN
91/2025. Cần một câu trả lời rõ: cột nào bắt buộc mã hoá, cột nào cố ý không, và vì sao.
**Chưa có tài liệu nào trong repo nói ra lựa chọn đó.**

### B.6 🔴 Nợ còn lại của phần B

| Nợ | Trạng thái |
|---|---|
| Xoay khoá B.4 | **Chưa diễn tập.** Quy tắc đã rõ, thao tác thật thì chưa |
| Phạm vi cột được mã hoá | 🔴 **Chưa có tài liệu.** `phone` mã hoá, `full_name` không — cần xác nhận đây là lựa chọn hay lỗ hổng |
| Chu kỳ xoay khoá | 🔒 **Đã khoá: 90 ngày** (D-SEC-01) |
| ✅ **Vết kiểm toán cho thao tác xoay khoá** | **ĐÃ CÓ (2026-07-28).** `AuditAction.ENCRYPTION_KEY_ROTATED` + lệnh `python -m seeds.record_key_rotation --from-version N --to-version M --operator-email … --reason …`. Lệnh **đọc cấu hình đang chạy** và **từ chối ghi** nếu: `current_version` chưa trỏ sang phiên bản mới (ghi trước việc chưa làm) · thiếu khoá cũ hoặc mới trong keyring · hai phiên bản trùng nhau · người thực hiện không có trong CSDL. Ghi kèm `keys_in_ring` — con số trả lời được câu *"còn bao nhiêu phiên bản đang chồng lấn"* mà D-SEC-01 giới hạn 7 ngày. 4 test canh, đã kiểm chứng có răng theo kỷ luật #14 (gỡ hết kiểm chứng ⇒ 3/4 đỏ) |
| 🔴 **Cưỡng chế chồng lấn ≤ 7 ngày** | **Chưa có.** Kiến trúc cho nhiều khoá sống song song **vô thời hạn**; giới hạn 7 ngày hiện là **kỷ luật của người vận hành**, không phải thứ hệ thống ép |

**Điều kiện đóng F-8 hoàn toàn:** chạy hết B.3 trên **staging có dữ liệu**, rồi diễn tập
lại phần A trên bản backup sau khi đã bật mã hoá. Chừng đó chưa làm thì tài liệu này là
**kế hoạch đã kiểm từng phần**, chưa phải **quy trình đã chạy** — và tài liệu này nói rõ
mình đang ở đâu thay vì để người đọc tự suy.
