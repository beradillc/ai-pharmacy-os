# 13 — COMPLIANCE SPEC (Đặc tả Tuân thủ Pháp lý)

> Nguồn sự thật pháp lý cho module `compliance`. Distilled từ văn bản gốc.
> Đặt tại `docs/13_COMPLIANCE_SPEC.md`. Mọi field/rule trong module `compliance`
> phải truy vết được về một mục trong file này.
>
> **Văn bản nguồn (đã đọc, có file gốc tại `docs/legal/`):**
> - **QĐ 540/QĐ-QLD (20/8/2018)** — Chuẩn yêu cầu dữ liệu đầu ra phần mềm kết nối liên thông cơ sở bán lẻ thuốc, v1.0. (`docs/legal/540_QD-QLD_m_391359.docx`)
> - **TT 18/2026/TT-BYT (01/6/2026, hiệu lực 16/7/2026)** — Thuốc & nguyên liệu phải kiểm soát đặc biệt. (`docs/legal/Thông-tư-18-2026-TT-BYT.docx` · tóm tắt đầy đủ: `docs/legal/Thông-tư-18-2026-TT-BYT.SUMMARY.md`) — **văn bản hiện hành, thay thế TT20/2017.**
> - ~~**TT 20/2017/TT-BYT (10/5/2017)**~~ — **ĐÃ HẾT HIỆU LỰC 16/7/2026** (bị TT18/2026 Điều 16.4 bãi bỏ, cùng TT 27/2024). Giữ file gốc `docs/legal/Thông-tư-20-2017-TT-BYT.docx` làm lịch sử; **không dùng làm căn cứ mới**.
> - **QĐ 1867/QĐ-BYT (24/6/2026)** — Kế hoạch triển khai Hệ thống CSDL về dược. (`docs/legal/Quyết-định-1867-QĐ-BYT.docx`)
>
> **⚠️ Văn bản CÒN THIẾU (chặn phần kết nối thật — phải lấy trước khi wiring production):**
> - Tài liệu **đặc tả API** kết nối CSDL Dược (do **Trung tâm Thông tin y tế Quốc gia** ban hành theo QĐ 1867 mục 1.2 — hoàn thành 6/2026). **Chưa có trong tay.**
> - **TT 11/2025/TT-BYT** (sửa đổi TT 02/2018, TT 03/2018, TT 36/2018) và **NĐ 163/2025/NĐ-CP** — QĐ 1867 dẫn chiếu ở phần "Căn cứ", có thể đổi field bắt buộc. **Chưa có trong tay.**
> - **NĐ 90/2026/NĐ-CP** — chế tài xử phạt không liên thông (QĐ 1867 mục V.4.d dẫn chiếu). **Chưa có trong tay.**
> - ~~**NĐ 163/2025/NĐ-CP** — chưa có trong tay~~ **ĐÃ ĐỌC 2026-07-25.** Hiệu lực 01/7/2025, thay
>   NĐ 54/2017. ⭐ **Điều 35.2: bán lẻ CÓ nghĩa vụ báo cáo định kỳ 6 tháng/năm gửi UBND cấp tỉnh**
>   (Mẫu số 06 Phụ lục II) — đảo ngược kết luận cũ. Xem `docs/legal/Nghị-định-163-2025-NĐ-CP.SUMMARY.md`
>   và mục C.7 (mới) bên dưới. **Đã tới hạn ≥3 kỳ (15/7/2025, 15/1/2026, 15/7/2026) — xác nhận
>   ngay với BeraLLC xem thực tế đã báo cáo chưa, đây là việc ngoài đời, không phải code.**
> - ~~**TT 33/2025/TT-BYT** + **TT 26/2025/TT-BYT** — chưa có trong tay~~ **ĐÃ ĐỌC 2026-07-25.**
>   TT33 không có mục riêng cho sổ KSĐB bán lẻ (mục gần nhất 20 năm, dùng làm sàn suy diễn — xem
>   mục C.4 bên dưới). TT26 không phát sinh nghĩa vụ mới, chỉ xác nhận 2 tham chiếu lỗi thời trong
>   chính nó (TT53/2017→TT33, TT20/2017→TT18 Điều 15.4). Xem 2 file SUMMARY tương ứng.
> - Văn bản quy định **kê đơn thuốc ngoại trú** hiện hành (áp dụng cho `RxClass.ETC` nói chung — TT 20/2017 CHỈ điều chỉnh thuốc kiểm soát đặc biệt, không phải mọi thuốc kê đơn). TT 20/2017 Điều 18.1 dẫn chiếu TT 05/2016/TT-BYT cho việc lưu đơn thuốc GN/HT, nhưng đó cũng không phải nguồn cho rule "mọi thuốc ETC cần prescription_code". **Chưa có trong tay — xem mục C.3.**

---

## Traceability (đối chiếu Bước 2, Bước 3)

