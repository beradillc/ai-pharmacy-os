# Biên bản nhận lại thuốc GN/HT/TC — Phụ lục XVIII (Bước 0-3 của `docs/14_FEATURE_PROCESS.md`)

> **Trạng thái: TỰ DUYỆT dưới ủy quyền toàn quyền chỉ đạo code (Chain, 2026-07-25).**
> Bước 4/6 mạch TT18, đã Chain duyệt phạm vi từ đầu. Nguồn: `docs/13_COMPLIANCE_SPEC.md` mục C.6;
> TT18 Điều 6.2 + Điều 12.1.d + Phụ lục XVIII.

## Bước 0 — Đích (DoD ngược)

**Khi xong, người dùng làm được gì:**

| Vai | Làm được |
|---|---|
| Dược sĩ | Ghi nhận việc nhận lại thuốc GN/HT/TC từ khách hàng (không dùng hết hoặc người bệnh tử vong), theo đúng mẫu Phụ lục XVIII; xuất biên bản 02 bản |

**Bằng chứng tuân thủ khi thanh tra hỏi:**

| Câu hỏi thanh tra | Hệ thống trả lời bằng |
|---|---|
| "Thuốc gây nghiện/hướng thần khách trả lại xử lý thế nào?" | Bản ghi bất biến: ai giao (tên + số CCCD/hộ chiếu), ai nhận (người chịu trách nhiệm chuyên môn dược), tình trạng thuốc, lý do, thời gian/địa điểm giao nhận |
| "Ai đã xem/ghi thông tin CCCD của người trả thuốc?" | `audit_logs` action mới, tương tự cách `CUSTOMER_SENSITIVE_READ` đã làm cho hồ sơ sức khỏe KH |

## Bước 1 — Checklist Compliance/Privacy by Design

| # | Mục | Trả lời |
|---|---|---|
| 1 | Căn cứ pháp lý | TT18 Điều 6.2 + Điều 12.1.d + mẫu Phụ lục XVIII — đã trích đủ, có file gốc |
| 2 | Đồng ý (consent) | ⚠️ **Không tự kết luận chắc tuyệt đối.** Đây là hồ sơ **bắt buộc lập theo luật chuyên ngành** (TT18), không phải xử lý theo mục đích marketing/tùy chọn — tương tự nguyên tắc đã ghi ở `docs/legal/Luật-91-2025-QH15.SUMMARY.md` dòng 9 ("lưu trữ theo mục đích, trừ pháp luật khác quy định khác"). Xử lý an toàn: **chỉ thu đúng field mẫu pháp lý yêu cầu, không thêm gì ngoài mẫu**, không dùng cho mục đích khác (không nối vào hồ sơ CRM/marketing). **Chưa hỏi qua** cơ chế xin đồng ý tường minh kiểu Điều 9 — vì đây là nghĩa vụ ghi chép bắt buộc, không phải thu thập để phục vụ mục đích của cơ sở. Nếu sau này cần chắc chắn tuyệt đối, nên hỏi ý kiến pháp lý chính thức, không chặn code lại vì lý do này |
| 3 | Phân loại dữ liệu | **Số CCCD/hộ chiếu = dữ liệu cá nhân.** Không phải "nhạy cảm" theo nghĩa sức khỏe/tài chính, nhưng là định danh — áp toàn bộ các bước còn lại nghiêm ngặt |
| 4 | Audit log bất biến | `AuditAction.DRUG_RETURN_RECORDED` mới, ghi ai tạo biên bản — **không** ghi số CCCD vào `context` audit (giữ nguyên tắc PII không lộ vào audit, giống `CONTROLLED_LEDGER_ENTRY_RECORDED` đã làm với tên/địa chỉ khách hàng) |
| 5 | RBAC | Tái dùng `compliance.ledger.write` (ghi) / `compliance.ledger.read` (đọc) — cùng nhóm nghiệp vụ với sổ kiểm soát đặc biệt, không tạo permission mới |
| 6 | Backup/restore | Bảng mới `drug_return_records` nằm trong backup Postgres hiện có, không cần xử lý riêng |
| 7 | AI qua port | N/A |
| 8 | Rà Luật Dược/BVDLCN/NĐ356/GPP | Đã rà Luật 91/2025 (mục 2 ở trên). NĐ 356/2025 không có mục riêng cho hồ sơ chuyên ngành dược — không phát sinh yêu cầu bổ sung |

