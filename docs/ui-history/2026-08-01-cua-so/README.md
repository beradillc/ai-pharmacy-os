# Mọi chi tiết thành cửa sổ có ✕ (P4, 2026-08-01)

Lệnh Chain giao 01/08 (`#2`): *"Tất cả các phím chức năng xem/nhập/sửa chi tiết trên giao
diện mobile cần dạng cửa sổ và thêm dấu ✕ để thoát khi cần"*.

## 14 dải trượt → 14 cửa sổ

| Màn | Cửa sổ |
|---|---|
| `/danh-muc-thuoc` | Hoạt chất · Giá niêm yết |
| `/ton-kho` | Sắp xếp lô vào ô |
| `/khach-hang` | Thêm khách hàng · Hồ sơ sức khoẻ · Đồng ý |
| `/nhan-vien` | Thêm nhân viên · Vai trò |
| `/don-mua-hang` | Nhận hàng |
| `/kiem-ke` | Phiên kiểm kê (cả trạng thái *đang tải*) |
| `/so-do-kho` | Thêm kho/chỗ · Hàng trong ô |
| `/cai-dat/luu-tru` | Ảnh đơn thuốc |
| `/hoa-don` | Chi tiết hoá đơn (đã làm ở P3) |

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Hình dạng | `<section>` nằm **cuối trang** — trên điện thoại phải cuộn hết bảng mới thấy, và không gì báo là có thứ để cuộn tới | `<dialog>` thật, trên điện thoại trượt từ đáy lên |
| Thoát | nút chữ "Đóng" (một số cửa sổ **không có nút nào**) | nút **✕** luôn có, không tắt được, dính ở đầu cửa sổ khi thân cuộn |
| Bấm ra ngoài · phím `Esc` | không có | trình duyệt lo (`<dialog>` + `::backdrop`) |
| Cuộn nền khi mở | trang phía sau trôi tự do | khoá |

## Vì sao làm bằng script, không sửa tay 14 lần

Mười bốn chỗ có **cùng một hình dạng**. Sửa tay là mười bốn cơ hội bỏ sót một `</section>`
— và một thẻ đóng **sai** thì `tsc` bắt được, nhưng một thẻ đóng **đúng mà gắn nhầm cửa sổ**
thì không cổng nào bắt.

## Cổng mới `check-cua-so`

Đo **bốn** mệnh đề cho mỗi lối vào, in riêng từng cái: ① mở ra có `<dialog open>` ② có nút ✕
③ **nút ✕ nằm trong khung nhìn** ④ bấm ✕ đóng thật.

Mệnh đề ③ là lý do cổng tồn tại, không phải ①. *"Có cửa sổ"* thì nhìn ảnh là biết; *"nút
thoát có chạm tới được ở khổ 390px không"* thì chỉ phép đo trả lời được — và đó đúng là chỗ
ba lần trước đã hỏng (kỷ luật #21).

## Chín cổng cũ bám vào hình dạng cũ

`section[aria-label=…]` → `dialog[aria-label=…]`. Ba cổng đỏ ngay lượt chạy đầu
(`check-customers`, `check-receive-flow`, `check-danh-muc-thuoc`) — **đúng là hồi quy của
P4**, không phải lỗi có sẵn, và đã sửa trong cùng phiên.

## Ảnh

Bốn cảnh × hai khổ (390×844 · 1440×900), `deviceScaleFactor: 2`.

## 📌 Ghi cho P5

`mobile-390-sua-gia.png` cho thấy bảng danh mục thuốc phía sau **vỡ chữ** ở khổ 390px
(`Alaxa` / `n` / `Ibu` / `prof`). Đây đúng là lệnh `#8` của Chain — *"danh mục thuốc mobile
chưa cân xứng"* — và là việc của P5.
