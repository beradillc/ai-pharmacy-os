# Hồ sơ sức khỏe khách hàng — Bước 0-3 của `docs/14_FEATURE_PROCESS.md`

> **Trạng thái: THIẾT KẾ, CHỜ DUYỆT.** Chưa code dòng nào. Lập 2026-07-23 (phiên Opus).
> Bước 4 (cập nhật ROADMAP/PROJECT_STATE) **chỉ làm sau khi sếp duyệt tài liệu này**.
>
> **2 hạng mục sếp đưa vào phạm vi ngay từ đầu** (không phải phát sinh giữa chừng):
> **(A)** tách `crm.read` → `crm.sensitive.read`; **(B)** action audit `CUSTOMER_SENSITIVE_READ`
> cho mọi lần đọc dữ liệu sức khỏe. Cả hai được thiết kế xuyên suốt bên dưới, không tách phụ lục.

---

## Bước 0 — Đích (DoD ngược)

**Khi xong, người dùng làm được gì:**

| Vai | Làm được | KHÔNG làm được |
|-----|----------|----------------|
| Dược sĩ (chuỗi/nhà thuốc) | Mở hồ sơ sức khỏe KH: dị ứng, bệnh nền, lịch sử dùng thuốc; ghi nhận thêm; dùng để tư vấn/cấp phát an toàn | — |
| Thu ngân | Tra **tên/SĐT** để gắn KH vào đơn bán; tạo KH mới ở mức cơ bản | **Không** xem được dị ứng/bệnh nền/lịch sử dùng thuốc |
| Chủ thể dữ liệu (khách hàng) | Được hỏi đồng ý tách theo mục đích; rút đồng ý; yêu cầu xem/xuất/xóa dữ liệu của mình | — |
| Quản trị/dược sĩ chuỗi | Trả lời được "ai đã xem hồ sơ bệnh của khách X, lúc nào" | — |

**Bằng chứng tuân thủ khi thanh tra hỏi** — đây là phần quyết định phạm vi, không phải phần phụ:

| Câu hỏi thanh tra có thể đặt | Hệ thống trả lời bằng | Căn cứ |
|------------------------------|----------------------|--------|
| "Vì sao được lưu dữ liệu sức khỏe của khách?" | Bản ghi đồng ý: thời điểm, tài khoản thực hiện, IP, phiên bản điều khoản, mục đích cụ thể | Luật 91/2025 Điều 9, Điều 26.1 |
| "Ai đã xem hồ sơ bệnh của khách X?" | `audit_logs` lọc `action=CUSTOMER_SENSITIVE_READ`, `target_id=<customer_id>` | NĐ356 Điều 4.2 · GPP TT02 I-1a.III.4.a |
| "Nhân viên bán hàng có xem được bệnh nền không?" | Ma trận vai trò: `crm.sensitive.read` **không** thuộc role `cashier`; có test e2e chốt | NĐ356 Điều 4.2 |
| "Khách rút đồng ý thì dữ liệu ra sao?" | Luồng rút đồng ý + xóa/khử nhận dạng, có audit | Luật 91/2025 Điều 4, 13, 14 |
| "Lưu bao lâu, xóa theo nguyên tắc nào?" | Chính sách lưu trữ ghi thành tài liệu + cấu hình | GPP TT02 I-1a.II.4.d (tối thiểu 1 năm kể từ khi hết hạn dùng thuốc) |
| "Dữ liệu có bị gửi ra nước ngoài không?" | Thiết kế AI chỉ gửi tên hoạt chất, không gửi định danh KH | Luật 91/2025 Điều 20 · NĐ356 Điều 17-18 |

**Câu chốt DoD:** *tính năng được coi là xong khi 6 câu hỏi trên đều trả lời được bằng dữ liệu
trong hệ thống, không phải bằng lời hứa trong tài liệu.*

---

## Bước 1 — Checklist Compliance/Privacy by Design (8 điểm, đúng thứ tự)

### 1.1 Căn cứ pháp lý

