# Sổ quỹ tiền mặt — Bước 0-3 của `docs/14_FEATURE_PROCESS.md`

> **Trạng thái: BƯỚC 0-3 XONG, CHƯA CODE MỘT DÒNG NÀO** (2026-07-29).
> Sinh từ nhận xét của Chain sau demo Sprint 10: *"chưa thấy sổ quỹ, báo cáo và một
> số tính năng khác trong tiến trình."* Đúng — sổ quỹ **không tồn tại** ở bất kỳ
> đâu: không trong mã, không trong `ROADMAP.md`. `grep` toàn repo cho "quỹ",
> "cash_book", "ca làm" ra 0 kết quả nghiệp vụ.
>
> 🔴 **Có một blocker pháp lý chưa gỡ được — đọc Bước 1 mục 1 và 8 trước khi duyệt.**

## Bước 0 — Đích (DoD ngược)

**Khi xong, người dùng làm được gì:**

| Vai | Làm được |
|---|---|
| Thu ngân | Mở ca với số dư đầu ca (tiền lẻ trong két), cuối ca **đếm tiền thật** và nhập vào; hệ thống nói ngay lệch bao nhiêu so với số nó tính được |
| Thu ngân / quản lý | Ghi **phiếu thu / phiếu chi ngoài bán hàng**: trả tiền mặt cho NCC, mua văn phòng phẩm, chủ rút tiền |
| Quản lý | Xem lịch sử ca: ai trực, bán được bao nhiêu tiền mặt, lệch bao nhiêu, giải thích gì |

**Bằng chứng khi bị hỏi:**

| Câu hỏi | Hệ thống trả lời bằng | Ghi chú |
|---|---|---|
| "Ca chiều thứ Ba lệch 200k, ai trực?" | `cash_sessions` — người mở, người đóng, thời điểm, số đếm, số tính | |
| "Ai sửa số liệu ca đã đóng?" | **Không ai sửa được.** Ca đã đóng là bất biến; muốn sửa phải mở phiếu điều chỉnh mới, giữ nguyên bản gốc (khuôn `ControlledLedgerEntry`) | |
| "Số tiền mặt hệ thống tính ra từ đâu?" | Tổng `payments` phương thức `CASH` của các đơn **hoàn tất trong ca** + phiếu thu − phiếu chi | Không nhập tay, không có nguồn thứ hai |
| **"Sổ này có giá trị pháp lý như sổ quỹ kế toán không?"** | **CHƯA TRẢ LỜI ĐƯỢC — xem Bước 1** | |

## Bước 1 — Checklist Compliance / Privacy by Design

| # | Mục | Trả lời |
|---|---|---|
| 1 | **Căn cứ pháp lý** | 🔴 **CHƯA KẾT LUẬN ĐƯỢC.** Sổ quỹ tiền mặt là chứng từ **kế toán**, không phải chứng từ ngành dược, nên nó nằm ngoài toàn bộ khối văn bản `docs/legal/` hiện có (Luật Dược 105/2016, 44/2024, TT20/TT18, QĐ540, NĐ163, Luật 91/2025). Khối kế toán — Luật Kế toán 88/2015, các nghị định hướng dẫn, thông tư chế độ kế toán (TT 133/2016 cho DNNVV hoặc TT 200/2014), và mẫu Phiếu thu 01-TT / Phiếu chi 02-TT / Sổ quỹ tiền mặt — **không có tệp nào trong `docs/legal/`**. Theo quy tắc R-10 (Chain chốt 2026-07-26): thiếu văn bản ở bất kỳ tầng nào ⇒ ghi **"chưa kết luận được"**, CẤM ghi "không áp dụng" |
| 2 | Đồng ý (consent) | **N/A** — dữ liệu là tiền của doanh nghiệp và danh tính **nhân viên** thực hiện, không phải dữ liệu chủ thể khách hàng. Không có trường nào của khách đi vào đây |
| 3 | Phân loại dữ liệu | **Không phải dữ liệu cá nhân nhạy cảm.** Là dữ liệu tài chính nội bộ + `user_id` nhân viên (đã có trong `users`, không nhân bản). Ghi rõ: một ca lệch tiền là dữ liệu **có thể dùng để kỷ luật một người**, nên quyền đọc phải hẹp — xem mục 5 |
| 4 | **Audit log bất biến** | Bắt buộc, và mạnh hơn mức thường: `cash_sessions` đã đóng **append-only**, sửa = tạo phiếu điều chỉnh mới. Thêm `AuditAction`: `CASH_SESSION_OPENED`, `CASH_SESSION_CLOSED`, `CASH_MOVEMENT_RECORDED`. Khuôn có sẵn: `ControlledLedgerEntry` |
| 5 | RBAC | ✅ **Đã thoả** — RBAC nay là JWT thật (Sprint IAM), khác hẳn ghi chú 2026-07-23 của `docs/14`. Bốn quyền mới: `cash.session.open` · `cash.session.close` · `cash.movement.write` · `cash.read`. **`cash.read` KHÔNG cấp cho vai thu ngân** — một thu ngân không cần đọc ca của người khác, và mục 3 nói vì sao |
| 6 | Backup / restore | Bảng mới ⇒ nằm trong cùng `pg_dump` của toàn CSDL (runbook F-16 đã diễn tập thật). Không có kho dữ liệu riêng, không thêm việc |
| 7 | AI | **N/A** — không dùng LLM |
| 8 | Rà theo văn bản | 🔴 **BLOCKER, cùng gốc với mục 1.** Cần bổ sung `docs/legal/` khối kế toán trước khi tuyên bố bất cứ điều gì về giá trị pháp lý của bản in |

