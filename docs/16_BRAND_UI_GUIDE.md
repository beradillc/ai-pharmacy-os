# 16 — BRAND & UI GUIDE (BERAS)

> Tài liệu thương hiệu & nguyên tắc giao diện. Sếp chốt **2026-07-23**.
> Có hiệu lực cho mọi màn hình, tài liệu bán hàng và văn bản đối ngoại của sản phẩm.
>
> **Phạm vi:** nhận diện, tông màu, thông điệp, nguyên tắc UI. **Ngoài phạm vi:** thiết kế đồ họa
> chi tiết, wireframe, design system (cần người làm thiết kế thật — tài liệu này định hướng, không
> thay thế).
>
> Quyết định thương hiệu gốc nên được ghi ở `01-WikiHub/BeraLLC/ChienLuoc/` theo mẫu T-QuyetDinh;
> tài liệu này là bản áp dụng vào sản phẩm, không phải nơi lưu quyết định chiến lược.

---

## 1. Nhận diện

| Hạng mục | Nội dung |
|----------|----------|
| **Tên sản phẩm** | **BERAS** |
| **Mascot** | Gấu đội áo blouse, kính tròn, cầm tablet |
| **Tagline** (thống nhất với `README.md`, chốt 2026-07-23) | "BERAS là sổ điện tử quản lý nhà thuốc chuẩn Cloud/SaaS thế hệ mới, tích hợp AI hỗ trợ chuyên sâu nghiệp vụ Dược và đảm bảo vận hành liên tục ngay cả khi mất kết nối Internet." |
| **Câu kết thương hiệu** | "BERAS & BeraLLC — Đồng hành bền vững, Vận hành thông minh" |

**Tên kỹ thuật của mã nguồn vẫn là `pharmacy_os`** (package, thư mục, migration, tên bảng). Đổi tên
kỹ thuật là việc riêng, có rủi ro và chi phí riêng — không gộp vào việc đổi định vị thương hiệu.

---

## 2. Tông màu (Eco-Tech)

| Vai trò | Màu |
|---------|-----|
| Nền | Kem / xanh lá nhạt |
| Điểm nhấn | Xanh lá đậm (rừng) |
| Điểm nhấn phụ | Nâu ấm (màu mascot) |
| Icon | Nét line-art, viền nâu / vàng đồng |

Mã màu cụ thể (hex), thang độ đậm nhạt và kiểm tra tương phản cho người khiếm thị: chưa chốt, thuộc
phần thiết kế chi tiết. **Lưu ý khi chốt:** nền kem + chữ xanh lá nhạt rất dễ rớt chuẩn tương phản —
màn POS thường dùng dưới đèn huỳnh quang, màn hình rẻ, người bán nhìn lướt. Ưu tiên đọc được trước,
đẹp sau.

---

## 3. Ba trụ cột thông điệp → module

Mọi màn hình chính phải phục vụ đúng một trong ba trụ cột này. Không thêm thông điệp lệch hướng.

| # | Trụ cột | Module | Thông điệp cho người dùng |
|---|---------|--------|---------------------------|
| 1 | **Bán Hàng Không Gián Đoạn** (POS Offline-First) | `sales` | Bán được cả khi mất mạng, không mất đơn, không bán trùng |
| 2 | **Đảm bảo Pháp Lý & Tuân Thủ Chuẩn Bộ Y Tế** | `compliance` | Sổ sách chứng minh được khi thanh tra hỏi |
| 3 | **Trợ Lý AI Dược Sĩ Thông Minh** (AI-Assisted) | `clinical` | Cảnh báo tương tác/dị ứng, gợi ý thay thế |

---

## 4. Nguyên tắc UI — BẮT BUỘC

### 4.1 Không quảng bá tính năng chưa sẵn sàng

**Không được** để giao diện, tài liệu bán hàng hay văn bản đối ngoại nói tính năng AI "đã sẵn sàng"
khi backend vẫn dùng `MockLLMProvider`. Dùng ngôn ngữ **"đang phát triển" / "sắp ra mắt"** cho tới
khi gỡ blocker `AI__API_KEY` (xem `core/bootstrap.py`, dòng có `# BLOCKER`).

Nguyên tắc này áp dụng cho **mọi** tính năng, không riêng AI: thứ gì backend chưa chạy thật thì UI
không được nói là chạy. Bảng §5 là căn cứ để biết được phép nói gì.

### 4.2 Giữ đúng ba trụ cột

