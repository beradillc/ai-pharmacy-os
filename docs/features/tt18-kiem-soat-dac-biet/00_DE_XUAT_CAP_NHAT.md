# Đề xuất cập nhật hệ thống theo TT 18/2026/TT-BYT — CHỜ DUYỆT

> Trạng thái: **ĐÃ DUYỆT 2026-07-25** — Chain chốt phạm vi **bước 1–3**. Soạn cùng ngày.
> Nguồn: `docs/legal/Thông-tư-18-2026-TT-BYT.SUMMARY.md` (trích nguyên văn từ bookmark).
> Áp dụng cổng `docs/14_FEATURE_PROCESS.md` — file này là **Bước 0–3**.

## 1. Vì sao phải làm — 1 câu

TT18/2026 có hiệu lực **16/7/2026** và **bãi bỏ TT20/2017**, trong khi toàn bộ mục C của
`docs/13_COMPLIANCE_SPEC.md` (đã khóa) đang trích dẫn TT20/2017 → **spec pháp lý của hệ thống
đang dựa trên văn bản hết hiệu lực 9 ngày**. Code không sai nghiệp vụ ở phần lõi, nhưng
**trích dẫn sai**, **thiếu 1 sổ bắt buộc mới**, và **quy tắc lưu trữ mất căn cứ**.

## 2. Trả lời trực tiếp câu "báo cáo thuốc danh mục đặc biệt đã bỏ qua trước đó"

| Câu hỏi | Trả lời theo TT18 | Căn cứ |
|---|---|---|
| Nhà thuốc bán lẻ có phải nộp báo cáo định kỳ PL IX/X không? | **Không — theo TT18.** Điều 7 nằm trong Chương II, Điều 1.2 giới hạn Chương II cho "cơ sở hoạt động dược **không vì mục đích thương mại**" | TT18 Điều 1.2 + Điều 7 |
| Báo cáo đột xuất 48h khi thất thoát (PL XI)? | **Không — theo TT18** (cùng Chương II). Nhưng đây là điểm **rủi ro nhất**, xem dòng dưới | TT18 Điều 7.3 |
| Vậy kết luận đính chính 2026-07-24 có sai không? | **Không sai** — vẫn đúng với TT18, chỉ cần đổi số hiệu phụ lục (X/XI → IX/X/XI) và đổi căn cứ TT20→TT18 | — |
| Vậy bán lẻ **thật sự** miễn báo cáo? | ⚠️ **CHƯA KẾT LUẬN ĐƯỢC.** Nghĩa vụ báo cáo của cơ sở **kinh doanh** dược xưa nay nằm ở **Nghị định** (NĐ 54/2017 Điều 47 cũ → nay **NĐ 163/2025/NĐ-CP**), không nằm ở Thông tư. **Chưa có NĐ163 trong `docs/legal/`** | TT18 chỉ "quy định chi tiết" NĐ163 |

⇒ **Cái thật sự bị bỏ qua trước đó KHÔNG phải báo cáo định kỳ**, mà là **3 nghĩa vụ hồ sơ dưới đây**.

## 3. Khoảng trống thật giữa TT18 và hệ thống hiện tại

| # | Nghĩa vụ TT18 | Hiện trạng code | Mức | Loại việc |
|---|---|---|:---:|---|
| 1 | **Sổ PL XVI** — xuất/nhập/tồn thuốc **dạng phối hợp** + **thuốc độc** + **thuốc danh mục cấm** (Điều 12.3) | ❌ Không có. `ControlledSubstanceCategory` chưa có `THUOC_DOC`, `DANH_MUC_CAM`; ledger chưa tách 2 loại sổ | 🔴 | Domain + migration |
| 2 | **Biên bản nhận lại thuốc PL XVIII** (Điều 12.1.d + Điều 6.2) | ❌ Bị gạt "ngoài phạm vi" ở `docs/13` mục G (khi đó gọi là PL XX) | 🔴 | Entity + endpoint mới |
| 3 | **Điều 15.1.d — chữ ký số / xác nhận điện tử** trên biểu mẫu | ❌ Không có bất kỳ cơ chế ký nào | 🔴 | Cross-cutting, cần thiết kế riêng |
| 4 | **PL VIII ghi chú** — dùng phần mềm thì phải **trích xuất + in cuối mỗi ngày**, ký từng trang | ❌ Không có job kết xuất cuối ngày | 🟠 | Export + job |
| 5 | **Lưu trữ** — đổi sang TT33/2025 + TT26/2025 | ⚠️ Đang hard-code tinh thần "2 năm sau hạn dùng" (TT20 Điều 18.1 — đã hết hiệu lực) | 🟠 | **Chặn: thiếu văn bản** |
| 6 | **PL XIX** thêm cột `số GPNK/số ĐKLH` so với PL XXI cũ | ⚠️ `CustomerDetail` chỉ có `patient_name`, `patient_address`; số ĐKLH lấy được từ `catalog` nhưng chưa gắn vào sổ | 🟠 | Export |
| 7 | **PL VII** — 9 tiêu chí phân loại + bảng giới hạn IV/V/VI | ⚠️ Hiện `category` gán tay theo thuốc, không suy ra từ hoạt chất/hàm lượng | 🟡 | Seed + rule (có thể để sau) |
| 8 | **Etomidate, Carisoprodol** thành hướng thần từ 01/6/2026 | ❌ Chưa có danh mục hoạt chất nào trong DB | 🟡 | Seed data |
| 9 | **Phiếu xuất kho PL XV của NCC** phải lưu (Điều 12.1.b) | ⚠️ `document_no` có ghi, nhưng không lưu chứng từ/ảnh chụp | 🟡 | Sau |
| 10 | Toàn bộ trích dẫn `docs/13` mục C: TT20 → TT18, PL XX→XVIII, PL XXI→XIX | ❌ Sai số hiệu toàn bộ | 🔴 | **Chỉ sửa tài liệu** |

