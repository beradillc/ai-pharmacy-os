# Báo cáo UAT — BERA Pharma SaaS

**Ngày:** 2026-08-01 · **Bản:** 0.2.0 · **Môi trường:** `qt650` (Quầy thuốc 650)
**Phạm vi:** UAT · UX Audit · Mobile Audit · Feature Gap Analysis · chuẩn bị video training

> ⚠️ **KHÔNG sửa code, KHÔNG đổi dữ liệu, KHÔNG tạo video** trong đợt này — theo STOP RULE.
> Mọi con số dưới đây **đo bằng máy**, lưu ở `uat-raw.json`, không viết từ trí nhớ.

---

## 0. Executive Summary

Phần mềm **chạy ổn định** ở mọi khổ và cả hai engine trình duyệt: **128 lượt đo, 0 lỗi
JavaScript, 0 tràn khung nhìn, 0 ô nhập biến dạng**. Đây là kết quả tốt hơn hầu hết sản phẩm
ở giai đoạn này.

Nhưng **không sẵn sàng phát hành thương mại**, vì hai lý do khác nhau về bản chất:

| | Vấn đề | Mức |
|---|---|---|
| **A** | **Người dùng không tự đổi được mật khẩu.** Hệ thống đặt cờ *"phải đổi mật khẩu"* nhưng **không có màn nào để đổi**, và cũng **không chặn đăng nhập**. Dược sĩ sẽ dùng vĩnh viễn mật khẩu do người khác đặt | 🔴 **Critical** |
| **B** | **7 nghiệp vụ có backend nhưng không có màn hình** — trong đó có **Đổi trả**, **Nhà cung cấp** và **Sổ thuốc kiểm soát đặc biệt** | 🔴 **Critical** (sổ kiểm soát) / 🟠 Major |

Vấn đề A chặn **ngày đầu tiên** dùng thật. Vấn đề B chặn **tuần đầu tiên**.

### Con số

| Hạng mục | Kết quả |
|---|---|
| Lượt đo | **128** (16 màn × 4 khổ × 2 engine) |
| Engine | WebKit (Safari/iOS) · Firefox |
| Khổ | iPhone dọc 390×844 · iPhone ngang 844×390 · iPad 820×1180 · Laptop 1440×900 |
| Lỗi JavaScript | **0** |
| Trang cuộn ngang | **0** |
| Phần tử tràn khung nhìn | **0** |
| Ô nhập biến dạng (>96px) | **0** |
| **Vùng chạm dưới 44px** | **128/128 lượt** — xem §3 |
| Màn thiếu trạng thái rỗng | **6/16** |
| Nghiệp vụ có backend, thiếu màn | **7** |

---

## 1. Business Audit — đối chiếu 22 luồng Chain liệt kê

