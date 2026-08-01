# Quầy thuốc 650 — bàn giao CSDL chạy thử (2026-08-01)

> Chain giao: xoá toàn bộ CSDL cũ, dựng **một** CSDL duy nhất cho Quầy thuốc 650 để chạy thử
> **một tuần tại quầy** và **làm video training**.

## Cơ sở

| | |
|---|---|
| Tên | **Quầy thuốc 650** |
| Địa chỉ | xã Thạnh Trị, tỉnh Vĩnh Long |
| Người phụ trách chuyên môn | **Dược sĩ Trần Thị Trinh Thư** — chủ quầy, hơn 10 năm kinh nghiệm |
| CSDL | `qt650` |
| Đăng nhập | `trinhthu@quaythuoc650.vn` · `QuayThuoc650@2026` — 🔴 **CẢI CHÍNH 01/08:** dòng này ban đầu ghi *"phần mềm bắt đổi mật khẩu ở lần đăng nhập đầu"*. **Sai.** UAT cùng ngày đo được: hệ thống đặt cờ *phải đổi* nhưng **không có màn để đổi** và **không chặn đăng nhập** — xem lỗi C-01 |
| Địa chỉ dùng trong quầy | `http://192.168.1.10:3000` (điện thoại/máy tính bảng cùng Wi-Fi) |

## Dữ liệu có gì

| Mục | Số lượng | Ghi chú |
|---|---|---|
| Thuốc | **70** | 25 kê đơn (ETC), 45 không kê đơn |
| Hoạt chất | **61** | nối cho **63/70** thuốc |
| Hoạt chất kiểm soát TT18 | **122** | danh mục tham chiếu, phục vụ báo cáo |
| Mã ATC · tương tác thuốc | 10 · 5 | bộ khởi đầu |
| Vai trò hệ thống | 5 | quản trị · dược sĩ chuỗi · dược sĩ chi nhánh · thu ngân · thủ kho |
| **Kho · tồn · khách hàng · đơn hàng · vị trí** | **0** | **cố ý trống** — xây trong quá trình thử |

Bảy mã **không có hoạt chất** là vật tư y tế (băng gạc, khẩu trang, nhiệt kế, găng tay, kim
tiêm, bông, băng keo). Màn Danh mục thuốc sẽ cảnh báo *"7 thuốc chưa có hoạt chất"* — **đó là
đúng**, không phải lỗi cần sửa.

## 🔴 Ba việc Chain phải làm trước khi bán đơn đầu tiên

### 1. Điền số điện thoại và mã số thuế

`backend/.env` có `ORG__PHONE=` và `ORG__TAX_CODE=` **để trống**. Hoá đơn in ra sẽ **bỏ hẳn
hai dòng đó**. Tôi không điền hộ vì không được bịa hai con số này.

### 2. Sửa giá bán theo giá nhập thật

70 mã đều có **giá tham khảo**. Để trống thì mỗi lần bán phần mềm lại hỏi giá — nên tôi đặt
sẵn. Nhưng chúng **không phải giá của quầy**: sửa ở màn *Danh mục thuốc → Sửa giá*.

Việc này cũng là **một cảnh video training tốt**: cho thấy giá niêm yết là quyết định cấp
chuỗi, và bán lệch giá thì phần mềm bắt ghi lý do vào sổ audit.

### 3. Tạo tài khoản thứ hai — nhân viên bán thuốc

Vào *Nhân viên → Thêm nhân viên*, chọn vai **Nhân viên bán thuốc / thu ngân**.

🔴 **Vì sao GĐ đề nghị việc này thay vì tự tạo hộ:** thu ngân **không có quyền `rx.approve`**
— ràng buộc pháp lý (Luật Dược Điều 6.5.h), không phải tuỳ chọn. Nghĩa là video training quay
được cảnh **thu ngân bán thuốc kê đơn thì bị chặn, phải nhờ dược sĩ duyệt** — đó vừa là điểm
mạnh nhất của phần mềm, vừa là điều một quầy thuốc cần chứng minh khi bị kiểm tra. Không có
tài khoản thứ hai thì không quay được cảnh đó.

