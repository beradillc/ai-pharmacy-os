# docs/legal/ — Chỉ mục văn bản pháp lý

> Mỗi văn bản `.docx` có 1 file `.SUMMARY.md` cùng tên đi kèm — đọc file tóm tắt
> trước, chỉ mở lại `.docx` gốc khi cần trích dẫn nguyên văn hoặc kiểm tra field mới.
> Cập nhật lần cuối: 2026-07-23 (đợt 2 — bổ sung Luật Dược + Luật sửa đổi).

## Bảng tra nhanh

| Văn bản | Số hiệu | Ngày ban hành | Mức liên quan | Đã distill ở |
|---|---|---|:---:|---|
| **Luật Dược** | 105/2016/QH13 | 06/4/2016 | 🔴 **Cao** — nguồn ETC/OTC còn thiếu ở docs/13 | `Luật-105-2016-QH13.SUMMARY.md` |
| **Luật sửa đổi Luật Dược** (chuỗi nhà thuốc, TMĐT dược) | 44/2024/QH15 | (hiệu lực 01/7/2025) | 🔴 **Cao** — khái niệm mới ảnh hưởng kiến trúc | `Luật-44-2024-QH15.SUMMARY.md` |
| Luật Bảo vệ dữ liệu cá nhân | 91/2025/QH15 | 26/6/2025 (hiệu lực 01/01/2026) | 🔴 **Cao** — chặn hồ sơ KH/tích điểm | `Luật-91-2025-QH15.SUMMARY.md` |
| NĐ hướng dẫn thi hành Luật BVDLCN | 356/2025/NĐ-CP | 31/12/2025 (hiệu lực 01/01/2026) | 🔴 **Cao** — chặn hồ sơ KH/tích điểm | `Nghị-định-356-2025-NĐ-CP.SUMMARY.md` |
| GPP — Thực hành tốt cơ sở bán lẻ thuốc | 02/2018/TT-BYT | 22/01/2018 | 🟡 **Trung bình** — retention, liên thông CNTT, quy trình bán/tư vấn | `02_2018_TT-BYT_m_326672.SUMMARY.md` (đã hợp nhất TT11/2025 + TT29/2020) |
| Sửa đổi GPP/GDP/GSP | 11/2025/TT-BYT | 16/5/2025 | 🟡 Đã hợp nhất vào file GPP trên | `Thông-tư-11-2025-TT-BYT.SUMMARY.md` (chỉ mục lục, tra điều khoản gốc) |
| Sửa đổi nhiều VB (mỹ phẩm/dược/HIV/ATTP) | 29/2020/TT-BYT | 31/12/2020 | ⚪ Thấp — 2 điểm nhỏ liên quan TT20/2017 | `Thông-tư-29-2020-TT-BYT.SUMMARY.md` |
| Chuẩn dữ liệu đầu ra liên thông bán lẻ thuốc | 540/QĐ-QLD | 20/8/2018 | 🟢 Đã distill đủ ở docs/13 | `540_QD-QLD_m_391359.SUMMARY.md` |
| Kế hoạch triển khai CSDL Dược | 1867/QĐ-BYT | 24/6/2026 | 🟢 Đã distill ở docs/13 — có bảng cập nhật blocker | `Quyết-định-1867-QĐ-BYT.SUMMARY.md` |
| Thuốc/nguyên liệu kiểm soát đặc biệt | 20/2017/TT-BYT | 10/5/2017 | 🟢 Đã distill đủ ở docs/13 | `Thông-tư-20-2017-TT-BYT.SUMMARY.md` |

## Việc tiếp theo cần đọc trước

1. **[`docs/13_COMPLIANCE_SPEC.md`](../13_COMPLIANCE_SPEC.md)** — spec pháp lý đã khóa cho module
   `compliance` (QĐ540/TT20/QĐ1867). Đầu file có bảng "Văn bản còn thiếu" — đã cập nhật trạng thái
   tại `Quyết-định-1867-QĐ-BYT.SUMMARY.md` mục "Cập nhật trạng thái blocker".
2. **[`docs/14_FEATURE_PROCESS.md`](../14_FEATURE_PROCESS.md)** — cổng bắt buộc cho tính năng mới
   (hồ sơ KH, tích điểm KH, in bill). 2 văn bản mới nhất (Luật 91/2025 + NĐ 356/2025) là input trực
   tiếp cho Bước 1.1/1.8 của cổng này đối với **hồ sơ KH/tích điểm KH**.

## Việc CHƯA làm / cần xác nhận thêm (tổng hợp từ các file tóm tắt)

| # | Việc | Nguồn | Ai quyết |
|---|---|---|---|
| 1 | BeraLLC có cần Giấy chứng nhận đủ điều kiện kinh doanh dịch vụ xử lý DLCN (NĐ356 Điều 21-27) không? | `Nghị-định-356-2025-NĐ-CP.SUMMARY.md` | Cần tư vấn luật sư — không tự kết luận |
| 2 | Thiết kế đồng ý (consent) tách theo mục đích + delete/export cho `Customer` — chưa có trong `CrmService` | `Luật-91-2025-QH15.SUMMARY.md` | Trợ lý Code thiết kế, GĐ duyệt trước khi code (cross-cutting PII) |
| 3 | Vẫn thiếu: NĐ 163/2025/NĐ-CP, NĐ 90/2026/NĐ-CP, đặc tả API CSDL Dược, văn bản kê đơn ngoại trú tổng quát | `Quyết-định-1867-QĐ-BYT.SUMMARY.md` | Sếp thả văn bản khi có — không chặn hồ sơ KH/in bill, chỉ chặn wiring liên thông CSDL Dược thật |
| 4 | ⭐ **Đã tìm thấy nguồn Luật cho rule "ETC cần đơn thuốc"** (Luật Dược Điều 2.27-28 + Điều 6.5.h — cấm bán lẻ ETC không đơn) mà `docs/13_COMPLIANCE_SPEC.md` dòng 14 đang đánh dấu "KHÔNG TÌM THẤY"; cũng tìm thấy nguồn Luật cấp cao nhất cho yêu cầu liên thông CSDL Dược (Điều 75.2 sửa bởi Luật 44/2024) | `Luật-105-2016-QH13.SUMMARY.md`, `Luật-44-2024-QH15.SUMMARY.md` | Sếp xác nhận có nên cập nhật `docs/13_COMPLIANCE_SPEC.md` (spec đã khóa) hay không — Trợ lý Code không tự sửa |
| 5 | **"Chuỗi nhà thuốc"** (Luật 44/2024) là khái niệm pháp lý mới, khớp sẵn với kiến trúc `tenant_id`+`branch_id` hiện tại (Customer scope theo tenant, không theo branch — đã validate đúng hướng); nhưng RBAC/IAM khi thiết kế cần role riêng "chuyên môn cấp chuỗi" vs "chuyên môn cấp nhà thuốc" | `Luật-44-2024-QH15.SUMMARY.md` | Đưa vào bài toán thiết kế IAM khi mở (chưa quyết định ngay) |
