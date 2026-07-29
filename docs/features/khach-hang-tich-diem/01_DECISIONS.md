# Khách hàng & Tích điểm — Bước 0-3 của `docs/14_FEATURE_PROCESS.md`

> **Trạng thái: BƯỚC 0-3 XONG · GIAI ĐOẠN A+B ĐƯỢC MỞ · GIAI ĐOẠN C BỊ CHẶN.**
> **CHƯA CODE MỘT DÒNG NÀO.** GĐ soạn dưới uỷ quyền của Chain 2026-07-29.
>
> 🔴 **Blocker pháp lý chưa gỡ được — đọc Bước 1 mục 1 trước khi duyệt bất cứ gì.**
> Kho `docs/legal/` **không có Luật Thương mại 2005 và NĐ 81/2018/NĐ-CP về khuyến
> mại** — đúng hai văn bản quyết định việc **đổi điểm lấy ưu đãi trên thuốc** có
> hợp pháp hay không. Theo quy tắc R-10 (Chain chốt 2026-07-26): thiếu văn bản ở
> bất kỳ tầng nào ⇒ ghi **"chưa kết luận được"**, KHÔNG ghi "không áp dụng" và
> cũng KHÔNG ghi "bị cấm".

---

## Bước 0 — Đích (DoD ngược)

**Khi xong, người dùng làm được gì:**

| | Việc |
|---|---|
| 1 | Ở màn Bán hàng, gõ số điện thoại là ra khách quen — **không phải rời màn** để tra |
| 2 | Gắn khách vào hoá đơn, xem được **lịch sử mua** của khách đó |
| 3 | Thấy **số điểm** khách đang có, và điểm tăng lên sau mỗi lần mua |
| 4 | Xem **sổ điểm** của một khách: mỗi dòng là một lần cộng/trừ, có mã hoá đơn đối chiếu |

**Bằng chứng tuân thủ khi bị hỏi:**

| Câu hỏi của đoàn kiểm tra | Bằng chứng hệ thống đưa ra |
|---|---|
| "Ai đồng ý cho các anh lưu thông tin người này?" | `CustomerConsent` — mục đích, phiên bản điều khoản, thời điểm, tài khoản nhân viên, IP. Append-only, trả lời được *"ngày đó có đồng ý không"* |
| "Khách rút lại đồng ý thì sao?" | Một dòng consent mới `granted=false`; điểm **đóng băng**, hồ sơ khử nhận dạng qua `POST /customers/{id}/anonymise` đã có |
| "Sổ điểm có lộ người này mua thuốc gì không?" | **Không.** Sổ điểm chỉ mang `order_id` + số tiền + số điểm. **Không có `drug_id`** — xem quyết định Đ-3 |
| "Điểm có bị sửa tay không?" | Sổ điểm **append-only**, sửa sai bằng **bút toán đảo**, không UPDATE. Cùng khuôn `ControlledLedgerEntry` |

---

## Bước 1 — Checklist Compliance by Design / Privacy by Design

### 1. Căn cứ pháp lý — 🔴 **CHẶN MỘT PHẦN**

| Phần | Căn cứ | Kết luận |
|---|---|---|
| Lưu **tên + SĐT** khách để nhận diện trên hoá đơn | Luật 91/2025 Điều 9 (đồng ý theo từng mục đích) — **đã có** trong kho, `ConsentPurpose.BASIC` đã cài | ✅ Có căn cứ |
| Gắn khách vào hoá đơn, xem lịch sử mua | Như trên + `sales.customer_id` **đã tồn tại** trong domain | ✅ Có căn cứ |
| **Cộng điểm** theo giá trị đơn hàng | Đây là ghi nhận nội bộ, chưa phải hành vi thương mại với bên thứ ba | 🟡 **Chưa kết luận được** — nghiêng về được, nhưng xem mục 1b |
| **Đổi điểm lấy giảm giá / quà / thuốc** | **THIẾU VĂN BẢN** | 🔴 **CHƯA KẾT LUẬN ĐƯỢC** |

