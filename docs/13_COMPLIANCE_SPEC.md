# 13 — COMPLIANCE SPEC (Đặc tả Tuân thủ Pháp lý)

> Nguồn sự thật pháp lý cho module `compliance`. Distilled từ văn bản gốc.
> Đặt tại `docs/13_COMPLIANCE_SPEC.md`. Mọi field/rule trong module `compliance`
> phải truy vết được về một mục trong file này.
>
> **Văn bản nguồn (đã đọc, có file gốc tại `docs/legal/`):**
> - **QĐ 540/QĐ-QLD (20/8/2018)** — Chuẩn yêu cầu dữ liệu đầu ra phần mềm kết nối liên thông cơ sở bán lẻ thuốc, v1.0. (`docs/legal/540_QD-QLD_m_391359.docx`)
> - **TT 20/2017/TT-BYT (10/5/2017)** — Thuốc & nguyên liệu phải kiểm soát đặc biệt. (`docs/legal/Thông-tư-20-2017-TT-BYT.docx`)
> - **QĐ 1867/QĐ-BYT (24/6/2026)** — Kế hoạch triển khai Hệ thống CSDL về dược. (`docs/legal/Quyết-định-1867-QĐ-BYT.docx`)
>
> **⚠️ Văn bản CÒN THIẾU (chặn phần kết nối thật — phải lấy trước khi wiring production):**
> - Tài liệu **đặc tả API** kết nối CSDL Dược (do **Trung tâm Thông tin y tế Quốc gia** ban hành theo QĐ 1867 mục 1.2 — hoàn thành 6/2026). **Chưa có trong tay.**
> - **TT 11/2025/TT-BYT** (sửa đổi TT 02/2018, TT 03/2018, TT 36/2018) và **NĐ 163/2025/NĐ-CP** — QĐ 1867 dẫn chiếu ở phần "Căn cứ", có thể đổi field bắt buộc. **Chưa có trong tay.**
> - **NĐ 90/2026/NĐ-CP** — chế tài xử phạt không liên thông (QĐ 1867 mục V.4.d dẫn chiếu). **Chưa có trong tay.**
> - Văn bản quy định **kê đơn thuốc ngoại trú** hiện hành (áp dụng cho `RxClass.ETC` nói chung — TT 20/2017 CHỈ điều chỉnh thuốc kiểm soát đặc biệt, không phải mọi thuốc kê đơn). TT 20/2017 Điều 18.1 dẫn chiếu TT 05/2016/TT-BYT cho việc lưu đơn thuốc GN/HT, nhưng đó cũng không phải nguồn cho rule "mọi thuốc ETC cần prescription_code". **Chưa có trong tay — xem mục C.3.**

---

## Traceability (đối chiếu Bước 2, Bước 3)

