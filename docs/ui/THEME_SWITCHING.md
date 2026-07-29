# THEME_SWITCHING — Đổi và ghi nhớ giao diện

## Người dùng làm gì

**Cài đặt → Giao diện** → bấm thẻ theme muốn dùng.

Vào Cài đặt: sidebar (máy tính, nhóm QUẢN TRỊ) hoặc nút **Thêm** trên thanh dưới
(điện thoại).

Đổi có hiệu lực **ngay**, không tải lại trang, không mất trạng thái màn đang xem —
giỏ hàng đang dở vẫn nguyên.

## Lưu ở đâu

`localStorage["beras.theme"]`, **trên trình duyệt này**. Máy khác hoặc trình duyệt
khác vẫn dùng Classic.

**Chưa lưu theo người dùng.** Dự án có `users` ở backend nhưng **không có bảng tuỳ
chọn người dùng**, và đặc tả cấm đụng CSDL/API. Thêm cột tuỳ chọn là việc backend
⇒ đã ghi vào mục nâng cấp sau. Khi làm: đọc lúc đăng nhập, ghi qua API, và
`localStorage` trở thành bộ nhớ đệm — kiến trúc hiện tại không phải sửa gì.

## Điều gì xảy ra bên trong

1. Bấm chọn → đặt/xoá `data-theme` trên `<html>`, ghi `localStorage`, phát một sự
   kiện.
2. `useSyncExternalStore` nghe sự kiện đó → **chỉ nút chọn** render lại.
3. Trình duyệt tính lại các biến CSS đã kế thừa. Không component nghiệp vụ nào vẽ lại.

Tải lại trang: script trong `<head>` đặt `data-theme` **trước lượt vẽ đầu tiên** ⇒
không có nháy màu.

## Trục trặc thường gặp

| Hiện tượng | Nguyên nhân |
|---|---|
| Đổi theme xong, tải lại thì về Classic | Trình duyệt chặn `localStorage` (chế độ riêng tư). Theme vẫn đổi cho phiên đang mở, chỉ không nhớ được |
| Máy khác vẫn Classic | Đúng như thiết kế — lưu theo trình duyệt, chưa theo người dùng |
| Thấy nháy màu khi tải trang | Script `<head>` bị chặn. Kiểm phần mở rộng chặn script nội tuyến |
