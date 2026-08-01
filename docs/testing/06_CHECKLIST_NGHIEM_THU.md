# Checklist nghiệm thu — BERA Pharma

> Output **10**. Ba cổng: **chạy thử tại quầy** → **quay video** → **phát hành thương mại**.
> Mỗi dòng phải **đo được**, không có dòng nào dựa vào cảm nhận.

---

## Cổng 1 — Cho phép CHẠY THỬ tại Quầy thuốc 650

| ✔ | Mục | Cách kiểm | Trạng thái |
|---|---|---|---|
| ☐ | Màn **Đổi mật khẩu** có, và chặn khi cờ bật | Đăng nhập tài khoản mới → phải bị đưa tới màn đổi | 🔴 **C-01 chưa xử lý** |
| ☐ | Dược sĩ **đã đổi** mật khẩu do kỹ thuật đặt | `select must_change_password` → `f` | 🔴 Chưa |
| ☐ | `ORG__PHONE` và `ORG__TAX_CODE` đã điền | In thử một hoá đơn, xem có đủ 4 dòng đầu | 🔴 Chờ Chain |
| ☐ | Tài khoản thứ hai (thu ngân) đã tạo | Màn Nhân viên có 2 dòng | 🔴 Chờ Chain |
| ☐ | Giá bán đã sửa theo giá nhập thật | Đối chiếu 10 mã bán chạy với giá quầy | 🔴 Chờ Chain |
| ☐ | Cờ pháp lý **quầy thuốc vs nhà thuốc** đã rà | Trợ lý Pháp Lý xác nhận 25 mã ETC | 🟠 Chờ |
| ☐ | Sao lưu hằng ngày đã chạy ít nhất một lần | `ls ~/beras-moc-khoi-phuc/` | 🟠 Chờ |
| ☑ | Không lỗi JS trên mọi màn, mọi khổ | 128 lượt đo | ✅ **Đạt** |
| ☑ | Không màn nào cuộn ngang / tràn khung nhìn | 128 lượt đo | ✅ **Đạt** |
| ☑ | Danh mục thuốc đủ dùng | 70 mã, 63 có hoạt chất | ✅ **Đạt** |
| ☑ | Bán được đơn thuốc kê đơn đầu-cuối | Cổng `write-pos-etc` | ✅ **Đạt** |
| ☑ | In được hoá đơn đúng một đơn, khổ K80 | Cổng `check-hoa-don` | ✅ **Đạt** |

**Kết luận cổng 1:** 🟠 **CHƯA QUA** — còn 1 mục Critical (C-01) và 5 mục chờ Chain.

> ⚠️ **Nếu Chain quyết chạy thử ngay dù chưa xử lý C-01:** ghi rõ vào sổ rằng dược sĩ đang
> dùng mật khẩu do kỹ thuật đặt, và đổi ngay khi có màn. Đây là **quyết định của Chain**, GĐ
> ghi nhận chứ không tự cho qua.

---

## Cổng 2 — Cho phép QUAY VIDEO

| ✔ | Mục | Vì sao |
|---|---|---|
| ☑ | ~~Dựng CSDL **riêng để quay** (`qt650_video`)~~ → **quay thẳng trên `qt650`** | ✅ **Chain chốt 2026-08-02.** Lý do cũ dựa trên suy đoán: đếm thật thì `qt650` có **0 đơn bán**, không có doanh thu nào để hoá đơn quay lẫn vào. Nó lại đúng là CSDL sạch-có-danh-mục mà thứ tự quay `02→03→…` cần. Xem `04_DANH_SACH_VIDEO.md` |
| ☐ | Nút **Thêm** đã nâng lên ≥44px | Quay cận cảnh sẽ lộ nút nhỏ; sửa trước rẻ hơn quay lại |
| ☐ | Sáu màn đã có trạng thái rỗng | Video 11 (Báo cáo) quay trên màn trống không giải thích được |
| ☐ | Màn **Đổi mật khẩu** có | Video 02 không quay được nếu thiếu |
| ☐ | Tài khoản thu ngân đã tạo | Video 07 — cảnh quan trọng nhất — không quay được nếu thiếu |
| ☐ | Kịch bản đã đọc thử thành tiếng | Lời viết ra và lời nói ra khác nhau; đọc thử mới biết chỗ nào vấp |
| ☐ | Thư mục `docs/testing/videos/` đã tạo | ✅ đã có |
| ☑ | **Kịch bản đủ 13/13 video** | ✅ **xong 2026-08-01** — `05_KICH_BAN_VIDEO.md`, trước đó chỉ có 01·06·07 |
| ☑ | 5 lỗi UAT còn treo đã đóng | ✅ **xong 2026-08-01** — C-03 · M-02 · M-05 · M-06 · M-07 |
| ☑ | **Nội dung nhạy cảm/pháp lý đã cắt khỏi kịch bản** | ✅ **xong 2026-08-01**, Chain chốt. Trích dẫn văn bản · khẳng định nghĩa vụ · nhắc cơ quan quản lý — cắt hết. Video 14 rút hẳn sang `07_CHO_PHAP_LY_…` |
| ☐ | Kịch bản đọc lại sau khi cắt, còn trôi chảy | Cắt câu giữa đoạn hay để lại chỗ hụt — đọc thành tiếng mới biết |