| #   | Mục spec                                               | Dẫn chiếu văn bản gốc / code                                                                                       |                                                                                                                                                                                            Trạng thái                                                                                                                                                                                            |
| --- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| 1   | A. `to_qld_date`                                       | QĐ540 Bảng 1 mục 14 `han_dung` (VD gốc: 15/12/2018 → 20181215)                                                     |                                                                                                                                                                                               KHỚP                                                                                                                                                                                               |
| 2   | A. `to_qld_datetime`                                   | QĐ540 Bảng 1 mục 20/21 `ngay_nhap`/`ngay_ban` (VD gốc: 10:30 08/08/2018 → 201808081030)                            |                                                                                                                                                                                               KHỚP                                                                                                                                                                                               |
| 3   | A. `to_qld_code`                                       | QĐ540 Bảng 1 mục 1 `ma_thuoc` (VD gốc: `VN-12345-18-lọ 200 viên` → `VN1234518lo200vien`)                           |                                                                                                          **SAI** — thiếu quy tắc bỏ dấu tiếng Việt (bản gốc bỏ dấu "lọ"→"lo", "viên"→"vien"); ví dụ cũ tự đổi sang chữ HOA không đúng bản gốc (bản gốc giữ nguyên chữ thường) → đã sửa                                                                                                           |
| 4   | B. 23 trường Bảng 1                                    | QĐ540 **Bảng 1** "Chuẩn dữ liệu đầu ra kết nối Bộ Y tế/Sở Y tế"                                                    |                                                                                                                                                               KHỚP — đối chiếu từng trường (tên, kiểu, cỡ, bắt buộc) khớp bản gốc                                                                                                                                                                |
| 5   | B mục 3 mapping `so_dang_ky`                           | `catalog.drug.registration_no`                                                                                     |                                                                                                                                                     KHỚP — field tồn tại (`entities.py:46`), nhưng **chưa có unique constraint** (xem mục F)                                                                                                                                                     |
| 6   | B mục 11 mapping `don_vi_dong_goi_nn`                  | `catalog.DrugUnit` base unit                                                                                       |                                                                                                   **SAI** — field thật là `catalog.Drug.base_unit` (chuỗi mô tả đơn vị nhỏ nhất trên `Drug`, không phải `DrugUnit`); `DrugUnit.factor` chỉ là hệ số quy đổi giữa các đơn vị đóng gói → đã sửa                                                                                                    |
| 7   | B mục 13 mapping `so_lo`                               | `inventory.ProductBatch.batch_no`                                                                                  |                                                                                                                                         **SAI** — field thật tên là `lot_no` (`entities.py:30`, `models.py:23`), không tồn tại field `batch_no` → đã sửa                                                                                                                                         |
| 8   | B mục 17 mapping `so_luong_ton`                        | `inventory.stock_balances`                                                                                         |                                                                              KHỚP — bảng thật `StockBalanceORM` (`__tablename__ = "stock_balances"`), tenant-scoped, unique theo (drug, batch, branch); là bảng lưu trữ được cập nhật qua service layer (read-then-upsert), không phải SQL view — đã làm rõ ghi chú                                                                              |
| 9   | B.1 cũ: "Bảng 2 QĐ 540 — Chuẩn Giao dịch Nhập kho"     | QĐ540 **Bảng 2 thật** = "Chuẩn dữ liệu đầu ra tổng hợp thông tin chung trên địa bàn tỉnh/TP" (18 trường, cấp tỉnh) |                                                            **SAI** — tên bảng và toàn bộ nội dung không khớp bản gốc. Các trường "nhập kho" (`so_hoa_don_nhap`, `ten_co_so_ban_buon`, `ma_so_thue_ncc`, `don_gia_nhap`) **không xuất hiện ở bất kỳ đâu** trong QĐ540 (Bảng 1-4) → đã XÓA, không bịa; đã viết lại đúng bản chất Bảng 2                                                            |
| 10  | B.2 cũ: "Bảng 3 QĐ 540 — Chuẩn Giao dịch Bán theo Đơn" | QĐ540 **Bảng 3 thật** = "Chuẩn dữ liệu đầu ra đối với đơn thuốc"                                                   |                                                                                                KHỚP phần lớn — tên gọi trong spec hơi khác nhưng nội dung field đúng; **thiếu** các trường dòng thuốc trong đơn (`ma_thuoc`, `ten_hoat_chat`, `ten_thuoc`) có trong bản gốc → đã bổ sung ghi chú                                                                                                 |
| 11  | C.1 phân loại                                          | TT20/2017 Điều 3 khoản 1–6                                                                                         |                                                                                                                                                                                               KHỚP                                                                                                                                                                                               |
| 12  | C.2 nghĩa vụ bán lẻ GN/HT/TC                           | TT20/2017 Điều 15.1 (a–đ)                                                                                          |                                                **THIẾU** — bỏ sót nghĩa vụ (b) "Phiếu xuất kho của nơi cung cấp" và (d) "Biên bản nhận thuốc gây nghiện Phụ lục XX" (mục này đã ghi ngoài phạm vi ở mục G, cần dẫn chiếu rõ); đồng thời "lưu đơn thuốc sau khi bán" theo bản gốc (c) **CHỈ áp dụng GN/HT**, KHÔNG áp dụng TC (tiền chất) → đã sửa                                                |
| 13  | C.2 dạng phối hợp                                      | TT20/2017 Điều 15.2                                                                                                |                                                                                                                                                                                               KHỚP                                                                                                                                                                                               |
| 14  | C.3 rule 1 (ETC nói chung)                             | Luật Dược 105/2016/QH13 Điều 2.27–28 (định nghĩa thuốc kê đơn/không kê đơn) + Điều 6.5.h (cấm bán lẻ thuốc kê đơn mà không có đơn thuốc)                                                                                                  |                                                         **ĐÃ TÌM THẤY (bổ sung 2026-07-23)** — TT20/2017 vẫn chỉ điều chỉnh thuốc kiểm soát đặc biệt (GN/HT/TC/phóng xạ), không điều chỉnh ETC nói chung, nhưng Luật Dược Điều 2.27–28 + Điều 6.5.h là nguồn cấp Luật cho rule "mọi thuốc ETC cần đơn thuốc" — giữ nguyên rule, chỉ bổ sung trích dẫn nguồn                                                         |
| 15  | C.3 rule 2 (GN/HT/TC, patient_id CCCD)                 | "Theo Phụ lục XXI TT 20/2017"                                                                                      | **SAI** — Phụ lục XXI (Sổ theo dõi thông tin chi tiết khách hàng) thật chỉ có 9 cột: *Ngày tháng, Số TT, Tên thuốc/quy cách đóng gói, Hoạt chất/nồng độ-hàm lượng, Đơn vị tính, Số lượng bán, Tên khách hàng, Địa chỉ, Ghi chú* — **KHÔNG có cột số CCCD/CMND** → đã sửa lại trích dẫn, tách `patient_id` thành yêu cầu nghiệp vụ bổ sung của hệ thống (không phải bắt buộc theo mẫu sổ pháp lý) |
| 16  | C.4 lưu trữ                                            | TT20/2017 Điều 18.1 ("ít nhất hai (02) năm kể từ ngày ... hết hạn dùng")                                           |                                                                                                                                                                                               KHỚP                                                                                                                                                                                               |
| 17  | D.1 yêu cầu liên thông                                 | QĐ1867 Mục I.2; Luật Dược 105/2016/QH13 Điều 75.2 (sửa bởi Luật 44/2024/QH15 — Bộ Y tế quy định liên thông dữ liệu với hệ thống thông tin về dược trong CSDL quốc gia về y tế)                                                                                                     |                                                                                          KHỚP nội dung, nhưng trích dẫn cũ "Mục I.2, II.3" không chính xác — câu "đúng, đủ, sạch, sống, thống nhất, dùng chung" chỉ nằm ở I.2; II.3 nói về tiến độ khởi tạo kết nối (nội dung khác) → đã sửa trích dẫn. Bổ sung 2026-07-23: Điều 75.2 Luật Dược là nguồn cấp Luật cao nhất cho yêu cầu liên thông này, QĐ1867 chỉ là kế hoạch triển khai chi tiết hơn                                                                                           |
| 18  | D.3 ghi chú blocker                                    | QĐ1867 mục 1.2; phần "Căn cứ" dẫn TT11/2025 + NĐ163/2025; mục V.4.d dẫn NĐ90/2026                                  |                                                                                                                                                                                KHỚP — đối chiếu chính xác câu chữ                                                                                                                                                                                |
| 19  | G. Bảng 4 QĐ540                                        | QĐ540 **Bảng 4** "Yêu cầu chức năng thống kê" (xuất PDF/Excel)                                                     |                                                                                                                                                       **THIẾU** — chưa được đề cập ở đâu trong spec cũ → đã bổ sung vào mục ngoài phạm vi                                                                                                                                                        |
| 20  | F. tenant config `ma_co_so_ban_le`/`ma_co_so_ban_buon` | Code hiện tại                                                                                                      |                                                                                  **GAP** — không tồn tại bảng cấu hình tenant nào (chỉ có `tenant_id`/`branch_id` dạng UUID scoping trong `TenantScopedMixin`/`RequestContext`). Phải **tạo mới** entity, không phải "thêm field" vào bảng đã có → đã sửa mục F                                                                                  |

