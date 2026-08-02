# Uỷ quyền quản trị + bộ quyền bảo trì sâu — ĐỀ XUẤT, CHƯA DUYỆT

- **Ngày:** 2026-08-03
- **Người yêu cầu:** Chain — *"Khi chủ chuỗi uỷ quyền, thì ngoài các quyền quản trị hệ thống
  thì có đầy đủ như chủ quầy, ngoài ra còn có các quyền cài đặt, sửa lỗi, bảo trì phần mềm
  can thiệp sâu. GĐ đề xuất phần này dựa trên kinh nghiệm lâu năm làm bảo trì, nâng cấp phần mềm."*
- **Trạng thái:** `docs/14_FEATURE_PROCESS.md` **Bước 0–3**, chờ Chain duyệt trước khi code

## Bước 0 — Đích

Một người bảo trì phần mềm phải **sửa được máy** mà **không mặc nhiên đọc được hồ sơ bệnh
nhân**; và khi công việc thật sự cần chạm dữ liệu thì phải có **một hành vi uỷ quyền có thể
chỉ tên, có hạn, và để lại vết**.

🔴 Chain bác phương án "cắt quyền" mà tôi đưa ban đầu, và bác đúng. Lý do tôi ghi lại để phiên
sau không đề xuất lại: **một người bảo trì bị cắt quyền đọc dữ liệu sẽ không sửa được phần lớn
lỗi thật.** Lỗi nghiêm trọng của phần mềm nhà thuốc hầu như luôn có dạng *"đơn hàng này tính
sai tiền"*, *"khách này hiện nhầm dị ứng"* — tức là **gắn với một bản ghi cụ thể**. Bắt người
sửa làm việc mù rồi họ sẽ đi đường vòng: mở `psql` xem thẳng CSDL, nơi **không có vết kiểm
toán nào**. Một quyền bị cắt mà người ta đi vòng được là **tệ hơn** một quyền được cấp có ghi
vết — đó là bài học chung của mọi hệ có "tài khoản kỹ thuật".

Nên đích không phải *ít quyền hơn*, mà là: **quyền cao nhất phải là quyền đắt nhất để dùng.**

## Bước 1 — Ba tầng, thay cho một vai duy nhất

| Tầng | Ai | Có gì | Lấy bằng cách nào |
|---|---|---|---|
| **T1 — Kỹ thuật** | người bảo trì, mặc định | 31 quyền kỹ thuật đã có + **bộ bảo trì mới** (Bước 2) | gán vai, thường trực |
| **T2 — Nghiệp vụ uỷ quyền** | cùng người đó, khi cần | **đầy đủ như chủ quầy** (25 quyền dữ liệu) | **chủ chuỗi uỷ quyền**, có hạn giờ, ghi vết |
| **T3 — Hành vi pháp lý** | **không bao giờ** uỷ quyền được | `compliance.ledger.sign` | chỉ người có Chứng chỉ hành nghề dược |

**T3 là ranh giới cứng và tôi đề nghị không thoả hiệp.** Ký sổ thuốc kiểm soát đặc biệt là
hành vi của **người chịu trách nhiệm chuyên môn dược** — nó gắn với chứng chỉ hành nghề của
một con người, không gắn với một vai trong phần mềm. Hôm nay `system_admin` ký được, và đó là
lỗi thiết kế chứ không phải tiện nghi: chữ ký ấy đi vào một **sổ pháp lý**, và nếu thanh tra
hỏi *"ai ký"* thì câu trả lời phải là một dược sĩ có tên, không phải "tài khoản kỹ thuật".

## Bước 2 — Bộ quyền BẢO TRÌ SÂU (mới, chưa tồn tại)

Đây là phần Chain giao tôi đề xuất. Nguyên tắc chọn: **mỗi quyền phải trả lời được một tình
huống hỏng có thật đã gặp**, không phải một khả năng nghe hay.

| Quyền đề xuất | Tình huống thật nó giải | Vì sao hôm nay phải mở `psql` |
|---|---|---|
| `maint.job.run` | Chạy lại một tác vụ nền đã chết (outbox relay, retry DAV, backfill) | Hôm nay phải `docker exec` + gõ Python |
| `maint.outbox.inspect` | Sự kiện kẹt trong `event_outbox` — xem cái gì kẹt, vì sao | Không có màn nào; phải `SELECT` |
| `maint.outbox.redrive` | Đẩy lại sự kiện kẹt sau khi đã sửa nguyên nhân | `UPDATE` tay, không vết |
| `maint.cache.clear` | Cấu hình đã đổi mà tiến trình còn giữ bản cũ | Phải khởi động lại cả app giữa giờ bán |
| `maint.config.read` | Xem **cấu hình đang chạy thật** (che bí mật) | Đọc `.env` — mà `.env` có thể khác thứ tiến trình đang giữ |
| `maint.migration.status` | Alembic đang ở revision nào, có lệch không | `alembic current` trên máy chủ |
| `maint.session.revoke` | Thu hồi phiên đăng nhập khi máy quầy mất | Chưa có; hôm nay chỉ đổi mật khẩu được |
| `maint.feature.toggle` | Tắt nhanh một tính năng đang gây lỗi, không cần deploy | Sửa `.env` + khởi động lại |
| `maint.diagnostics.read` | Đọc **mã sự cố → dòng log** (B1a) và số đo (B1b) qua giao diện | `grep` trên máy chủ |