| # | Luồng | Màn hình | API | Trạng thái |
|---|---|---|---|---|
| 1 | Đăng nhập | ✅ `/login` | ✅ | Đạt |
| 2 | **Đổi mật khẩu** | ❌ **không có** | ✅ `/auth/change-password` | 🔴 **Critical** |
| 3 | **Thông tin cơ sở** | ❌ **không có** | ⚠️ chỉ biến môi trường | 🟠 Major |
| 4 | **Thông tin người dùng** | ❌ **không có** | ✅ `/auth/me` | 🟠 Major |
| 5 | Quản lý nhân viên | ✅ `/nhan-vien` | ✅ | Đạt |
| 6 | Phân quyền | ✅ trong `/nhan-vien` | ✅ | Đạt |
| 7 | Danh mục thuốc | ✅ `/danh-muc-thuoc` | ✅ | Đạt — 70 mã |
| 8 | Nhập hàng | ✅ `/nhap-nhanh` | ✅ | Đạt |
| 9 | Điều chỉnh giá | ✅ trong Danh mục | ✅ | Đạt |
| 10 | **Điều chỉnh tồn** | ❌ **không có** | ⚠️ chỉ qua kiểm kê | 🟠 Major |
| 11 | Kiểm kê | ✅ `/kiem-ke` | ✅ | Đạt |
| 12 | Bán hàng | ✅ `/` | ✅ | Đạt |
| 13 | **Đổi trả** | ❌ **không có** | ✅ `/sales/{id}/returns` | 🔴 **Critical** |
| 14 | Khách hàng | ✅ `/khach-hang` | ✅ | Đạt |
| 15 | **Nhà cung cấp** | ❌ **không có** | ✅ `/suppliers` | 🟠 Major |
| 16 | Đơn thuốc | ⚠️ một phần | ✅ | Chụp ảnh + duyệt ở quầy; **không có màn tra cứu** |
| 17 | In hoá đơn | ✅ `/hoa-don` | ✅ K80/A5/A4 | Đạt |
| 18 | Báo cáo | ✅ `/bao-cao` | ✅ | Đạt |
| 19 | Dashboard | ✅ `/bang-dieu-hanh` | ✅ | Đạt |
| 20 | **Nhật ký hoạt động** | ❌ **không có** | ✅ `/audit/dashboard` | 🟠 Major |
| 21 | Cấu hình | ⚠️ `/cai-dat` | — | Chỉ giao diện + lưu trữ |
| 22 | **Sổ thuốc kiểm soát đặc biệt** | ❌ **không có** | ✅ `/controlled-ledger/*` | 🔴 **Critical (pháp lý)** |

**15/22 đạt · 7 thiếu màn hình.** Đáng chú ý: **không luồng nào thiếu backend** — mọi thứ đã
có API và đã có test. Đây là khoảng cách **giao diện**, không phải khoảng cách năng lực.

### 🔴 Vì sao §22 là Critical, không phải Major

Sổ theo dõi thuốc kiểm soát đặc biệt là **nghĩa vụ pháp lý** của cơ sở bán lẻ (TT18). Backend
đã có đủ: bút toán, chốt sổ ngày, xuất báo cáo, **122 hoạt chất kiểm soát đã nạp sẵn**. Nhưng
không có màn nào ⇒ **dược sĩ không dùng được**, và khi thanh tra hỏi thì phần mềm không giúp
được gì dù dữ liệu nằm sẵn trong đó.

---

## 2. Mobile Audit

Đo trên **WebKit** (đúng engine Safari/iOS) và Firefox, bốn khổ.

| Phép đo | Kết quả |
|---|---|
| Trang cuộn ngang | **0/128** |
| Phần tử tràn khung nhìn | **0/128** |
| Ô nhập cao bất thường | **0/128** |
| Lỗi JavaScript | **0/128** |
| Xoay ngang (844×390) | Không màn nào vỡ |
| Tablet (820×1180) | Không màn nào vỡ |

**Đánh giá:** phần responsive **đạt chuẩn phát hành**. Các lỗi bố cục từng có (chữ vỡ, cột bị
cắt, ô nhập 260px) **đã hết** và có cổng tự động canh.

### 🟠 Vùng chạm dưới 44px — 128/128 lượt

| Phần tử | Cao | Gặp | Đánh giá |
|---|---|---|---|
| Logo **BERAS** trên thanh đầu | 23px | 128× | ⚪ **Không phải lỗi** — là nhãn thương hiệu, không phải nút. *Đề nghị: bỏ khỏi danh sách phần tử bấm được* |
| Tab **Nhập hàng nhanh / Khởi tạo tồn kho** | 38px | 16× | 🟠 Thiếu 6px so với chuẩn |
| Tab **Sơ đồ kho / Kiểm kê** | 38px | 16× | 🟠 Thiếu 6px |
| Nút **Tính lại** (Đề xuất đặt hàng) | 36px | 8× | 🟠 Thiếu 8px |
| Nút **Thêm** (thêm thuốc vào giỏ) | 36px | 2× | 🔴 **Nút bấm nhiều nhất trong ngày** |
| Nút **Thanh toán** | 43px | 2× | 🟠 Thiếu 1px |