---

## A. Quy chuẩn Định dạng Dữ liệu & Converter Helpers (QĐ 540)

Để bảo đảm Domain Purity, CSDL nội bộ dùng kiểu `datetime`/`date` chuẩn ISO. Khi đồng bộ dữ liệu lên cổng CSDL Dược Quốc gia, hệ thống bắt buộc chạy qua các hàm chuyển đổi (Helpers):

1. **`to_qld_date(d: date) -> int`**: Chuyển ngày sang dạng số 8 chữ số **`YYYYMMDD`** (VD: `20260721`).
2. **`to_qld_datetime(dt: datetime) -> int`**: Chuyển ngày giờ sang dạng số 12 chữ số **`YYYYMMDDHHmm`** (VD: `202607211305`).
3. **`to_qld_code(s: str) -> str`**: Mã hóa mã thuốc — loại bỏ khoảng trắng, dấu gạch ngang, **và dấu tiếng Việt** (theo đúng ví dụ trong văn bản gốc). VD gốc (QĐ540 Bảng 1 mục 1): `VN-12345-18-lọ 200 viên` → `VN1234518lo200vien` (giữ nguyên chữ thường, không viết hoa).

---

## B. NationalDrugCatalog — 23 trường chuẩn đầu ra (QĐ 540, Bảng 1)