**Quay được ngay không chờ gì:** video **01 · 02 · 03 · 06 · 08 · 13**.

**Thứ tự quay đề nghị** (mỗi video dùng dữ liệu video trước vừa tạo ⇒ không phải dựng dữ liệu
giả lần nào): `02 → 03 → 04 → 05 → 01 → 08 → 06 → 07 → 09 → 10 → 13 → 11 → 12`.

🔴 **Bộ video KHÔNG còn video về Sổ thuốc kiểm soát đặc biệt.** Chain chốt 2026-08-01: nội
dung pháp lý bỏ ra khỏi kịch bản. Với các màn khác thì bỏ câu chữ pháp lý là đủ; riêng màn đó
**bỏ phần pháp lý ra thì không còn video nào cả** — nên rút hẳn, giữ ở `07_CHO_PHAP_LY_…` để
sau khi Trợ lý Pháp Lý rà xong thì có cái sửa tiếp thay vì viết lại từ đầu.

⚠️ Việc này **không** đóng nhu cầu rà pháp lý — nó chỉ tách nhu cầu đó ra khỏi đường găng của
việc quay video. Màn Sổ kiểm soát vẫn chạy trong phần mềm và vẫn mang nhãn đỏ tự khai.

---

## Cổng 3 — Cho phép PHÁT HÀNH THƯƠNG MẠI

| ✔ | Nhóm | Mục |
|---|---|---|
| ☐ | Nghiệp vụ | Đủ **7 màn còn thiếu** (đổi mật khẩu · đổi trả · sổ kiểm soát · nhà cung cấp · nhật ký · thông tin cơ sở · thông tin người dùng) |
| ☐ | Pháp lý | Sổ thuốc kiểm soát đặc biệt **chạy được**, Trợ lý Pháp Lý xác nhận |
| ☐ | Audit | Log có **giá trị cũ → mới** cho nhóm đụng tiền và đụng hàng |
| ☐ | Vùng chạm | Mọi nút ≥44px (trừ nhãn thương hiệu) |
| ☐ | UAT đầy đủ | **22/22 luồng** kiểm thử đầu-cuối trên CSDL có dữ liệu |
| ☐ | Chủ chuỗi | Nghiệm thu trên tenant **hai chi nhánh** |
| ☐ | Cổng tự động | `make ci-full` xanh trọn |
| ☐ | Tài liệu | Handover + 14 video + hướng dẫn sao lưu |
| ☑ | Ổn định | 0 lỗi JS / 128 lượt · pytest **1455** xanh trên **cả SQLite và Postgres** |

---

## Ghi chú về cách dùng checklist này

**Một dòng chỉ được tick khi có bằng chứng đo được.** Không tick vì *"đã làm rồi"* — dự án này
đã có 16 ca *"niềm tin giả"* được kiểm toán đếm ra, và tất cả đều bắt đầu bằng một dòng được
tick mà không ai đo lại.

Với mục có cổng tự động, **ghi mã thoát** vào ô trạng thái, không ghi chữ *"xanh"*.
