# Sổ lỗi LIÊN THÔNG — sửa gộp một đợt, không sửa lẻ

> Chain chốt 2026-08-02: *"Các tính năng liên thông giữa các video thì ghi nhận lại, sửa cùng
> lúc."*
>
> **Vì sao không sửa ngay:** sửa một lỗi chạm nhiều màn ngay giữa lúc quay video 04 sẽ làm sai
> bản quay video 02 **đã đóng** — và không ai biết cho tới lúc phát hành cả bộ. Gộp lại sửa
> một đợt thì quay lại một đợt.
>
> Quy tắc phân loại và vòng lặp: `10_QUY_TRINH_QUAY_LA_RA_SOAT.md`.

## Đang mở

| # | Lỗi | Phát hiện ở | Chạm video nào | Mức |
|---|---|---|---|---|
| L-2 | 🔴 **`check-thong-tin-co-so.mjs` nằm nhóm ĐỌC-THUẦN nhưng GHI ĐÈ thông tin pháp lý của cơ sở** bằng dữ liệu bịa: `"Nhà thuốc Kiểm thử 428374"`, `"650 Nguyễn Trãi, P.11, Q.5"`, MST `0312345678`, mã cơ sở `01234`. Mỗi lượt chạy bộ cổng là một lần ghi đè. Đây là **cổng thứ hai** trong nhóm "đọc-thuần" bị bắt đang ghi (sau `check-rejected-sales`), và cổng này ghi đúng thứ **đi vào báo cáo gửi cơ quan quản lý** | video 02 (02/08) | **02** Thông tin cơ sở · **09** Hoá đơn · **11** Báo cáo · và **mọi** lượt chạy `ui-gates.sh` | 🔴 cao — phải sửa trước khi quay bản chính thức |
| L-1 | **Phiếu nhập `PARTIALLY_RECEIVED` không đóng cũng không huỷ được** — `/close` và `/cancel` đều trả 422, lối ra duy nhất là nhận nốt. Nhà cung cấp giao thiếu rồi thôi ⇒ phiếu kẹt vĩnh viễn | tổng quan (02/08) | **05** Nhập hàng · **09** Hoá đơn/trả hàng · **11** Báo cáo | 🟠 nghiệp vụ — **cần Chain quyết** trước khi sửa |

## Đã đóng

*(chưa có)*

## Không phải lỗi — ghi để khỏi bị báo lại

| Hiện tượng | Vì sao đúng | Ghi ngày |
|---|---|---|
| `Thối lại: −6.000 đ` khi khách chưa đưa tiền | **Cố ý**, có chú thích ngay trong mã: *"thiếu tiền hiện số ÂM chứ không hiện 0 — thu ngân cần biết còn thiếu bao nhiêu, và một số 0 ở đây đọc y hệt 'vừa đủ'"* | 02/08 |
| Màn bán hàng trống hơn nửa màn sau khi tìm 1 kết quả | Trang ngắn thật — đã đo, không khối nào cao bất thường. Là chuyện **dàn cảnh**: dùng từ khoá ra 4–6 dòng | 02/08 |
| Nút "Xong" · "Xem giỏ" · "Tải CSV" màu đỏ | Đỏ là **màu hành động chính** của BERAS, nhất quán toàn ứng dụng | 02/08 |
| Video quay nhiều lượt để lại nhiều kho `QUAY-*` trùng tên | **Không phải lỗi sản phẩm** — bản quay tạo dữ liệu thật, quay hỏng giữa chừng thì để lại vết. Dọn bằng cách ngừng (`is_active=false`) các kho `QUAY-*` trước khi quay lại. Ảnh khung hình bắt được, không cổng nào thấy | 02/08 |
| Dòng ⚠️ *"Hoá đơn in ra chưa dùng thông tin ở đây"* trên màn Thông tin cơ sở | **Cố ý** — màn tự khai nợ N-1 (hoá đơn chưa đọc thông tin cơ sở). Đúng nguyên tắc "chỗ nào chưa chắc thì phần mềm tự nói ra". KHÔNG gỡ | 02/08 |
| 7 cổng trả `EXIT=2` khi chạy trên `qt650` | `2` = **chưa đo được**, không phải hỏng. CSDL mới chưa có khách/đơn thuốc/bút toán sổ để đo. Sẽ tự xanh dần khi video 04→10 dựng ra dữ liệu | 02/08 |