> ⚠️ **Đọc trước (2026-07-25):** các dòng **11–16 và 21** dưới đây đối chiếu theo **TT20/2017 — nay
> đã hết hiệu lực**. Nội dung nghiệp vụ phần lớn **không đổi** khi sang TT18/2026, nhưng **số hiệu
> điều/phụ lục đổi hết** (Điều 15 → Điều 12, PL XX → PL XVIII, PL XXI → PL XIX). Dòng **22–27** là
> phần đối chiếu lại theo TT18 — khi có mâu thuẫn, **lấy dòng 22–27**.

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
| 21  | G. "Báo cáo định kỳ Phụ lục X/XI" (đứng cùng dòng với các mục ngoài phạm vi khác, ngụ ý "chưa làm") | TT20/2017 Điều 8.1 (a,b) — đối tượng lập báo cáo | **SAI TIỀN ĐỀ** — Điều 8.1 chỉ bắt buộc cơ sở khám bệnh/chữa bệnh, cơ sở cai nghiện bắt buộc, cơ sở nghiên cứu/đào tạo y dược, cơ sở hoạt động dược phi thương mại lập Phụ lục X; Phụ lục XI do **Sở Y tế/Cục Quân y** lập. Nhà thuốc **bán lẻ** (Điều 15 — đối tượng AI Pharmacy OS) không nằm trong danh sách này → không phải "ngoài phạm vi sprint" mà là **không áp dụng cho loại hình cơ sở này**, không cần implement. Phát hiện 2026-07-24 khi Chain hỏi lại nội dung/nơi nộp 2 biểu mẫu, đối chiếu nguyên văn docx mới lộ ra (SUMMARY.md cũ chỉ có mục lục, không đủ chi tiết để thấy sai) |
| 22  | **Toàn bộ mục C — căn cứ pháp lý** | TT18/2026 Điều 16.1 + 16.4 (hiệu lực 16/7/2026, bãi bỏ TT20/2017 + TT27/2024) | **ĐÃ HẾT HIỆU LỰC → đã đổi căn cứ 2026-07-25.** Nội dung nghiệp vụ lõi (phân loại, nghĩa vụ sổ sách bán lẻ) giữ nguyên; chỉ đổi số hiệu điều/phụ lục và bổ sung nghĩa vụ mới ở dòng 24–25 |
| 23  | C.1 phân loại | TT18 **Phụ lục VII** (bảng 9 tiêu chí, trước nằm ở TT20 Điều 3) + bảng giới hạn PL IV/V/VI | **KHỚP nội dung, THIẾU 2 giá trị** — enum hiện có 7 giá trị (GN/HT/TC/PHOI_HOP_×3/NONE). TT18 Điều 12.3 kéo thêm **thuốc độc** và **thuốc trong danh mục chất bị cấm** vào nghĩa vụ sổ sách của **bán lẻ** ⇒ cần `THUOC_DOC`, `DANH_MUC_CAM`. Xem C.1 |
| 24  | C.2 nghĩa vụ bán lẻ | TT18 **Điều 12** (thay TT20 Điều 15) | **KHỚP a–đ** (đổi số phụ lục: VIII giữ nguyên, XX→**XVIII**, XXI→**XIX**). **THIẾU khoản 12.3** — sổ xuất/nhập/tồn **Phụ lục XVI** cho thuốc dạng phối hợp + thuốc độc + danh mục cấm; **TT20 không có nghĩa vụ này với bán lẻ** ⇒ nghĩa vụ MỚI, chưa implement |
| 25  | C.5 (mới) sổ điện tử | TT18 **Điều 15.1 (a–d)** — điều kiện dùng sổ/hồ sơ trên phần mềm | **GAP LỚN** — điểm (d) buộc người theo dõi/xác nhận **ký bằng chữ ký số hoặc kỹ thuật xác nhận điện tử**; ghi chú PL VIII buộc **trích xuất + in cuối mỗi ngày, ký từng trang**. Hệ thống **chưa có cơ chế ký nào** ⇒ sổ điện tử hiện chưa đủ điều kiện thay sổ giấy. Xem C.5 |
| 26  | C.4 lưu trữ | TT18 **Điều 15.3** (dẫn chiếu **TT 33/2025** cho sổ sách, **TT 26/2025** cho đơn thuốc) | **MẤT CĂN CỨ** — quy tắc "≥2 năm kể từ ngày hết hạn dùng" (TT20 Điều 18.1) không còn tồn tại trong TT18. Giữ nguyên hành vi hiện tại (không hard-delete) như **mức sàn an toàn**, chờ 2 thông tư trên mới chốt số năm |
| 27  | G. báo cáo định kỳ (đính chính dòng 21, ĐÍNH CHÍNH LẦN 2 2026-07-25) | TT18 **Điều 1.2 + Điều 7** (đúng cho phần phi thương mại) **+ NĐ163 Điều 35.2** (đã đọc) | **TT18 Điều 7 đúng nhưng KHÔNG PHẢI TOÀN BỘ CÂU TRẢ LỜI** — TT18 Điều 7 quả thật không áp cho bán lẻ (đúng cơ sở phi thương mại). Nhưng nghĩa vụ báo cáo của cơ sở **kinh doanh** (bán lẻ) nằm ở **NĐ163 Điều 35.2**, đã đọc: **CÓ nghĩa vụ**, 6 tháng/năm, gửi **UBND cấp tỉnh**, Mẫu số 06 Phụ lục II NĐ163 (khác hẳn PL IX/X/XI của TT18). Kết luận đúng: "bán lẻ **CÓ** báo cáo định kỳ, theo NĐ163 không phải TT18" — xem mục **C.7** (mới) |
| 28  | (mới) C.4 lưu trữ — đã đọc TT33+TT26 | TT33/2025 Phụ lục mục #67 (suy diễn) + TT26/2025 Điều 11 | **CẬP NHẬT** — nâng sàn retention lên ≥20 năm kể từ ngày phát sinh hồ sơ (thay ≥2 năm sau hạn dùng); TT26 xác nhận 2 tham chiếu lỗi thời tự sửa (TT53→TT33, TT20→TT18 Điều 15.4), không phát sinh nghĩa vụ mới |

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