### 🔴 Hệ quả của blocker — và cách đi tiếp mà không nói dối

Blocker này **không chặn việc xây**, nó chặn việc **tuyên bố**. Ranh giới:

| Được phép làm | KHÔNG được phép làm |
|---|---|
| Xây công cụ **vận hành nội bộ**: đối chiếu tiền cuối ca, tìm ra lệch, biết ai trực | In ra một tờ gọi là "Sổ quỹ tiền mặt" theo mẫu chế độ kế toán và ngụ ý nó thay được sổ kế toán |
| Gọi tên đúng trong giao diện: **"Đối chiếu tiền mặt cuối ca"** | Gọi là "Sổ quỹ" trong giao diện khi chưa xác nhận mẫu biểu |
| Ghi trong tài liệu bán hàng: *"giúp phát hiện lệch tiền trong ca"* | Ghi *"đáp ứng chế độ kế toán"* |

Đây đúng hình dạng sai lầm mà R-10 sinh ra để chặn: ngày 2026-07-24 một kết luận
*"không áp dụng"* rút từ một Thông tư đã bỏ sót nghĩa vụ ở tầng Nghị định, và
BeraLLC trễ **≥3 kỳ báo cáo ngoài đời thật**.

**Việc phải giao ra ngoài vai Trợ lý Code:** Trợ lý Kế toán xác nhận (a) nhà thuốc
BeraLLC áp chế độ kế toán nào, (b) sổ quỹ tiền mặt có bắt buộc lưu theo mẫu không,
(c) bản điện tử có được chấp nhận không. Chưa có ba câu đó thì phần **in ấn/mẫu
biểu** không được code.

## Bước 2 — Rà chồng lấn với module đã có

| Khái niệm đã có | Có trùng không? | Quyết định |
|---|---|---|
| `sales.Payment` (`method=CASH`, `amount`) | **Gần trùng nhất.** Đây là nguồn duy nhất của "tiền mặt lẽ ra phải có" | **KHÔNG tạo khái niệm thanh toán thứ hai.** Sổ quỹ **đọc** tổng tiền mặt từ sales, không tự ghi |
| `sales.SalesOrder.created_at` | Dùng để xếp đơn vào ca | Ca = khoảng `[mở, đóng)`; đơn thuộc ca theo `created_at` |
| `procurement` trả tiền NCC | Chưa có khái niệm thanh toán cho NCC trong procurement | Phiếu chi của sổ quỹ **không** tự động khấu trừ công nợ NCC (công nợ chưa tồn tại). Ghi nhận là nợ, không giả vờ có |
| `audit_logs` | Có sẵn, append-only | Dùng lại, không tạo bảng nhật ký riêng |
| `compliance.ControlledLedgerEntry` | Khuôn bất biến + ký xác nhận | **Dùng lại khuôn**, không dùng lại bảng — thuốc kiểm soát đặc biệt và tiền là hai sổ khác nhau |

**Thực thể mới:** `CashSession` (ca quỹ) · `CashMovement` (phiếu thu/chi ngoài bán hàng).

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module

| Đụng module | Kiểu | Rủi ro |
|---|---|---|
| `sales` | **Cross-module thật** — sổ quỹ cần tổng tiền mặt theo khoảng thời gian + chi nhánh | Sổ quỹ khai **port** `CashSalesSource`, adapter dựng ở composition root chạy dưới danh tính hệ thống — đúng khuôn `analytics_wiring.py` đã được duyệt 25/07. **Không** thêm contract import-linter mới |
| `iam` | Chỉ đọc `user_id` từ context | Không phụ thuộc mã |
| `analytics` | Không đụng | — |

**Rủi ro nghiệp vụ lớn nhất — phải quyết trước khi code:**

| # | Câu hỏi | Đề xuất (chờ Chain xác nhận, đã ghi giả định để đi tiếp) |
|---|---|---|
| R1 | Ca gắn với **người** hay với **quầy/chi nhánh**? | **Chi nhánh** — một ca có thể đổi người trực. Người mở/người đóng ghi riêng |
| R2 | Hai ca mở cùng lúc ở một chi nhánh? | **Cấm** — ràng buộc duy nhất một ca `OPEN` mỗi chi nhánh, đúng cửa CSDL chứ không chỉ kiểm ở service (bài học F-5: số học phải nằm trong câu SQL) |
| R3 | Lệch tiền thì chặn hay chỉ ghi? | **Chỉ ghi + bắt buộc nhập lý do khi lệch ≥ ngưỡng.** Chặn đóng ca không làm tiền quay lại, chỉ làm người ta đóng ca giả |
| R4 | Đơn bán khi ca đang đóng (quên mở ca)? | **Vẫn bán được.** Bán hàng không được phụ thuộc sổ quỹ; đơn không thuộc ca nào sẽ hiện ở mục "ngoài ca" khi đối chiếu |
| R5 | Thanh toán chuyển khoản/thẻ có vào sổ quỹ? | **Không.** Sổ quỹ chỉ tiền mặt. Tiền chuyển khoản đối chiếu với sao kê ngân hàng — việc khác, chưa làm |

## Bước 4 — Cập nhật ROADMAP + PROJECT_STATE

Chưa làm — chờ Chain duyệt Bước 0-3, đặc biệt là **cách xử lý blocker pháp lý**
(xây công cụ vận hành, không tuyên bố giá trị kế toán) và **R1–R5**.
