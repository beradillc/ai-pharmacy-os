# Tóm tắt — Nghị định 356/2025/NĐ-CP (hướng dẫn thi hành Luật BVDLCN)

> Văn bản gốc: `Nghị-định-356-2025-NĐ-CP.docx` (cùng thư mục). Ban hành 31/12/2025,
> **hiệu lực 01/01/2026**. Thay thế NĐ 13/2023/NĐ-CP. Đọc cùng
> `Luật-91-2025-QH15.SUMMARY.md` — nghị định này quy định chi tiết các điều Luật
> giao Chính phủ hướng dẫn.

## Mục lục (5 Chương, 42 Điều + Phụ lục biểu mẫu)

| Chương | Nội dung | Điều |
|---|---|---|
| I | Danh mục dữ liệu cá nhân **cơ bản** (Điều 3) và **nhạy cảm** (Điều 4) | 1–4 |
| II | Yêu cầu/điều kiện: thực hiện quyền chủ thể (thời hạn phản hồi), phương thức đồng ý, chuyển giao, DLCN trong tài chính/big data/AI/blockchain/cloud, nhân sự & tổ chức bảo vệ DLCN | 5–16 |
| III | Hồ sơ/trình tự/thủ tục: chuyển xuyên biên giới, DPIA, cấp phép dịch vụ xử lý DLCN, thông báo vi phạm | 17–29 |
| IV | Thực thi: hợp tác quốc tế, kiểm tra, quản lý nhà nước, trách nhiệm các bộ/ngành | 30–40 |
| V | Miễn trừ SME, hiệu lực | 41–42 |

## Danh mục dữ liệu cá nhân (Điều 3–4) — áp dụng trực tiếp cho `crm`/`sales`

| Loại | Ví dụ trong hệ thống | Field tương ứng |
|---|---|---|
| **Cơ bản** (Điều 3) | Họ tên, SĐT, địa chỉ, giới tính, ngày sinh | `Customer.name/phone/address` |
| **Nhạy cảm** (Điều 4.1.d) | **Tình trạng sức khỏe** | `Allergy`, `Condition`, `MedicationHistoryEntry` — TOÀN BỘ module `crm` liên quan bệnh án đều là dữ liệu nhạy cảm |
| **Nhạy cảm** (Điều 4.1.k) | Lịch sử giao dịch tài chính | Không áp dụng trực tiếp (hệ thống không lưu thông tin thẻ ngân hàng KH — chỉ `PaymentMethod` enum không định danh) |

## Nội dung áp dụng cho dự án

