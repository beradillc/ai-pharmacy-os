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
| ☐ | Dựng CSDL **riêng để quay** (`qt650_video`) | 🔴 **Bắt buộc.** Quay trên CSDL thật để lại hoá đơn rác không tách được khỏi doanh thu thật |
| ☐ | Nút **Thêm** đã nâng lên ≥44px | Quay cận cảnh sẽ lộ nút nhỏ; sửa trước rẻ hơn quay lại |
| ☐ | Sáu màn đã có trạng thái rỗng | Video 11 (Báo cáo) quay trên màn trống không giải thích được |
| ☐ | Màn **Đổi mật khẩu** có | Video 02 không quay được nếu thiếu |
| ☐ | Tài khoản thu ngân đã tạo | Video 07 — cảnh quan trọng nhất — không quay được nếu thiếu |
| ☐ | Kịch bản đã đọc thử thành tiếng | Lời viết ra và lời nói ra khác nhau; đọc thử mới biết chỗ nào vấp |
| ☐ | Thư mục `docs/testing/videos/` đã tạo | ✅ đã có |

**Quay được ngay không chờ gì:** video **01** và **03**.

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
