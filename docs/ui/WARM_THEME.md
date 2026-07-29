# WARM_THEME — BERAS Warm

> Theme thứ hai. Tông ấm, hiện đại, thân thiện — cảm hứng từ phong cách phần mềm
> quản lý nhà thuốc hiện đại nói chung. **Không sao chép nhận diện của bất kỳ đối
> thủ nào**: không logo, không tên, không icon độc quyền, không bảng màu thương
> hiệu của ai. Màu chọn từ hai tông cơ bản (coral + hổ phách) rồi **hạ bậc cho tới
> khi đạt tương phản**, không lấy mã màu từ đâu.

## 1. Bảng màu

| Vai trò | Mã | Ghi chú |
|---|---|---|
| Chính (coral) | `#C6413A` | hành động, nhấn |
| Chính đậm (nút, thanh trên) | `#B1372F` | chữ trắng đạt **6,07** |
| Chính nhạt | `#FCEAE7` | nền chip, nền icon |
| Phụ (hổ phách) | `#B8730B` | cảnh báo, nhấn phụ |
| Nhấn (đào) | `#FAF0EA` | nền phụ |
| Nền | `#FDF8F5` | trắng ngà |
| Mặt thẻ | `#FFFFFF` | |
| Chữ | `#2A211E` | 14,93 trên nền |
| Chữ mờ | `#6E5C56` | 5,99 trên nền |
| Thành công | `#2F7A4F` | |
| Cảnh báo | `#B8730B` (chữ trên nền nhạt: `#9C6209`) | |
| Nguy | `#C0392B` | |
| Thông tin / focus | `#1D6CA8` | khác mọi màu trạng thái, cố ý |
| Viền | `#EADDD6` | |

## 2. 🔴 Tương phản — ĐO TRƯỚC KHI VIẾT

Chạy công thức WCAG trên từng cặp **trước** khi chốt giá trị. Bản nháp đầu trượt
ba cặp; đã hạ bậc cùng tông tới khi đạt:

| Cặp | Nháp đầu | Sau khi hạ bậc |
|---|---|---|
| chữ trắng / nút hổ phách | `#B8730B` **3,82** 🔴 | `#A6680A` **4,56** |
| chữ chip coral | `#C6413A` **4,28** 🔴 | `#BF3E37` **4,56** |
| chữ chip hổ phách | `#B8730B` **3,42** 🔴 | `#9C6209` **4,51** |

Kết quả cuối: **14/14 cặp PASS** — gồm chữ/nền, chữ mờ/nền, chữ trắng trên nút,
cả bốn chip trạng thái, nét biểu đồ (ngưỡng 3:1), viền.

## 3. Màu biểu đồ

`#C6413A` · `#1D6CA8` · `#B8730B` · `#2F7A4F` · `#7A5EA8` — chạy trình kiểm bảng
màu: **4 PASS, 1 WARN**.

WARN là tách CVD của cặp xanh lá ↔ hổ phách: **ΔE 7,1 (protan)**, nằm trong dải sàn
6–8 ⇒ **chỉ hợp lệ khi có mã hoá phụ**. Điều kiện đó thoả: biểu đồ luôn có chú
giải, ≤4 chuỗi thì thêm nhãn trực tiếp. Mắt thường ΔE **18,8** — thoải mái.

*(Classic cũng ở đúng dải này: tritan 7,7. Không phải Warm kém hơn.)*

## 4. Hình khối

| | Classic | Warm |
|---|---|---|
| Bo góc thẻ | 16px | **18px** |
| Bóng | ám xanh, `0 1px 2px` | ám ấm, `0 1px 2px` / `0 6px 16px` |
| Thanh trên | xanh rừng đặc | **dải màu** coral → hổ phách |
| Nền | kem `#EDEFE7` | trắng ngà `#FDF8F5` |

## 5. Cái Warm KHÔNG đổi

Bố cục · khoảng cách · cỡ chữ · vùng chạm 44px · điểm ngắt · thứ tự khối · hành vi
cuộn · hiệu ứng chuyển cảnh · `prefers-reduced-motion`.

Warm **chỉ** đổi màu, bóng, bo góc — đúng phạm vi đặc tả cho phép.
