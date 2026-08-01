# ⛔ CHỜ PHÁP LÝ — kịch bản màn Sổ thuốc kiểm soát đặc biệt

> **KHÔNG QUAY.** Tài liệu này **không** thuộc bộ kịch bản `05_KICH_BAN_VIDEO.md`.
>
> **Chain chốt 2026-08-01:** *"Cái nào nhạy cảm, pháp lý thì bỏ ra khỏi kịch bản."*

---

## Vì sao tách hẳn ra chứ không sửa cho nhẹ đi

Ba video khác cũng từng có câu chữ pháp lý, và với chúng thì **bỏ câu chữ là đủ** — phần còn
lại vẫn là hướng dẫn bấm nút bình thường.

Màn Sổ kiểm soát đặc biệt thì khác: **bỏ phần pháp lý ra thì không còn video nào cả.** Lý do
tồn tại của màn đó là một nghĩa vụ theo quy định; hướng dẫn *"bấm nút này rồi bấm nút kia"* mà
không nói vì sao thì người xem không biết khi nào phải dùng, và đó là loại hướng dẫn tệ hơn
không có.

Cộng thêm một lý do độc lập: **màn đó hiện một nhãn đỏ *"Chưa được rà pháp lý"*** — do chính
GĐ đặt làm điều kiện khi Chain gác phần pháp lý lại (`PROJECT_STATE` §7dg quyết định 8). Quay
một màn tự khai là chưa được rà, rồi phát video ấy cho người dùng, là biến một ảnh chụp thành
một lời cam kết tuân thủ **mà không ai đứng sau**.

---

## Điều kiện để tài liệu này quay lại bộ kịch bản

| # | Điều kiện | Ai |
|---|---|---|
| 1 | Rà soát đối chiếu màn hình với văn bản gốc, kết luận thành văn | **Trợ lý Pháp Lý** |
| 2 | Nhãn đỏ trên màn được gỡ **vì đã rà xong**, không phải vì bị xoá | Trợ lý Code, sau (1) |
| 3 | Chain duyệt lại nội dung nói trước máy quay | Chain |

🔴 **Không đủ ba điều kiện thì không quay**, kể cả khi tới hạn bàn giao. Một video hướng dẫn
sai về nghĩa vụ tuân thủ gây thiệt hại lớn hơn nhiều so với việc thiếu một video.

---

## Phần thao tác thuần tuý — dùng được ngay, không cần chờ

Nếu cần hướng dẫn người dùng **thao tác** trên màn này trước khi có video, dùng ba câu sau
trong tài liệu bàn giao (không quay thành video, không phát ra ngoài):

- Chọn **Mẫu sổ**, chọn **Từ ngày / Đến ngày** để xem các bút toán trong kỳ.
- **Kết xuất sổ (CSV)** tải cả kỳ; **Kết xuất cuối ngày** tải đúng một ngày.
- **Ký xác nhận sổ ngày** cần nhập lại mật khẩu, và **ký rồi thì không sửa được ngày đó nữa**.

Ba câu trên chỉ mô tả phần mềm làm gì. Chúng **không** nói khi nào bắt buộc phải làm — đó là
phần chờ (1).

---

## Bản nháp kịch bản đã viết (giữ lại, KHÔNG dùng)

Nội dung dưới đây viết ngày 2026-08-01 trước khi Chain ra chỉ đạo. Giữ nguyên để sau khi rà
pháp lý xong thì có cái sửa tiếp, thay vì viết lại từ đầu.

⚠️ **Mọi câu trích dẫn văn bản trong bản nháp này CHƯA ĐƯỢC KIỂM CHỨNG** — chúng chép lại từ
chú thích trong mã nguồn, không phải từ việc đọc văn bản gốc. Đó chính là thứ điều kiện (1)
phải làm.

<details>
<summary>Mở bản nháp</summary>

Xem `git show 765a927 -- docs/testing/05_KICH_BAN_VIDEO.md` — mục *VIDEO 14*.

Tóm tắt cấu trúc đã dựng, để người sửa tiếp biết có sẵn gì:

| Cảnh | Nội dung | Còn dùng được sau khi rà? |
|---|---|---|
| 1 | Mở đầu | ✅ khung dựng lại được |
| 2 | Đọc nhãn đỏ cùng người xem | ❓ tuỳ nhãn còn hay đã gỡ |
| 3 | Chọn mẫu sổ, đọc các cột, giải thích cột *Còn lại* | ✅ phần thao tác dùng được |
| 4 | Kết xuất + nghĩa vụ in hằng ngày | 🔴 **phải rà lại toàn bộ** |
| 5 | Ký xác nhận sổ ngày | ✅ phần thao tác · 🔴 phần "vì sao" phải rà |
| 6 | Lỗi thường gặp | ✅ |
| 7 | Tóm tắt | 🔴 viết lại sau khi rà |

</details>
