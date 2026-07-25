# Báo cáo định kỳ Mẫu số 06 (NĐ163 Điều 35.2) — Bước 0-3 của `docs/14_FEATURE_PROCESS.md`

> **Trạng thái: TỰ DUYỆT dưới ủy quyền toàn quyền chỉ đạo code (Chain, 2026-07-25).** Full-auto cho
> phép GĐ tự quyết cross-module + nghiệp vụ, vẫn giữ 4 cổng xanh + 1 commit/bước + ghi PROJECT_STATE.
> Nguồn pháp lý: `docs/legal/Nghị-định-163-2025-NĐ-CP.SUMMARY.md`; `docs/13_COMPLIANCE_SPEC.md` mục C.7.

## Bước 0 — Đích (DoD ngược)

**Khi xong, người dùng làm được gì:**

| Vai | Làm được |
|---|---|
| Người quản lý thuốc (dược sĩ phụ trách) | Chọn kỳ (6 tháng: 01/01–30/06, hoặc năm: 01/01–31/12), xuất CSV đúng khuôn Mẫu số 06 (12 cột) cho GN/HT/TC + thuốc dạng phối hợp, để nộp UBND cấp tỉnh trước 15/7 hoặc 15/01 |

**Bằng chứng tuân thủ khi thanh tra hỏi:**

| Câu hỏi thanh tra | Hệ thống trả lời bằng | Căn cứ |
|---|---|---|
| "Đã báo cáo kỳ này chưa, tạo lúc nào, ai tạo?" | `audit_logs` action mới `PERIODIC_REPORT_EXPORTED`, `target_id` = kỳ báo cáo | NĐ163 Điều 35.2 |
| "Số liệu báo cáo có khớp sổ sách không?" | Báo cáo tính trực tiếp từ `controlled_ledger_entries` (nguồn duy nhất, cùng dữ liệu dùng cho sổ PL VIII/XVI) — không nhập tay riêng | Đối chiếu nội bộ |
| "Tại sao thiếu cột X (nước SX, quy cách đóng gói, số công văn)?" | Trả lời thẳng: catalog hiện chưa lưu 3 trường này — để trống có chủ đích, ghi rõ trong export, người dùng điền tay trước khi nộp (xem "Nợ đã biết" bên dưới) | — |

## Bước 1 — Checklist Compliance/Privacy by Design

| # | Mục | Trả lời |
|---|---|---|
| 1 | Căn cứ pháp lý | NĐ163/2025 Điều 35.2 + Mẫu số 06 Phụ lục II — đã trích dẫn đầy đủ, có file gốc |
| 2 | Đồng ý (consent) | **N/A** — dữ liệu tổng hợp số lượng thuốc theo kỳ, không phải dữ liệu cá nhân của khách hàng |
| 3 | Phân loại dữ liệu | **Không nhạy cảm** — số liệu tồn/nhập/xuất theo thuốc, không chứa tên/CCCD khách hàng |
| 4 | Audit log bất biến | Thêm `AuditAction.PERIODIC_REPORT_EXPORTED`, ghi mỗi lần export (ai, lúc nào, kỳ nào) — dùng `audit_logs` đã có, không cần bảng mới |
| 5 | RBAC | Tái dùng quyền `compliance.ledger.read` đã có — không tạo permission mới (đúng pattern `reports.py` đã dùng cho revenue/stock: không nhạy cảm hơn thứ role đó đã xem) |
| 6 | Backup/restore | Dữ liệu nguồn `controlled_ledger_entries` đã nằm trong backup hiện có; không có bảng mới |
| 7 | AI qua port | N/A — không dùng LLM |
| 8 | Rà theo Luật Dược/BVDLCN/NĐ356/GPP | Không áp — không xử lý dữ liệu cá nhân. Xác nhận lại: **RBAC không còn ở trạng thái "CHƯA THỎA" ghi ở đầu file docs/14 (2026-07-23)** — module IAM + JWT thật đã dựng xong từ Sprint 6, permission `compliance.ledger.read` đã tồn tại trong `system_roles.py` |

## Bước 2 — Rà chồng lấn

- `LedgerBookRow`/`ledger_book_rows` (vừa làm ở mạch TT18 bước 3) là **per-transaction**, theo mẫu
  sổ PL VIII/XVI (TT18) — **khác** với báo cáo này: **per-drug aggregate theo kỳ 6 tháng/năm**,
  theo Mẫu số 06 (NĐ163, cơ quan nhận là UBND tỉnh, không phải nội bộ cơ sở). Không trùng, không
  gộp chung được — 2 khái niệm sinh từ cùng nguồn dữ liệu (`ControlledLedgerEntry`) nhưng hình dạng
  khác nhau, giữ 2 hàm/2 port riêng, đúng nguyên tắc "không premature abstraction khi 2 thứ chỉ
  giống bề ngoài lúc này nhưng có thể lệch nhau sau" (đã có tiền lệ ở việc tách PL VIII/XVI).