## Bước 2 — Rà chồng lấn

- `ControlledLedgerEntry` (Phụ lục VIII/XVI, xuất/nhập/tồn) — **khác hẳn**: biên bản nhận lại không
  phải giao dịch xuất/nhập kho, mà là hồ sơ xác nhận nhận lại + ý định biệt trữ/tiêu hủy. Không gộp
  vào ledger — tạo entity riêng `DrugReturnRecord`.
- `sales.SaleReturned` (trả hàng OTC/thường) — đã có tiền lệ **"trả tồn" (auto-restock) CHỦ Ý CHƯA
  làm** (PROJECT_STATE §7aa): dược sĩ phải kiểm tra thuốc trả trước khi cho bán lại, không tự động.
  Áp dụng đúng nguyên tắc đó ở đây: **`DrugReturnRecord` KHÔNG động vào `inventory`** — thuốc GN/HT/TC
  trả lại đi thẳng vào biệt trữ/tiêu hủy (Điều 6.2: "biệt trữ ... rồi tiêu hủy"), không quay lại tồn
  kho bán được, nên không có bước "cộng tồn" nào để tự động hay chặn tự động cả. **Sửa lại giả định cũ
  trong docs/13 mục C.6** ("hệ quả kỹ thuật: khóa khỏi tồn kho bán được, cross-module inventory") —
  giả định đó dư thừa, không cần cross-module.

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module

| Module bị đụng | Thay đổi | Cross-module? |
|---|---|---|
| `compliance` (domain/app/infra/interface) | Entity mới `DrugReturnRecord`, service, migration, endpoint | Không |
| `inventory` | **Không đụng** (xem Bước 2 — sửa giả định cross-module cũ, không cần nữa) | Không |
| `core/audit` | Thêm `AuditAction.DRUG_RETURN_RECORDED` | Không |

**Không có cross-module thật trong tính năng này** — đơn giản hơn báo cáo Mẫu số 06 (không cần đọc
`catalog` vì biểu mẫu chỉ cần tên/mô tả thuốc do người dùng nhập tại thời điểm ghi, giống cách
`ControlledLedgerEntry` không bắt buộc tra catalog để ghi sổ).

## Thiết kế trường dữ liệu (theo đúng mẫu Phụ lục XVIII)

| Trường | Nguồn mẫu | Ghi chú |
|---|---|---|
| `returner_name`, `returner_address` | "Họ, tên người giao" + địa chỉ | Bắt buộc |
| `returner_id_number`, `returner_id_issuer`, `returner_id_issued_at` | Số CCCD/Hộ chiếu + nơi cấp + ngày cấp | PII — không đưa vào audit context |
| `returner_is_patient` | Cờ "Là người bệnh / Là người đại diện" | bool |
| `receiving_pharmacist_name` | "Tên cơ sở nhận lại thuốc... ghi rõ tên người chịu trách nhiệm chuyên môn về dược" (bán lẻ) | |
| `items: list[ReturnedDrugItem]` | Bảng danh mục thuốc nhận lại | Mỗi dòng: tên/dạng bào chế/nồng độ/quy cách/số ĐKLH (chuỗi tự do, không tra catalog), đơn vị tính, số lượng, số lô, hạn dùng, tình trạng cảm quan, lý do nhận lại |
| `handover_at` | "giờ...phút ngày...tháng...năm" | datetime |
| `handover_location` | Địa điểm giao nhận thực tế | |

Không có trường suy ra từ `ControlledLedgerEntry` bắt buộc (VD: không tự động liên kết `drug_id` —
mẫu giấy gốc không yêu cầu, và cưỡng ép tra cứu sẽ vượt phạm vi mẫu pháp lý gốc).
