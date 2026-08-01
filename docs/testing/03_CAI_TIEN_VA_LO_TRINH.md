# Danh sách cải tiến · Missing Features · Priority Roadmap

> Output **03** (cải tiến) · **UI Improvements** · **Missing Features** · **Priority Roadmap**
> của MASTER PROMPT V3. Không sửa code trong đợt này.

---

## A. Missing Features — 7 màn có backend, thiếu giao diện

Xếp theo **thiệt hại nếu thiếu**, không theo công sức.

| # | Màn cần dựng | Backend đã có | Vì sao xếp ở đây |
|---|---|---|---|
| 1 | **Đổi mật khẩu** | `POST /auth/change-password` | Không có ⇒ mật khẩu do người khác đặt, vĩnh viễn. Chặn **ngày đầu** |
| 2 | **Đổi trả hàng** | `POST /sales/{id}/returns` | Khách trả thuốc là chuyện **chắc chắn xảy ra** trong một tuần bán lẻ; thiếu ⇒ tồn và doanh thu sai |
| 3 | **Sổ thuốc kiểm soát đặc biệt** | `/controlled-ledger/*` + 122 hoạt chất đã nạp | **Nghĩa vụ pháp lý**. Dữ liệu nằm sẵn mà không ai chạm được |
| 4 | **Nhà cung cấp** | `/suppliers` | Thiếu ⇒ **màn Đơn mua hàng hiện có nhưng dùng không được** |
| 5 | **Nhật ký hoạt động** | `/audit/dashboard` | Thứ chủ quầy cần khi có chênh lệch tiền/hàng |
| 6 | **Thông tin cơ sở** | ⚠️ chỉ biến môi trường | Dược sĩ không tự sửa được thông tin in trên hoá đơn |
| 7 | **Thông tin người dùng** | `GET /auth/me` | Gộp chung với #1 thì rẻ |

> 🔴 **Điểm chung đáng chú ý:** *không màn nào cần viết backend mới*. Toàn bộ là **nối dây
> giao diện**. Đây là loại việc rẻ nhất trong phần mềm — và cũng là loại dễ bị hoãn nhất, vì
> nhìn từ phía backend thì "đã xong rồi".

---

## B. UI Improvements

### B-1 · Vùng chạm 44px

| Phần tử | Hiện | Đề nghị |
|---|---|---|
| Nút **Thêm** (Bán hàng) | 36px | **48px** — nút bấm nhiều nhất trong ngày, nên rộng tay hơn chuẩn |
| Tab nhóm (4 tab) | 38px | 44px |
| Nút **Tính lại** | 36px | 44px |
| Nút **Thanh toán** | 43px | 48px |
| Logo **BERAS** | 23px | giữ nguyên, **đánh dấu là nhãn** |

⚠️ **Rủi ro hồi quy:** các lớp này dùng ở hàng chục chỗ. Tăng chiều cao từng làm trang phình
**3,5 → 12,5 màn** (31/07). Phải đo lại chiều dài trang sau khi sửa, không chỉ đo nút.

### B-2 · Trạng thái rỗng cho 6 màn

Mỗi màn một câu, nói đúng ba điều: *đang trống*, *vì sao*, *làm gì tiếp*.

| Màn | Câu đề nghị |
|---|---|
| Báo cáo | *"Chưa có dữ liệu bán hàng. Báo cáo sẽ có sau đơn hàng đầu tiên."* |
| Đề xuất đặt hàng | *"Cần khoảng 30 ngày bán hàng để dự báo. Hiện chưa đủ dữ liệu."* |
| Nhập hàng | *"Chọn thuốc, nhập số lô và hạn dùng. Hàng vào kho ngay khi lưu."* |
| Khởi tạo tồn | *"Dùng MỘT LẦN khi bắt đầu — đếm hàng đang có sẵn trên kệ. Không hỏi giá vốn."* |
| Cài đặt · Nhân viên | chấp nhận được, không cần |

