# Tóm tắt — TT 20/2017/TT-BYT (Thuốc & nguyên liệu phải kiểm soát đặc biệt)

> Văn bản gốc: `Thông-tư-20-2017-TT-BYT.docx` (cùng thư mục), ban hành 10/5/2017.
> **Đã được distill đầy đủ tại [`docs/13_COMPLIANCE_SPEC.md`](../13_COMPLIANCE_SPEC.md)
> mục C** (phân loại GN/HT/TC, nghĩa vụ bán lẻ, lưu trữ hồ sơ). File này tóm tắt mục lục
> + 1 điểm bổ sung nhỏ từ TT29/2020.

## Mục lục (5 Chương, 22 Điều + 21 Phụ lục biểu mẫu sổ sách)

| Chương | Nội dung | Điều | Đã distill ở docs/13 |
|---|---|---|---|
| I | Phạm vi, đối tượng, phân loại thuốc kiểm soát đặc biệt (7 loại — GN/HT/TC/phóng xạ/độc/danh mục cấm...) | 1–3 | ✅ Mục C.1 |
| II | Bảo quản, sản xuất/pha chế, cấp phát/sử dụng/hủy, giao nhận/vận chuyển, báo cáo | 4–8 | Một phần (chưa toàn bộ, ngoài phạm vi sales/inventory hiện tại) |
| III | Cung cấp thuốc phóng xạ: hồ sơ, trình tự | 9–11 | ❌ Ngoài phạm vi (AI Pharmacy OS chưa xử lý thuốc phóng xạ) |
| IV | Hồ sơ sổ sách theo loại hình cơ sở (sản xuất/XNK/bán buôn/**bán lẻ**/dịch vụ bảo quản-thử nghiệm/khám chữa bệnh), **lưu giữ hồ sơ** | 12–18 | ✅ Mục C.2 (Điều 15 — bán lẻ), C.4 (Điều 18 — lưu trữ) |
| V | Hiệu lực, chuyển tiếp, tham chiếu, trách nhiệm thi hành | 19–22 | — |
| Phụ lục I–XXI | Biểu mẫu sổ sách theo từng loại thuốc/loại cơ sở (Phụ lục XXI = Sổ theo dõi khách hàng bán lẻ GN/HT/TC — nguồn cho `ControlledLedgerEntry`) | | ✅ Mục C.2/C.3 |

## Cập nhật nhỏ từ TT29/2020 (đã đưa vào bảng trên, ghi lại để không đọc sót)

Phụ lục VII (Danh mục thuốc/dược chất bị cấm sử dụng trong một số ngành/lĩnh vực) được TT29/2020
bổ sung câu: **"Danh mục này bao gồm tất cả dạng muối (nếu có) của các chất ghi trong Danh mục"**
— chỉ là làm rõ phạm vi danh mục dữ liệu tham chiếu (seed data), không phải business rule code mới,
không ảnh hưởng `ControlledSubstanceCategory` (7 giá trị) đã có trong domain.

## Trạng thái đối chiếu

Xem bảng Traceability đầu `docs/13_COMPLIANCE_SPEC.md` (dòng 11–16) — đã đối chiếu Điều 3
(phân loại), Điều 15 (nghĩa vụ bán lẻ GN/HT/TC), Điều 18 (lưu trữ ≥2 năm kể từ hết hạn dùng) với
code `compliance` module. Rule ETC nói chung (C.3 rule 1) **vẫn thiếu nguồn** — TT20/2017 chỉ điều
chỉnh thuốc kiểm soát đặc biệt, không phải mọi thuốc kê đơn (ETC) — xem file tóm tắt QĐ1867 mục
"Cập nhật trạng thái blocker" để biết văn bản nào vẫn còn thiếu cho rule này.