Và việc **tự tạo tài khoản** cũng chính là một cảnh trong video.

## Sao lưu — bắt buộc trong tuần chạy thử

Đây là **dữ liệu bán hàng thật**, không phải demo.

```bash
docker exec -e PGPASSWORD=pharma ai_pharmacy_os-postgres-1 pg_dump -U pharma qt650 \
  > ~/beras-moc-khoi-phuc/qt650_$(date +%Y%m%d).sql
```

Chạy **cuối mỗi ngày bán**. Bảy ngày là bảy tệp, mỗi tệp vài trăm KB.

**Mốc khôi phục "quay lại đầu"** (kho trống như lúc bàn giao) đã có sẵn — dùng khi quay video
hỏng và muốn làm lại từ cảnh đầu. Xem `~/beras-moc-khoi-phuc/README.md`.

⚠️ Khôi phục mốc đó **xoá sạch mọi dữ liệu bán hàng đã nhập**. Trong tuần chạy thật, đừng
dùng trừ khi cố ý bỏ hết.

## GĐ đề xuất — thứ tự dựng dữ liệu cho video training

Thứ tự này cũng là thứ tự **dựng thật ở quầy**, nên quay một lần được cả hai:

| # | Cảnh | Màn | Vì sao trước |
|---|---|---|---|
| 1 | Đổi mật khẩu lần đầu | Đăng nhập | Bắt buộc, và là cảnh mở tự nhiên |
| 2 | Dựng sơ đồ kho: Kho → Kệ → Ô | Sơ đồ & Kiểm kê | Không có ô thì không cất hàng vào đâu |
| 3 | Khởi tạo tồn kho — đếm hàng đang có trên kệ | Nhập hàng → Khởi tạo tồn | Đây là bước quầy thật phải làm **một lần duy nhất** |
| 4 | Nhập hàng mới từ nhà cung cấp | Nhập hàng → Nhập nhanh | Khác bước 3: có hoá đơn nhập, có giá vốn |
| 5 | Bán một đơn thường (OTC) | Bán hàng | Cảnh ngắn, cho thấy quầy → tiền → hoá đơn |
| 6 | **Bán một đơn kê đơn** — chụp đơn, dược sĩ duyệt | Bán hàng | Cảnh **quan trọng nhất**: chứng minh phần mềm giữ đúng luật |
| 7 | Thu ngân thử bán ETC → **bị chặn** | Bán hàng (tài khoản thu ngân) | Cảnh chứng minh phân quyền có thật |
| 8 | Khách quay lại, cảnh báo dị ứng kêu | Bán hàng | Cần khai dị ứng cho khách ở bước trước |
| 9 | In hoá đơn khổ K80 | Hoá đơn → Xem → In | Nếu quầy có máy in nhiệt thì quay luôn tờ giấy thật |
| 10 | Kiểm kê một ô, có chênh lệch | Sơ đồ & Kiểm kê | Cho thấy chênh lệch **chờ duyệt**, không tự đụng tồn |

**Cảnh 6 và 7 là hai cảnh đáng quay nhất** — chúng là thứ phân biệt phần mềm này với một
cuốn sổ bán hàng.

## 🟠 Một cờ pháp lý GĐ phải nêu, không kết luận

Chain gọi cơ sở là **"Quầy thuốc"**. Theo Luật Dược, **quầy thuốc** và **nhà thuốc** là hai
loại hình cơ sở bán lẻ **khác nhau** — khác về trình độ người phụ trách chuyên môn và về
**phạm vi thuốc được bán**.

Danh mục tôi dựng có **25 mã kê đơn** (kháng sinh, tim mạch, tiểu đường…). Nếu phạm vi hành
nghề của Quầy thuốc 650 hẹp hơn nhà thuốc, một số mã trong đó **có thể không được phép bán**
tại quầy.