Đây là "hợp đồng dữ liệu" bắt buộc khi đẩy danh mục lên cổng CSDL Dược Quốc gia.

| # | Field | Kiểu | Cỡ | Bắt buộc | Ghi chú format & Mapping |
|---|-------|------|-----|:---:|----------------|
| 1 | `ma_thuoc` | str | 50 | ✔ | SĐK + quy cách nhỏ nhất, **đã mã hóa** qua `to_qld_code()` |
| 2 | `ten_thuoc` | str | 50 | ✔ | Theo tên được cấp SĐK |
| 3 | `so_dang_ky` | str | 20 | ✔ | VD `VD-12345-17`. **→ map từ `catalog.drug.registration_no`** (field tồn tại — chưa unique, xem mục F) |
| 4 | `ten_hoat_chat` | str | 50 | ✔ | Chỉ ghi khi thuốc có ≤ 3 dược chất |
| 5 | `nong_do_ham_luong` | str | 20 | ✔ | Theo danh mục Cục QLD công bố |
| 6 | `nha_san_xuat` | str | 100 | ✔ | |
| 7 | `nuoc_san_xuat` | str | 20 | ✔ | |
| 8 | `nha_nhap_khau` | str | 100 | ✔ | |
| 9 | `quy_cach_dong_goi` | str | 20 | ✔ | hộp/viên/lọ/chai... |
| 10 | `dang_bao_che` | str | 20 | ✔ | Theo danh mục cấp SĐK |
| 11 | `don_vi_dong_goi_nn` | str | 20 | ✔ | Đơn vị đóng gói nhỏ nhất (Khoản 4, Điều 136, NĐ 54/2017/NĐ-CP). **→ map từ `catalog.Drug.base_unit`** (KHÔNG phải `DrugUnit` — `DrugUnit.factor` chỉ là hệ số quy đổi) |
| 12 | `gia_ban_le` | num | 10 | ✔ | Theo đơn vị nhỏ nhất |
| 13 | `so_lo` | str | 20 | ✔ | **→ `inventory.ProductBatch.lot_no`** (field thật tên `lot_no`, KHÔNG phải `batch_no`) |
| 14 | `han_dung` | num | 8 | ✔ | **`YYYYMMDD`** qua `to_qld_date()` |
| 15 | `so_luong_nhap` | num | — | ✔ | Theo đơn vị nhỏ nhất |
| 16 | `so_luong_ban` | num | — | ✔ | Theo đơn vị nhỏ nhất |
| 17 | `so_luong_ton` | num | — | ✔ | Theo đơn vị nhỏ nhất. **→ `inventory.stock_balances`** (bảng `StockBalanceORM`, cập nhật qua service layer — không phải SQL view) |
| 18 | `don_vi_bthuoc_cho_csbl` | str | 100 | ✔ | Tên đơn vị bán thuốc cho cơ sở bán lẻ |
| 19 | `so_hoa_don_mthuoc` | str | 20 | ✔ | Số hóa đơn VAT mua thuốc |
| 20 | `ngay_nhap` | num | 12 | ✔ | **`YYYYMMDDHHmm`** qua `to_qld_datetime()` |
| 21 | `ngay_ban` | num | 12 | ✔ | **`YYYYMMDDHHmm`** qua `to_qld_datetime()` |
| 22 | `ma_co_so_ban_le` | str | 12 | ✔ | **Do Cục QLD cấp — cấu hình trong tenant config** (bảng này CHƯA tồn tại, xem mục F) |
| 23 | `ma_co_so_ban_buon` | str | 12 | ✔ | Do Cục QLD cấp cho nhà cung cấp |

