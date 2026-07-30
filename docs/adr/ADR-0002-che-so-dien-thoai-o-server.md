# ADR-0002 · Che số điện thoại khách ở server — đổi NGỮ NGHĨA hợp đồng API có chủ ý

- **Ngày:** 2026-07-31
- **Trạng thái:** Đã áp dụng (`2628d3b`)
- **Người quyết:** Chain (CEO) — yêu cầu trực tiếp

## 🔴 Đây là một thay đổi phá vỡ tương thích, và nó được duyệt có chủ ý

Chính sách 31/07 ghi *"✗ tạo Breaking Change"* và *"API cũ hoạt động"*. Cần nói rõ ADR này
đứng ở đâu so với hai câu đó:

| | Trước | Sau |
|---|---|---|
| Đường dẫn, phương thức, mã trạng thái | không đổi | **không đổi** |
| Hình dạng phản hồi | `phone: string \| null` | **không đổi** |
| **Giá trị** của `phone` | `"0357205494"` | `"*494"` |

Hợp đồng **hình dạng** giữ nguyên; hợp đồng **ngữ nghĩa** đổi. Bên gọi nào đang dùng
`phone` từ `GET /customers` để nhắn tin hay gọi điện sẽ hỏng, và hỏng **im lặng** — không
có mã lỗi nào, chỉ là một số sai.

Đã rà: bên gọi duy nhất là frontend trong repo này (3 chỗ), đã cập nhật cùng commit. Không
có bên thứ ba. Nếu về sau có API công khai, thay đổi kiểu này phải đi kèm phiên bản.

**Vì sao vẫn làm:** đây là biện pháp bảo vệ dữ liệu cá nhân do CEO yêu cầu. Giữ nguyên
hành vi cũ để "không phá vỡ tương thích" nghĩa là tiếp tục phát số điện thoại đầy đủ của
khách cho mọi vai ở quầy — cái giá đó lớn hơn.

## Vì sao che ở SERVER, không ở giao diện

Che ở giao diện là **trang trí**: số đầy đủ vẫn nằm trong phản hồi HTTP, mở tab Network là
đọc được. Nó không chặn được ai — chỉ làm người viết mã tưởng là đã chặn.

Phép che đặt ở `CustomerOutput.of(reveal_phone=False)`, **mặc định là che**. Một đường đọc
mới quên truyền cờ thì hỏng về phía an toàn, không lặng lẽ rò số.

## Đường mở lộ

`GET /customers/{id}/phone` — tài nguyên **riêng**, không phải một trường của
`CustomerResponse`. Nhờ vậy số đầy đủ chỉ đi qua dây khi có người **chủ động hỏi**, và mỗi
lần hỏi là một dòng `CUSTOMER_PHONE_REVEALED`. Là một trường thì mọi lượt tải danh sách đều
mang theo nó và việc "che" chỉ còn là trang trí.

Quyền `crm.pii.reveal` **riêng**, chỉ `system_admin` + `chain_pharmacist`. Không gộp vào
`crm.sensitive.read`: quyền đó là dữ liệu **sức khoẻ** và dược sĩ chi nhánh cũng giữ — gộp
vào thì câu "chỉ Chủ chuỗi xem được" sai ngay.

## Định dạng: một dấu sao

`*494`, không phải `*******494`. Ngắn hơn trong bảng hẹp, và tình cờ lộ ít hơn: dãy sao dài
đúng bằng phần bị che sẽ nói luôn số dài bao nhiêu.

## Hệ quả

- ✅ Không migration, không mất dữ liệu — cột CSDL không đổi, chỉ đổi cái đọc ra.
- ✅ Đảo ngược được bằng `git revert`: không có thay đổi lược đồ nào phải quay lui.
- ⚠️ Tra khách theo số điện thoại vẫn chạy (che chỉ đổi cái ĐỌC RA, không đổi cái tra vào),
  nhưng **lọc tại chỗ theo số** ở frontend nay chỉ khớp được ba chữ số cuối.
- 🔴 Che mà không ghi vết là vô nghĩa: khi số khách rò ra ngoài, câu hỏi là *"ai đã lấy"*.
  Đó là lý do đường mở lộ bắt buộc ghi audit.