## 4. Trình tự đề xuất — 6 bước, mỗi bước 1 commit, 4 cổng xanh

| Bước | Nội dung | Chạm code? | Phụ thuộc |
|:---:|---|:---:|---|
| **1** | **Chỉ tài liệu.** Cập nhật `docs/13_COMPLIANCE_SPEC.md` mục C: đổi căn cứ TT20→TT18, đánh lại số phụ lục, thêm bảng traceability mới; cập nhật `docs/legal/README.md`; ghi PROJECT_STATE | Không | — |
| **2** | **Seed data pháp lý.** Nạp PL I/II/III (42+72+8 hoạt chất) + PL IV/V/VI (giới hạn nồng độ) thành bảng tham chiếu `controlled_substance` (dùng chung, không theo tenant) | Có — migration + seed | Bước 1 |
| **3** | **Sổ PL XVI.** Mở rộng `ControlledSubstanceCategory` thêm `THUOC_DOC`, `DANH_MUC_CAM`; tách `LedgerBookType` (PL VIII / PL XVI); migration; export CSV/Excel 2 mẫu sổ | Có — domain→app/infra→interface (3 commit con) | Bước 2 |
| **4** | **Biên bản nhận lại PL XVIII.** Entity `DrugReturnRecord` + endpoint + export biểu mẫu 02 bản; ràng buộc "biệt trữ" (đánh dấu lô không được bán lại) | Có — **cross-module** `compliance` ↔ `inventory` | Bước 3 |
| **5** | **Kết xuất cuối ngày (Điều 15 + ghi chú PL VIII).** Job/endpoint kết xuất sổ theo ngày, đóng số trang, hash toàn vẹn để phục vụ ký | Có | Bước 3 |
| **6** | **Chữ ký số (Điều 15.1.d).** Thiết kế riêng — chọn phương án (chữ ký số USB token / ký nội bộ + hash chain / xác nhận điện tử bằng tài khoản IAM) | **Thiết kế trước, chờ duyệt riêng** | Bước 5 |

**Việc bị chặn, không đưa vào 6 bước trên:**

| Việc | Chặn bởi |
|---|---|
| Chốt "bán lẻ có phải báo cáo định kỳ không" | Thiếu **NĐ 163/2025/NĐ-CP** |
| Sửa policy retention (`docs/13` mục C.4) | Thiếu **TT 33/2025** + **TT 26/2025** |
| Nội dung danh mục **thuốc độc** và **danh mục chất bị cấm** cho sổ PL XVI (bước 3 chỉ dựng khung, chưa có dữ liệu) | Thiếu **QĐ 3235/QĐ-BYT** + danh mục thuốc độc hiện hành |

## 5. Quyết định của Chain — chốt 2026-07-25

| # | Câu hỏi | **Chain chốt** | Hệ quả |
|---|---|---|---|
| Q1 | Làm tới bước nào đợt này? | **Bước 1–3** | Bước 4 (biên bản PL XVIII), 5 (kết xuất cuối ngày), 6 (chữ ký số) → đợt sau |
| Q2 | Chữ ký số (Điều 15.1.d)? | **Thiết kế trước, chưa code** | Soạn `01_THIET_KE_KY_DIEN_TU.md` với 3 hướng + chi phí, chờ duyệt riêng |
| Q3 | Spec đã khóa sửa kiểu nào? | **Sửa tại chỗ + changelog** | `docs/13` giữ 1 nguồn sự thật; changelog ở mục H cuối file |
| Q4 | Có bán thuốc độc / danh mục cấm? | **KHÔNG bán** | Bước 3 **chỉ dựng khung** enum + sổ PL XVI cho thuốc dạng phối hợp; **không** seed danh mục thuốc độc/QĐ 3235 ⇒ gỡ 2 blocker 🟡 khỏi đường găng |

## 6. Nhật ký thực thi

| Bước | Trạng thái | Ghi chú |
|:---:|---|---|
| 1 — tài liệu | ✅ **XONG 2026-07-25** | `docs/13` mục C viết lại theo TT18 + mục C.5/C.6 mới + Traceability #22–27 + changelog mục H; `docs/legal/README.md` cập nhật; SUMMARY TT18 đầy đủ |
| 2 — seed danh mục | ⬜ Chưa bắt đầu | PL I (42 GN) + PL II (72 HT) + PL III (8 TC) + giới hạn PL IV/V/VI |
| 3 — sổ PL XVI | ⬜ Chưa bắt đầu | Enum +2 giá trị, `book_type`, migration, export 2 mẫu sổ |
