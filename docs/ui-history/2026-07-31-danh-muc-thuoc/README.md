# Màn Danh mục thuốc — 2026-07-31

**Trước:** không có màn này. `PUT /drugs/{id}/ingredients` đã chạy được từ 30/07 nhưng
**không ai chạm được** — dược sĩ nhập sai một hoạt chất thì cảnh báo dị ứng sai người
vĩnh viễn, và cách duy nhất sửa là gọi người viết mã.

**Sau:** xem toàn bộ danh mục kèm hoạt chất, bấm **Sửa** để đặt lại danh sách.

Ảnh Firefox thật qua LAN IP, `nt650v2`. Sinh lại: `node scripts/check-danh-muc-thuoc.mjs`

## Đo được

| | desktop | mobile |
|---|---|---|
| Thuốc trong danh mục | 36 | 36 |
| Cảnh báo "chưa có hoạt chất" | **10** | 10 |
| Hiện **tên** hoạt chất (không phải id cụt) | ✓ | ✓ |
| Bảng sửa mở đúng số dòng | ✓ | ✓ |
| Cuộn ngang | không | **không** |
| Ô tìm kiếm cao | 44px | 44px |
| Lỗi JS | 0 | 0 |

## 🔴 Ảnh bắt được lỗi mà bốn cổng chữ đều mù

`desktop-danh-muc-TRUOC-o-tim-260px.png` là bản đầu: **ô tìm kiếm cao 260px** — một hộp
trống chiếm một phần tư màn hình. ESLINT · TSC · VITEST · BUILD **xanh cả bốn** lúc đó.

Nguyên nhân: `.input` mang `flex: 1 1 auto` (dành cho hàng ngang `.controls`); đặt thẳng
vào `.page` — vốn là flex **cột** — thì nó nở theo **chiều cao**. Vá bằng cách bọc lại
trong `.controls`.

Điện thoại **không lộ** lỗi này (đo 44px) vì nội dung đã lấp đầy cột, không còn chỗ trống
để ô nở ra. Chụp một khổ thì không thấy.

Nay phép đo `caoOTim` (sàn 44 – trần 80) nằm trong cổng. Đã kiểm nó có răng theo kỷ luật
#14: bỏ lớp bọc ⇒ `MUTANT_GATE_EXIT=1`, in `ô tìm cao 260px 🔴`; bọc lại ⇒ `GATE_EXIT=0`,
`44px ✓`.

Con số **10** khớp đúng những mã đã biết: 3 vật tư (băng gạc, khẩu trang, nhiệt kế — cố ý
rỗng) + 7 mã chờ Chain quyết.

## Quyết định thiết kế

- **Cột "Hoạt chất" đứng ngay sau tên**, không nằm trong trang con: nó là thứ quyết định
  cảnh báo dị ứng có kêu hay không.
- **Cảnh báo đếm số thuốc trống** ngay đầu màn — con số đó chính là số mã mà cảnh báo dị
  ứng sẽ im lặng.
- **Nút Sửa chỉ hiện với `catalog.update`** (cấp chuỗi). Không có quyền thì không thấy
  nút, thay vì thấy rồi bị từ chối.
- **Hàm lượng để trống khi thêm mới**, không điền sẵn `1`: một con số bịa nằm trong hồ sơ
  thuốc trông y hệt một con số đã tra.

Ảnh cho thấy hàm lượng hiện `1.0000` ở các mã do seeder nối — đó là **chỗ giữ chỗ** đã ghi
rõ trong `seeds/drug_ingredient_map.py`, và màn này là đường để dược sĩ sửa lại cho đúng.
