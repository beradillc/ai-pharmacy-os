# V3-1 — Thêm thuốc mới, gọi được giữa lúc nhập hàng (2026-08-04)

Chain duyệt lộ trình đợt V3 ngày 04/08; đây là mục ưu tiên 1.

## Trước / sau

| | Trước bản này | Sau |
|---|---|---|
| Tạo mã thuốc mới | **Không có chỗ nào trong cả giao diện.** `POST /drugs` có sẵn ở backend, không dòng frontend nào gọi. Thuốc vào CSDL bằng cách chạy seed | Nút ở `/danh-muc-thuoc` **và** ngay trong `/nhap-nhanh` |
| Gặp mặt hàng lạ giữa lúc dỡ hàng | **Dừng hẳn** — không đường đi tiếp | Mở cửa sổ, tạo, mã mới **được chọn sẵn**, dữ liệu gõ dở còn nguyên |

## Ảnh

| Tệp | Nội dung |
|---|---|
| `dienthoai-1-truoc.png` · `maytinh-1-truoc.png` | Nút nằm ngay dưới ô chọn thuốc, đã gõ dở SL 42 · lô LO-A7 |
| `dienthoai-2-cua-so.png` · `maytinh-2-cua-so.png` | Cửa sổ thêm thuốc — 4 mục bắt buộc + cảnh báo hoạt chất |

Chụp qua **trình duyệt thật**, đăng nhập thật bằng tài khoản chủ chuỗi, qua **đúng IP LAN**
`192.168.1.8:3000` — không phải `localhost` (kỷ luật #15: bộ chụp cũ đi localhost trong khi
điện thoại đi LAN IP, ba lớp cùng xanh mà app trắng trên iPhone).
`deviceScaleFactor: 2`, hai khổ 390×844 và 1440×900.

## Cổng

```
V31_GATE_EXIT=0   6/6 mệnh đề, gồm: nút NẰM TRONG khung nhìn 390px (x=16, w=358) ·
                  trang không cuộn ngang · mã mới được chọn sẵn ·
                  🔴 số lượng + số lô gõ dở VẪN CÒN sau khi tạo xong
MUTANT6_EXIT=1    bỏ `onCreated` ⇒ đỏ đúng 1 mệnh đề ("đang chọn: — chọn thuốc —")
LINT=0  TSC=0  VITEST=0 (122)  BUILD=0
```

🔴 **Một lỗi bắt được trước khi lên bản:** bản nháp dùng `styles.primary` — class **không tồn
tại** trong `screen.module.css` (chỉ có `.button` và `.ghost`). Đúng bẫy kỷ luật #22:
`class="undefined"`, nút rơi về mặc định, và **không cổng nào đỏ** vì mọi chuỗi đều hợp lệ.
Bắt được nhờ đọc thẳng danh sách class từ tệp CSS trước khi tin tên mình vừa gõ.