### B.1 Bảng 2 QĐ 540 — Chuẩn dữ liệu tổng hợp cấp tỉnh/thành phố

> **Đính chính:** Bảng 2 QĐ540 **không phải** "Chuẩn Giao dịch Nhập kho" như bản spec trước ghi nhầm. Tên gọi thật: *"Chuẩn yêu cầu dữ liệu đầu ra phần mềm tổng hợp các thông tin chung trên địa bàn tỉnh, thành phố"* — đây là dữ liệu **tổng hợp cấp tỉnh** (do phần mềm Sở Y tế tổng hợp từ nhiều cơ sở bán lẻ), không phải một giao dịch nhập kho của từng cơ sở.

Gồm 18 trường: `ma_thuoc`, `ten_thuoc`, `so_dang_ky`, `ten_hoat_chat`, `nong_do_ham_luong`, `nha_san_xuat`, `nuoc_san_xuat`, `nha_nhap_khau`, `quy_cach_dong_goi`, `dang_bao_che`, `don_vi_dong_goi_nn`, `gia_ban_le` (cỡ 8, khác Bảng 1), `so_lo`, `han_dung`, `so_luong_nhap`, `so_luong_ban`, `so_luong_ton`, và `ngay_tong_hop` (`YYYYMMDD`).

> Các trường "giao dịch nhập kho" mà bản spec cũ liệt kê (`so_hoa_don_nhap`, `ten_co_so_ban_buon`, `ma_so_thue_ncc`, `don_gia_nhap`) **không có nguồn** trong QĐ540 (đã rà cả 4 bảng) — đã **XÓA**, không bịa thêm. Thông tin nhập kho liên quan (số hóa đơn, mã cơ sở bán buôn, ngày nhập) đã được phủ bởi các trường 19/23/20 trong Bảng 1 ở mục B — không cần một chuẩn riêng.
>
> Vì Bảng 2 là dữ liệu **tổng hợp cấp tỉnh do Sở Y tế/hệ thống trung ương tính toán**, module `compliance` ở cơ sở bán lẻ **không cần tự sinh** bảng này — chỉ cần bảo đảm dữ liệu Bảng 1 (mục B) đủ, đúng, sạch để hệ thống trung ương tổng hợp lên Bảng 2. Ghi chú TODO, không implement Bảng 2 trong sprint này.

### B.2 Bảng 3 QĐ 540 — Chuẩn dữ liệu đầu ra đối với đơn thuốc

Gồm: `ma_don_thuoc`, `ten_co_so_kcb`, `nguoi_ke_don`, `ho_ten_benh_nhan`, `tuoi_benh_nhan`, `dia_chi_benh_nhan`, `ten_benh`, `ma_benh` (ICD-10), `ngay_ke_don` (`YYYYMMDDHHmm`), `lieu_dung`.