**1b. Vì sao phần đổi điểm bị chặn.** Đổi điểm lấy ưu đãi là một hình thức **khuyến
mại**. Nghĩa vụ và giới hạn của khuyến mại nằm ở **Luật Thương mại 2005** (chương
khuyến mại, gồm các hành vi bị cấm) và **NĐ 81/2018/NĐ-CP** hướng dẫn. **Cả hai đều
không có trong `docs/legal/`.** Ngoài ra Luật Dược 105/2016 Điều 6 liệt kê các hành
vi bị nghiêm cấm trong kinh doanh dược, và bản `SUMMARY.md` hiện có **không tóm hết
Điều 6** — mới trích Điều 6.5.h.

Ba câu hỏi phải trả lời **bằng văn bản, không bằng suy luận**:

| | Câu hỏi | Vì sao quan trọng |
|---|---|---|
| Q-1 | Thuốc có thuộc nhóm hàng hoá/dịch vụ **bị cấm dùng để khuyến mại** hoặc **bị cấm khuyến mại** không? | Nếu có, giai đoạn C **không được làm**, không phải "làm rồi tắt cờ" |
| Q-2 | Nếu được, có phải **thông báo/đăng ký** với Sở Công Thương trước mỗi chương trình không? | Quyết định phần mềm có phải sinh hồ sơ chương trình hay không |
| Q-3 | Có **hạn mức giá trị** ưu đãi (thường nghe là 50% giá trị hàng hoá) không? | Quyết định có phải cài ràng buộc chặn cứng trong domain |

> ⚠️ Ba câu trên **không phải việc của Trợ lý Code**. Chuyển **Trợ lý Pháp Lý**
> (`BeraLLC/PhapLy/`), kèm yêu cầu bổ sung 2 văn bản vào `docs/legal/`.
> Theo R-10: đọc đủ **Luật → Nghị định → Thông tư** rồi mới kết luận.

**Hệ quả thiết kế:** tách làm **ba giai đoạn**, giai đoạn C nằm sau một cờ mặc định
TẮT và **không có giao diện** cho tới khi Q-1..Q-3 có câu trả lời. Đúng tiền lệ đã
giữ: *giữ điều chưa xác nhận ở dạng cờ, không chuyển thành khẳng định*.

### 2. Đồng ý — **CẦN**, và cần một mục đích MỚI

`ConsentPurpose` hiện có đúng 2 mức: `BASIC` (tên, SĐT) và `HEALTH` (dị ứng, bệnh
nền, lịch sử dùng thuốc). **Tích điểm không thuộc mức nào.**

- Không phải `BASIC`: `BASIC` là để *nhận diện người mua trên hoá đơn*. Tích điểm
  là **mục đích khác** — theo dõi hành vi mua để thưởng. Luật 91/2025 Điều 9 đòi
  đồng ý **theo từng mục đích riêng**; gộp vào `BASIC` là lấy đồng ý cho việc A rồi
  dùng cho việc B.
- Không phải `HEALTH`: không đụng dữ liệu sức khoẻ (nhờ quyết định Đ-3 bên dưới).

⇒ **Thêm `ConsentPurpose.LOYALTY`.** Rút lại được, và rút lại thì **đóng băng điểm**
chứ không xoá — số dư là **nghĩa vụ của nhà thuốc với khách**, xoá đi là tự ý huỷ
quyền lợi của họ. Xoá hẳn chỉ khi khách yêu cầu xoá dữ liệu (Điều 13, 14).

> 🔴 Ghi chú cho người cài đặt: bản thân việc **thêm một giá trị enum consent** là
> thay đổi có ảnh hưởng pháp lý, không phải refactor. Phải có **phiên bản điều
> khoản mới** (`terms_version`) — đồng ý cũ không tự động phủ mục đích mới.

### 2b. 🔴 Đ-4 · Khách tự đưa số điện thoại ở quầy = đồng ý mục đích `BASIC`