🔴 **Nút "Thêm" đáng lo nhất**: đây là nút người bán bấm hàng trăm lần mỗi ngày, và 36px là
dưới chuẩn WCAG/iOS (44px). Bấm trượt ở quầy đông khách là thêm một hộp sai vào giỏ.

---

## 3. UX Audit — góc nhìn người lần đầu dùng

### 🟠 Sáu màn không nói gì khi trống

Trên CSDL mới (kho chưa có gì — đúng trạng thái quầy ngày đầu), sáu màn **không có dòng
hướng dẫn nào**:

| Màn | Người mới sẽ nghĩ | Nên hiện |
|---|---|---|
| **Báo cáo** | *"Phần mềm hỏng?"* | *"Chưa có dữ liệu bán hàng. Báo cáo sẽ có sau đơn hàng đầu tiên."* |
| **Đề xuất đặt hàng** | *"Bấm Tính lại mãi không ra gì"* | *"Cần ít nhất 30 ngày bán hàng để dự báo."* |
| **Nhập hàng** | (biểu mẫu trống, không rõ bắt đầu từ đâu) | *"Chọn thuốc, nhập số lô và hạn dùng."* |
| **Khởi tạo tồn** | (không rõ khác Nhập hàng chỗ nào) | *"Dùng một lần khi bắt đầu — đếm hàng đang có trên kệ."* |
| **Cài đặt** | — | chấp nhận được |
| **Nhân viên** | — | chấp nhận được (đã có 1 dòng) |

**Đây là loại lỗi UX đắt nhất với người mới**: màn hình trống không phân biệt được *"chưa có
dữ liệu"* với *"phần mềm lỗi"*, và người dùng lần đầu luôn đoán vế thứ hai.

### ✅ Điểm mạnh rõ rệt

| Điểm | Vì sao đáng giữ |
|---|---|
| Cảnh báo **"7 thuốc chưa có hoạt chất"** ở Danh mục | Nói rõ hệ quả (*"cảnh báo dị ứng sẽ im lặng"*) chứ không chỉ đếm |
| **Xác nhận hai bước** khi thanh toán | Đúng cho một thao tác đụng tiền và tồn kho |
| **Dược sĩ duyệt đơn** trước khi bán thuốc kê đơn | Đúng luật, và nói rõ khi tài khoản không đủ quyền |
| Cửa sổ chi tiết có **✕**, đóng bằng `Esc`, khoá cuộn nền | Nhất quán trên 14 chỗ |
| Hoá đơn in **đúng một đơn**, khổ K80 | Không in nhầm cả trang |
| Số tiền theo quy ước Việt Nam (`2.200 đ`) | Không còn `2200.00` |

---

## 4. Dashboard & Report Audit — không kiểm thử được đầu-cuối

🔴 **Chặn:** CSDL chạy thử có **0 đơn hàng, 0 tồn kho, 0 khách hàng** (đúng chỉ đạo của Chain
ngày 01/08 — dữ liệu sẽ nhập tay trong tuần thử). STOP RULE cấm thay đổi dữ liệu.

⇒ **13/22 luồng không kiểm thử được đầu-cuối**: Nhập hàng · Điều chỉnh tồn · Kiểm kê · Bán
hàng · Đổi trả · Khách hàng · Đơn thuốc · In hoá đơn · Báo cáo · Dashboard · Nhật ký · Top
thuốc · Cảnh báo cận hạn.

**Đề nghị — Chain chọn một:**

| Phương án | Được | Mất |
|---|---|---|
| **(a)** Dựng CSDL UAT **riêng** (`uat650`), có dữ liệu thử đầy đủ | Kiểm thử được 22/22 luồng; **không đụng** `qt650` | Cần khoảng một phiên |
| **(b)** Chờ tuần chạy thử — dữ liệu thật tự sinh | Không tốn gì | Lỗi phát hiện **sau khi** đã dùng thật |
| **(c)** Chỉ nghiệm thu phần đã đo | Xong ngay | 13 luồng chưa có bằng chứng |