## C. ControlledDrugLedger — Sổ thuốc kiểm soát đặc biệt (**TT 18/2026**, thay TT 20/2017)

> **Cập nhật 2026-07-25.** Căn cứ cũ TT20/2017 hết hiệu lực 16/7/2026. Ánh xạ điều khoản:
> TT20 Điều 3 → **TT18 Phụ lục VII**; TT20 Điều 15 → **TT18 Điều 12**; TT20 Điều 18 → **TT18 Điều 15**.
> Ánh xạ phụ lục: PL VIII giữ nguyên · PL XX → **PL XVIII** · PL XXI → **PL XIX** · **PL XVI mới**.
> Bảng đối chiếu đầy đủ 19 phụ lục: `docs/legal/Thông-tư-18-2026-TT-BYT.SUMMARY.md` mục 4.

### C.1 Phân loại (**Phụ lục VII**) — enum `ControlledSubstanceCategory`
- `GAY_NGHIEN` (gây nghiện)
- `HUONG_THAN` (hướng thần)
- `TIEN_CHAT` (tiền chất dùng làm thuốc)
- `PHOI_HOP_GN` (dạng phối hợp chứa gây nghiện)
- `PHOI_HOP_HT` (dạng phối hợp chứa hướng thần)
- `PHOI_HOP_TC` (dạng phối hợp chứa tiền chất)
- `THUOC_DOC` (thuốc độc, nguyên liệu độc làm thuốc) — **BỔ SUNG 2026-07-25**
- `DANH_MUC_CAM` (thuốc/dược chất thuộc danh mục chất bị cấm sử dụng trong một số ngành, lĩnh vực) — **BỔ SUNG 2026-07-25**
- `NONE` (không thuộc diện kiểm soát — mặc định)

> **Vì sao bổ sung 2 giá trị:** bản cũ loại `thuốc độc`/`danh mục cấm` khỏi enum với lý do "chỉ áp
> cho loại hình cơ sở khác". **Tiền đề đó sai với TT18** — Điều 12.3 buộc **chính cơ sở bán lẻ**
> lập sổ Phụ lục XVI cho thuốc độc và thuốc thuộc danh mục cấm.
>
> `RxClass.CONTROLLED` trong `catalog` là mức thô. Map: `RxClass.CONTROLLED` ⇒ `ControlledSubstanceCategory ≠ NONE`.
>
> Thuốc **phóng xạ** vẫn ngoài phạm vi (nhà thuốc bán lẻ không kinh doanh) — không đưa vào enum.

**Tiêu chí phân loại (Phụ lục VII, 9 dòng) — thứ tự ưu tiên khi suy ra category từ công thức thuốc:**

| # | Kết quả | Điều kiện |
|---|---|---|
| 1–2 | `GAY_NGHIEN` | Chỉ chứa GN; **hoặc** nhiều thành phần + có ≥1 GN **vượt** giới hạn PL IV |
| 3–4 | `HUONG_THAN` | Chỉ chứa HT; **hoặc** nhiều thành phần + ≥1 HT **vượt** PL V + GN (nếu có) **không vượt** PL IV |
| 5–6 | `TIEN_CHAT` | Chỉ chứa TC; **hoặc** ≥1 TC **vượt** PL VI + GN không vượt PL IV + HT không vượt PL V |
| 7 | `PHOI_HOP_GN` | Mọi GN **không vượt** PL IV + có ≥1 thành phần không phải GN + HT không vượt PL V + TC không vượt PL VI |
| 8 | `PHOI_HOP_HT` | Mọi HT **không vượt** PL V + có ≥1 thành phần không phải HT + **không chứa GN** + TC không vượt PL VI |
| 9 | `PHOI_HOP_TC` | Mọi TC **không vượt** PL VI + có ≥1 thành phần không phải TC + **không chứa GN** + **không chứa HT** |

Danh mục hoạt chất nguồn: **PL I** (42 dược chất GN), **PL II** (**72** dược chất HT — đã gồm
**Carisoprodol, Etomidate** là hướng thần **từ 01/6/2026**, TT18 Điều 16.2), **PL III** (8 tiền chất).
Cả 3 danh mục **bao gồm muối, đồng phân, ester, ether và muối của chúng**.

### C.2 Nghĩa vụ với cơ sở BÁN LẺ (**Điều 12**)
**GN/HT/TC** (Điều 12.1) phải lập và ghi chép đầy đủ:
- (a) Sổ theo dõi xuất/nhập/tồn (**Phụ lục VIII**);
- (b) Phiếu xuất kho của nơi cung cấp thuốc (**Phụ lục XV** — lưu chứng từ đầu vào);
- (c) Đơn thuốc gây nghiện, hướng thần lưu tại cơ sở sau khi bán — **chỉ áp dụng GN/HT, KHÔNG áp dụng TC**;
- (d) Biên bản nhận lại thuốc GN/HT/TC (**Phụ lục XVIII**, trước là PL XX) — xem C.6;
- (đ) Sổ theo dõi thông tin chi tiết khách hàng (**Phụ lục XIX**, trước là PL XXI).

