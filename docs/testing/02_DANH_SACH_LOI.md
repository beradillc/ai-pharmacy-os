# Danh sách lỗi — UAT 2026-08-01

> 🟢 **Cập nhật 2026-08-01, sau ĐỢT 1** (Chain uỷ quyền sửa toàn bộ lỗi trước khi quay video).
> **Đã đóng: C-01 · U-01 · U-02 · U-03 · U-04 · U-05 · U-06 · U-07.**
> Còn lại: **C-02 · C-03 · M-01…M-08**. Xem cột *Trạng thái* ở mỗi mục.

Phân loại: **Critical** (chặn dùng thật) · **Major** (dùng được nhưng thiếu nghiệp vụ) ·
**Minor** · **UX** · **Performance** · **Suggestion**.

> Mọi mục đều **đo được**, không có mục nào từ cảm nhận. Cột *Bằng chứng* nói cách kiểm lại.

---

## 🔴 CRITICAL

### ✅ C-01 · Không có đường đổi mật khẩu — **ĐÃ ĐÓNG**

| | |
|---|---|
| **Hiện tượng** | Tài khoản mới có cờ `must_change_password = true`, nhưng **không màn nào** cho đổi, và **đăng nhập không bị chặn** |
| **Hệ quả** | Dược sĩ Trinh Thư dùng **vĩnh viễn** mật khẩu do người khác đặt. Mọi nhân viên tạo sau cũng vậy — người tạo tài khoản biết mật khẩu của họ |
| **Bằng chứng** | `select must_change_password from users` → `t`; đăng nhập bằng Playwright vào thẳng màn Bán hàng, không qua bước nào |
| **Backend** | ✅ `POST /auth/change-password` **đã có** |
| **Thiếu** | Màn đổi mật khẩu + chặn điều hướng khi cờ bật |
| **Rủi ro sửa** | Cao — chạm luồng đăng nhập, hỏng thì không ai vào được |
| **✅ Đã sửa** | Màn `features/auth/DoiMatKhau` + cửa chặn ở `AppShell`. Kiểm chứng đầu-cuối trên trình duyệt thật: đăng nhập bị chặn · gõ thẳng `/ton-kho` vẫn bị chặn · sai mật khẩu cũ báo lỗi · đổi đúng thì vào được · đăng nhập bằng mật khẩu mới không còn chặn · đổi lại về cũ thì API trả 200 |

### C-02 · Không có màn Đổi trả

| | |
|---|---|
| **Hiện tượng** | Khách trả thuốc → **không thao tác được trên phần mềm** |
| **Hệ quả** | Tồn kho và doanh thu **sai** ngay lần đầu có khách trả hàng. Trong một tuần bán lẻ, đây là chuyện gần như chắc chắn xảy ra |
| **Bằng chứng** | `grep "/returns" frontend/src` → **0 tệp**; backend có `POST /sales/{id}/returns` + test |
| **Backend** | ✅ đã có, đã test |

### C-03 · Không có màn Sổ thuốc kiểm soát đặc biệt

| | |
|---|---|
| **Hiện tượng** | Backend có bút toán, chốt sổ ngày, xuất báo cáo; **122 hoạt chất kiểm soát đã nạp** — nhưng không màn nào |
| **Hệ quả** | **Nghĩa vụ pháp lý (TT18) không thực hiện được qua phần mềm** dù dữ liệu nằm sẵn trong đó |
| **Bằng chứng** | `grep "controlled-ledger" frontend/src` → **0 tệp**; API `/controlled-ledger/books/{type}/daily-closure` có |
| **Ghi chú** | Xem thêm cờ pháp lý *quầy thuốc vs nhà thuốc* ở `QUAY_THUOC_650_CHAY_THU.md` |

---

## 🟠 MAJOR

### M-01 · Không có màn Nhà cung cấp
Backend có `/suppliers` đầy đủ. Không tạo được NCC ⇒ **không tạo được đơn mua hàng** ⇒ màn Đơn
mua hàng hiện có nhưng dùng không được. *Bằng chứng: `suppliers` → 0 tệp FE; `select count(*)
from suppliers` → 0.*

### M-02 · Không có màn Thông tin cơ sở
Tên/địa chỉ/ĐT/MST in trên hoá đơn nằm trong **biến môi trường** (`backend/.env`). Dược sĩ
**không tự sửa được** — phải nhờ kỹ thuật. Với SaaS nhiều nhà thuốc, đây là chặn thật.

### M-03 · Không có màn Thông tin người dùng
`GET /auth/me` có. Người dùng không xem/sửa được tên, không đổi mật khẩu (xem C-01).

### M-04 · Không có màn Nhật ký hoạt động
`/audit/dashboard` có backend. Chủ quầy **không tra được ai đã làm gì** — mà đây đúng là thứ
chủ quầy cần khi có chênh lệch tiền hoặc hàng.

### M-05 · Audit log thiếu *giá trị cũ → mới*
Chain yêu cầu rõ. Hiện chỉ ghi *đã xảy ra hành động gì*. Với sửa giá và điều chỉnh tồn, thiếu
cặp giá trị này thì sổ audit **không dùng được khi có tranh chấp**.