**Chain chốt 2026-07-29.** Khi thu ngân hỏi *"cho em xin số điện thoại"* và khách
**đọc số**, đó là **hành vi khẳng định, tự nguyện, cho một mục đích đã nói rõ**.
Không cần thêm một hộp thoại nữa để bấm.

**Vì sao chấp nhận được về pháp lý:** Điều 9 cấm coi **im lặng** là đồng ý. Đây
không phải im lặng — khách chủ động đưa dữ liệu sau khi được hỏi. Bằng chứng vẫn
đủ bốn thứ Điều 9 đòi: **thời điểm** (lúc lập đơn), **ai ghi** (tài khoản thu ngân),
**từ đâu** (IP máy quầy), **theo điều khoản nào** (`terms_version`).

**🔴 CHỈ ÁP CHO `BASIC`, DỪNG ĐÚNG Ở ĐÓ.** Đưa số điện thoại để ghi lên hoá đơn
**không phải** đồng ý cho theo dõi lịch sử mua (`LOYALTY`), càng không phải đồng ý
lưu dị ứng/bệnh nền (`HEALTH`). Suy rộng ra hai mục kia chính là lỗi *"lấy đồng ý
cho việc A rồi dùng cho việc B"* mà toàn bộ mục 2 dựng lên để tránh — và nó sẽ
**trông rất hợp lý** lúc làm, vì đằng nào cũng chỉ là một số điện thoại.

**Ghi lại NGUỒN GỐC, không chỉ ghi "đã đồng ý".** Câu đoàn kiểm tra hỏi không phải
*"có đồng ý không"* mà *"đồng ý đó lấy thế nào"*. Hai nguồn khác hẳn nhau về sức
nặng:

| Nguồn | Nghĩa |
|---|---|
| `COUNTER` | Khách tự đọc số ở quầy khi được hỏi (Đ-4) |
| `EXPLICIT` | Nhân viên đọc nội dung rồi bấm thay khách trên bảng đồng ý |

⇒ Thêm trường `basis` vào `CustomerConsent`. Không nhét vào `terms_version` — trường
đó có nghĩa riêng, mượn tạm là làm hỏng cả hai.

**Không tự tạo hồ sơ khi khách KHÔNG đưa số.** Bán hàng không cần khách hàng; ô số
điện thoại để trống thì bán bình thường, không tạo hồ sơ nào.

### 3. Phân loại dữ liệu

| Dữ liệu | Phân loại | Ghi chú |
|---|---|---|
| Tên, SĐT, số dư điểm | Dữ liệu cá nhân **thường** | |
| Sổ điểm (`order_id`, số tiền, số điểm) | Thường — **nhờ Đ-3** | Nếu có `drug_id` thì thành **nhạy cảm** ngay |
| Liên kết khách ↔ hoá đơn | 🟡 **Suy ra được dữ liệu sức khoẻ** | Hoá đơn có dòng thuốc; nối với tên khách là ra hồ sơ bệnh. **Đã nhạy cảm sẵn**, không phải cái tính năng này tạo ra — nhưng tính năng này làm nó **dễ tra hơn** ⇒ RBAC ở mục 5 |

### 4. Audit log bất biến

Sổ điểm **là** một sổ append-only, theo đúng khuôn `ControlledLedgerEntry` đã có.
Không UPDATE, không DELETE. Sai thì ghi **bút toán đảo** có lý do và người thực hiện.
Ngoài ra mọi thao tác cộng/trừ điểm ghi `AuditEntry` như các module khác.

### 5. Phân quyền (RBAC)

RBAC nay là **JWT thật** (module `iam`, từ 2026-07-23) — không còn dev-header tạm,
nên điều kiện tiên quyết của `docs/14` đã thoả. Quyền mới:

| Quyền | Ai | Vì sao tách |
|---|---|---|
| `crm.loyalty.read` | Thu ngân, dược sĩ | Xem số dư để nói với khách |
| `crm.loyalty.adjust` | **Chỉ quản lý** | Cộng/trừ tay là **cửa gian lận trực tiếp ra tiền**. Không gộp vào `crm.create` |
| `crm.purchase_history.read` | **Chỉ dược sĩ + quản lý** | Lịch sử mua **suy ra được bệnh** (mục 3). Thu ngân không cần |