**GĐ đề nghị (a).** Lý do: dashboard và báo cáo là hai màn *chỉ có ý nghĩa khi có dữ liệu*, và
đây đúng là hai màn chủ chuỗi dùng để ra quyết định. Nghiệm thu chúng trên màn trống là nghiệm
thu một khung rỗng.

### Chủ chuỗi — giới hạn cấu trúc

Quầy thuốc 650 có **một chi nhánh**. Mọi so sánh giữa chi nhánh (doanh thu từng chi nhánh, xếp
hạng) **không có gì để so**. Đây là giới hạn của dữ liệu, không phải của phần mềm — cần một
tenant hai chi nhánh mới nghiệm thu được nhóm tính năng đó.

---

## 5. Activity Log Audit

Backend **có ghi** và có test: `audit_logs` với *ai · lúc nào · chi nhánh · đối tượng · hành
động*. Kiểm chứng thật trong phiên này: mỗi thuốc được tạo sinh đúng một dòng
`CATALOG_DRUG_CREATED`.

| Chain yêu cầu log có | Backend có | Ghi chú |
|---|---|---|
| Ai thực hiện | ✅ `actor_user_id` | |
| Thời gian | ✅ `occurred_at` | |
| Chi nhánh | ✅ trong `context` | |
| **Thiết bị** | ⚠️ chỉ có `client_ip` | Không có user-agent |
| **Giá trị cũ / mới** | ⚠️ **không có** | Chỉ ghi *đã xảy ra hành động gì*, không ghi *đổi từ gì sang gì* |

🟠 **Hai thiếu sót thật.** Với thao tác đụng tiền (sửa giá) và đụng hàng (điều chỉnh tồn), *giá
trị cũ → mới* là thứ khiến sổ audit dùng được khi có tranh chấp. Hiện phải suy ra từ bảng
`price_history` riêng.

Và **không có màn hình nào để xem** — xem §1 mục 20.

---

## 6. Regression Risks

| Rủi ro | Vì sao |
|---|---|
| **Sửa vùng chạm 44px** | Chạm vào `.ghost`, `.menhGiaNut`, `TabManGop` — dùng ở **hàng chục chỗ**. Tăng chiều cao có thể làm dài trang trên khổ nhỏ, đúng lỗi đã gặp 31/07 (trang phình 3,5→12,5 màn) |
| **Thêm màn mới** (đổi trả, nhà cung cấp, sổ kiểm soát) | Mỗi màn thêm một mục menu; menu vừa được gộp còn 13 mục — thêm 4 nữa là quay lại vấn đề cũ |
| **Thêm màn đổi mật khẩu** | Chạm luồng đăng nhập — luồng duy nhất mà hỏng thì **không ai vào được** |
| **Thêm giá trị cũ/mới vào audit** | Đổi lược đồ bảng `audit_logs`; bảng này đã có ràng buộc độ rộng cột từng gây sự cố (varchar(32)) |

---

## 7. Kết luận nghiệm thu

| Hạng mục | Kết luận |
|---|---|
| Ổn định kỹ thuật | ✅ **Đạt** — 0 lỗi trên 128 lượt đo |
| Responsive / Mobile | ✅ **Đạt** |
| Vùng chạm | 🟠 **Chưa đạt** — 5 loại nút dưới 44px |
| Đầy đủ nghiệp vụ | 🔴 **Chưa đạt** — 7 màn thiếu |
| Bảo mật tài khoản | 🔴 **Chưa đạt** — không đổi được mật khẩu |
| Tuân thủ pháp lý | 🔴 **Chưa đạt** — không có màn sổ kiểm soát đặc biệt |
| Sẵn sàng chạy thử tại quầy | 🟠 **Có điều kiện** — xem checklist `06` |
| Sẵn sàng phát hành thương mại | 🔴 **Chưa** |

**Khuyến nghị:** cho phép **chạy thử nội bộ tại Quầy thuốc 650** sau khi xử lý 3 mục Critical;
**chưa phát hành thương mại** cho tới khi đóng đủ nhóm Major.
