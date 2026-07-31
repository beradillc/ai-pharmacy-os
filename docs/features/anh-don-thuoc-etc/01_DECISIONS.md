# Ảnh đơn thuốc ETC — Bước 0-3 của `docs/14_FEATURE_PROCESS.md`

> **Trạng thái: BƯỚC 0-3 ✅ VIẾT XONG — CHỜ CHAIN DUYỆT. CHƯA CODE MỘT DÒNG NÀO.**
> `docs/14` cấm code khi Bước 0-3 chưa xong và chưa được duyệt.
>
> Chain giao 2026-07-31: *"ETC demo chỉ cần có nút chụp, chụp lại đơn, có file ảnh lưu hệ
> thống là xong, các tính năng kia tạm đóng."*
> Hai quyết định Chain chốt cùng ngày: **ảnh lưu trong CSDL**, **nút chụp đặt ở quầy**.
>
> Tổng số bước triển khai **chốt là 5** (kỷ luật #12 cấm mẫu số mở) — xem cuối tệp.

## Hiện trạng đo được trước khi làm (kỷ luật #16 — grep, không đọc sổ nợ)

| Mảnh | Trạng thái |
|---|---|
| `prescriptions.image_url` | ✅ **Đã có** — `String(500)` nullable, xuyên suốt domain → DTO → ORM → schema |
| API đơn thuốc | ✅ Đã có 5 đường: tạo · duyệt · từ chối · cấp phát · đọc, đủ 4 quyền `rx.*` |
| Nơi cất tệp ảnh | ❌ `grep UploadFile\|multipart\|StorageProvider\|S3` toàn backend = **0** |
| Màn đơn thuốc ở frontend | ❌ **Không có màn nào**, không mục nav, không route |
| Nút chụp / ô chọn tệp | ❌ `grep 'type="file"\|capture=\|getUserMedia'` toàn frontend = **0** |
| Ai từng đặt `image_url` | ❌ **0 test, 0 seed** — trường có, chưa ai ghi giá trị vào bao giờ |

⇒ Hệ thống có **chỗ ghi địa chỉ ảnh**, nhưng không có gì sinh ra được địa chỉ đó và không
có chỗ nào để bấm. Nửa nối dây — từ phía sổ nợ đọc y hệt "chưa làm".

## Bước 0 — Đích (DoD ngược)

| Vai | Khi xong làm được gì |
|---|---|
| Thu ngân | Bán đơn có thuốc ETC ⇒ thấy nút **Chụp đơn**; bấm là mở camera điện thoại; ảnh gắn vào đơn |
| Dược sĩ | Mở lại một đơn ETC đã bán và **xem lại ảnh** đơn thuốc gốc |
| Quản lý | Truy được **ai đã xem ảnh đơn của bệnh nhân nào, lúc nào** |

**Bằng chứng khi bị hỏi:**

| Câu hỏi | Hệ thống trả lời bằng |
|---|---|
| "Đơn ETC ngày ấy có đơn thuốc gốc không?" | Ảnh gắn trên bản ghi `prescriptions` |
| "Ai đã xem ảnh đơn của bệnh nhân này?" | Audit `RX_IMAGE_VIEWED` — xem Bước 1 mục 4 |
| "Ảnh có bị lộ khi ai đó lấy được bản `pg_dump` không?" | Không — mã hoá at-rest bằng đúng key ring đã có |
| **"Lưu ảnh đơn bao lâu thì được xoá?"** | 🔴 **CHƯA TRẢ LỜI ĐƯỢC** — xem Bước 1 mục 1 |

## Bước 1 — Checklist Compliance / Privacy by Design

| # | Mục | Trả lời |
|---|---|---|
| 1 | **Căn cứ pháp lý** | 🟠 **Có cho việc LƯU, chưa kết luận được cho THỜI HẠN lưu.** Luật Dược **Điều 74**: *"Đơn thuốc là căn cứ để bán thuốc, cấp phát thuốc"*; GPP TT02/2018 **I-1a.II.4.b** đòi sổ sách ghi *"số hiệu đơn thuốc + người kê đơn + cơ sở hành nghề đối với thuốc kê đơn"*. Lưu chính ảnh đơn là cách chứng minh mạnh hơn mức tối thiểu ấy. **Thời hạn lưu thì chưa**: `Thông-tư-18-2026.SUMMARY.md` mục 8 ghi **TT 26/2025/TT-BYT** (*thời hạn lưu đơn thuốc GN/HT*) là văn bản **còn thiếu, chặn kết luận**. Theo R-10: ghi **"chưa kết luận được"**, KHÔNG tự đặt một thời hạn |
| 2 | **Đồng ý** | **Không dựa trên đồng ý.** Cơ sở là **nghĩa vụ pháp lý** của cơ sở bán lẻ khi bán thuốc kê đơn (Điều 74), không phải sự tự nguyện của khách — hỏi đồng ý rồi khách từ chối thì nhà thuốc vẫn phải có căn cứ để bán. 🟠 Nhưng phải **thông báo** cho khách rằng ảnh được lưu; chưa có chỗ hiển thị thông báo đó ⇒ ghi là nợ, không tự bịa câu chữ |
| 3 | **Phân loại dữ liệu** | 🔴 **DỮ LIỆU CÁ NHÂN NHẠY CẢM (sức khoẻ).** Ảnh mang tên, tuổi, **chẩn đoán**, tên bác sĩ. Đây là lần đầu hệ thống lưu một khối nhạy cảm **không cấu trúc** — không cắt nhỏ được, không che từng trường như đã làm với số điện thoại (ADR-0002). Áp toàn bộ các bước còn lại ở mức nghiêm ngặt, không có ngoại lệ "làm tạm cho demo" |
| 4 | **Audit log bất biến** | Bắt buộc, và **phép ĐỌC cũng phải ghi vết**, không chỉ phép ghi — cùng lý do `CUSTOMER_SENSITIVE_READ` tồn tại. Hai `AuditAction` mới: `RX_IMAGE_ATTACHED` (18 ký tự), `RX_IMAGE_VIEWED` (16). Cột `audit_logs.action` là `varchar(64)` (đã đo bằng SQL trên `nt650v2`) ⇒ vừa. `context` **không** mang ảnh và không mang chẩn đoán — chỉ id đơn |
| 5 | **RBAC** | ✅ Nền đã đủ (JWT thật). **Không thêm quyền mới cho việc gắn ảnh**: dùng `rx.create` (ai tạo được đơn thì gắn được ảnh của chính đơn đó). 🟠 **Nhưng việc XEM lại ảnh cần Chain quyết** — xem "Câu hỏi còn treo" |
| 6 | **Truy xuất, sao lưu, phục hồi** | ✅ **Chính là lý do Chain chọn lưu trong CSDL.** `scripts/backup_verify.sh` chỉ chạy `pg_dump` — nó **không chạm tệp nào**. Ảnh trên đĩa sẽ khiến diễn tập phục hồi F-16 khôi phục CSDL đầy đủ và **mất sạch ảnh mà không có gì đỏ lên**, vì phép kiểm phục hồi chỉ so CSDL. Trong CSDL thì không có đường nào để quên |
| 7 | **AI / RAG** | **N/A** — không dùng `LLMProvider`. Không OCR, không đọc nội dung ảnh. Ảnh chỉ được lưu và hiện lại |
| 8 | **Rà theo Luật Dược + BVDLCN + NĐ 356 + GPP** | Luật Dược: mục 1. **Luật 91/2025**: dữ liệu sức khoẻ ⇒ mã hoá at-rest + audit đọc, cả hai đã có khuôn. **NĐ 356/2025 Điều 4.2**: cấm nhân bản dữ liệu nhạy cảm sang nơi khác ⇒ audit **không** được chép nội dung ảnh, và **không** sinh bản thu nhỏ lưu riêng. **GPP TT02/2018**: mục 1 |

## Bước 2 — Rà chồng lấn với module đã có

| Khái niệm định thêm | Đã có gì | Quyết định |
|---|---|---|
| Ảnh đơn thuốc | `prescriptions.image_url` (`String(500)`) | ⚠️ **Không dùng lại được như đang có.** Nó giữ một **địa chỉ**, mà lưu-trong-CSDL thì không có địa chỉ nào. Thêm cột nội dung, **giữ nguyên** `image_url` (không xoá — kỷ luật #17 cấm xoá mã đang dùng, và một deployment khác có thể đang trỏ tệp ngoài) |
| Mã hoá at-rest | `EncryptedText` + key ring `crypto.py` | **Dùng lại.** `encrypt(str) -> str` nên ảnh đi vào dưới dạng **base64**. Không viết kiểu nhị phân mã hoá mới: thêm mặt phẳng mật mã mới là chỗ tốn kém nhất để sai |
| Nơi bấm | Quầy `(pos)/page.tsx` | **Dùng lại**, Chain chốt. Không dựng màn Đơn thuốc |
| Đơn thuốc trong đơn bán | `sales.prescription_ref` + `PrescriptionInfoProvider` | **Dùng lại** — dây cross-module đã có sẵn |

### 🔴 Quyết định nặng nhất của Bước 2: nén ở TRÌNH DUYỆT trước khi gửi

Ảnh điện thoại thô là **2–5 MB**. Qua base64 → mã hoá → base64 lần nữa, một dòng CSDL
thành **3,6–9 MB**. Với 50 đơn ETC/ngày là ~15 GB/tháng — `pg_dump` sẽ chậm tới mức người
ta thôi chạy nó, và mất backup còn tệ hơn mất ảnh.

⇒ Thu nhỏ về cạnh dài **1600px, JPEG chất lượng 0,7** ngay trong trình duyệt (`canvas`)
trước khi gửi: ~200–400 KB, đủ nét để đọc chữ viết tay trên đơn. Máy chủ **kiểm lại kích
thước** và từ chối quá **2 MB** — chặn ở máy khách là tiện lợi, không phải cổng.

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module

| Bước | Module đụng | Cross-module? |
|---|---|---|
| Cột ảnh + mã hoá | `prescription` | Không |
| Endpoint gắn/xem ảnh | `prescription` | Không |
| Nút chụp ở quầy | frontend `(pos)` gọi thẳng API `prescription` | Không — trình duyệt gọi hai module là chuyện bình thường, không phải điểm nối máy chủ |

**Rủi ro thật không nằm ở cross-module mà ở kích thước:** đây là lần đầu một request mang
tải trọng cỡ MB. Cần kiểm giới hạn thân yêu cầu của uvicorn/Next trước khi kết luận "đã
chạy" — nếu proxy cắt ở 1 MB thì lỗi sẽ hiện ra dưới dạng một mã lỗi không liên quan.

## Câu hỏi còn treo — cần Chain quyết trước bước 3

**Ai được XEM lại ảnh đơn thuốc?** `rx.read` hiện có ở cả **Thu ngân**. Ảnh mang chẩn
đoán — thứ mà `crm.sensitive.read` cố ý **không** cấp cho thu ngân. Ba lựa chọn:

| | Ai xem được | Đánh đổi |
|---|---|---|
| A | `rx.read` (gồm thu ngân) | Đơn giản nhất, nhưng thu ngân đọc được chẩn đoán — trái tinh thần tách quyền đã có |
| B | Thêm `rx.image.read`, chỉ cấp Dược sĩ + cấp chuỗi | Khớp cách đã tách `crm.pii.reveal`; thêm một quyền |
| C | Dùng lại `crm.sensitive.read` | Không thêm quyền, nhưng trộn hai khái niệm: hồ sơ khách ≠ đơn thuốc |

**GĐ nghiêng về B** — cùng hình dạng với `crm.pii.reveal` (Chain đã duyệt khuôn đó ngày
31/07), và nó giữ được nguyên tắc: *gắn ảnh* là việc của quầy, *đọc chẩn đoán* thì không.

## 5 bước triển khai (chốt, kỷ luật #12)

| # | Việc | Cổng |
|---|---|---|
| 1 | Tệp này + Chain duyệt Bước 0-3 và câu hỏi quyền | — |
| 2 | `prescription` domain + migration: cột ảnh mã hoá, giới hạn kích thước | 4 cổng + pg_dump trước migration |
| 3 | `prescription` app + interface: gắn ảnh · xem ảnh · 2 audit action | 4 cổng |
| 4 | Quầy: nút **Chụp đơn** khi đơn có ETC, nén trong trình duyệt | 4 cổng + `check-fe` |
| 5 | Cổng trình duyệt thật + ảnh nghiệm thu cả 2 khổ | `make ui-gates` + ảnh |

## Các mục pháp lý Chain TẠM ĐÓNG cùng ngày

Không xoá khỏi sổ, đánh dấu để phiên sau biết vì sao im lặng (kỷ luật #18):

| Mục | Trạng thái |
|---|---|
| ADR reporting (Luật Dược Đ77.4) | ⏸️ **Tạm đóng** — Chain 2026-07-31 |
| Hồ sơ khiếu nại / thu hồi thuốc (TT02 I-1a.III.4.c) | ⏸️ **Tạm đóng** — Chain 2026-07-31 |
| Luân chuyển tồn kho giữa chi nhánh (Luật 44/2024 Đ47a.1.d) | ⏸️ **Tạm đóng** — Chain 2026-07-31 |
| `docs/13` dòng 14 ghi "KHÔNG TÌM THẤY" cho nguồn đã tìm thấy | 🟠 **Còn treo** — sửa tài liệu, rẻ nhất trong nhóm |
| TT 26/2025/TT-BYT thiếu tệp | 🔴 **Còn treo, và nay CHẶN mục này** — nó là văn bản quyết định thời hạn lưu đơn |