**Dạng phối hợp** (Điều 12.2): Tối thiểu lưu Sổ thông tin chi tiết khách hàng (**Phụ lục XIX**).

**⭐ NGHĨA VỤ MỚI — Điều 12.3:** cơ sở bán lẻ **thuốc dạng phối hợp GN/HT/TC**, **thuốc độc**,
**thuốc trong danh mục chất bị cấm** phải lập sổ theo dõi **xuất, nhập, tồn kho** theo
**Phụ lục XVI**. TT20/2017 **không** có nghĩa vụ này với bán lẻ ⇒ đây là phần hệ thống còn thiếu.

Điều 12.4: lưu giữ chứng từ mua bán mọi thuốc kiểm soát đặc biệt.

### C.2.1 Cấu trúc `ControlledDrugLedger` (map từ mẫu sổ pháp lý)

Hệ thống phải phủ đủ cột của **3** mẫu sổ bắt buộc (trước đây chỉ tính 2):

- **Phụ lục VIII** — sổ xuất/nhập/tồn GN/HT/TC: `ngay_thang`, `noi_xuat_nhap`, `so_chung_tu`,
  `so_luong_nhap`, `so_luong_xuat`, `so_luong_con_lai`, `so_lo`, `han_dung`, `ghi_chu`.
  Header sổ: `ten_co_so`, `dia_chi`, `dien_thoai`, `ten_thuoc_nong_do_ham_luong`,
  `so_dang_ky_hoac_gpnk`, `don_vi_tinh`, kỳ sổ (`tu_ngay`/`den_ngay`).
  **Mỗi thuốc/nguyên liệu là một sổ riêng** — kết xuất phải tách theo `drug_id`.
- **Phụ lục XVI** (MỚI) — sổ xuất/nhập/tồn thuốc dạng phối hợp + thuốc độc + danh mục cấm:
  cột (1)–(8) **giống hệt PL VIII**, header có thêm **`nha_san_xuat`**.
- **Phụ lục XIX** (thay PL XXI) — thông tin khách hàng, chỉ áp dụng khi bán ra: `ngay_thang`,
  `so_thu_tu`, `ten_thuoc_quy_cach` **+ `so_dang_ky_hoac_gpnk`** (⚠️ **cột mới so với PL XXI cũ**),
  `hoat_chat_nong_do`, `don_vi_tinh`, `so_luong_ban`, `ten_khach_hang`, `dia_chi_khach_hang`, `ghi_chu`.

> Phụ lục XIX **vẫn không có cột số CCCD/CMND** — chỉ "Tên khách hàng" và "Địa chỉ". Xem rule C.3.2.

**Cách implement `book_type` (chốt khi code 2026-07-25):** `LedgerBookType` (`PL_VIII` | `PL_XVI`)
là hàm **suy ra từ `category`** (`book_type_for()`), **không lưu thành cột** — lưu thì có 2 nguồn
sự thật cho cùng một dữ kiện và chúng lệch nhau được. Hệ quả: không cần migration cho phần này.

**Nợ còn mở của phần kết xuất:** hai mẫu sổ có **cùng 8 cột (1)–(8)** nên dùng chung một hàm
shaping; nhưng **phần ĐẦU SỔ chưa kết xuất được** — `Tên cơ sở`/`Địa chỉ`/`Điện thoại`,
`Tên thuốc, nồng độ/hàm lượng`, `Số ĐKLH`, `Đơn vị tính` (PL XVI thêm `Nhà sản xuất`) nằm ở
`catalog`, đọc chúng phải mở rộng read-port `DrugMasterFacts` ⇒ **cross-module, chờ duyệt thiết kế**.
File CSV hiện tại là **phần bảng của sổ + cột `drug_id`**, chưa phải sổ hoàn chỉnh để in ra ký.

### C.3 Rule kiểm tra bắt buộc khi tạo giao dịch Bán hàng (Validation Rules)
1. **Thuốc kê đơn (`RxClass.ETC`):**
   > ⚠️ **NGUỒN CHƯA XÁC ĐỊNH — chờ văn bản kê đơn ngoại trú hiện hành.**
   > TT 20/2017 không điều chỉnh thuốc kê đơn thông thường (chỉ điều chỉnh GN/HT/TC/phóng xạ) nên rule dưới đây **chưa có căn cứ pháp lý trực tiếp** trong 3 văn bản hiện có.
   - **Dự kiến (khi có nguồn):** `prescription_code` + `patient_name` + `doctor_name`. Thiếu → `422 Unprocessable Entity`.
   - **Trạng thái implement:** đưa vào domain dưới dạng **feature-flag/TODO**, KHÔNG hard-validate cho tới khi có văn bản xác nhận — ví dụ một cờ cấu hình kiểu `require_etc_prescription_fields: bool = False` (mặc định tắt) đặt cạnh rule, kèm comment `# TODO(compliance): bật khi có văn bản kê đơn ngoại trú hiện hành`. Khi có văn bản, chỉ cần bật cờ / đổi default, không thiết kế lại rule hay schema.