Mỗi màn hình chính phục vụ đúng một trụ cột ở §3. Không chèn thông điệp ngoài ba trụ cột.

### 4.3 Hệ quả UI của các quyết định đã chốt

Ba việc đã chốt ở tầng nghiệp vụ, kéo theo yêu cầu giao diện cụ thể — ghi ở đây để người thiết kế
không phải đi tìm:

| Quyết định đã chốt | Yêu cầu UI |
|--------------------|-----------|
| Đồng ý của khách "bấm có là xong" (2026-07-23) | Nút xin đồng ý nằm **trong luồng bán hàng ở quầy**, một chạm, **không tick sẵn**. Tách rõ 2 mức: cơ bản (tên/SĐT) và sức khỏe (dị ứng/bệnh nền) |
| Thu ngân không xem được dữ liệu sức khỏe | Màn tra khách của thu ngân **không hiển thị** ô dị ứng/bệnh nền — ẩn hẳn, không hiện ô xám hay chữ "bị khóa" (hiện ra là đã tiết lộ có dữ liệu) |
| Khử nhận dạng không đảo ngược được | Thao tác xóa hồ sơ phải có bước xác nhận rõ ràng, nói thẳng "không khôi phục được", **không** gộp chung vào nút rút đồng ý |
| Chi nhánh nằm trong token đã ký | Bộ chọn chi nhánh gọi `POST /auth/switch-branch` và **cấp lại phiên**, không phải đổi một biến ở phía client |

---

## 5. Trạng thái backend thật của ba trụ cột (kiểm chứng 2026-07-23)

> Bảng này tồn tại để §4.1 dùng được chứ không phải khẩu hiệu. Cập nhật mỗi khi trạng thái đổi.

| Trụ cột | Backend | UI được phép nói gì |
|---------|---------|---------------------|
| **1 — POS Offline-First** | ✅ **Chạy được.** `sales` có tạo đơn, xem đơn, in bill (K80/PDF), và endpoint đồng bộ offline `sync_sale`. Đã có e2e | Nói bình thường. Đây là trụ cột vững nhất |
| **2 — Tuân thủ** | 🟠 **Một nửa.** Sổ thuốc kiểm soát, liên thông, `audit_logs` (append-only), `GET /audit-logs`, `GET /privacy/processing-record` đều chạy — **NHƯNG module `compliance` chưa mount router**, nên phần sổ kiểm soát **chưa có mặt HTTP nào** để UI gọi | Nói được về: nhật ký truy vết không sửa được, phân quyền dữ liệu nhạy cảm, bản ghi hoạt động xử lý DLCN. **CHƯA nói được** về màn hình sổ thuốc kiểm soát — chưa có API |
| **3 — Trợ lý AI Dược sĩ** | 🔴 **Chưa thật.** `clinical` chạy engine tương tác/dị ứng **tất định** (không AI); phần AI giải thích dùng `MockLLMProvider`, chưa gọi mô hình thật lần nào. Có cổng theo tenant, mặc định TẮT | **"Đang phát triển"/"sắp ra mắt"** cho phần AI. Phần cảnh báo tương tác/dị ứng tất định thì nói được — nhưng đừng gọi nó là AI |

**Đọc bảng này trước khi viết bất kỳ chữ nào lên màn hình hoặc tài liệu bán hàng.**

⚠️ Điểm dễ sai nhất: trụ cột 3 mang chữ "AI" ngay trong tên trụ cột, trong khi đó lại là phần **yếu
nhất** hiện nay. Cảnh báo tương tác thuốc và dị ứng đang chạy thật nhưng bằng engine tất định, không
phải AI — gọi đúng tên thì vẫn là điểm mạnh bán được, gọi sai thành "AI" là hứa thứ chưa có.

---

## 6. Việc còn treo

| Việc | Ghi chú |
|------|---------|
| Mã màu hex, thang độ, kiểm tra tương phản | Cần người thiết kế |
| Bộ icon line-art | Cần người thiết kế |
| Wireframe màn bán hàng ở quầy | Chưa quyết màn hình nào xây trước |
| Bán cho nhà thuốc lẻ hay chuỗi trước | GĐ đã hỏi, chưa có câu trả lời — ảnh hưởng cả UI lẫn thứ tự tính năng |
| Ghi quyết định thương hiệu vào `BeraLLC/ChienLuoc/` | Theo mẫu T-QuyetDinh |
| Mount router `compliance` | Chặn trụ cột 2 có màn hình sổ kiểm soát |