| Nội dung | Kết luận |
|----------|----------|
| Có văn bản nào **cho phép** xử lý dữ liệu sức khỏe KH? | **CÓ, nhưng cơ sở pháp lý DUY NHẤT là ĐỒNG Ý của chủ thể** (Luật 91/2025 Điều 26.1: dữ liệu sức khỏe bắt buộc có đồng ý trước khi thu thập/xử lý) |
| Có văn bản nào **bắt buộc** nhà thuốc phải lưu dị ứng/bệnh nền? | **KHÔNG TÌM THẤY.** GPP TT02 I-1a.III.4.a chỉ nói người bán lẻ phải *giữ bí mật* thông tin người bệnh — tức thừa nhận nhà thuốc có nắm thông tin, không bắt buộc phải lưu thành hồ sơ |

> ⚠️ **Hệ quả thiết kế quan trọng, không được bỏ qua:** vì đồng ý là cơ sở pháp lý **duy nhất**
> (không có nghĩa vụ luật định nào chống lưng), nên **rút đồng ý phải thật sự làm được** — không
> thể trả lời "luật bắt tôi giữ". Đây là lý do mục 2 và câu hỏi mở **Q2** bên dưới là bắt buộc chứ
> không phải tùy chọn. Đối chiếu: dữ liệu bán thuốc kê đơn thì ngược lại — có nghĩa vụ lưu theo
> GPP/Luật Dược, nên xóa được từ chối hợp pháp.

### 1.2 Đồng ý

| Yêu cầu (Luật 91/2025 Điều 9) | Thiết kế đáp ứng |
|-------------------------------|------------------|
| Tự nguyện, biết rõ, **theo từng mục đích riêng** | **2 mức đồng ý tách biệt**: `BASIC` (tên/SĐT — phục vụ bán hàng, hóa đơn) và `HEALTH` (dị ứng/bệnh nền/lịch sử — phục vụ tư vấn an toàn dược lý) |
| **Im lặng ≠ đồng ý**, không mặc định bật sẵn | Không có giá trị mặc định `True` ở bất kỳ đâu trong domain lẫn schema |
| Bằng chứng kiểm chứng được | Bảng `customer_consents`: `customer_id`, `purpose`, `granted`, `granted_at`/`revoked_at`, `actor_user_id` (nhân viên thực hiện), `client_ip`, `terms_version` |
| Rút lại đồng ý | Use-case `revoke_consent` — **rút `HEALTH` phải kéo theo xử lý dữ liệu sức khỏe đã lưu**, xem Q2 |
| Xóa dữ liệu theo yêu cầu (Điều 13-14) | Use-case `erase_customer` — hiện `CrmService` **chưa có** delete/export |

### 1.3 Phân loại dữ liệu

**NHẠY CẢM.** NĐ356 Điều 4.1.d liệt kê rõ "tình trạng sức khỏe" — bao trùm `Allergy`, `Condition`,
`MedicationHistoryEntry`. ⇒ Áp dụng nghiêm ngặt toàn bộ các bước còn lại, **không có ngoại lệ "làm
tạm"** (đúng chữ trong docs/14).

> ⚠️ **NĐ356 Điều 41.2:** miễn trừ DPIA cho hộ kinh doanh/DN siêu nhỏ **KHÔNG áp dụng** khi trực
> tiếp xử lý dữ liệu nhạy cảm. Nghĩa là **mọi tenant, kể cả nhà thuốc lẻ nhỏ nhất, vẫn phải lập
> DPIA** khi dùng tính năng này. Đây là nghĩa vụ đổ lên đầu khách hàng của BeraLLC — xem Q6.

### 1.4 Audit log bất biến

**ĐÃ CÓ SẴN** — `audit_logs` append-only (PROJECT_STATE §7l, migration `0014`): repository không có
`update`/`delete`, có test chốt. Tính năng này **mở rộng** chứ không dựng lại:

| Action mới | Khi nào phát | Ghi chú |
|------------|--------------|---------|
| `CUSTOMER_SENSITIVE_READ` | **Mọi lần đọc** dị ứng/bệnh nền/lịch sử dùng thuốc | `target_type="customer"`, `target_id=<customer_id>`, `context` thêm `fields` (loại dữ liệu đã đọc) — **không chép nội dung dữ liệu** |
| `CUSTOMER_SENSITIVE_WRITE` | Ghi/sửa dữ liệu sức khỏe | Bổ sung của Trợ lý Code: docs/14 mục 4 nói "ghi/sửa/xóa **phải** có audit" — chỉ audit lượt đọc là thiếu đúng thứ điều lệ đòi |
| `CONSENT_GRANTED` / `CONSENT_REVOKED` | Cấp/rút đồng ý | Chính là bằng chứng cho câu hỏi thanh tra số 1 và 4 |
| `CUSTOMER_ERASED` | Xóa/khử nhận dạng theo yêu cầu | Bản ghi audit **phải sống sót** sau khi hồ sơ bị xóa ⇒ `target_id` là UUID trần, không FK (audit hiện đã thiết kế đúng vậy) |