2. **Thuốc kiểm soát đặc biệt (`category ∈ {GAY_NGHIEN, HUONG_THAN, TIEN_CHAT}`):**
   - **BẮT BUỘC theo mẫu Phụ lục XIX:** `patient_name` (Tên khách hàng) + `patient_address` (Địa chỉ). Thiếu → Báo lỗi `422 Unprocessable Entity`.
   - `prescription_code`: bắt buộc khi GN/HT (đơn phải lưu tại cơ sở theo **Điều 12.1.c**); với TC không có yêu cầu lưu đơn theo văn bản gốc.
   - `patient_id` (Số CCCD/CMND): **không phải yêu cầu bắt buộc theo mẫu sổ Phụ lục XIX** (mẫu sổ không có cột này). Nếu giữ lại, cần ghi rõ đây là **yêu cầu nghiệp vụ bổ sung của hệ thống**, không phải trích dẫn pháp lý trực tiếp.
3. Ghi nhận giao dịch: Mỗi giao dịch controlled → ghi 1 dòng `ControlledDrugLedger` (immutable, không sửa/xóa cứng).
4. **(bổ sung 2026-07-25)** Với `category ∈ {PHOI_HOP_GN, PHOI_HOP_HT, PHOI_HOP_TC, THUOC_DOC, DANH_MUC_CAM}`:
   ghi ledger với `book_type = PL_XVI`. Riêng 3 nhóm phối hợp còn phải ghi Sổ khách hàng PL XIX
   (Điều 12.2) ⇒ vẫn cần `patient_name` + `patient_address`. Thuốc độc/danh mục cấm **chỉ** cần sổ
   xuất/nhập/tồn, **không** cần sổ khách hàng.

### C.4 Lưu trữ (**Điều 15.3** — thay Điều 18 TT20) — **cập nhật 2026-07-25, đã đọc TT33+TT26**

TT18 **không còn** quy tắc "tối thiểu 2 năm kể từ ngày thuốc hết hạn dùng" — Điều 15.3 giao thời
hạn cho 2 văn bản khác. Cả hai **đã đọc**:

- **Đơn thuốc GN/HT/TC → TT 26/2025/TT-BYT Điều 11.1** → dẫn tiếp sang **TT 33/2025** (TT26 tự
  dẫn TT53/2017 nhưng văn bản đó đã hết hiệu lực cùng ngày, bị chính TT33 bãi bỏ — áp nguyên tắc
  "văn bản dẫn chiếu bị thay thế thì theo văn bản mới", giống TT18 Điều 18).
