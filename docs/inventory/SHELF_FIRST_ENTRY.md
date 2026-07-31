# Nhập theo kệ (BERAS V2 Phase 10)

> Ngày: 2026-07-31 · Màn `/khoi-tao-ton`

## Vấn đề

`/nhap-nhanh` (Phase 6) đặt ô nhập vị trí ở **dưới cùng, không bắt buộc** — đúng cho người
đứng cạnh thùng hàng vừa dỡ. Sai cho người **đi dọc kệ đếm hàng**.

Một ô có mười hai mặt hàng. Nếu mỗi lượt phải chọn lại ô thì đó là mười hai lần chọn lại một
thứ không đổi — và mỗi lần chọn lại là **một cơ hội chọn nhầm ô bên cạnh**.

## Quyết định: đảo thứ tự, không đảo màn

| | Nhập hàng nhanh | Khởi tạo tồn |
|---|---|---|
| Đứng đâu | cạnh thùng hàng vừa dỡ | đi dọc kệ |
| Cái gì **cố định** | mặt hàng đang nhận | **cái ô đang đứng trước mặt** |
| Ô nhập vị trí | dưới cùng, không bắt buộc | **trên cùng, chọn một lần, khoá lại** |
| Sau khi lưu, giữ lại gì | thuốc + ô | **chỉ ô** |

Dòng cuối là chỗ dễ chép nhầm nhất: ở `/nhap-nhanh` cái lặp là **mặt hàng** (nhiều lô cùng một
thuốc vào một ô), ở đây cái lặp là **ô** (nhiều thuốc khác nhau trong cùng một ô). Giữ lại
thuốc cũ ở màn này là mời người dùng nhập trùng.

## Hai chi tiết nhỏ, mỗi cái một lý do

- **Đổi ô là hành động có chủ ý**, không phải một `select` luôn mở trên đầu màn. Người đi kiểm
  kê cầm điện thoại một tay — select mở sẵn ngay đầu màn là thứ dễ quẹt trúng nhất, và quẹt
  trúng nó thì mọi dòng sau đó vào **nhầm ô**.
- **Không hỏi giá vốn.** Xem `STOCK_INITIALIZATION.md`.

## Cổng đo gì

`check-khoi-tao-ton.mjs` đo ba mệnh đề; mệnh đề ③ là lý do màn này tồn tại:

1. chọn ô một lần rồi **ô ở lại** sau khi ghi;
2. phần mặt hàng **trống trở lại**;
3. hàng vừa đếm **thật sự vào đúng ô đó** (kiểm qua Sơ đồ kho).

① và ② chỉ nói về trạng thái trong trình duyệt. Một màn giữ ô rất đẹp mà gửi `location_id`
rỗng lên máy chủ vẫn xanh cả ① lẫn ②. Đột biến `location_id: o` → `null` ⇒ **chỉ ③ đỏ**,
đúng như thiết kế.

## 🔴 Bài học: bốn cổng xanh trong lúc ba ô nhập cao 250px

Lần chụp đầu, ảnh 390×844 cho thấy ba ô nhập cao gần **250px mỗi ô** — cả màn phải kéo ba lần
mới hết một biểu mẫu bốn dòng. `eslint` · `tsc` · `build` · cổng Playwright **xanh hết**, vì
không cái nào đo chiều cao.

Nguyên nhân: `.o` là flex **column**, còn `.input` dùng chung mang `flex: 1 1 auto` để giãn
**ngang** trong các hàng ngang. Đặt thêm `flex: 1 1 14rem` lên `.o` thì `flex-basis` đó thành
chiều **cao**. Cùng họ với lỗi ô tìm kiếm 260px ngày 30/07 — lần thứ hai. Lần thứ ba thì theo
kỷ luật #18 phải nâng thành kỷ luật chính thức.