**Điểm tinh tế:** `audit_logs.context` tuyệt đối không được chứa nội dung dữ liệu sức khỏe. Ghi
"đã đọc dị ứng của KH X" chứ **không** ghi "đã đọc: dị ứng penicillin". Chép dữ liệu nhạy cảm vào
nhật ký là tạo kho thứ hai ít được canh hơn kho gốc — đã có test chốt nguyên tắc này ở §7l, tính
năng này phải giữ nguyên.

### 1.5 Phân quyền theo vai trò (RBAC)

**ĐÃ THỎA** — module `iam` thật, JWT có `branch_id` ký sẵn, không còn dev-header mặc định
(PROJECT_STATE §7k). Điều kiện tiên quyết của docs/14 mục 5 đã xử lý xong trước, đúng thứ tự.

**Tách permission (hạng mục A sếp giao):**

| Permission | Phạm vi dữ liệu | admin | chain_ph | branch_ph | cashier | warehouse |
|------------|-----------------|:-----:|:--------:|:---------:|:-------:|:---------:|
| `crm.read` | Tên, SĐT, ngày sinh, giới tính — **dữ liệu cơ bản** | ✅ | ✅ | ✅ | ✅ **(mới)** | — |
| `crm.create` | Tạo hồ sơ ở mức cơ bản | ✅ | ✅ | ✅ | ✅ **(mới)** | — |
| `crm.sensitive.read` | **Dị ứng, bệnh nền, lịch sử dùng thuốc** | ✅ | ✅ | ✅ | ❌ | — |
| `crm.sensitive.write` | Ghi/sửa dữ liệu sức khỏe | ✅ | ✅ | ✅ | ❌ | — |
| `crm.write` | Sửa dữ liệu cơ bản | ✅ | ✅ | ✅ | ❌ | — |
| `crm.consent.manage` | Cấp/rút đồng ý thay mặt KH tại quầy | ✅ | ✅ | ✅ | ✅ **(mới)** | — |
| `crm.erase` | Xóa/khử nhận dạng theo yêu cầu | ✅ | ✅ | ❌ | ❌ | — |

**Thu ngân được mở `crm.read` + `crm.create` + `crm.consent.manage`** — đảo lại quyết định D8
(phương án a: "thu ngân không có quyền crm nào"). D8 chọn vậy vì lúc đó `crm.read` gộp cả dữ liệu
nhạy cảm **và** `SalesOrder` chưa có `customer_id` nên không mất gì. Nay cả hai tiền đề đều đổi:
`crm.read` được tách, và bán hàng cần gắn KH. Ghi rõ đây là **đảo quyết định có lý do**, không phải
quên.

> ⚠️ **Thay đổi ngắt tương thích (breaking):** `crm.read` hiện nay **đang** trả về cả dị ứng/bệnh
> nền qua `CustomerResponse`. Sau khi tách, cùng một endpoint sẽ trả **ít dữ liệu hơn** cho ai chỉ
> có `crm.read`. Không có client thật nào đang chạy nên chi phí bằng 0 **nếu làm ngay**; để lâu thì
> đắt. Đây là lý do việc tách phải nằm trong phạm vi ngay từ đầu — đúng như sếp chỉ đạo.

### 1.6 Truy xuất, sao lưu, phục hồi