- **Hồ sơ, sổ sách khác → TT 33/2025/TT-BYT Phụ lục** — **không có mục riêng** cho sổ kiểm soát
  đặc biệt của cơ sở bán lẻ. Mục gần đúng nhất (#67 trong phụ lục TT33): "Hồ sơ cấp phép NK/XK
  nguyên liệu/thuốc GN/HT/TC; **báo cáo định kỳ**" = **20 năm**. Đây là **suy diễn theo mục tương
  đương** (TT33 Điều 1.2.b cho phép, yêu cầu không thấp hơn mức đã có), không phải trích dẫn trực
  tiếp — xem `docs/legal/Thông-tư-33-2025-TT-BYT.SUMMARY.md`.

**Quyết định (GĐ, dưới ủy quyền toàn quyền chỉ đạo code 2026-07-25):** nâng sàn retention từ
"≥2 năm sau `expiry_date`" lên **≥20 năm kể từ ngày phát sinh hồ sơ** (không neo theo hạn dùng
thuốc nữa — mục #67 TT33 không neo theo hạn dùng). Hướng **an toàn hơn** (giữ lâu hơn, không xóa
sớm), phù hợp nguyên tắc chọn phương án ít rủi ro khi chưa chắc chắn tuyệt đối.

- **Hành vi:** **KHÔNG hard-delete**, dùng soft-delete + audit. Retention ≥ 20 năm kể từ ngày tạo
  bản ghi (không phải từ `expiry_date`).
- Hết thời hạn lưu trữ → người đứng đầu lập **hội đồng hủy**, lập **biên bản hủy**, lưu hồ sơ việc
  hủy tại cơ sở (**Điều 15.4** TT18 — cũng là tham chiếu đúng cho TT26 Điều 11.2, xem trên) — quy
  trình hành chính, **ngoài phạm vi phần mềm**.

### C.5 (MỚI 2026-07-25) Điều kiện dùng sổ/hồ sơ ĐIỆN TỬ — **Điều 15.1**

Đây là điều khoản **trực tiếp điều chỉnh phần mềm**. Được dùng sổ điện tử thay sổ giấy khi đủ **cả 4**:

| Điểm | Yêu cầu | Hiện trạng hệ thống |
|---|---|---|
| a | Dữ liệu **đầy đủ theo đúng biểu mẫu**, **được mã hóa**, **toàn vẹn**, không đổi khi truyền/chia sẻ | ⚠️ Một phần (TLS), chưa có hash toàn vẹn bản ghi |
| b | Chính xác, bảo mật; **mọi thay đổi phải LƯU VẾT đầy đủ** | ✅ ledger immutable + `audit_log` |
| c | Tra cứu được suốt thời gian lưu trữ; **phục hồi & truy xuất** khi cần | ⚠️ Có export, chưa có quy trình phục hồi kiểm chứng |
| d | Người theo dõi/xác nhận **phải ký bằng chữ ký số hoặc kỹ thuật xác nhận điện tử** | ❌ **KHÔNG CÓ** |

Ghi chú bắt buộc của **Phụ lục VIII**: dùng phần mềm ⇒ phải **trích xuất, in thông tin theo dõi vào
cuối MỖI NGÀY**, lưu hồ sơ, **có chữ ký xác nhận trên TỪNG TRANG** của người quản lý thuốc và
trưởng bộ phận.

> **Kết luận thẳng:** chừng nào chưa có (d), sổ điện tử của hệ thống **chưa đủ điều kiện pháp lý
> thay sổ giấy** — nhà thuốc vẫn phải in và ký tay hằng ngày. Đây là **nợ pháp lý mức 🔴**, đã
> chốt 2026-07-25: **thiết kế trước, chưa code** (xem `docs/features/tt18-kiem-soat-dac-biet/`).

### C.6 (MỚI 2026-07-25) Biên bản nhận lại thuốc GN/HT/TC — **Điều 6.2 + Điều 12.1.d, Phụ lục XVIII**

Khi người bệnh không dùng hết hoặc tử vong, cơ sở bán lẻ nhận lại thuốc GN/HT/TC phải:
- Lập **Biên bản Phụ lục XVIII thành 02 bản**, mỗi bên giữ 01;
- **Biệt trữ** thuốc nhận lại tại khu vực bảo đảm an ninh chống thất thoát, rồi tiêu hủy theo quy định
  ⇒ hệ quả kỹ thuật: lô nhận lại phải bị **khóa khỏi tồn kho bán được** (cross-module `inventory`).

Trường bắt buộc của biểu mẫu: người giao (`họ tên`, `địa chỉ`, **`số CCCD/hộ chiếu` + nơi cấp, ngày
cấp**, cờ *là người bệnh* / *là người đại diện*), cơ sở nhận (**ghi rõ người chịu trách nhiệm chuyên
môn về dược**), bảng thuốc (tên/dạng bào chế/nồng độ/quy cách/số ĐKLH, ĐVT, số lượng, số lô, hạn
dùng, **tình trạng cảm quan**, lý do nhận lại), thời gian giao nhận (giờ–phút–ngày), địa điểm giao nhận.

> ⚠️ Biểu mẫu này **có** thu thập số CCCD — khác Sổ PL XIX. Đây là dữ liệu cá nhân nhạy cảm ⇒ phải
> qua cổng `docs/14_FEATURE_PROCESS.md` (Luật 91/2025 + NĐ 356/2025) khi implement.

### C.7 (MỚI 2026-07-25) ⭐ Báo cáo định kỳ 6 tháng/năm gửi UBND cấp tỉnh — **NĐ 163/2025 Điều 35.2**

> **Đây là nghĩa vụ pháp lý QUAN TRỌNG NHẤT phát hiện trong đợt đọc 3 văn bản 2026-07-25 — đảo
> ngược hoàn toàn kết luận cũ ở Traceability #27.** Không nằm ở TT18 (Thông tư chỉ điều chỉnh
> phần "cơ sở dược không vì mục đích thương mại"), mà nằm ở **Nghị định** — đúng như dự đoán ở
> `docs/legal/README.md` mục "việc chưa làm #6" trước khi đọc được văn bản.

**Nội dung nghĩa vụ (NĐ163 Điều 35.2.a):** cơ sở **bán buôn, bán lẻ, tổ chức chuỗi nhà thuốc**
phải lập báo cáo **6 tháng** (kỳ 01/01–30/06, nộp trước **15/7**) và **năm** (kỳ 01/01–31/12, nộp
trước **15/01** năm sau) về xuất/nhập/tồn/sử dụng **GN/HT/TC + thuốc dạng phối hợp chứa GN/HT/TC**,
theo **Mẫu số 06 Phụ lục II NĐ163**, gửi **Ủy ban nhân dân cấp tỉnh** nơi đặt trụ sở chính.

**Mẫu số 06 — 12 cột:** TT · Tên thuốc/dạng bào chế/hoạt chất/nồng độ-hàm lượng/quy cách/số ĐKLH ·
Nước sản xuất · Đơn vị tính · Số công văn cho phép mua trong nước · Tồn kỳ trước · Nhập trong kỳ ·
Tổng số · Xuất trong kỳ · Tồn cuối kỳ · Hao hụt · Ghi chú.

**Báo cáo thất thoát 48h** cũng đổi cơ quan nhận: NĐ163 Điều 35.4 → gửi **UBND cấp tỉnh** (không
phải Cục Quân y/Cục Y tế/Sở Y tế như TT18 Điều 7.3, vì đó chỉ áp cho cơ sở phi thương mại).

**Chế tài (Điều 35.5):** không báo cáo đúng hạn → "bị ngừng tiếp nhận, xem xét hồ sơ đề nghị mua,
xuất khẩu, nhập khẩu thuốc, nguyên liệu làm thuốc đến khi cơ sở báo cáo đầy đủ".

> ⚠️ **KHẨN — việc thật ngoài đời, không phải code:** NĐ163 hiệu lực **01/7/2025**, không có lộ
> trình ân hạn cho khoản 2 Điều 35 (Điều 124 chỉ áp lộ trình cho khoản 1). Tính đến 2026-07-25 đã
> qua **3 kỳ hạn nộp**: 15/7/2025, 15/1/2026, 15/7/2026. **Cần xác nhận ngay với người chịu trách
> nhiệm chuyên môn dược của BeraLLC xem đã từng nộp báo cáo nào trong 3 kỳ này chưa** — nếu chưa,
> đây là việc cần xử lý bên ngoài phần mềm trước (liên hệ Sở Y tế/UBND tỉnh), không phải chờ code
> xong mới xử lý.