- `NationalDrugRecord`/QĐ540 Bảng 1 — báo cáo liên thông CSDL Dược Quốc gia theo **từng giao dịch**
  real-time, khác báo cáo **tổng hợp theo kỳ** gửi UBND tỉnh. Không trùng.
- **`DrugMasterProvider`/`DrugMasterFacts`** (đã định nghĩa ở `compliance/domain/ports.py` từ trước,
  dự phòng cho QĐ540 Bảng 1) — **CHƯA TỪNG ĐƯỢC WIRING** (không có adapter ở composition root, không
  ai gọi). Tái dùng port này cho báo cáo mới thay vì tạo port khác — mở rộng thêm field, không tạo
  khái niệm song song.

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module

| Module bị đụng | Thay đổi | Cross-module? |
|---|---|---|
| `compliance` domain | Thêm `PeriodicReportRow` (application/dto.py, không phải domain — đây là hình dạng báo cáo suy ra, không phải khái niệm nghiệp vụ mới); mở rộng `ControlledLedgerRepository` port thêm `aggregate_for_period()` | Không |
| `compliance` infra | Hiện thực `aggregate_for_period()` bằng SQL aggregate (SUM theo hướng NHAP/XUAT, nhóm theo `drug_id`, 2 khoảng: trước kỳ + trong kỳ) — không load từng dòng lịch sử vào Python | Không |
| `compliance` interface | Endpoint mới `GET /compliance/periodic-report/export` | Không |
| `catalog` (đọc qua composition root) | Wiring **lần đầu tiên** adapter cho `DrugMasterProvider` tại `api/v1/cross_module.py`, theo đúng khuôn `CatalogDrugInfoProvider` đã có cho `sales` | **CÓ** — nhưng đọc-only qua read-port đã thiết kế sẵn từ trước, không đổi schema `catalog`, không đổi hợp đồng import-linter (compliance vẫn không import catalog trực tiếp) |
| `iam` | Không đổi — tái dùng permission có sẵn | Không |

**Quyết định cross-module (tự quyết dưới full-auto, ghi lại để xem sau):** wiring `DrugMasterProvider`
tại composition root là rủi ro thấp — port đã tồn tại từ trước với đúng field cần (`registration_no`,
`base_unit`), chỉ cần mở rộng thêm `name`/`form`/`strength` (đều là field có sẵn trên `catalog.Drug`,
không cần migration `catalog`).

## Nợ đã biết — không chặn v1, ghi rõ để không quên

| Cột Mẫu số 06 | Có dữ liệu? | Xử lý |
|---|---|---|
| Tên thuốc, dạng bào chế, nồng độ/hàm lượng, số ĐKLH, đơn vị tính | ✅ Có (catalog.Drug: name/form/strength/registration_no/base_unit) | Điền tự động |
| Hoạt chất | ✅ Có (`Drug.ingredients` → `ActiveIngredient.name`) | Điền tự động, nối bằng dấu `+` nếu nhiều hoạt chất |
| **Quy cách đóng gói** | ❌ Không có trường lưu sẵn dạng chuỗi (VD: "Hộp 10 vỉ x 10 viên") trên `catalog.Drug`/`DrugUnit` | Để trống, ghi chú "điền tay trước khi nộp" |
| **Nước sản xuất** | ❌ Catalog hiện không lưu trường này | Để trống, ghi chú "điền tay trước khi nộp" |
| **Số công văn cho phép mua trong nước** | ❌ Không có nguồn — là văn bản duyệt riêng theo Điều 38/39 NĐ163, ngoài phạm vi `ControlledLedgerEntry` | Để trống, điền tay |
| Tồn kỳ trước, Nhập trong kỳ, Tổng số, Xuất trong kỳ, Tồn cuối kỳ | ✅ Tính được từ `controlled_ledger_entries` | Tính tự động |
| **Hao hụt** | ⚠️ Ledger hiện không phân biệt "xuất bán" và "xuất do hỏng/vỡ/hết hạn" — không suy ra được đáng tin cậy | Mặc định 0, để cột trống cho người dùng ghi tay theo kiểm kê thực tế (đúng ghi chú Mẫu 06: "nếu có, cần báo cáo chi tiết" — số này vốn cần xác nhận qua kiểm kê vật lý, không phải suy từ giao dịch) |

Không mở rộng schema `catalog` (thêm `manufacturer_country`, `packaging_spec`) trong đợt này —
đó là thay đổi module `catalog` thật sự (không chỉ đọc), phạm vi lớn hơn báo cáo này, để dành khi
có nhu cầu rõ hơn (VD: khi làm liên thông CSDL Dược Quốc gia QĐ540 Bảng 1 cần đúng những trường này).