| # | Điều | Nội dung | Áp dụng |
|---|------|----------|---------|
| 1 | Điều 4.2 | Xử lý dữ liệu nhạy cảm phải có **phân quyền giới hạn truy cập** riêng | RBAC/IAM (đang chờ xây) cần permission riêng cho dữ liệu dị ứng/bệnh nền, tách khỏi quyền đọc hồ sơ KH cơ bản (ví dụ nhân viên bán hàng thấy tên/SĐT nhưng không nhất thiết thấy bệnh nền, trừ dược sĩ) — **cần quyết định khi thiết kế IAM**, không tự quyết ở đây |
| 2 | Điều 5 | Thời hạn phản hồi yêu cầu chủ thể dữ liệu: **2 ngày làm việc** phản hồi ban đầu, rồi 10 ngày (sửa/xem), 15 ngày (rút đồng ý/hạn chế), **20 ngày (xóa)** — có thể gia hạn 1 lần | Nếu xây tính năng tự phục vụ (KH tự yêu cầu xóa dữ liệu), timeline này là ràng buộc SLA; nếu xử lý thủ công qua nhân viên nhà thuốc thì đây là quy trình vận hành, không phải code, nhưng hệ thống nên hỗ trợ tra cứu nhanh để kịp hạn |
| 3 | Điều 6.3 | **Cấm** thiết lập đồng ý mặc định bật sẵn hoặc gây hiểu lầm | Form UI xin đồng ý (khi làm) phải để checkbox **mặc định tắt** |
| 4 | Điều 6.4 | Xin đồng ý dữ liệu nhạy cảm phải **thông báo rõ đây là dữ liệu nhạy cảm** | Copy UI khi nhập dị ứng/bệnh nền phải có dòng thông báo tường minh, không gộp chung với đồng ý dữ liệu cơ bản |
| 5 | Điều 9 | Xử lý dữ liệu lớn (big data): chỉ thu thập đúng phạm vi, có chính sách xóa/hủy, đào tạo nhân viên | Nếu sau này làm `analytics` (Sprint 7 — dự báo nhu cầu, dashboard) mà gộp dữ liệu KH quy mô lớn, áp dụng điều này |
| 6 | Điều 10 | AI: dữ liệu suy luận từ AI nếu định danh được người cụ thể vẫn là DLCN; phải thông báo & cho phép "không tham gia" | **Module `clinical`**: nếu tương lai AI đưa ra khuyến nghị gắn với `customer_id` cụ thể (hiện tại `AiRecommendation` không gắn `customer_id`, chỉ gắn theo đơn/tương tác thuốc) — giữ nguyên thiết kế ẩn danh này khi mở rộng |
| 7 | Điều 13-16 | Nhân sự bảo vệ DLCN: cao đẳng trở lên, ≥2 năm kinh nghiệm liên quan (pháp chế/CNTT/an ninh mạng...) | BeraLLC (bên xử lý) cần chỉ định người phụ trách bảo vệ DLCN bằng văn bản khi vận hành thật — việc tổ chức, không phải code |
| 8 | **Điều 41.2** | **Miễn trừ hộ kinh doanh/DN siêu nhỏ**: KHÔNG cần DPIA (Đ.21), cấp phép dịch vụ xử lý DLCN (Đ.22), nhân sự chuyên trách (Đ.33.2) — **trừ** khi kinh doanh dịch vụ xử lý DLCN, **trực tiếp xử lý dữ liệu nhạy cảm**, hoặc đạt ≥100.000 chủ thể dữ liệu (lũy kế) | ⚠️ **Đọc kỹ**: pharmacy tenant nhỏ dùng module hồ sơ KH (có dị ứng = nhạy cảm) → **KHÔNG được miễn**, dù là hộ kinh doanh. Miễn trừ quy mô chỉ có giá trị thực tế cho tenant KHÔNG bật tính năng hồ sơ sức khỏe (VD chỉ dùng `sales`/`inventory`/`in bill`, không dùng `crm` bệnh án) |
| 9 | Điều 21 | 9 loại hình **dịch vụ xử lý DLCN** cần Giấy chứng nhận đủ điều kiện kinh doanh riêng (Bộ Công an cấp), bao gồm mục 4: "dịch vụ thu thập/xử lý DLCN qua ứng dụng/phần mềm chăm sóc sức khỏe, theo dõi sức khỏe, dịch vụ y tế" | ⚠️ **Cần xác nhận với sếp/luật sư**: AI Pharmacy OS có rơi vào định nghĩa "dịch vụ xử lý DLCN" cần giấy phép riêng (Điều 21-27) hay chỉ là phần mềm nội bộ nhà thuốc dùng cho hoạt động kinh doanh của chính mình (không phải "kinh doanh dịch vụ xử lý DLCN" cho bên thứ ba)? Đây là câu hỏi pháp lý cần tư vấn chuyên môn, **không tự suy luận** — có khả năng BeraLLC (SaaS B2B) rơi vào diện phải xin Giấy chứng nhận nếu bị coi là "cung cấp dịch vụ xử lý DLCN" cho khách hàng (các nhà thuốc) |

## Việc CHƯA làm / cần xác nhận thêm

1. **Câu hỏi pháp lý mở**: BeraLLC có cần **Giấy chứng nhận đủ điều kiện kinh doanh dịch vụ xử lý DLCN** (Điều 21-27) không? Ảnh hưởng lớn đến timeline ra mắt hồ sơ KH — cần hỏi luật sư trước khi launch, GĐ/Trợ lý Code không tự kết luận.
2. Chưa xác nhận NĐ 163/2025/NĐ-CP mà QĐ 1867 dẫn chiếu trong "Căn cứ" có phải là văn bản khác NĐ 356/2025 hay không — **KHÔNG nhầm lẫn 2 nghị định này**; NĐ 356/2025 là về BVDLCN, còn NĐ 163/2025 (docs/13 header nhắc) có thể là văn bản khác chưa có trong tay.