**Trạng thái implement:** **CHƯA CÓ** trong code — đây là tính năng hoàn toàn mới, ngoài phạm vi
6-bước đã duyệt cho mạch TT18 (docs/features/tt18-kiem-soat-dac-biet/). Cần qua cổng
`docs/14_FEATURE_PROCESS.md` trước khi code (Bước 0-3), dù dữ liệu nguồn (ledger) đã có sẵn qua
`ControlledLedgerEntry` — phần việc mới là **tổng hợp theo kỳ 6 tháng/năm** + **kết xuất đúng Mẫu
số 06** + (tùy chọn) nhắc lịch nộp báo cáo trước hạn.

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
- ~~Biên bản nhận thuốc gây nghiện (Phụ lục XX, Điều 15.1.d)~~ — **ĐƯA VÀO PHẠM VI 2026-07-25**:
  TT18 Điều 12.1.d + Điều 6.2, nay là **Phụ lục XVIII**. Xem mục **C.6**. Sổ pha chế (PL XIV/XVII)
  vẫn ngoài phạm vi — bán lẻ không pha chế.
- ~~Báo cáo định kỳ Phụ lục X/XI~~ — **đính chính 2026-07-24 (GĐ, đối chiếu lại nguyên văn TT20/2017):**
  nghĩa vụ này thuộc **Điều 8.1** (cơ sở khám bệnh/chữa bệnh, cơ sở cai nghiện bắt buộc, cơ sở
  nghiên cứu/đào tạo y dược, cơ sở hoạt động dược phi thương mại khác) — **KHÔNG thuộc Điều 15**
  (nhà thuốc bán lẻ, đối tượng của AI Pharmacy OS). Phụ lục XI hơn nữa do **Sở Y tế/Cục Quân y**
  lập (tổng hợp cấp tỉnh/ngành), không phải cơ sở bán lẻ. Nghĩa vụ hồ sơ sổ sách thật của bán lẻ
  theo Điều 15 chỉ có Phụ lục VIII + XX + XXI (đã làm ở C.1–C.5) — **không cần Phụ lục X/XI**,
  không phải "chưa làm", là **không áp dụng**. Xem Traceability #20.
  > **Cập nhật 2026-07-25 theo TT18:** kết luận trên **vẫn đúng** với TT18 (Điều 7 nằm ở Chương II,
  > Điều 1.2 giới hạn Chương II cho cơ sở dược **không vì mục đích thương mại**); số hiệu mẫu đổi
  > thành PL IX / PL X / PL XI. **Nhưng hạ mức chắc chắn:** nghĩa vụ báo cáo của cơ sở **kinh doanh**
  > dược nằm ở **NĐ 163/2025/NĐ-CP** (chưa có văn bản), không nằm ở Thông tư ⇒ đọc là
  > **"chưa kết luận được"**, không phải "chắc chắn không áp dụng". Xem Traceability #27.
  > **ĐÍNH CHÍNH LẦN 2 (2026-07-25, đã đọc NĐ163):** Phụ lục IX/X/XI của TT18 quả thật không áp
  > cho bán lẻ (kết luận cũ đúng phần này). **NHƯNG bán lẻ CÓ nghĩa vụ báo cáo định kỳ khác** —
  > theo **NĐ163 Điều 35.2** (Mẫu số 06 Phụ lục II, gửi UBND cấp tỉnh) — **ĐƯA RA KHỎI MỤC NÀY,
  > chuyển vào phạm vi làm việc ở mục C.7.** Đây không còn là "ngoài phạm vi" nữa. Xem Traceability #27.
- Kê đơn điện tử liên thông.
- **Bảng 2 QĐ540** (dữ liệu tổng hợp cấp tỉnh) — do hệ thống trung ương/Sở Y tế tổng hợp, không phải trách nhiệm sinh dữ liệu của cơ sở bán lẻ.
- **Bảng 4 QĐ540** — "Yêu cầu chức năng thống kê" (kết xuất PDF/Excel: số lượng cơ sở nhập liệu theo tỉnh, danh mục thuốc theo cơ sở/tỉnh). Đây là chức năng thống kê phía cơ quan quản lý (Bộ Y tế/Sở Y tế), không phải chuẩn dữ liệu phải implement ở cơ sở bán lẻ trong sprint này.

---

## H. Changelog của spec (spec đã khóa — mọi thay đổi phải ghi tại đây)

### 2026-07-25 — Chuyển căn cứ TT 20/2017 → TT 18/2026 (Chain duyệt cùng ngày)

