# Lời thoại — video tổng quan (bản nháp `00_tong-quan_ban-nhap.mp4`)

> **Đây là thứ đang thiếu để video có tiếng.** Chain báo 2026-08-02: *"Có video demo, chưa có
> tiếng."* Máy không đọc được tiếng Việt ở mức giao khách — trên máy chỉ có `spd-say`, không
> có bộ đọc nào dùng được. Nên phần này **phải do người thu**.
>
> Bảng dưới là lời thoại đã **khớp sẵn mốc thời gian thật** của bản quay
> (`timeline.json`), nên người đọc không phải căn giờ — cứ đọc theo dòng.

## Cách dùng

1. **Thu tiếng theo bảng dưới**, mỗi đoạn một tệp: `00.wav`, `01.wav`, … `15.wav`.
   Hai giọng như quy ước: **NỮ** nói chính, **NAM** hỏi lại/tóm tắt.
2. Đo lại độ dài thật và sinh nhịp mới:
   ```
   for f in 0*.wav 1*.wav; do
     printf '"%s": %s,\n' "${f%.wav}" "$(ffprobe -v error -show_entries format=duration \
       -of default=nw=1:nk=1 "$f" | cut -d. -f1)"
   done
   ```
   Dán vào `durations.json`.
3. **Quay lại** — hình sẽ tự khớp giọng, vì `hold()` giữ màn theo đúng số giây đó:
   ```
   cd frontend && node scripts/lib/dung-du-lieu-quay.mjs
   BERAS_OUT=/tmp/quay BERAS_DURATIONS=/tmp/quay/durations.json node scripts/record-tutorial.mjs
   ```
4. Ghép tiếng vào hình bằng `ffmpeg` (nối 16 tệp theo thứ tự, chèn 0,7 giây lặng giữa mỗi đoạn
   — đúng `GAP_MS` mà script dùng).

🔴 **Nếu đọc xong thấy `⚠ tràn Xs`** trong log: thao tác dài hơn lời thoại. **Viết lại lời cho
dài ra**, đừng cắt thao tác — thao tác là thứ người xem cần nhìn.

## Lời thoại

| # | Mốc | Hình đang chiếu | Ai | Lời |
|---|---|---|---|---|
| 00 | 0:00 | bìa mở | — | *(nhạc nền, không lời)* |
| 01 | 0:09 | lời chào | **NỮ** | Chào chị. Video này đi trọn một vòng của Quầy thuốc 650 trong phần mềm: nhập hàng về, xếp vào kho, bán cho khách, in hoá đơn, rồi xem lại doanh thu. Khoảng ba phút. |
| 02 | 0:21 | màn đăng nhập | **NỮ** | Bắt đầu bằng đăng nhập. Mỗi người một tài khoản riêng — không dùng chung, vì phần mềm ghi lại ai làm việc gì. |
| 03 | 0:34 | màn tổng quan | **NAM** | Vào rồi thì thấy gì trước? · **NỮ** Màn tổng quan: hôm nay bán được bao nhiêu, hàng nào sắp hết, hàng nào cận hạn. Nhìn một cái là biết cần làm gì. |
| 04 | 0:46 | Đơn mua hàng → Nhận hàng | **NỮ** | Giờ có xe hàng về. Mình vào Đơn mua hàng, tìm đúng phiếu đã đặt, bấm **Nhận hàng**. |
| 05 | 0:59 | điền số lô + hạn dùng | **NỮ** | Với mỗi mặt hàng, mình nhập **số lượng thực nhận**, **số lô** và **hạn dùng** ghi trên hộp. Ba ô này là ba ô quan trọng nhất — về sau muốn truy một lô thuốc đi đâu thì dựa vào đây. |
| 06 | 1:12 | hạn gần ⇒ cảnh báo | **NAM** | Hàng cận hạn thì sao? · **NỮ** Phần mềm tự nhắc ngay khi mình gõ hạn dùng. Và nếu nhận thiếu so với đơn đặt, nó ghi là **nhận một phần** — phiếu vẫn để mở, hôm sau giao nốt thì nhận tiếp. |
| 07 | 1:24 | chốt phiếu | **NỮ** | Xong thì chốt phiếu. Tồn kho tăng lên ngay theo từng lô vừa nhập — mình không phải cộng tay chỗ nào cả. |
| 08 | 1:37 | màn tồn kho | **NỮ** | Qua Tồn kho kiểm lại. Gõ số lô là ra đúng lô vừa nhập, kèm hạn dùng và số lượng còn. |
| 09 | 1:50 | bán hàng: tìm thuốc | **NAM** | Giờ tới phần dùng nhiều nhất trong ngày. · **NỮ** Bán hàng. Gõ vài chữ đầu của tên thuốc là ra — không cần gõ đủ, không cần nhớ mã. |
| 10 | 2:04 | thêm vào giỏ | **NỮ** | Bấm **Thêm** là vào giỏ. |
| 11 | 2:16 | thêm hai loại nữa | **NỮ** | Thêm vài món nữa cho giống một đơn thật. Giỏ cộng tiền ngay ở thanh dưới cùng, khách hỏi bao nhiêu là trả lời được luôn. |
| 12 | 2:31 | xem giỏ → thanh toán 2 bước | **NỮ** | Trên điện thoại, giỏ thu gọn thành thanh dưới — bấm **Xem giỏ** để mở ra. Kiểm lại một lượt rồi bấm **Thanh toán**. · **NAM** Sao lại hỏi lại lần nữa? · **NỮ** Vì bước này trừ tồn kho và ghi doanh thu thật. Phần mềm cho mình đọc lại số tiền một lần trước khi chốt — bấm lần thứ hai mới xong. |
| 13 | 2:45 | màn hoá đơn | **NỮ** | Đơn vừa bán nằm ngay đầu danh sách Hoá đơn. Mở ra in được khổ giấy nhỏ của máy in nhiệt. |
| 14 | 2:57 | màn báo cáo | **NAM** | Cuối ngày muốn xem lại thì vào đâu? · **NỮ** Báo cáo. Chọn khoảng ngày, xem doanh thu, tải file mở bằng Excel đưa cho kế toán. |
| 15 | 3:09 | bìa kết | **NAM** | Vậy là trọn một vòng: nhập hàng, tồn kho, bán hàng, hoá đơn, báo cáo. · **NỮ** Từng phần có video riêng nói kỹ hơn. Chị cứ làm thử trên máy, sai cũng không sao — dữ liệu thử tách riêng với dữ liệu thật. |

## Ghi chú cho người đọc

- **Đọc chậm hơn bình thường một nhịp.** Người xem vừa nghe vừa nhìn tay mình bấm; đọc tốc độ
  hội thoại là họ mất một trong hai.
- **Đoạn 03 · 06 · 09 · 12 · 15 có hai giọng.** Câu của NAM là câu người mới thật sự sẽ hỏi —
  đọc như đang hỏi thật, đừng đọc như đang dẫn chương trình.
- **Không thêm câu nào về quy định, văn bản, hay cơ quan quản lý** — xem mục *Nguyên tắc nội
  dung* cuối `05_KICH_BAN_VIDEO.md`. Bản lời thoại này đã viết theo đúng lằn ranh đó: chỗ nào
  cũng chỉ nói **phần mềm làm gì**.
- Nhịp hiện tại (7–14 giây/đoạn) là **ước lượng của máy**, không phải đo. Đọc thử một lượt là
  biết chỗ nào hụt chỗ nào thừa — sửa lời ở bảng trên rồi mới thu.
