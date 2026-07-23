# docs/legal/ — Chỉ mục văn bản pháp lý

> Mỗi văn bản `.docx` có 1 file `.SUMMARY.md` cùng tên đi kèm — đọc file tóm tắt
> trước, chỉ mở lại `.docx` gốc khi cần trích dẫn nguyên văn hoặc kiểm tra field mới.
> Cập nhật lần cuối: 2026-07-23 (đợt bổ sung văn bản cho gate hồ sơ KH/tích điểm/in bill).

## Bảng tra nhanh

| Văn bản | Số hiệu | Ngày ban hành | Mức liên quan | Đã distill ở |
|---|---|---|:---:|---|
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
| 4 | ⚠️ **Luật Dược hiện hành (105/2016/QH13, sửa đổi bởi Luật 44/2024/QH15) bản thân luật CHƯA có file riêng** trong thư mục này — mới chỉ có 3 văn bản **hướng dẫn thi hành** Luật Dược (TT02/2018, TT11/2025, TT20/2017). Đủ dùng cho phạm vi GPP/kiểm soát đặc biệt hiện tại, nhưng nếu cần đối chiếu điều khoản gốc của Luật Dược (VD định nghĩa ETC/OTC chính thức) thì vẫn chưa có nguồn | 4 văn bản pháp lý yêu cầu ban đầu, còn thiếu 1/4 | Sếp thả file khi cần đối chiếu sâu hơn |