| # | Thay đổi | Mục | Loại |
|---|---|---|---|
| 1 | Đổi văn bản nguồn: TT18/2026 (hiệu lực 16/7/2026) thay TT20/2017 (bị bãi bỏ, cùng TT27/2024) | Header, mục C | Căn cứ |
| 2 | Ánh xạ điều/phụ lục: Điều 3→PL VII · Điều 15→Điều 12 · Điều 18→Điều 15 · PL XX→PL XVIII · PL XXI→PL XIX | C.1–C.4 | Đánh số |
| 3 | **Thêm 2 giá trị enum** `THUOC_DOC`, `DANH_MUC_CAM` — TT18 Điều 12.3 kéo 2 nhóm này vào nghĩa vụ sổ sách của **bán lẻ** (TT20 không có) | C.1 | **Nghĩa vụ mới** |
| 4 | **Thêm sổ Phụ lục XVI** (xuất/nhập/tồn thuốc phối hợp + thuốc độc + danh mục cấm) ⇒ ledger cần `book_type` (`PL_VIII` / `PL_XVI`) | C.2, C.2.1, C.3.4 | **Nghĩa vụ mới** |
| 5 | Bổ sung bảng 9 tiêu chí phân loại (PL VII) + nguồn danh mục PL I/II/III và giới hạn PL IV/V/VI; ghi nhận **Carisoprodol, Etomidate là hướng thần từ 01/6/2026** | C.1 | Nội dung |
| 6 | Sổ khách hàng PL XIX **thêm cột** `số ĐKLH/GPNK` so với PL XXI cũ | C.2.1 | Nội dung |
| 7 | **C.4 mất căn cứ** — "≥2 năm sau hạn dùng" không còn trong TT18; chuyển sang chờ TT 33/2025 + TT 26/2025, giữ hành vi hiện tại làm mức sàn | C.4 | **Blocker** |
| 8 | **Thêm mục C.5** — Điều 15.1 (điều kiện sổ điện tử, có yêu cầu **chữ ký số/xác nhận điện tử** + in & ký từng trang cuối mỗi ngày). Gap 🔴, chốt: thiết kế trước, chưa code | C.5 | **Gap mới** |
| 9 | **Thêm mục C.6** — Biên bản nhận lại thuốc PL XVIII (kéo từ "ngoài phạm vi" vào phạm vi); kèm cảnh báo PII vì mẫu có số CCCD | C.6, G | Phạm vi |
| 10 | Hạ mức kết luận "bán lẻ miễn báo cáo định kỳ" từ **không áp dụng** → **chưa kết luận được** (chờ NĐ 163/2025) | G, #27 | Thận trọng |
| 11 | Thêm Traceability #22–27 | Traceability | Đối chiếu |

**Đã implement 2026-07-25 (bước 2–3, Chain duyệt):** mục 3, 4, 5 của bảng trên đã vào code —
bảng `controlled_substances` (mig `0024`) + seed 122 hoạt chất, enum 9 giá trị, `LedgerBookType`
suy ra từ `category`, endpoint kết xuất CSV 2 mẫu sổ. Mục 7 (lưu trữ), 8 (chữ ký số), 9 (biên bản
PL XVIII) **vẫn là nợ**.

**Chưa làm trong đợt này (Chain chốt 2026-07-25):** chữ ký số (chỉ thiết kế), job kết xuất cuối
ngày, seed danh mục thuốc độc/danh mục cấm (nhà thuốc BeraLLC **không bán** 2 nhóm này — chỉ dựng
khung enum + sổ PL XVI cho thuốc dạng phối hợp).

Trạng thái từng bước: `docs/features/tt18-kiem-soat-dac-biet/00_DE_XUAT_CAP_NHAT.md` mục 6.

### 2026-07-25 (cùng ngày, đợt 2) — Đọc xong NĐ163/2025 + TT33/2025 + TT26/2025

Chain chép 3 văn bản đang thiếu lên bookmark, ủy quyền toàn quyền cho GĐ tiếp tục chỉ đạo code.

| # | Thay đổi | Mục | Loại |
|---|---|---|---|
| 1 | ⭐ **Đảo ngược kết luận báo cáo định kỳ** — bán lẻ **CÓ** nghĩa vụ (NĐ163 Điều 35.2), không phải TT18. Thêm **mục C.7 hoàn toàn mới** | C.7, Traceability #27, mục G | **Đảo ngược kết luận cũ** |
| 2 | Nâng sàn retention từ ≥2 năm sau hạn dùng lên **≥20 năm kể từ ngày phát sinh** (suy diễn từ TT33 mục #67, không neo hạn dùng nữa) | C.4, Traceability #28 | Quyết định GĐ (dưới ủy quyền) |
| 3 | Xác nhận 2 tham chiếu lỗi thời trong TT26 tự sửa: TT53/2017→TT33/2025, TT20/2017→TT18 Điều 15.4 | C.4 | Đối chiếu |
| 4 | 3 file SUMMARY mới trong `docs/legal/`, `docs/legal/README.md` cập nhật bảng tra | — | Tài liệu |

**🔴 Việc khẩn ngoài phần mềm (không chờ code):** xác nhận với người chịu trách nhiệm chuyên môn
dược của BeraLLC xem đã báo cáo định kỳ theo NĐ163 Điều 35.2 kỳ nào chưa (đã tới hạn 15/7/2025,
15/1/2026, 15/7/2026). Nếu chưa, xử lý với UBND cấp tỉnh **trước**, không đợi phần mềm xong.

**Việc mới cần qua cổng `docs/14_FEATURE_PROCESS.md`:** tính năng "báo cáo định kỳ Mẫu số 06"
(mục C.7) — ngoài phạm vi 6-bước đã duyệt cho mạch TT18, cần Bước 0-3 riêng trước khi code.
