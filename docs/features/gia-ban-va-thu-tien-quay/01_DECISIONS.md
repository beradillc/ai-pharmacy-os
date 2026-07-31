# Quy định giá bán & thu tiền ở quầy — Bước 0-3 của `docs/14_FEATURE_PROCESS.md`

> **Trạng thái: BƯỚC 0-3 ✅ — Chain giao trực tiếp 2026-07-31.**
> Sinh từ yêu cầu của Chain: *"rà soát cách quy định giá bán ra. Áp dụng cho chủ chuỗi
> cửa hàng mới quy định được. Ghi nhận lại biến động giá mỗi lần điều chỉnh. Ngoài ra
> triển khai phần thành tiền, nhận tiền, tiền thối lại… như một phần mềm bán hàng
> chuyên nghiệp."*
>
> Tổng số bước triển khai **chốt là 6** (kỷ luật #12 cấm mẫu số mở) — xem cuối tệp.

## Hiện trạng đo được trước khi làm (grep trên mã, không đọc tài liệu)

| Câu hỏi | Hiện trạng | Chỗ trong mã |
|---|---|---|
| Giá bán nằm ở đâu | `drugs.sale_price`, `Numeric(18,2)`, cho phép NULL | `catalog/infrastructure/models.py:40` |
| Đặt giá lúc nào | **Chỉ lúc tạo thuốc**, `POST /drugs` | `catalog/interface/router.py:33` |
| Sửa giá sau đó | **Không có endpoint nào** | router chỉ có `POST` · `GET` · `PUT /ingredients` |
| Ai được đặt giá | `catalog.create`/`catalog.update` — **đã là quyền cấp chuỗi**; Dược sĩ chi nhánh và Thu ngân bị loại trừ tường minh | `iam/domain/system_roles.py:181` |
| Quầy có bị ép theo giá chuỗi | **Không** — `POST /sales` nhận `unit_price` từ máy khách, không đối chiếu | `sales/interface/schemas.py:27` |
| Quầy lấy giá ở đâu | `drug.sale_price` nếu có; **null thì hỏi thu ngân gõ tay** | `(pos)/page.tsx:56–68` |
| Biến động giá | **Không bảng nào** — đổi giá là ghi đè | `grep price_history` → 0 |
| Tiền khách đưa / thối lại | **Không có** — quầy gửi cứng `payments: [{CASH, đúng bằng tổng}]` | `features/sales/use-checkout.ts:65` |

Kỷ luật #16 đã chạy: `grep price` trong `api/v1/cross_module.py`, `api/v1/__init__.py`,
`modules/*/domain/rules.py` → **0 kết quả**. Không có mảnh nào nối dây sẵn.

## Bước 0 — Đích (DoD ngược)

| Vai | Khi xong làm được gì |
|---|---|
| Chủ chuỗi | Đặt và **sửa** giá bán của từng thuốc từ màn Danh mục thuốc; xem toàn bộ lịch sử giá của một mã |
| Dược sĩ chi nhánh · Thu ngân | **Không** đổi được giá danh mục (không thấy nút) |
| Thu ngân | Ở quầy thấy **thành tiền · khách đưa · thối lại**, có nút mệnh giá nhanh; bán lệch giá niêm yết thì phải ghi lý do |
| Quản lý | Truy được: giá mã X đổi mấy lần, ai đổi, lúc nào, từ bao nhiêu sang bao nhiêu, vì sao |

**Bằng chứng khi bị hỏi:**

| Câu hỏi | Hệ thống trả lời bằng |
|---|---|
| "Giá niêm yết của mã X ngày 12/7 là bao nhiêu?" | `drug_price_history` — bảng chỉ-ghi-thêm, mỗi dòng có giá cũ, giá mới, người đổi, thời điểm |
| "Ai hạ giá mã này?" | Cùng bảng trên + audit log `DRUG_PRICE_CHANGED` |
| "Đơn này bán lệch giá niêm yết, vì sao?" | `price_override_reason` trên đơn + audit `SALE_PRICE_OVERRIDE` |
| "Quầy tự đổi giá danh mục được không?" | Không — `catalog.update` là quyền cấp chuỗi, `require_permission` chặn ở service |

## Bước 1 — Checklist Compliance / Privacy by Design

| # | Mục | Trả lời |
|---|---|---|
| 1 | **Căn cứ pháp lý** | ✅ **Có, và đã nằm sẵn trong `docs/legal/`.** `Luật-105-2016-QH13.SUMMARY.md`: **Điều 107.4** — niêm yết giá bán lẻ bằng VNĐ tại nơi bán; **Điều 6.5.i** — cấm *"Bán thuốc cao hơn giá kê khai, giá niêm yết"*. Chính tệp đó đã ghi chú: *"Không có enforcement tự động trong `sales` hiện tại"* — khoảng trống này là thứ mục này đóng |
| 2 | Đồng ý (consent) | **N/A** — giá thuốc là dữ liệu của doanh nghiệp, không phải dữ liệu chủ thể khách hàng. Không trường nào của khách đi vào đây |
| 3 | Phân loại dữ liệu | **Không phải dữ liệu cá nhân nhạy cảm.** Là dữ liệu giá + `user_id` người đổi giá (đã có trong `users`, không nhân bản) |
| 4 | **Audit log bất biến** | Bắt buộc. Hai `AuditAction` mới: `CATALOG_DRUG_PRICE_CHANGED` (26 ký tự), `SALE_PRICE_OVERRIDE` (19). ⚠️ Kỷ luật #7 ghi sự cố `audit_logs.action` varchar(32) — **đã đo lại bằng truy vấn thật trên `nt650v2`: nay là varchar(64)**, và `CATALOG_DRUG_INGREDIENTS_REPLACED` (33 ký tự) đang dùng được chứng minh điều đó. Cả hai tên mới đều vừa. `drug_price_history` là bảng **chỉ-ghi-thêm**: không `UPDATE`, không `DELETE` |
| 5 | RBAC | ✅ Đã thoả — JWT thật. **Không thêm quyền mới**: dùng lại `catalog.update` (đã là cấp chuỗi, đã loại trừ dược sĩ chi nhánh và thu ngân đúng như Chain yêu cầu). Thêm quyền mới ở đây sẽ tạo ra một tầng phân quyền thứ hai cho cùng một khái niệm — xem Bước 2 |
| 6 | Backup / restore | Bảng mới ⇒ nằm trong cùng `pg_dump` toàn CSDL (runbook F-16). Không kho dữ liệu riêng |
| 7 | AI / RAG | **N/A** — không dùng `LLMProvider` |
| 8 | Rà theo Luật Dược + BVDLCN + NĐ 356 + GPP | Luật Dược: xem mục 1. Luật BVDLCN 91/2025: không chạm dữ liệu cá nhân. NĐ 356/2025 và GPP TT02/2018: giá là nghĩa vụ **niêm yết**, đã khớp; không phát sinh yêu cầu mới. **Luật Giá 16/2023 (sửa bởi Luật 44/2024)**: `Luật-44-2024-QH15.SUMMARY.md` dòng 13 nói phần sửa liên quan **giá bán buôn dự kiến** — không phải bán lẻ; ghi nhận là **chưa kết luận được** cho phần bán buôn, không suy diễn (quy tắc R-10) |

### 🟠 Cờ pháp lý giữ lại — Chain đã quyết, ghi để truy được về sau

GĐ nêu tại phiên 31/07: Điều 6.5.i cấm bán **cao hơn** giá niêm yết, nên đề nghị làm bất
đối xứng (cao hơn ⇒ chặn; thấp hơn ⇒ cho, kèm lý do). **Chain giữ nguyên quyết định ban
đầu: cả hai chiều đều cho bán, đều đòi lý do, đều vào audit.**

Ghi lại nguyên văn đánh đổi để phiên sau không phải đoán: cách này giữ được linh hoạt ở
quầy (khuyến mãi, làm tròn, khách quen, mặt hàng chưa kịp cập giá), đổi lại **hệ thống
không chặn hành vi mà Điều 6.5.i cấm** — nó chỉ ghi lại. Nếu về sau muốn siết, chỗ sửa là
đúng một quy tắc miền (`sales/domain/rules.py`), không phải sửa lược đồ. Đây là **cờ**,
không phải khẳng định pháp lý — theo tiền lệ giữ điều chưa xác nhận ở dạng cờ.

## Bước 2 — Rà chồng lấn với module đã có

| Khái niệm định thêm | Đã có gì tương tự | Quyết định |
|---|---|---|
| Giá bán của thuốc | `drugs.sale_price` **đã tồn tại** | **Không tạo entity mới.** Chỉ thêm đường sửa + bảng lịch sử |
| Lịch sử giá | `grep price_history` → 0 | Bảng mới `drug_price_history` |
| Quyền đổi giá | `catalog.update` đã là cấp chuỗi | **Dùng lại**, không thêm quyền |
| Tiền khách đưa / thối lại | `docs/features/so-quy/01_DECISIONS.md` (Bước 0-3 đã duyệt, **chưa code**) nói về **ca làm việc và đối chiếu két** | **Không chồng lấn.** Sổ quỹ = tiền trong két theo ca; thối lại = phép tính tại một đơn. Mục này **không** động tới sổ quỹ, và cố ý không tạo bảng nào để sổ quỹ sau này không phải gỡ ra |
| `payments[]` nhiều phương thức | `PaymentMethod` đã có `CASH · CARD · TRANSFER · EWALLET · VNPAY`, `payments` đã là danh sách | Lượt này **chỉ làm tiền mặt** (Chain chọn). Không đụng hợp đồng `payments` |

### 🔴 Quyết định quan trọng nhất của Bước 2: tiền khách đưa **KHÔNG** phải `payments[].amount`

`SaleOrder.complete()` đòi `paid_total >= subtotal` (`sales/domain/entities.py:169`) — trả
thừa thì **được chấp nhận, không báo lỗi**. Nếu quầy gửi `amount` = tiền khách đưa
(100.000đ cho đơn 87.000đ) thì đơn vẫn hoàn tất, nhưng `paid_total` ghi 100.000đ và hoá
đơn in ra số đó.

⇒ **Tiền khách đưa và tiền thối là phép tính của quầy, không phải số tiền của đơn.**
`payments[].amount` giữ nguyên = tổng đơn. Nhờ vậy lượt này **không đổi một dòng hợp đồng
API nào** — bốn câu hỏi tương thích của kỷ luật #17 đều trả lời được ngay: frontend cũ
chạy, API cũ chạy, CSDL cũ chạy, migration lùi được (bảng mới + cột nullable).

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module

| Bước | Module đụng | Cross-module? |
|---|---|---|
| Giá + lịch sử giá | `catalog` | **Không** — nội bộ một module |
| Đối chiếu giá khi bán | `sales` **đọc** `catalog` | 🔴 **CÓ** — `sales` phải biết `sale_price` của thuốc |
| Tiền mặt ở quầy | frontend | Không |

**Rủi ro cross-module và cách xử:** `sales` **đã** đọc `catalog` sẵn — `_resolve_requires_rx`
tra `catalog` để lấy cờ Rx cho từng dòng. Việc lấy thêm `sale_price` đi **đúng đường đã
có**, không mở điểm nối mới, không đụng `cross_module.py`.

Kèm theo đó là hành vi đã ghi ở §7cl: `_resolve_requires_rx` gặp thuốc lạ thì
`return line.requires_prescription  # unknown drug — trust the caller`. Với giá thì **không
thể "tin bên gọi"** — không có giá niêm yết để đối chiếu. Quy tắc: thuốc không tra được
`sale_price` (chưa đặt giá, hoặc mã lạ) ⇒ **không coi là lệch giá**, không đòi lý do. Ghi
rõ ở đây để phiên sau không tưởng đó là lỗ hổng bị bỏ quên.

## 6 bước triển khai (chốt, kỷ luật #12)

| # | Việc | Cổng |
|---|---|---|
| 1 | Tệp này (Bước 0-3 docs/14) — **không code** | — |
| 2 | `catalog` domain thuần: quy tắc đổi giá + entity `DrugPriceChange` | 4 cổng |
| 3 | `catalog` app + infra + migration: use-case `set_drug_price`, repo, bảng `drug_price_history`, audit action | 4 cổng + pg_dump trước migration |
| 4 | `catalog` interface: `PUT /drugs/{id}/price` · `GET /drugs/{id}/price-history` | 4 cổng |
| 5 | `sales`: đối chiếu giá, lệch ⇒ đòi `price_override_reason` + audit (+ ADR-0003) | 4 cổng |
| 6 | Giao diện: cột giá + sửa giá + lịch sử ở Danh mục thuốc; quầy: thành tiền · khách đưa · thối lại · nút mệnh giá nhanh | `make check-ui` + ảnh cả 2 khổ |
