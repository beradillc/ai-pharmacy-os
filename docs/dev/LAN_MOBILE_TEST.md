# LAN_MOBILE_TEST — Test BERAS trên điện thoại/tablet

> Dành cho người cầm điện thoại. Không cần biết gì về mã nguồn.

## Chạy trên laptop

```bash
make lan          # hoặc: ./scripts/lan-dev.sh
```

Script tự tìm IP LAN, kiểm cổng, dựng Postgres/Redis, chạy API + giao diện, rồi
in địa chỉ cho điện thoại. Dừng bằng **Ctrl+C**.

**Lần đầu, nếu UFW đang bật** — script sẽ in ra hai lệnh; chạy chúng một lần:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 3000 proto tcp comment 'BERAS dev FE'
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp comment 'BERAS dev API'
```

## Trên điện thoại

1. Nối **cùng Wi-Fi** với laptop (không dùng 4G, không dùng mạng khách của router).
2. Mở trình duyệt, gõ địa chỉ script in ra — dạng `http://192.168.1.10:3000`
   *(IP đổi khi router cấp lại; luôn lấy theo dòng script in, đừng nhớ thuộc lòng)*.
3. Đăng nhập bằng tài khoản demo.

> Muốn dùng bộ dữ liệu demo đẹp (36 thuốc, 28 ngày doanh thu) thay vì CSDL dev:
> ```bash
> DB__URL='postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os_demo' make lan
> ```

## Bảng kiểm trên điện thoại

Đánh dấu từng dòng. Chỗ nào sai thì **chụp màn hình + ghi lại khổ máy**.

### Khung chung
- [ ] Trang đăng nhập hiện đủ, chữ không bị cắt
- [ ] Đăng nhập được, vào thẳng màn hình chính
- [ ] **Thanh điều hướng dưới** có 5 ô: Tổng quan · Bán hàng · Kho · Báo cáo · Thêm
- [ ] Bấm "Thêm" mở ngăn kéo từ dưới lên, đóng được bằng nút Đóng và bằng cách bấm ra ngoài
- [ ] Không có thanh cuộn NGANG ở bất kỳ màn nào
- [ ] Ô đang chọn trên thanh dưới nhìn ra được **kể cả khi không phân biệt màu** (icon đặc + chữ đậm + vạch trên)

### Bán hàng — màn dùng nhiều nhất
- [ ] Danh mục thuốc và giỏ hàng xếp **một cột** (không phải hai cột chen nhau)
- [ ] Gõ "para" ra Paracetamol
- [ ] Bấm "Thêm" → vào giỏ, **giá tự điền** (không hỏi giá bằng hộp thoại)
- [ ] Ô số lượng bấm trúng bằng ngón tay
- [ ] Tổng tiền + nút Thanh toán **luôn thấy được**, không bị thanh dưới che
- [ ] Thanh toán xong hiện mã đơn

### Tổng quan
- [ ] 8 ô hành động nhanh, 4 cột
- [ ] 4 thẻ KPI đọc được, số tiền dài không tràn
- [ ] Thẻ "Cần xử lý" hiện đúng việc (hoặc câu "không có việc nào")
- [ ] Biểu đồ doanh thu vẽ ra, chạm vào đường hiện được số liệu
- [ ] Danh sách giao dịch gần đây

### Kho · Hoá đơn · Khách hàng · Đơn mua hàng · Báo cáo
- [ ] Bảng **cuộn ngang trong khung của nó**, không kéo cả trang
- [ ] Kho: bấm "Chỉ lô cận hạn" lọc được
- [ ] Hoá đơn: đổi ngày được, mở chi tiết được
- [ ] Báo cáo: bấm "Tải CSV" ra tệp thật

### Điều đáng nghi — báo ngay
- [ ] Có màn nào chữ **nhỏ hơn 14px** không?
- [ ] Có nút nào **bấm hụt** (vùng chạm nhỏ hơn đầu ngón tay) không?
- [ ] Có chỗ nào **quay ngang máy** thì vỡ bố cục không?

## Khi hỏng — ba câu hỏi theo thứ tự

| Triệu chứng | Nguyên nhân hay gặp nhất |
|---|---|
| Trang **không mở được chút nào** | Chưa chạy 2 lệnh `ufw`, hoặc điện thoại đang dùng 4G / mạng khách |
| Trang mở nhưng **đăng nhập xoay mãi / báo lỗi mạng** | Điện thoại gọi API sai địa chỉ. Kiểm dòng `URL API trình duyệt nhận:` script in ra — phải là LAN IP, không phải `localhost` |
| Đăng nhập được nhưng **màn nào cũng trống** | API tới được nhưng CSDL chưa seed. Chạy `make demo` rồi trỏ `DB__URL` như mục trên |

Địa chỉ đúng luôn nằm ở khung script in ra lúc khởi động — **không đoán IP**.
