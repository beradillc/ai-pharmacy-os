# Lời thoại — VIDEO 09: Hoá đơn · In · Ghi nhận trả hàng

> Khớp 6 đoạn của `frontend/scripts/record-v09.mjs`. Giọng chuẩn: `scripts/giong-he-thong.json`.

## Lời thoại

| # | Mốc | Hình đang chiếu | Ai | Lời |
|---|---|---|---|---|
| 00 | 0:00 | bìa mở | — | *(nhạc mở đầu ~3 giây, không lời)* |
| 00b | 0:03 | bìa mở | **NỮ** | Video này hướng dẫn xem lại hoá đơn đã bán, in lại khi khách cần, và ghi nhận khi khách trả hàng. |
| 01 | | màn Hoá đơn | **NỮ** | Đây là màn Hoá đơn. Mọi đơn đã bán đều nằm ở đây, mới nhất lên đầu, nên đơn vừa bán xong chị thấy ngay dòng trên cùng. |
| 02 | | lọc theo ngày | **NỮ** | Muốn xem lại một khoảng thời gian thì chị chọn từ ngày đến ngày, hoặc bấm Hôm nay cho nhanh. Cuối ca mà cần đối chiếu tiền mặt thì đây là chỗ chị mở. |
| 03 | | mở chi tiết hoá đơn | **NỮ** | Bấm Xem là mở chi tiết đơn đó ra: bán những gì, số lượng bao nhiêu, thành tiền bao nhiêu, ai là người bán. Có nút in ngay trong này, đúng khổ giấy nhỏ của máy in nhiệt, nên khách quay lại xin hoá đơn thì chị in lại được. |
| 04 | | nút Ghi nhận trả hàng | **NỮ** | Còn đây là nút ghi nhận trả hàng, dùng khi khách mang thuốc trở lại. Trong cửa sổ chi tiết, mỗi dòng thuốc có nút Trả lại riêng, vì khách mua năm món mà trả một món là chuyện thường. Ghi nhận trả hàng sẽ làm giảm doanh thu của đơn đó. Nhưng có một điều chị cần nhớ: thuốc khách trả KHÔNG tự động quay lại kho. Phần mềm cố ý làm vậy, vì thuốc trả về phải được dược sĩ xem tình trạng trước đã, rồi mới quyết định có nhập lại bán tiếp hay không. Trong video này mình chỉ chỉ chỗ thôi, không bấm, vì mỗi lần bấm là một phiếu trả thật nằm lại trong sổ. |
| 05 | | bìa kết | **NỮ** | Tóm lại, hoá đơn là nơi chị tra lại mọi thứ đã bán, in lại khi cần, và ghi nhận hàng trả. Video kế tiếp mình sẽ kiểm kê, tức là đếm lại hàng thật trên kệ rồi so với sổ. |

## Ghi chú

- **Không nói câu nào về quy định, văn bản hay cơ quan quản lý.**
- Đoạn 04 nói rõ **vì sao video không bấm nút trả hàng** — thẳng thắn hơn là lặng lẽ bỏ qua,
  và nó cũng dạy người xem rằng nút đó có hậu quả thật.
- 🔴 **Bản đầu của đoạn 04 tôi viết SAI**: *"phần mềm sẽ cộng lại tồn kho"*. Đọc mã mới thấy
  chú thích ngay tại chỗ: ghi nhận trả hàng **KHÔNG** tự đưa thuốc về kho — đó là quyết định
  riêng sau khi dược sĩ kiểm tình trạng. Chú thích còn ghi rằng **bản đầu của chính hộp thoại
  ấy** từng hứa *"hàng sẽ quay lại kho"* và đã bị sửa vì SAI, đo được bằng SQL
  (`returned_quantity=1` có ghi, `stock_movements` không có dòng nào).
  Suýt nữa video đi ra ngoài lặp lại đúng lời hứa sai mà sản phẩm đã sửa xong.