> **Bổ sung (thiếu ở bản spec cũ):** bản gốc Bảng 3 còn có các trường dòng thuốc trong đơn: `ma_thuoc`, `ten_hoat_chat`, `ten_thuoc` (mỗi thuốc trong đơn cần các trường này, giống định dạng ở mục B). Cần đưa các trường này vào cấu trúc dữ liệu chi tiết đơn thuốc khi implement.

---

## C. ControlledDrugLedger — Sổ thuốc kiểm soát đặc biệt (TT 20/2017)

### C.1 Phân loại (Điều 3) — enum `ControlledSubstanceCategory`
- `GAY_NGHIEN` (gây nghiện)
- `HUONG_THAN` (hướng thần)
- `TIEN_CHAT` (tiền chất dùng làm thuốc)
- `PHOI_HOP_GN` (dạng phối hợp chứa gây nghiện)
- `PHOI_HOP_HT` (dạng phối hợp chứa hướng thần)
- `PHOI_HOP_TC` (dạng phối hợp chứa tiền chất)
- `NONE` (không thuộc diện kiểm soát — mặc định)

> Lưu ý: `RxClass.CONTROLLED` hiện có trong `catalog` là mức thô (đã xác nhận tồn tại tại `catalog/domain/entities.py`). Map: `RxClass.CONTROLLED` ⇒ phải có `ControlledSubstanceCategory ≠ NONE`.
>
> Phạm vi chỉ áp dụng module bán lẻ (TT20/2017 còn có thuốc phóng xạ/thuốc độc/danh mục cấm cho các loại hình cơ sở khác — ngoài phạm vi nhà thuốc bán lẻ, không đưa vào enum này).

### C.2 Nghĩa vụ với cơ sở BÁN LẺ (Điều 15)
**GN/HT/TC** (Điều 15.1) phải lập và ghi chép đầy đủ:
- (a) Sổ theo dõi xuất/nhập/tồn (Phụ lục VIII);
- (b) Phiếu xuất kho của nơi cung cấp thuốc (lưu chứng từ đầu vào);
- (c) Đơn thuốc gây nghiện, hướng thần lưu tại cơ sở sau khi bán — **chỉ áp dụng GN/HT, KHÔNG áp dụng TC** (tiền chất không có nghĩa vụ này theo văn bản gốc);
- (d) Biên bản nhận thuốc gây nghiện (Phụ lục XX) — **đã đưa ra ngoài phạm vi sprint này, xem mục G**;
- (đ) Sổ theo dõi thông tin chi tiết khách hàng (Phụ lục XXI).

**Dạng phối hợp** (Điều 15.2): Tối thiểu lưu Sổ thông tin chi tiết khách hàng (Phụ lục XXI).

### C.2.1 Cấu trúc `ControlledDrugLedger` (map từ mẫu sổ pháp lý)

Bảng ghi sổ trong hệ thống cần phủ đủ cột của 2 mẫu sổ bắt buộc:

- Từ **Phụ lục VIII** (xuất/nhập/tồn): `ngay_thang`, `noi_xuat_nhap`, `so_chung_tu`, `so_luong_nhap`, `so_luong_xuat`, `so_luong_con_lai`, `so_lo`, `han_dung`, `ghi_chu`.
- Từ **Phụ lục XXI** (thông tin khách hàng — chỉ áp dụng khi bán ra): `ngay_thang`, `so_thu_tu`, `ten_thuoc_quy_cach`, `hoat_chat_nong_do`, `don_vi_tinh`, `so_luong_ban`, `ten_khach_hang`, `dia_chi_khach_hang`, `ghi_chu`.

> Phụ lục XXI **không có cột số CCCD/CMND** — chỉ có "Tên khách hàng" và "Địa chỉ". Xem rule C.3.2 bên dưới.

