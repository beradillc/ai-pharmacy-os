# Cân xứng: định dạng số · cửa sổ laptop · danh mục thuốc (P5, 2026-08-01)

Chain giao kèm lượt duyệt P5: cửa sổ laptop ở giữa và kéo được · danh mục thuốc mobile chật
chội · `1.0000` thừa · giá VND không `.00` · số lượng chẵn không `,0` · phải có `.` phân
cách ngàn/triệu theo quy ước Việt Nam.

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Giá trong giỏ hàng | `2200.00 đ × viên` | **`2.200 đ × viên`** |
| Ô nhập hoạt chất | `1.0000` | **`1`** |
| Ô nhập giá | `2200.00` | **`2200`** |
| Cửa sổ trên laptop | bám mép trên | **giữa màn**, kéo di chuyển được bằng thanh tiêu đề |
| Danh mục thuốc mobile | chữ **vỡ từng ký tự** — `Alaxa`/`n`/`Ibu`/`prof` | đọc bình thường |
| Nhãn thẻ | `Giá niêm yết2.200 đ` dính nhau, font đánh máy | tách bạch, font chữ |
| Cỡ chữ thân bài | mobile **7 cỡ**, laptop 6 | **6 cỡ, giống hệt nhau** |

## Bộ định dạng đã có sẵn — vấn đề là chỗ không dùng nó

`formatMoney` (chấm ngăn ngàn, không thập phân) và `formatQty` (bỏ 0 thừa) đã đúng quy ước
Việt Nam từ trước. Chín chỗ render số **thô** bằng `toLocaleString` hoặc chuỗi Decimal
nguyên. Đã dồn hết về bộ dùng chung.

Thêm `formatSo` cho **ô nhập**: bỏ 0 thừa nhưng **không** chấm ngăn ngàn. Khác `formatQty`
ở đúng điểm đó, và điểm đó quan trọng — giá trị trong ô nhập là thứ sẽ được **gửi lên máy
chủ**. Đưa `"1.500"` vào ô rồi bấm Lưu thì backend hiểu là *một phẩy năm*: sai 1000 lần, và
sai **im lặng**.

## 🔴 Ba lỗi thật, đều chỉ lộ ở khổ laptop hoặc chỉ trên ảnh

### 1. Ô nhập cao 260px — lần thứ BA cùng một bẫy

`flex: 0 1 260px` áp cho **mọi** `.input` ở `≥600px`. `flex-basis` đo theo **trục chính**
của hộp cha; trong hộp dọc (mọi khối `<label>` nhãn-trên-ô-dưới của dự án) `260px` trở thành
**chiều cao**.

`danh-muc-thuoc/page.module.css` đã ghi sẵn *"KHÔNG dùng flex-basis px trong hộp dọc — hai
lần đã sai vì thế"*. Hai lần trước sửa ở chỗ **dùng**; lần này sửa ở chỗ **khai** (thu hẹp
về `.controls .input`), nên nó không quay lại được nữa.

Cổng đột biến cho thấy nó đang ảnh hưởng **ba màn**, không chỉ màn phát hiện ra:
`/danh-muc-thuoc` · `/nhap-nhanh` · `/so-do-kho`.

### 2. Danh mục thuốc mobile — hai media query đá nhau

`@media (max-width: 640px)` đặt `table-layout: fixed` + `width: 42%/38%`; `@media (width <
720px)` đổi bảng thành **thẻ**. Ở 390px **cả hai cùng áp** ⇒ `td` vừa là `block` của thẻ vừa
mang `width: 42%` ⇒ cột giá trị co còn ~90px và chữ vỡ dọc.

Không cổng cũ nào bắt được: trang không cuộn ngang, không phần tử nào tràn khung nhìn,
`innerText` đọc **đủ chữ**. Cùng họ với ba ca kỷ luật #21 nhưng **khác cơ chế** — đây là chữ
**vỡ**, không phải chữ **bị cắt**, nên `boundingBox` cũng không thấy.

### 3. Font đánh máy lây sang nút và nhãn

`.ghost` dùng `font: inherit` ⇒ nút nằm trong một `td.num` (ô số, monospace) hiện chữ
"Sửa giá" bằng font đánh máy, lệch hẳn mọi nút khác cùng màn.

## ⚠️ Một quyết định cũ của Chain bị đổi

Bảng khách hàng để `font-size: 13px` ở khổ điện thoại — **Chain chốt 31/07**. Chỉ đạo mới
01/08 (*"kích thước chữ tương đồng nhau tại mọi cửa sổ"*) đè lên nó: `13px` là con số **duy
nhất trong toàn hệ** không thuộc thang chữ, và đo được — mobile 7 cỡ, laptop 6, cái thừa ra
đúng là nó. Đổi sang `--text-sm` (14px): giữ nguyên ý định *nhỏ hơn 15px* nhưng dùng bậc có
sẵn.

## Cổng mới `check-can-xung`

15 màn × 2 khổ, ba phép đo: ô nhập không cao quá 96px · ô chứa chữ không cao gấp >3 lần bề
rộng (chữ vỡ dọc) · số cỡ chữ thân bài. Cả ba sinh từ một lỗi thật đã xảy ra, không phải từ
lý thuyết.

## Ảnh

4 cảnh × 2 khổ (390×844 · 1440×900), `deviceScaleFactor: 2`.