🔴 **Tôi KHÔNG kết luận** — đúng quy tắc R-10 (không kết luận phạm vi/nghĩa vụ từ một tầng
văn bản; phải đọc đủ Luật → Nghị định → Thông tư). Đây là **cờ để Chain cho Trợ lý Pháp Lý
rà**, trước khi tuần chạy thử phát sinh giao dịch thật.

Việc rà rẻ: xem Giấy chứng nhận đủ điều kiện kinh doanh dược của cơ sở ghi loại hình gì, rồi
đối chiếu danh mục 25 mã ETC. Sửa danh mục thì chỉ là đổi phân loại hoặc bỏ mã — vài phút.

## 🔴 Kết quả nghiệm thu UAT (2026-08-01) — đọc trước khi bán đơn đầu tiên

Đợt UAT chạy cùng ngày, **128 lượt đo** (16 màn × 4 khổ × 2 engine). Báo cáo đầy đủ ở
`docs/testing/`.

**Phần mềm ổn định:** 0 lỗi JavaScript · 0 màn cuộn ngang · 0 phần tử tràn khung nhìn.

**Nhưng có ba mục CHẶN, xếp theo mức độ:**

| # | Vấn đề | Ảnh hưởng tới quầy |
|---|---|---|
| **C-01** | **Không có màn đổi mật khẩu** — hệ thống đặt cờ *"phải đổi"* nhưng không có chỗ đổi, và không chặn đăng nhập | Dược sĩ Thư dùng **vĩnh viễn** mật khẩu kỹ thuật đặt. Mọi nhân viên tạo sau cũng vậy |
| **C-02** | **Không có màn Đổi trả** (backend đã có) | Khách trả thuốc ⇒ **không thao tác được** ⇒ tồn kho và doanh thu sai. Trong một tuần bán lẻ, gần như chắc chắn xảy ra |
| **C-03** | **Không có màn Sổ thuốc kiểm soát đặc biệt** (backend đã có, 122 hoạt chất đã nạp) | **Nghĩa vụ pháp lý TT18** không thực hiện được qua phần mềm |

Thêm **8 mục Major** — trong đó **không có màn Nhà cung cấp** khiến màn Đơn mua hàng hiện có
nhưng **dùng không được**.

⚠️ **Bảy nghiệp vụ thiếu màn đều ĐÃ CÓ BACKEND và đã có test.** Đây là khoảng cách **giao
diện**, không phải khoảng cách năng lực — loại việc rẻ nhất, và cũng dễ bị hoãn nhất vì nhìn
từ phía backend thì "đã xong rồi".

### Chạy thử được không?

**Được, có điều kiện.** Ba việc ở mục trên cộng thêm:

- Đổi mật khẩu **bằng tay qua kỹ thuật** cho tới khi có màn (C-01);
- **Ghi tay sổ đổi trả** trong tuần thử (C-02);
- **Chưa bán thuốc kiểm soát đặc biệt** qua phần mềm cho tới khi có màn (C-03).

Checklist đầy đủ: `docs/testing/06_CHECKLIST_NGHIEM_THU.md`.

### 🔴 Trước khi quay video

**Không quay trên CSDL này.** Mỗi lần quay lại cảnh bán hàng để lại một hoá đơn không có
khách; sau một buổi quay, doanh thu tuần sai và **không ai tách được đâu là đơn thật**. Dựng
`qt650_video` từ mốc sạch để quay.

## Lịch sử dữ liệu cũ

Toàn bộ 8 CSDL cũ (`nhathuoc650`, `nt650`, `nt650v2`, `pharmacy_os`, `pharmacy_os_demo`,
`pharmacy_os_restore_drill`, `pharmacy_os_test`, `beras_test`) **đã xoá** theo chỉ đạo, sau
khi sao lưu toàn cụm:

    ~/backup_truoc_khi_xoa_20260801_1406.sql   (5,8 MB, pg_dumpall)

Giữ tệp đó cho tới khi Chain xác nhận không cần tra lại gì từ dữ liệu cũ.