🔴 **`crm.read` hiện tại quá rộng để dùng lại.** Nó đang gộp mọi thứ đọc của CRM.
Không mở rộng nó — thêm quyền hẹp, đúng kỷ luật đã dùng cho `audit.dashboard.read`
tách khỏi `audit.read` (§7al).

### 6. Truy xuất, sao lưu, phục hồi

Bảng mới (`loyalty_ledger`, `loyalty_balance`) nằm trong cùng CSDL ⇒ `pg_dump` hiện
có phủ. **Phải xác nhận bằng lệnh thật sau migration**, không tin suy luận này.

### 7. AI

Tính năng này **không dùng LLM**. Không có gì để rà. Nếu sau này gợi ý "khách này
nên nhắc mua lại" thì đó là **tính năng mới**, qua lại `docs/14` từ đầu.

### 8. Rà theo từng văn bản

| Văn bản | Có trong kho | Trạng thái |
|---|---|---|
| Luật 91/2025 (BVDLCN) | ✅ | Đã rà — mục 2, 3 |
| NĐ 356/2025 | ✅ | Đã rà — phân loại nhạy cảm |
| Luật Dược 105/2016 | ✅ nhưng SUMMARY **chưa tóm hết Điều 6** | 🟡 Phải bổ sung trước khi mở giai đoạn C |
| Luật 44/2024 | ✅ | Không đụng tích điểm |
| **Luật Thương mại 2005** | 🔴 **THIẾU** | Chặn giai đoạn C |
| **NĐ 81/2018/NĐ-CP** | 🔴 **THIẾU** | Chặn giai đoạn C |

---

## Bước 2 — Rà chồng lấn với module đã có

| Khái niệm định làm | Đã có chưa | Quyết định |
|---|---|---|
| Hồ sơ khách hàng | ✅ `crm.Customer` — đủ tên, SĐT, ngày sinh, dị ứng, bệnh nền, consent, khử nhận dạng | **DÙNG LẠI**, không tạo entity mới |
| Đồng ý theo mục đích | ✅ `CustomerConsent` append-only | **DÙNG LẠI**, chỉ thêm một giá trị enum |
| Khách trên hoá đơn | ✅ `sales.SalesOrder.customer_id` đã có sẵn | **DÙNG LẠI** — hoá ra nền đã có, chỉ thiếu giao diện |
| Tra khách theo SĐT | 🔴 Chưa có endpoint tìm kiếm | Thêm `GET /customers?search=` |
| Số dư điểm, sổ điểm | 🔴 **Không tồn tại** — `grep` "loyalty/tích điểm" ra **0 kết quả nghiệp vụ** trong `modules/` | Tạo mới |
| Sổ append-only | ✅ có khuôn `ControlledLedgerEntry` | **DÙNG LẠI KHUÔN**, không phát minh lại |

`docs/08_MODULES.md` ghi loyalty thuộc trách nhiệm `crm`, `docs/01_ANALYSIS.md` ghi
`FR-CRM-3: Điểm thưởng / loyalty (tùy chọn)`. ⇒ **Đặt trong `crm`, không mở module
mới.** Điểm là thuộc tính của quan hệ với khách, không phải một nghiệp vụ riêng.

### Ba quyết định thiết kế đáng ghi

**Đ-1 · Điểm tính trên TIỀN, không trên MẶT HÀNG.** Cộng theo giá trị đơn. Không có
bảng "thuốc này ×2 điểm" — cái đó biến điểm thành công cụ **đẩy một loại thuốc cụ
thể**, tức là đúng thứ Q-1 đang hỏi có bị cấm không. Tránh hẳn cho tới khi có văn bản.

