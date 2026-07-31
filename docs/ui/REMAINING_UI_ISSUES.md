# REMAINING_UI_ISSUES — Còn nợ sau đợt giao diện

> PHASE 8. Xếp theo mức nghiêm trọng. Không mục nào bị làm tròn thành "xong".

## 🔴 Chặn — cần người, máy không tự làm được

| # | Việc | Vì sao chưa xong |
|---|---|---|
| **1** | **Chưa mắt người nào nhìn giao diện ở 360/390/430px** | Phiên không có công cụ trình duyệt. Cái đã chứng minh: **dữ liệu** mỗi màn đúng (gọi đúng chuỗi API bằng token thật). Cái chưa: bố cục, tương phản dưới đèn thật, chỗ chữ bị cắt. Bảng kiểm sẵn ở `docs/dev/LAN_MOBILE_TEST.md`; Chain đã bắt được **2 lỗi thật** bằng đúng cách này |
| ~~**2**~~ | ~~UFW chưa mở cổng~~ → ✅ **ĐÓNG 29/07 08:03** | Chain uỷ quyền kèm mật khẩu sudo. `ufw status`: 2 luật cho `192.168.1.0/24`. 🔴 Nhưng **vẫn chưa ai cầm điện thoại thử** — máy không tự kiểm được tường lửa của chính nó |

## 🟠 Cao — làm được, chưa làm

| # | Việc | Ghi chú |
|---|---|---|
| ~~**3**~~ | ~~Frontend vẫn 0 test~~ → ✅ **ĐÓNG 29/07** | **27 test** (vitest) phủ `shared/nav.ts`, `format/number.ts`, và hàm gộp doanh thu theo ngày. Ba mutant đều đỏ đúng lý do. `make check-fe` chạy lint+tsc+test+build. **Còn nợ hẹp hơn:** chưa có test render component (cần jsdom + testing-library) |
| ~~**4**~~ | ~~Không cưỡng chế ranh giới `components/*` ⇄ `features/*`~~ → ✅ **ĐÓNG 29/07** | `no-restricted-imports` trong `eslint.config.mjs`. **Bắt được vi phạm thật ngay lần chạy đầu**: `AppShell` import `features/auth` ⇒ đã chuyển sang `app/_shell/` (nó là composition root, không phải component tái dùng). Luật KHÔNG có ngoại lệ nào |
| ~~**5**~~ | ~~Màn **Nhân viên** chưa có~~ → ✅ **ĐÓNG 29/07** | Xem danh sách · thêm nhân viên · bật/tắt tài khoản. Đã chạy thật: `POST /users → 201`, `must_change_password: true`. **Gán vai trò cũng XONG 29/07** — cấp/thu hồi, phân biệt phạm vi chi nhánh ⇄ toàn chuỗi. Đã chạy thật: cấp 201 · thu hồi 204 · cấp lại phạm vi toàn chuỗi 201 |
| **6** | Màn **Tuân thủ** (12 endpoint) · **AI** (5) · **Nhập hàng** (3) · ~~**Đơn thuốc** (5)~~ | Mỗi màn là một tính năng mới. **Đơn thuốc đóng một phần 31/07**: ảnh đơn chụp được ở quầy và xem lại được ở Cài đặt → Lưu trữ. **Còn nợ 3 đường**: duyệt · từ chối · cấp phát — chưa màn nào gọi |
| **11** | **Lưu trữ mới có một loại chứng từ** (ảnh đơn thuốc) | Bố cục đặt sẵn theo loại để loại sau có chỗ vào. Chưa có: hoá đơn, phiếu nhập, biên bản |
| **12** | **Tiếng ồn `_rsc` làm cổng trình duyệt đỏ oan** | WebKit huỷ request prefetch điều hướng và báo bằng thông điệp đọc y hệt lỗi CORS. Đã chứng minh không phải lỗi sản phẩm ba lần (cây đã commit cũng đỏ y hệt; `check-customers` tự xanh lại mà không ai sửa). Cần **lọc tiếng ồn đó khỏi bộ đếm lỗi JS**, hoặc ghi rõ các cổng ấy chỉ chạy dưới `next dev` |
| **13** | **`scripts/lan-dev.sh` vẫn dùng `next dev`** | Máy dev 3,7 GB RAM không chạy nổi: 1,5 GB RSS, swap 3,4/3,9 GB, 305% CPU, `/login` không trả lời trong 120 giây. Đường đang dùng để chạy cổng là **build + `next start`**. Script chưa sửa |

## 🟡 Vừa