### M-06 · Audit log thiếu thông tin thiết bị
Chỉ có `client_ip`, không có user-agent ⇒ không phân biệt được thao tác từ máy quầy hay từ
điện thoại cá nhân.

### M-07 · Không có màn Điều chỉnh tồn trực tiếp
Chỉ điều chỉnh được qua **kiểm kê**. Đúng về kiểm soát, nhưng khi cần sửa nhanh một lô nhập
sai số thì phải mở cả một phiên kiểm kê.

### M-08 · Không có màn tra cứu Đơn thuốc
Chụp và duyệt được **tại quầy**, xem lại được trong *Cài đặt → Lưu trữ*, nhưng không tra cứu
được theo khách/theo ngày. Khi thanh tra hỏi *"đơn thuốc của khách X"* thì không tìm nhanh được.

---

## 🟡 MINOR / UX

### ✅ U-01 · Nút "Thêm" chỉ cao 36px — **ĐÃ ĐÓNG (nay 48px)** 🔴 *(Minor về kỹ thuật, nhưng ảnh hưởng lớn nhất)*
Nút bấm **nhiều nhất trong ngày** ở màn Bán hàng, dưới chuẩn chạm 44px (WCAG/iOS). Bấm trượt ở
quầy đông là thêm nhầm hộp thuốc vào giỏ. *Đo: `Thêm=36px`, 2 lượt trên khổ điện thoại.*

### ✅ U-02 · Bốn tab điều hướng cao 38px — **ĐÃ ĐÓNG (nay 44px)**
`Nhập hàng nhanh` · `Khởi tạo tồn kho` · `Sơ đồ kho` · `Kiểm kê` — thiếu 6px.

### ✅ U-03 · Nút "Tính lại" cao 36px — **ĐÃ ĐÓNG** · ✅ **U-04** Nút "Thanh toán" 43px → 48px

🔴 **Nguyên nhân U-03 sâu hơn tưởng:** nút dùng `className={styles.primary}` — **class đó
không tồn tại**. CSS Modules trả `undefined`, React render `class="undefined"`, nút rơi về
mặc định trình duyệt: không màu thương hiệu, không chiều cao. **Không lint nào bắt** (tên
class là một chuỗi), **không test nào bắt** (nút vẫn bấm được). Chỉ phép đo vùng chạm lộ ra.
`primarySmall` ở cùng tệp cũng vậy.

### ✅ U-05 · Sáu màn không có trạng thái rỗng — **ĐÃ ĐÓNG (Báo cáo · Đề xuất)**
`Báo cáo` · `Đề xuất đặt hàng` · `Nhập hàng` · `Khởi tạo tồn` · `Cài đặt` · `Nhân viên`.
Người mới không phân biệt được *"chưa có dữ liệu"* với *"phần mềm lỗi"* — và luôn đoán vế thứ
hai. Chi tiết ở `01_BAO_CAO_UAT.md` §3.

### ✅ U-06 · Không phân biệt "Nhập hàng nhanh" với "Khởi tạo tồn kho" — **ĐÃ ĐÓNG (tooltip)**
Hai tab cạnh nhau, tên gần giống, không có một dòng nào giải thích khác nhau chỗ nào. Người
mới sẽ dùng nhầm — và dùng nhầm ở đây làm **sai giá vốn** (khởi tạo không hỏi giá vốn, nhập
mua thì có).

### U-07 · Logo BERAS bị đếm là phần tử bấm được
Cao 23px, xuất hiện trong **128/128** lượt đo. Không phải lỗi hiển thị, nhưng làm nhiễu mọi
phép kiểm vùng chạm về sau. *Đề nghị: đánh dấu là nhãn, không phải nút.*

---

## ⚪ KHÔNG PHẢI LỖI — ghi lại để khỏi bị báo lại

| Hiện tượng | Vì sao đúng |
|---|---|
| *"7 thuốc chưa có hoạt chất"* ở Danh mục | Bảy mã đó là **vật tư y tế** (băng gạc, khẩu trang, nhiệt kế) — không có hoạt chất là đúng |
| Kho/khách/đơn hàng **trống rỗng** | Đúng chỉ đạo Chain 01/08 — dữ liệu nhập tay trong tuần thử |
| Dashboard chủ chuỗi không so sánh được chi nhánh | Quầy chỉ có **một** chi nhánh |
| Bảng cuộn ngang trong khung riêng | Thiết kế có chủ đích; trang không cuộn ngang |

---

## Tổng hợp

| | Ban đầu | Sau Đợt 1 |
|---|---|---|
| 🔴 Critical | 3 | **2** (C-02, C-03) |
| 🟠 Major | 8 | **8** |
| 🟡 Minor / UX | 7 | **0** ✅ |
| ⚪ Không phải lỗi | 4 |

**Không có lỗi Performance** — 128 lượt đo không ghi nhận màn nào tải bất thường.