**Đ-2 · Thuốc kê đơn (ETC) — mặc định KHÔNG tính điểm.** Thưởng cho việc mua thuốc
kê đơn dễ bị đọc là **khuyến khích dùng thuốc kê đơn**. Có cờ để bật, **mặc định
tắt**, và bật là **quyết định của Chain sau khi Pháp Lý trả lời**, không phải mặc
định kỹ thuật. Chọn hướng an toàn khi chưa biết.

**Đ-3 · 🔴 Sổ điểm KHÔNG mang `drug_id`.** Chỉ `order_id` + số tiền + số điểm. Đây
là quyết định **quan trọng nhất về quyền riêng tư** của cả tính năng: nếu sổ điểm
mang mã thuốc, thì một bảng vốn để đếm điểm trở thành **hồ sơ bệnh án** — người có
quyền xem điểm (thu ngân) đọc được bệnh của khách. Cần chi tiết thì đi qua
`order_id` và **chịu kiểm quyền của module `sales`**, không đi tắt.

---

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module

| Bước | Module | Cross-module? | Model |
|---|---|---|---|
| A1 | `crm` — thêm `ConsentPurpose.LOYALTY`, tìm khách theo SĐT | Không | Sonnet |
| A2 | `crm` — giao diện màn Khách hàng: tìm, tạo, xin đồng ý tường minh | Không | Sonnet |
| B1 | `crm` — domain điểm: số dư, sổ append-only, bút toán đảo | Không | Sonnet |
| B2 | `crm` — app + infra + migration (2 bảng, 3 quyền) | Không | Sonnet |
| B3 | 🔴 **`sales` → `crm`**: bán xong thì cộng điểm | **CÓ** | **Opus, phiên riêng** |
| B4 | `crm` — interface + giao diện điểm trên màn Bán hàng | Không | Sonnet |
| C | Đổi điểm | — | **CHẶN — không mở** |

**Tổng số bước: 6** (A1, A2, B1, B2, B3, B4). Chốt trước, không dùng mẫu số mở
(kỷ luật #12).

### 🔴 B3 là bước nguy hiểm nhất

`sales` **không được** import `crm` trực tiếp — 18 contract import-linter chặn.
Nối qua **sự kiện + composition root**, đúng tiền lệ `GoodsReceived → inventory`
(`api/v1/cross_module.py`). Bốn rủi ro phải xử lý ngay từ thiết kế:

| | Rủi ro | Vì sao gắt |
|---|---|---|
| R-1 | **Cộng điểm hai lần** khi sự kiện được gửi lại | Đơn hàng có `client_uuid` chống trùng; sổ điểm phải có **khoá duy nhất trên `order_id`**, giống cách `inventory` chống `GoodsReceived` trùng |
| R-2 | **Cộng điểm cho đơn đã huỷ** | Huỷ đơn phải sinh **bút toán đảo**, không xoá dòng cũ |
| R-3 | **Cộng điểm khi khách chưa đồng ý** `LOYALTY` | Kiểm consent tại thời điểm cộng, không tại thời điểm tạo hồ sơ |
| R-4 | Bán hàng **hỏng vì** cộng điểm lỗi | Cộng điểm là **việc phụ**. Lỗi ở đó **không được** làm hỏng giao dịch bán. Phải đi qua outbox như các phản ứng cross-module khác |

R-4 là rủi ro dễ bị xem nhẹ nhất và đắt nhất: một lỗi ở tính năng thưởng làm quầy
không bán được hàng.

---

## Bước 4 — Trước khi mở sprint

- [ ] Chain duyệt Bước 0-3 này
- [ ] **Trợ lý Pháp Lý trả lời Q-1..Q-3** + bổ sung 2 văn bản vào `docs/legal/`
- [ ] Chain quyết Đ-2 (ETC có tính điểm không) sau khi có câu trả lời
- [ ] Cập nhật `ROADMAP.md` + `PROJECT_STATE.md`

**Giai đoạn A và B mở được NGAY** — không phụ thuộc Q-1..Q-3, vì chưa có ưu đãi nào
được trao. **Giai đoạn C chỉ mở sau khi có văn bản.**