| # | Việc | Ghi chú |
|---|---|---|
| **7** | KPI **chưa có `comparison`/`trend`** dù component đã sẵn prop | Cần gọi hai kỳ (kỳ này / kỳ trước). Cố ý để dành: dashboard chưa có gì mà đã hai lượt gọi là tự chuốc chậm |
| **8** | Biểu đồ doanh thu gộp **ở client** từ `GET /sales` | Trần 400 đơn; vượt thì màn hình **nói ra**. Nhà thuốc lớn hơn cần endpoint JSON riêng |
| **9** | Ba media query còn dạng `width <=` | `AppHeader` 480px · Tổng quan 720px · Đề xuất 820px. **Không sai** — nền của chúng vốn đã hợp mobile, câu truy vấn chỉ là tinh chỉnh màn hẹp. Đổi sang mobile-first phải lật ngược style nền: nhiều rủi ro hơn giá trị |
| **10** | Ô lọc ở màn **Khách hàng** và **Tồn kho** chỉ lọc **trong trang đang tải** | Không phải chưa kịp làm: họ tên/điện thoại là **cột mã hoá at-rest**, `LIKE` không chạy. Tìm thật cần blind index. Giao diện đã nói đúng điều đó ở phụ đề |

## ⚪ Thấp

| # | Việc |
|---|---|
| **11** | Chưa có dark mode — yêu cầu không đòi. Khi làm phải **chọn lại từng bậc** và chạy lại trình kiểm với nền tối, không lật màu tự động |
| **12** | Điểm ngắt 600/900px lặp 9 chỗ. **Giới hạn của CSS** (`@media` không nhận biến), không phải chỗ chưa làm. Giá trị ghi ở `tokens.css` làm nguồn sự thật cho người đọc |
| **13** | `NotificationBadge` / `AlertCard` / `DataTable` / `StatusChip` / `Button` chưa tách thành component React riêng — hiện là lớp CSS dùng chung, đã đủ nhất quán. Tách khi có màn thứ hai cần đúng hành vi đó |

## 🔴 Bài học 29/07 — cổng xanh, ảnh đẹp, mà app vẫn trắng trên điện thoại

Chain báo *"Safari iPhone mở lên khoảng trắng"*. Đo ra: **không phải lỗi Safari**.
Firefox cũng trắng, và trắng ở **mọi màn trong ứng dụng khi chưa đăng nhập** — trên
mọi trình duyệt.

Nguyên nhân: Next **chặn request chéo nguồn tới tài nguyên dev** (mặc định chỉ cho
`localhost`). Qua LAN IP thì HTML server-render vẫn về, nhưng thời chạy client bị
chặn ⇒ **React không bao giờ hydrate** ⇒ màn server-render ra `null` rồi đứng im.

**Vì sao không cổng nào bắt được, và đây mới là phần đáng nhớ:**

| Cổng | Kết quả | Vì sao mù |
|---|---|---|
| `lint` · `tsc` · `test` · `build` | tất cả xanh | không có cái nào mở trình duyệt |
| 22 ảnh chụp màn hình | tất cả đẹp | **bộ chụp chạy qua `localhost`**, còn điện thoại đi qua **LAN IP** |
| `lan-dev.sh` 7 phép kiểm | tất cả xanh | kiểm `curl` — mà `curl` chỉ tải HTML, **không chạy JavaScript** |

Ba lớp phòng thủ, cả ba cùng mù vì cùng một lý do: **không lớp nào chạy đúng thứ
người dùng chạy** (một trình duyệt thật, qua đúng địa chỉ thật).

⇒ Thêm `npm run check:browsers`: mở Firefox + WebKit thật, qua LAN IP, kiểm màn
được bảo vệ có chuyển về `/login` và có nội dung không. Đây là cổng đầu tiên của dự
án **chạy JavaScript trong một trình duyệt thật**.

## Điều đáng nhớ nhất của đợt này

Bốn lỗi trong hai ngày, **cùng một nguyên nhân**: `viewport` (suy từ `grep` rỗng) ·
POS không sidebar (suy từ "thu ngân chắc cần diện tích") · `granularity=DAY` (suy
từ tên hằng) · cửa sổ "hôm nay" lệch 7 giờ (suy từ `date.today()`).

Cả bốn đều **nghe rất hợp lý**. Không cái nào bị bắt bởi đọc lại mã: chúng bị bắt
bởi **gỡ ra rồi đo**, **người dùng bấm thử**, **`curl` một lần**, và **chạy cổng
trước khi đóng phiên**.

Với giao diện thì tỉ lệ này còn tệ hơn — vì phần lớn cái sai của giao diện *không
có cổng nào bắt được*. Đó là lý do mục 🔴 số 1 ở trên là mục quan trọng nhất tài
liệu này, chứ không phải mục dễ nhất để bỏ qua.