**Bốn quyền cuối là thứ hôm nay không có bằng bất kỳ cách nào**, kể cả `psql`. Đó là dấu hiệu
chúng đáng làm: chúng không phải bản sao của một đường vòng, chúng là năng lực mới.

🔴 **Cái tôi cố ý KHÔNG đề xuất**, dù nghe hợp lý:
- **`maint.sql.run`** (chạy SQL tuỳ ý qua giao diện). Nó biến ứng dụng thành một cửa hậu
  hoàn chỉnh có sẵn xác thực. Ai cần chạy SQL thì dùng `psql` — chậm hơn, khó hơn, và **đó
  là điểm**: một việc nguy hiểm nên khó.
- **`maint.data.edit`** (sửa thẳng bản ghi). Sửa dữ liệu sai phải đi qua **nghiệp vụ** (huỷ
  đơn, điều chỉnh kiểm kê) để sổ sách khớp. Một nút "sửa thẳng" là cách chắc chắn nhất để
  tồn kho và sổ pháp lý lệch nhau mà không ai biết.

## Bước 3 — Cơ chế uỷ quyền T2

- **Chủ chuỗi bấm uỷ quyền**, chọn **thời hạn** (đề xuất mặc định **4 giờ**, tối đa 24) và
  **nêu lý do** — lý do là trường bắt buộc, không phải tuỳ chọn.
- Quyền T2 **tự hết hạn**. Không có bước "thu hồi" nào phải nhớ — thứ phải nhớ là thứ sẽ quên.
- Mỗi lần uỷ quyền ghi audit **hai đầu**: người cấp và người nhận.
- Trong thời gian uỷ quyền, **mọi lượt đọc dữ liệu nhạy cảm vẫn ghi `CUSTOMER_SENSITIVE_READ`**
  như hiện nay — uỷ quyền mở cửa, nó không tắt camera.
- Hết hạn ⇒ **thông báo cho chủ chuỗi** kèm số bản ghi đã đọc. Đây là chỗ cơ chế này thật sự
  có răng: không phải ở lúc cấp, mà ở lúc **báo cáo lại**.

🔴 **Giới hạn phải nói thẳng với Chain.** Ở quầy 650, Chain **vừa là chủ chuỗi vừa là quản trị
hệ thống** (Chain đã chốt giữ một tài khoản toàn quyền). Nên hôm nay việc uỷ quyền là **tự uỷ
quyền cho chính mình**, và giá trị của nó **không phải là sự hạn chế** — mà là **cái vết**.
Nó thành một biện pháp thật khi có người thứ hai: một nhà thuốc khách hàng, với BeraLLC là bên
bảo trì. Xây bây giờ vì lúc đó mới xây thì đã có dữ liệu thật của người khác nằm trong máy.

## Chưa trả lời được — cần Trợ lý Pháp Lý

`docs/legal/` **thiếu Nghị định hướng dẫn Luật BVDLCN 91/2025**. Ba câu chưa kết luận được,
và theo quy tắc R-10 tôi **không** kết luận từ suy đoán:

1. Uỷ quyền có hạn giờ **có đủ** làm cơ sở pháp lý cho việc một người ngoài chuyên môn dược
   đọc dữ liệu sức khoẻ không, hay còn cần đồng ý của chính bệnh nhân?
2. BeraLLC khi bảo trì cho nhà thuốc khách hàng là **bên xử lý dữ liệu** hay **bên kiểm soát
   chung**? Hai vai này có nghĩa vụ khác nhau.
3. Thời hạn lưu vết uỷ quyền — theo TT33/2025 (≥20 năm) hay theo luật dữ liệu cá nhân?

## Ước lượng

| Phần | Ước lượng | Ghi chú |
|---|---|---|
| T3 — gỡ `compliance.ledger.sign` khỏi `system_admin` | **nhỏ** | Sửa một dòng + test + kiểm CSDL đã có dữ liệu (kỷ luật #7) |
| Bộ quyền bảo trì (Bước 2) | **vừa**, chia được nhiều bước | Mỗi quyền một endpoint; làm dần theo mức hữu ích |
| Cơ chế uỷ quyền T2 | **lớn** — bảng mới, migration, màn hình, hết hạn nền | Cross-module `iam` ↔ audit |

**Đề nghị thứ tự:** T3 trước (nhỏ, đóng một lỗi thiết kế thật) → `maint.diagnostics.read` +
`maint.config.read` (nối vào B1a/B1b vừa dựng, dùng được ngay) → phần còn lại theo nhu cầu →
cơ chế uỷ quyền T2 khi có khách hàng đầu tiên ngoài BeraLLC.
