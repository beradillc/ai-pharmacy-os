# Tóm tắt — QĐ 1867/QĐ-BYT (Kế hoạch triển khai Hệ thống CSDL về dược)

> Văn bản gốc: `Quyết-định-1867-QĐ-BYT.docx` (cùng thư mục), Bộ Y tế ban hành 24/6/2026.
> **Đã được distill tại [`docs/13_COMPLIANCE_SPEC.md`](../13_COMPLIANCE_SPEC.md) mục D**
> (yêu cầu liên thông, blocker). File này chỉ tóm tắt mục lục + cập nhật trạng thái các
> văn bản blocker mà QĐ1867 dẫn chiếu, nay đã có một phần.

## Mục lục (3 Điều + Kế hoạch triển khai 5 phần I-V)

| Mục | Nội dung |
|---|---|
| Điều 1–3 | Ban hành kế hoạch, hiệu lực (thay QĐ 5071/QĐ-BYT cũ), trách nhiệm thi hành |
| I | Mục đích, yêu cầu |
| II.1 | Rà soát/cập nhật quy chế vận hành + hướng dẫn kết nối liên thông + quy trình hỗ trợ |
| II.2 | Đăng ký tài khoản, định danh xác thực |
| II.3 | Khởi tạo dữ liệu, thực hiện liên thông dữ liệu |
| II.4 | Kiểm tra giám sát, khai thác dữ liệu phục vụ quản lý nhà nước |
| II.5 | Tập huấn, hỗ trợ người dùng |
| III (ẩn) | (không có mục III độc lập trong bố cục gốc — xem IV/V) |
| IV | Kinh phí thực hiện |
| V | Tổ chức thực hiện |

## Cập nhật trạng thái blocker (so với header docs/13)

`docs/13_COMPLIANCE_SPEC.md` đầu file liệt kê các văn bản QĐ1867 dẫn chiếu nhưng "chưa có trong
tay" tại thời điểm khóa spec. Cập nhật sau đợt bổ sung văn bản 2026-07-23:

| Văn bản blocker (theo docs/13) | Trạng thái hiện tại |
|---|---|
| TT 11/2025/TT-BYT (sửa TT02/2018, TT03/2018, TT36/2018) | ✅ **Đã có** — xem `Thông-tư-11-2025-TT-BYT.SUMMARY.md` |
| NĐ 163/2025/NĐ-CP | ❌ Vẫn **chưa có** — không nhầm với NĐ 356/2025 (BVDLCN) vừa nhận, đây là văn bản khác |
| NĐ 90/2026/NĐ-CP (chế tài xử phạt không liên thông) | ❌ Vẫn **chưa có** |
| Đặc tả API kết nối CSDL Dược (Trung tâm Thông tin y tế Quốc gia, hoàn thành dự kiến 6/2026) | ❌ Vẫn **chưa có** — đây là blocker chính chặn wiring `NationalSyncService` thật (`MockNationalDrugDbGateway` vẫn giữ nguyên) |
| Văn bản kê đơn ngoại trú (nguồn cho rule "mọi thuốc ETC cần prescription_code", mục C.3 docs/13) | ❌ Vẫn **chưa có** — TT 11/2025 chỉ nói đến "đơn thuốc điện tử" khi bán online, KHÔNG phải nguồn tổng quát cho rule ETC nói chung |

**Kết luận:** đợt bổ sung văn bản lần này (Luật 91/2025, NĐ 356/2025, TT02/2018, TT11/2025,
TT29/2020) giải quyết được đúng 2 blocker "In bill"/"hồ sơ KH" (BVDLCN + GPP), nhưng **KHÔNG**
giải quyết blocker liên thông CSDL Dược thật (vẫn cần đặc tả API + NĐ163/2025 + NĐ90/2026) — việc
đó vẫn đứng nguyên, không ảnh hưởng tới quyết định mở hồ sơ KH/tích điểm/in bill.