### C.3 Rule kiểm tra bắt buộc khi tạo giao dịch Bán hàng (Validation Rules)
1. **Thuốc kê đơn (`RxClass.ETC`):**
   > ⚠️ **NGUỒN CHƯA XÁC ĐỊNH — chờ văn bản kê đơn ngoại trú hiện hành.**
   > TT 20/2017 không điều chỉnh thuốc kê đơn thông thường (chỉ điều chỉnh GN/HT/TC/phóng xạ) nên rule dưới đây **chưa có căn cứ pháp lý trực tiếp** trong 3 văn bản hiện có.
   - **Dự kiến (khi có nguồn):** `prescription_code` + `patient_name` + `doctor_name`. Thiếu → `422 Unprocessable Entity`.
   - **Trạng thái implement:** đưa vào domain dưới dạng **feature-flag/TODO**, KHÔNG hard-validate cho tới khi có văn bản xác nhận — ví dụ một cờ cấu hình kiểu `require_etc_prescription_fields: bool = False` (mặc định tắt) đặt cạnh rule, kèm comment `# TODO(compliance): bật khi có văn bản kê đơn ngoại trú hiện hành`. Khi có văn bản, chỉ cần bật cờ / đổi default, không thiết kế lại rule hay schema.
2. **Thuốc kiểm soát đặc biệt (`category ∈ {GAY_NGHIEN, HUONG_THAN, TIEN_CHAT}`):**
   - **BẮT BUỘC theo mẫu Phụ lục XXI:** `patient_name` (Tên khách hàng) + `patient_address` (Địa chỉ). Thiếu → Báo lỗi `422 Unprocessable Entity`.
   - `prescription_code`: bắt buộc khi GN/HT (đơn phải lưu tại cơ sở theo Điều 15.1.c); với TC không có yêu cầu lưu đơn theo văn bản gốc.
   - `patient_id` (Số CCCD/CMND): **không phải yêu cầu bắt buộc theo mẫu sổ Phụ lục XXI** (mẫu sổ không có cột này). Nếu giữ lại, cần ghi rõ đây là **yêu cầu nghiệp vụ bổ sung của hệ thống**, không phải trích dẫn pháp lý trực tiếp.
3. Ghi nhận giao dịch: Mỗi giao dịch controlled → ghi 1 dòng `ControlledDrugLedger` (immutable, không sửa/xóa cứng).

### C.4 Lưu trữ (Điều 18)
- Chứng từ/sổ lưu **tối thiểu 2 năm kể từ ngày thuốc hết hạn dùng** (Điều 18.1).
- ⇒ **KHÔNG hard-delete trong thời gian lưu trữ**. Dùng soft-delete + audit. Chính sách retention ≥ 2 năm sau `expiry_date`.
- Sau thời hạn lưu trữ, việc hủy hồ sơ là một quy trình hành chính riêng (lập hội đồng, biên bản hủy — Điều 18.2) — **ngoài phạm vi phần mềm sprint này**.

---

## D. NationalSyncLog — Liên thông CSDL Dược Quốc gia (QĐ 1867)

### D.1 Yêu cầu (Mục I.2)
- Cơ sở bán lẻ phải **cập nhật, đồng bộ, liên thông dữ liệu đầy đủ, chính xác, kịp thời** lên CSDL Dược.
- Tiêu chí: **"đúng, đủ, sạch, sống, thống nhất, dùng chung"** (theo Nghị quyết 214/NQ-CP) — đồng bộ gần real-time.
- Lưu credential kết nối an toàn (KHÔNG hard-code, KHÔNG log lộ).

> Đính chính: bản spec cũ trích "Mục I.2, II.3" — nội dung tiêu chí "đúng, đủ, sạch, sống..." chỉ nằm ở **Mục I.2**. Mục II.3 (QĐ1867) nói về tiến độ tổ chức khởi tạo/kết nối dữ liệu (mốc thời gian, đơn vị chủ trì), không phải yêu cầu chất lượng dữ liệu — đã tách trích dẫn cho chính xác.