### B-3 · Phân biệt "Nhập hàng nhanh" với "Khởi tạo tồn kho"

Hai tab cạnh nhau, tên gần giống, hệ quả **khác nhau về kế toán**: khởi tạo **không hỏi giá
vốn**, nhập mua thì có. Dùng nhầm ⇒ sai giá vốn bình quân ⇒ sai lãi gộp.

**Đề nghị:** một dòng dưới mỗi tab —
*"Nhập hàng: hàng mới mua về, có hoá đơn."* / *"Khởi tạo: hàng đã có sẵn trên kệ từ trước."*

### B-4 · Audit log — thêm *giá trị cũ → mới* và thiết bị

Chain yêu cầu rõ. Ưu tiên cho nhóm đụng tiền và đụng hàng: **sửa giá · điều chỉnh tồn · huỷ
đơn · hoàn đơn · phân quyền**.

---

## C. Priority Roadmap

### Đợt 1 — trước khi bán đơn thật đầu tiên 🔴

| # | Việc | Vì sao trước |
|---|---|---|
| 1 | Màn **Đổi mật khẩu** + chặn khi cờ bật | Chặn ngày đầu |
| 2 | Nâng nút **Thêm** và **Thanh toán** lên 48px | Rẻ nhất; ảnh hưởng mỗi lượt bán |
| 3 | Trạng thái rỗng cho **Báo cáo** và **Đề xuất** | Rẻ; chặn hiểu nhầm "phần mềm hỏng" |

*Ba việc này gọn trong một phiên và không đụng nghiệp vụ.*

### Đợt 2 — trong tuần chạy thử 🟠

| # | Việc |
|---|---|
| 4 | Màn **Đổi trả hàng** |
| 5 | Màn **Nhà cung cấp** (mở khoá màn Đơn mua hàng đang có) |
| 6 | Màn **Thông tin cơ sở** (bỏ phụ thuộc biến môi trường) |
| 7 | Phân biệt Nhập hàng ↔ Khởi tạo tồn |

### Đợt 3 — trước khi phát hành thương mại 🔴🟠

| # | Việc |
|---|---|
| 8 | **Sổ thuốc kiểm soát đặc biệt** — cần Trợ lý Pháp Lý rà trước |
| 9 | Màn **Nhật ký hoạt động** |
| 10 | Audit log: **giá trị cũ → mới** + thiết bị |
| 11 | Màn tra cứu **Đơn thuốc** |
| 12 | Còn lại của vùng chạm 44px |

### Đợt 4 — nợ kỹ thuật đã biết

| # | Việc |
|---|---|
| 13 | Gom port `SalesService` thành `SalesPorts` (chữ ký 8 tham số, đã suýt nổ một lần) |
| 14 | Sơ đồ kho **mức 2** — mặt bằng thật ⚠️ chỉ khi có người **đo toạ độ** |
| 15 | Phase 8 multi-supplier — cần Chain chốt tiêu chí chọn NCC |

---

## D. Suggestions — ngoài phạm vi lỗi

| Đề xuất | Vì sao |
|---|---|
| **Nút "Bán lại đơn này"** ở màn Hoá đơn | Khách mua lại đúng toa cũ là ca rất thường ở quầy xã |
| **Quét mã vạch bằng camera điện thoại** | Ô tìm thuốc đã nhận mã vạch; thiếu đúng phần đọc camera |
| **Chế độ tối (Dark Mode)** | Quầy mở sớm/đóng muộn; hiện chưa có |
| **Nhắc hạn dùng theo tuần** | Đã có cảnh báo cận hạn; thiếu bản tóm tắt đầu tuần |
| **Xuất Excel cho báo cáo** | Đã có CSV; kế toán quen Excel hơn |
| **Tách `thieu` ở lộ trình lấy hàng** thành *chưa xếp ô* / *không đủ trong ô* | Hai nguyên nhân, hai cách xử lý |