| Mục | Trạng thái |
|-----|-----------|
| Bảng hiện có (`customers`, `customer_allergies`, `customer_conditions`, `customer_medication_history`) | Đã nằm trong `pg_dump` toàn CSDL — cơ chế backup hiện tại là dump cả database, nên bảng mới **tự động được phủ**, không cần cấu hình thêm |
| Bảng mới (`customer_consents`) | Phủ theo cùng cơ chế; **xác nhận lại bằng lệnh thật** sau khi migration chạy (kỷ luật #7) |
| Phục hồi | Chưa từng diễn tập restore thật bao giờ — **ghi nợ**, không phải blocker của tính năng này nhưng là rủi ro vận hành có thật |

### 1.7 AI chỉ qua lớp phân quyền + RAG

| Mục | Kết luận |
|-----|----------|
| Tính năng này có gọi `LLMProvider` không? | **KHÔNG.** Hồ sơ sức khỏe là CRUD + phân quyền + audit, không có AI |
| Ràng buộc phải giữ | `clinical.check_interactions` hiện chỉ gửi **tên hoạt chất**, không gửi định danh KH. Khi thay `MockLLMProvider` bằng `AnthropicProvider` thật, **không được** kèm `customer_id`/tên/dị ứng gắn danh tính vào request |
| Vì sao | Luật 91/2025 Điều 20 + NĐ356 Điều 17-18: gửi DLCN thu thập tại VN ra API nước ngoài kích hoạt nghĩa vụ **đánh giá tác động chuyển dữ liệu xuyên biên giới** trong 60 ngày |

### 1.8 Rà theo 4 nhóm văn bản

**Không thiếu văn bản ⇒ không blocker.** 10 file `docs/legal/*.SUMMARY.md` đã có.

| Văn bản | Điều khoản áp dụng | Đã phản ánh ở mục |
|---------|-------------------|-------------------|
| Luật BVDLCN 91/2025/QH15 | Điều 9 (đồng ý), 4/13/14 (quyền), 20 (xuyên biên giới), 21 (DPIA), 23 (báo vi phạm 72h), 24 (trẻ em), 26 (dữ liệu sức khỏe) | 1.1, 1.2, 1.7, Q3, Q6 |
| NĐ 356/2025/NĐ-CP | Điều 4.1.d (phân loại nhạy cảm), 4.2 (phân quyền riêng), 19 (DPIA), 41.2 (không miễn trừ) | 1.3, 1.5 |
| GPP TT02/2018 (+TT11/2025, TT29/2020) | I-1a.II.4.d (lưu ≥1 năm sau hạn dùng), I-1a.III.4.a (giữ bí mật) | 1.1, Bước 0, Q2 |
| Luật Dược 105/2016 + sửa đổi 44/2024 | Điều 6.5.h (cấm bán lẻ ETC không đơn), 17a (2 cấp chuyên môn) | Đã phản ánh ở `iam` (§7k), không phát sinh thêm |

**Việc pháp lý-hành chính, KHÔNG phải code (ghi để sếp không nhầm là đã xong khi code xong):**
DPIA phải nộp Bộ Công an trong **60 ngày kể từ khi bắt đầu xử lý dữ liệu thật** — tức tính từ khi
có khách hàng thật đầu tiên, không phải từ khi merge code. Code chỉ cần **cho phép trích xuất** đủ
thông tin (loại dữ liệu, mục đích, luồng, biện pháp bảo vệ), không tự động hóa việc nộp hồ sơ.

---

## Bước 2 — Rà chồng lấn với module đã có

| Khái niệm đã có | Ở đâu | Quyết định |
|-----------------|-------|-----------|
| `crm.Customer` (aggregate root, tenant-scoped) | `modules/crm/domain/entities.py` | **TÁI SỬ DỤNG.** Không tạo entity "HealthProfile" riêng — hồ sơ sức khỏe *là* các collection con của `Customer` đã có |
| `crm.Allergy` (keyed theo `ingredient_id`, FK thật tới `active_ingredients`) | cùng file | **TÁI SỬ DỤNG nguyên trạng.** Không đổi shape |
| `crm.Condition` (ICD-10) | cùng file | **TÁI SỬ DỤNG nguyên trạng** |
| `crm.MedicationHistoryEntry` (ref-only, `drug_id` không FK) | cùng file | **TÁI SỬ DỤNG.** Việc *ghi* từ event `SaleCompleted`/`PrescriptionDispensed` vẫn là nợ cross-module cũ (§7i nợ 2) |
| `compliance.CustomerDetail` (value object, snapshot cho sổ thuốc kiểm soát Phụ lục XXI) | `modules/compliance` | **GIỮ TÁCH BIỆT.** Đã có quyết định từ trước (ghi trong docstring `crm/domain/entities.py`): nó không có identity, gắn với 1 dòng sổ tại thời điểm bán; `Customer` là master data tenant-owned. Không gộp |
| `clinical` đọc dị ứng để cảnh báo | `api/v1/cross_module.py` (`wire_safety_checks`) | **ĐÃ CÓ.** Xem Q3 — luồng tự động này có phải ghi `CUSTOMER_SENSITIVE_READ` không |
| `audit_logs` + `AuditAction` | `core/audit` | **MỞ RỘNG** (thêm 5 action), không dựng mới |
| `iam` role catalogue | `modules/iam/domain/system_roles.py` | **MỞ RỘNG** (tách/thêm permission), không dựng mới |

**Kết luận Bước 2: KHÔNG tạo module mới, KHÔNG tạo entity trùng.** Tính năng = mở rộng `crm` +
`core/audit` + `iam` role catalogue.

**Cái thật sự CHƯA có (đây mới là phần phải xây):**

| Thiếu | Vì sao cần |
|-------|-----------|
| `CustomerConsent` (entity + bảng) | Cơ sở pháp lý duy nhất là đồng ý (1.1) mà hiện không lưu bằng chứng nào |
| `export_customer_data` | Luật 91 Điều 13-14 (quyền xem/yêu cầu cung cấp) |
| `erase_customer` | Luật 91 Điều 13-14 (quyền xóa) |
| Tách quyền đọc nhạy cảm ở tầng service + schema | NĐ356 Điều 4.2 |
| 5 action audit mới | docs/14 mục 4 + NĐ356 Điều 4.2 |
| Chính sách lưu trữ (retention) | GPP II.4.d vs quyền xóa — xem Q2 |

---

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module

| # | Việc | Module đụng | Cross-module thật? | Ghi chú |
|---|------|-------------|:------------------:|---------|
| 1 | `CustomerConsent` domain + bảng + use-case cấp/rút | `crm` | Không | Nội bộ 1 module |
| 2 | Tách `crm.read` / `crm.sensitive.read` ở service + schema | `crm` | Không | Sửa `CrmService` + `CustomerResponse` |
| 3 | Thêm 5 `AuditAction` | `core/audit` | Không | Hạ tầng core, đã có khuôn |
| 4 | `crm` gọi `AuditLogger` khi đọc/ghi dữ liệu nhạy cảm | `crm` → `core` | **Không** | `modules → core` là chiều hợp lệ của contract `layers`; `iam` đã làm y hệt |
| 5 | Thêm permission mới vào 5 role hệ thống | `iam` | Không | Nội bộ `iam`; **phải chạy `sync_system_roles` trên CSDL có dữ liệu** (kỷ luật #7) |
| 6 | `export_customer_data` / `erase_customer` | `crm` | Không | Nội bộ |
| 7 | **`SalesOrder.customer_id`** — gắn KH vào đơn bán | `sales` ↔ `crm` | 🔴 **CÓ** | Nợ cũ §7i mục 3. Xem Q5 |
| 8 | Luồng `clinical` tự động đọc dị ứng có ghi audit không | `clinical` ↔ `crm` ↔ `core/audit` | 🟠 **CÓ (nếu chọn ghi)** | Xem Q3 |
| 9 | Ghi `MedicationHistoryEntry` từ `SaleCompleted`/`PrescriptionDispensed` | `sales`/`prescription` → `crm` | 🔴 **CÓ** | Nợ cũ §7i mục 2. **Đề xuất để NGOÀI phạm vi** |

**Rủi ro cần nói thẳng:**

1. **Việc #7 (`SalesOrder.customer_id`) là cross-module thật và có migration đụng bảng đang có dữ
   liệu.** Đây là thứ duy nhất trong danh sách không revert được bằng `git revert` đơn thuần. Nếu
   sếp muốn giữ phạm vi gọn, tách nó ra làm bước riêng sau — nhưng khi đó *lý do* mở `crm.read` cho
   thu ngân tạm thời chưa dùng đến (họ tra được KH nhưng chưa gắn được vào đơn).
2. **Việc #8 có thể làm audit_logs phình rất nhanh.** Mỗi lần bán hàng có KH đều chạy safety check
   → mỗi giao dịch sinh thêm 1 bản ghi audit. Với POS bán vài trăm đơn/ngày/chi nhánh thì đây là
   quyết định về dung lượng, không chỉ về tuân thủ.
3. **Không có việc nào đụng `compliance`** — sổ thuốc kiểm soát giữ nguyên, không rủi ro spec đã khóa.

---

## Câu hỏi mở — cần sếp quyết trước khi code (Bước 4)

| # | Câu hỏi | Đề xuất của Trợ lý Code | Rủi ro nếu chọn khác |
|---|---------|------------------------|---------------------|
| **Q1** | Đồng ý tách mấy mức? | **2 mức**: `BASIC` (tên/SĐT) + `HEALTH` (dị ứng/bệnh nền/lịch sử) | Nhiều mức hơn = UX quầy thuốc nặng, nhân viên bấm bừa cho xong ⇒ đồng ý hình thức, tệ hơn về pháp lý |
| **Q2** | 🔴 **Rút đồng ý/yêu cầu xóa vs nghĩa vụ lưu ≥1 năm của GPP — xử lý mâu thuẫn thế nào?** | **Khử nhận dạng thay vì xóa cứng**: gỡ định danh (tên/SĐT/CCCD hash) nhưng giữ dòng lịch sử bán/cấp phát đã gắn nghĩa vụ lưu trữ. **CẦN LUẬT SƯ XÁC NHẬN** | Xóa cứng có thể vi phạm GPP II.4.d; giữ nguyên có thể vi phạm Luật 91 Điều 13-14. Đây là **mâu thuẫn pháp lý thật giữa 2 văn bản**, tôi không tự kết luận |
| **Q3** | Luồng `clinical` **tự động** đọc dị ứng khi bán hàng — có ghi `CUSTOMER_SENSITIVE_READ` không? | **Có, nhưng dùng action riêng** `CUSTOMER_SENSITIVE_AUTO_CHECK` để không lẫn với người thật mở hồ sơ | Gộp chung: báo cáo "ai xem hồ sơ" sẽ đầy bản ghi máy, che mất hành vi người. Không ghi gì: thủng đúng chỗ NĐ356 Điều 4.2 quan tâm |
| **Q4** | Thu ngân được `crm.read` + `crm.create` + `crm.consent.manage`? (đảo D8) | **Có** — tiền đề của D8 đã đổi (quyền được tách, bán hàng cần gắn KH) | Không mở: thu ngân không tra được KH ⇒ tính năng gắn KH vào đơn vô dụng ở quầy |
| **Q5** | `SalesOrder.customer_id` làm trong phạm vi này hay tách bước riêng? | **Tách bước riêng sau**, để phạm vi này không có cross-module + migration đụng bảng có dữ liệu | Làm chung: phạm vi phình, rủi ro migration cao hơn, nhưng đổi lại tính năng dùng được ngay |
| **Q6** | Nghĩa vụ DPIA đổ lên tenant (kể cả nhà thuốc nhỏ) — BeraLLC hỗ trợ tới đâu? | Cung cấp **mẫu hồ sơ DPIA + endpoint trích xuất metadata**; không nộp thay khách hàng | Bán tính năng mà không nói rõ nghĩa vụ kèm theo = rủi ro thương mại + pháp lý cho chính BeraLLC |
| **Q7** | Ghi `MedicationHistoryEntry` tự động từ bán hàng/cấp phát (nợ §7i mục 2) | **Ngoài phạm vi** — cross-module riêng | Nếu gộp: 2 cross-module trong 1 sprint |

---

## Phạm vi đề xuất (nếu sếp duyệt nguyên trạng)

**TRONG:** `CustomerConsent` (domain+bảng+use-case) · tách 4 permission crm · 5 action audit mới ·
`crm` ghi audit khi đọc/ghi dữ liệu nhạy cảm · `export_customer_data` · `erase_customer` (theo Q2) ·
cập nhật 5 role hệ thống + `sync_system_roles` trên CSDL thật · tài liệu chính sách lưu trữ.

**NGOÀI (ghi nợ rõ, không im lặng bỏ):** `SalesOrder.customer_id` (Q5) · ghi
`MedicationHistoryEntry` tự động (Q7) · luồng "người đại diện" cho bệnh nhân trẻ em (Luật 91 Điều
24 — chưa có nhu cầu, nhưng nếu nhập KH là trẻ em thì form người lớn dùng chung là **sai luật**) ·
diễn tập restore · xóa tự động theo hạn lưu trữ.