### D.2 Bảng `NationalSyncLog` (audit truyền nhận)
Mỗi lần đẩy 1 bản ghi/lô: `id`, `tenant_id`, `payload_type` (drug/sale/prescription), `payload_hash`, `client_uuid` (idempotency), `status` (PENDING/SENT/ACK/FAILED), `request_at`, `response_at`, `response_code`, `response_body`, `retry_count`, `error`.

### D.3 ⚠️ CHẶN CỨNG & MOCK ADAPTER
- **Endpoint API thật CHƯA có** (QĐ1867 mục 1.2 — Trung tâm Thông tin y tế Quốc gia hoàn thành đặc tả API vào tháng 6/2026). Vì vậy:
  - Định nghĩa **port** `NationalDrugDbGateway` (interface thuần).
  - Hiện thực **MockAdapter** (trả ACK giả, ghi log) ở composition root để test toàn luồng.
  - **KHÔNG wiring endpoint thật** cho tới khi có tài liệu đặc tả. Đánh dấu rõ `# BLOCKER: DAV API spec` trong code.

---

## E. Ràng buộc kiến trúc (bắt buộc giữ)

- Module `compliance` theo **Hexagonal 4 lớp** (`domain` → `application` → `infrastructure` → `interface`). (Module chưa tồn tại trong code — xác nhận cần tạo mới từ đầu.)
- **Domain purity**: domain không import framework (SQLAlchemy/Pydantic/FastAPI).
- **Module-independence**: `compliance` KHÔNG import `catalog`/`sales`/`inventory`/`prescription`. Đọc dữ liệu qua **read-port** ở `compliance` và **adapter** ở composition root `api/v1/cross_module.py`.
- Tạo migration `0005_compliance`, autogenerate → apply live Postgres → `alembic check` không drift → reversible.
- 4 cổng chất lượng phải xanh: `ruff` · `mypy --strict` · `import-linter` (giữ ≥ 9 contract) · `pytest`.

---

## F. Nợ kỹ thuật liên quan (xử lý trong sprint này)

- **Enforce uniqueness `registration_no` (SĐK)** — Xác nhận field tồn tại (`catalog/domain/entities.py:46`, `infrastructure/models.py:29`) nhưng **hiện chưa có unique constraint nào** (đã grep, 0 kết quả). Bật unique constraint (theo tenant) trong migration `0005`.
- **Tạo bảng cấu hình tenant (chưa tồn tại)** — Đã xác nhận: hiện KHÔNG có `Tenant`/`TenantConfig` entity nào trong code, chỉ có `tenant_id`/`branch_id` dạng cột UUID scoping (`TenantScopedMixin`, `RequestContext`). Việc "thêm `ma_co_so_ban_le`/`ma_co_so_ban_buon`" thực chất là phải **tạo mới** một entity cấu hình tenant, không phải bổ sung field vào bảng có sẵn — cần đưa vào phạm vi ước lượng của sprint.

---

## G. Ngoài phạm vi (KHÔNG làm trong sprint này — ghi TODO)

- Wiring endpoint DAV thật (chờ đặc tả API).
- Biên bản nhận thuốc gây nghiện (Phụ lục XX, Điều 15.1.d), sổ pha chế.
- Báo cáo định kỳ Phụ lục X/XI.
- Kê đơn điện tử liên thông.
- **Bảng 2 QĐ540** (dữ liệu tổng hợp cấp tỉnh) — do hệ thống trung ương/Sở Y tế tổng hợp, không phải trách nhiệm sinh dữ liệu của cơ sở bán lẻ.
- **Bảng 4 QĐ540** — "Yêu cầu chức năng thống kê" (kết xuất PDF/Excel: số lượng cơ sở nhập liệu theo tỉnh, danh mục thuốc theo cơ sở/tỉnh). Đây là chức năng thống kê phía cơ quan quản lý (Bộ Y tế/Sở Y tế), không phải chuẩn dữ liệu phải implement ở cơ sở bán lẻ trong sprint này.
